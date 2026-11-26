"""Metric definitions checked against hand-calculated examples."""

from typing import Any

import pytest

from services.ingestion.extraction.evaluation.metrics import Counts, evaluate

SKILLS = ["python", "sql", "docker"]


def metrics(expected: dict[str, Any], predicted: dict[str, Any]) -> dict[str, Any]:
    return evaluate(expected, predicted, SKILLS)


def block(tp: int, fp: int, fn: int, p: Any, r: Any, f1: Any) -> dict[str, Any]:
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f1}


def test_perfect_predictions() -> None:
    result = metrics(
        {"c1": {"python": "required", "sql": "preferred"}},
        {"c1": [("python", "required"), ("sql", "preferred")]},
    )
    assert result["identification"] == block(2, 0, 0, 1.0, 1.0, 1.0)
    assert result["exact_label"] == block(2, 0, 0, 1.0, 1.0, 1.0)


def test_extra_skill_is_a_false_positive() -> None:
    result = metrics(
        {"c1": {"python": "required"}},
        {"c1": [("python", "required"), ("docker", "mentioned")]},
    )
    # P = 1/2, R = 1/1, F1 = 2*1 / (2*1 + 1 + 0) = 2/3.
    assert result["identification"] == block(1, 1, 0, 0.5, 1.0, pytest.approx(2 / 3))
    assert result["exact_label"] == block(1, 1, 0, 0.5, 1.0, pytest.approx(2 / 3))
    assert result["category_confusion"]["spurious_skills"] == 1


def test_missed_skill_is_a_false_negative() -> None:
    result = metrics(
        {"c1": {"python": "required", "sql": "required"}}, {"c1": [("sql", "required")]}
    )
    assert result["identification"] == block(1, 0, 1, 1.0, 0.5, pytest.approx(2 / 3))
    assert result["category_confusion"]["missed_skills"] == 1


def test_wrong_category_is_identification_tp_but_exact_fp_and_fn() -> None:
    result = metrics({"c1": {"python": "required"}}, {"c1": [("python", "preferred")]})
    assert result["identification"] == block(1, 0, 0, 1.0, 1.0, 1.0)
    assert result["exact_label"] == block(0, 1, 1, 0.0, 0.0, 0.0)
    assert result["category_confusion"]["matrix"]["required"] == {
        "required": 0,
        "preferred": 1,
        "mentioned": 0,
    }
    assert result["per_category"]["required"]["fn"] == 1
    assert result["per_category"]["preferred"]["fp"] == 1


def test_duplicate_predictions_count_once() -> None:
    result = metrics(
        {"c1": {"python": "required"}},
        {"c1": [("python", "required"), ("python", "required")]},
    )
    assert result["identification"] == block(1, 0, 0, 1.0, 1.0, 1.0)
    assert result["exact_label"] == block(1, 0, 0, 1.0, 1.0, 1.0)
    assert result["counts"]["duplicate_predictions"] == 1


def test_conflicting_duplicate_categories_use_strongest_for_confusion() -> None:
    result = metrics(
        {"c1": {"python": "required"}},
        {"c1": [("python", "mentioned"), ("python", "required")]},
    )
    assert result["identification"] == block(1, 0, 0, 1.0, 1.0, 1.0)
    # Two distinct tuples: one matches, one is spurious.
    assert result["exact_label"] == block(1, 1, 0, 0.5, 1.0, pytest.approx(2 / 3))
    assert result["category_confusion"]["matrix"]["required"]["required"] == 1


def test_no_predictions_has_undefined_precision() -> None:
    result = metrics({"c1": {"python": "required"}}, {"c1": []})
    assert result["identification"] == block(0, 0, 1, None, 0.0, 0.0)


def test_no_expected_skill_has_undefined_recall() -> None:
    result = metrics({"c1": {}}, {"c1": [("docker", "mentioned")]})
    assert result["identification"] == block(0, 1, 0, 0.0, None, 0.0)


def test_empty_sets_are_entirely_undefined() -> None:
    result = metrics({"c1": {}}, {"c1": []})
    assert result["identification"] == block(0, 0, 0, None, None, None)
    assert result["exact_label"] == block(0, 0, 0, None, None, None)
    assert result["per_skill"]["python"]["identification"]["f1"] is None
    assert result["per_category"]["required"] == {"support": 0, **block(0, 0, 0, None, None, None)}


def test_pairs_are_distinct_per_case_and_per_skill_metrics_have_support() -> None:
    expected = {
        "c1": {"python": "required", "sql": "required"},
        "c2": {"python": "preferred"},
        "c3": {"docker": "mentioned"},
    }
    predicted = {
        "c1": [("python", "required"), ("sql", "mentioned")],
        "c2": [],
        "c3": [("docker", "mentioned"), ("python", "mentioned")],
    }
    result = metrics(expected, predicted)
    # Pairs: TP {c1 python, c1 sql, c3 docker}; FP {c3 python}; FN {c2 python}.
    assert result["identification"] == block(3, 1, 1, 0.75, 0.75, 0.75)
    # Tuples: TP {c1 python req, c3 docker men}; FP {c1 sql men, c3 python men};
    # FN {c1 sql req, c2 python pref}.
    assert result["exact_label"] == block(2, 2, 2, 0.5, 0.5, 0.5)
    python = result["per_skill"]["python"]
    assert python["support"] == 2
    assert python["identification"] == block(1, 1, 1, 0.5, 0.5, 0.5)
    assert result["per_skill"]["sql"]["exact_label"] == block(0, 1, 1, 0.0, 0.0, 0.0)
    assert result["per_category"]["required"] == {
        "support": 2,
        **block(1, 0, 1, 1.0, 0.5, pytest.approx(2 / 3)),
    }
    assert result["per_category"]["mentioned"] == {
        "support": 1,
        **block(1, 2, 0, pytest.approx(1 / 3), 1.0, 0.5),
    }
    assert result["per_category"]["preferred"] == {
        "support": 1,
        **block(0, 0, 1, None, 0.0, 0.0),
    }
    assert result["category_confusion"]["matrix"] == {
        "required": {"required": 1, "preferred": 0, "mentioned": 1},
        "preferred": {"required": 0, "preferred": 0, "mentioned": 0},
        "mentioned": {"required": 0, "preferred": 0, "mentioned": 1},
    }


def test_skills_outside_the_reported_list_are_appended_in_order() -> None:
    result = evaluate({"c1": {}}, {"c1": [("zeta", "mentioned"), ("alpha", "mentioned")]}, ["sql"])
    assert list(result["per_skill"]) == ["sql", "alpha", "zeta"]


def test_counts_ratios() -> None:
    assert Counts(0, 0, 0).f1 is None
    assert Counts(1, 1, 1).f1 == 0.5
