"""Set-based extraction metrics. Pure functions with no I/O.

Identification items are distinct ``(case_id, skill)`` pairs; exact-label items are distinct
``(case_id, skill, requirement_type)`` tuples. A skill identified with the wrong category is an
identification TP but an exact-label FP *and* FN. Undefined ratios (zero denominators) are
``None``, including F1 when TP = FP = FN = 0.
"""

from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from services.ingestion.extraction.skills import STRENGTH, RequirementType

REQUIREMENT_TYPES: tuple[RequirementType, ...] = ("required", "preferred", "mentioned")

Expected = Mapping[str, Mapping[str, RequirementType]]
Predicted = Mapping[str, Sequence[tuple[str, RequirementType]]]


def ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


@dataclass(frozen=True)
class Counts:
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float | None:
        return ratio(self.tp, self.tp + self.fp)

    @property
    def recall(self) -> float | None:
        return ratio(self.tp, self.tp + self.fn)

    @property
    def f1(self) -> float | None:
        return ratio(2 * self.tp, 2 * self.tp + self.fp + self.fn)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


def score[T: Hashable](expected: Iterable[T], predicted: Iterable[T]) -> Counts:
    gold, guess = set(expected), set(predicted)
    return Counts(tp=len(gold & guess), fp=len(guess - gold), fn=len(gold - guess))


def _strongest(labels: Iterable[RequirementType]) -> RequirementType:
    return max(labels, key=lambda label: STRENGTH[label])


def evaluate(expected: Expected, predicted: Predicted, skills: Sequence[str]) -> dict[str, Any]:
    """Compute aggregate, per-skill, and per-category metrics plus a category confusion matrix.

    ``expected`` holds one label per skill per case. ``predicted`` may contain duplicates; they
    are collapsed to distinct items and counted in ``duplicate_predictions``. ``skills`` lists the
    taxonomy keys reported per skill, in order; skills seen only in data are appended.
    """
    case_ids = sorted(set(expected) | set(predicted))
    gold_pairs = {(case, skill) for case in case_ids for skill in expected.get(case, {})}
    gold_labels = {
        (case, skill, label) for case in case_ids for skill, label in expected.get(case, {}).items()
    }
    entries = [
        (case, skill, label) for case in case_ids for skill, label in predicted.get(case, ())
    ]
    guess_labels = set(entries)
    guess_pairs = {(case, skill) for case, skill, _ in guess_labels}

    identification = score(gold_pairs, guess_pairs)
    exact = score(gold_labels, guess_labels)

    # Confusion over identification TPs; a skill predicted with several categories counts as
    # its strongest, matching the extractor's deduplication semantics.
    predicted_category = {
        pair: _strongest(label for case, skill, label in guess_labels if (case, skill) == pair)
        for pair in gold_pairs & guess_pairs
    }
    confusion = {row: dict.fromkeys(REQUIREMENT_TYPES, 0) for row in REQUIREMENT_TYPES}
    for (case, skill), label in predicted_category.items():
        confusion[expected[case][skill]][label] += 1

    ordered = list(skills) + sorted({skill for _, skill in gold_pairs | guess_pairs} - set(skills))
    per_skill = {}
    for name in ordered:
        per_skill[name] = {
            "support": sum(1 for _, skill in gold_pairs if skill == name),
            "identification": score(
                (item for item in gold_pairs if item[1] == name),
                (item for item in guess_pairs if item[1] == name),
            ).as_dict(),
            "exact_label": score(
                (item for item in gold_labels if item[1] == name),
                (item for item in guess_labels if item[1] == name),
            ).as_dict(),
        }
    per_category = {
        category: {
            "support": sum(1 for item in gold_labels if item[2] == category),
            **score(
                (item for item in gold_labels if item[2] == category),
                (item for item in guess_labels if item[2] == category),
            ).as_dict(),
        }
        for category in REQUIREMENT_TYPES
    }
    return {
        "counts": {
            "cases": len(case_ids),
            "expected_labels": len(gold_labels),
            "predicted_labels": len(guess_labels),
            "duplicate_predictions": len(entries) - len(guess_labels),
        },
        "identification": identification.as_dict(),
        "exact_label": exact.as_dict(),
        "per_skill": per_skill,
        "per_category": per_category,
        "category_confusion": {
            "rows": "expected",
            "columns": "predicted",
            "scope": "identification true positives only",
            "matrix": confusion,
            "missed_skills": identification.fn,
            "spurious_skills": identification.fp,
        },
    }
