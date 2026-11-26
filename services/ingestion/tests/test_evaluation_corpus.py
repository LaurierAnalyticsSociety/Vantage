"""Benchmark validation, the committed corpus, and its freeze record."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from services.ingestion.extraction.evaluation.corpus import (
    BENCHMARK_DIR,
    BenchmarkError,
    fingerprint,
    load_benchmark,
    parse_split,
    parse_taxonomy,
)
from services.ingestion.tests.benchmark_helpers import (
    case_data,
    split_data,
    taxonomy_data,
    write_benchmark,
)

Mutation = Callable[[dict[str, Any]], None]


def valid_split() -> dict[str, Any]:
    return split_data(
        "development", [case_data("t-1", "Python is required.", {"python": "required"})]
    )


def test_valid_inputs_load() -> None:
    taxonomy = parse_taxonomy(taxonomy_data())
    split = parse_split(valid_split(), taxonomy, "development", "development.json")
    assert taxonomy.keys == ("python", "sql", "docker")
    assert split.cases[0].expected == (("python", "required"),)
    assert split.fingerprint == fingerprint(valid_split())


@pytest.mark.parametrize(
    ("skills", "message"),
    [
        (
            [
                {"key": "javascript", "name": "JavaScript", "aliases": ["JS"]},
                {"key": "jscript", "name": "JScript", "aliases": ["js"]},
            ],
            r"skills\[1\]\.aliases\[0\]: alias 'js' .* already belongs to skill 'javascript'",
        ),
        (
            [
                {"key": "python", "name": "Python", "aliases": []},
                {"key": "python", "name": "Python 3", "aliases": []},
            ],
            r"skills\[1\]\.key: duplicate skill key 'python'",
        ),
        (
            [
                {"key": "python", "name": "Python", "aliases": []},
                {"key": "py", "name": "python", "aliases": []},
            ],
            r"skills\[1\]\.name: skill name 'python' is already used by 'python'",
        ),
        ([{"key": "Python", "name": "Python", "aliases": []}], r"must be lowercase"),
        ([{"key": "python", "name": "Python", "aliases": ["  "]}], r"aliases\[0\]: must not be"),
        ([], r"skills: must contain at least one skill"),
    ],
)
def test_invalid_taxonomies_are_rejected(skills: list[dict[str, Any]], message: str) -> None:
    with pytest.raises(BenchmarkError, match=message):
        parse_taxonomy(taxonomy_data(skills))


def test_taxonomy_requires_synthetic_marker_and_known_fields() -> None:
    data = taxonomy_data()
    data["synthetic"] = False
    with pytest.raises(BenchmarkError, match="synthetic: must be true"):
        parse_taxonomy(data)
    data = taxonomy_data()
    data["uuid"] = "x"
    with pytest.raises(BenchmarkError, match=r"unknown field\(s\): uuid"):
        parse_taxonomy(data)


def _set(path: list[str | int], value: object) -> Mutation:
    def mutate(data: dict[str, Any]) -> None:
        target: Any = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


def _delete(path: list[str | int]) -> Mutation:
    def mutate(data: dict[str, Any]) -> None:
        target: Any = data
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return mutate


def _duplicate_case(data: dict[str, Any]) -> None:
    data["cases"].append(dict(data["cases"][0]))


def _duplicate_label(data: dict[str, Any]) -> None:
    data["cases"][0]["expected"].append({"skill": "python", "requirement_type": "mentioned"})


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (_duplicate_case, r"cases\[1\]\.id: duplicate case ID 't-1'"),
        (
            _set(["cases", 0, "expected", 0, "skill"], "pyhton"),
            r"\(t-1\)\.expected\[0\]\.skill: unknown skill key 'pyhton'; add it to taxonomy",
        ),
        (
            _set(["cases", 0, "expected", 0, "requirement_type"], "optional"),
            r"invalid category \"optional\"; use one of: required, preferred, mentioned",
        ),
        (_duplicate_label, r"skill 'python' is labeled more than once"),
        (_set(["cases", 0, "synthetic"], False), r"\(t-1\)\.synthetic: must be true"),
        (_set(["provenance", "synthetic"], False), r"provenance\.synthetic: must be true"),
        (_set(["split"], "heldout"), r"split: must be \"development\", found \"heldout\""),
        (_set(["taxonomy_version"], "other"), r"does not match taxonomy\.json version"),
        (_set(["format_version"], 2), r"format_version: must be 1, found 2"),
        (_set(["format_version"], True), r"format_version: must be 1, found true"),
        (_delete(["cases", 0, "description"]), r"missing required field\(s\): description"),
        (_set(["cases", 0, "description"], None), r"description: expected a string"),
        (_set(["cases", 0, "confidence"], 1), r"unknown field\(s\): confidence"),
        (_set(["cases"], {}), r"cases: expected an array, found dict"),
    ],
)
def test_invalid_splits_are_rejected(mutate: Mutation, message: str) -> None:
    data = valid_split()
    mutate(data)
    with pytest.raises(BenchmarkError, match=message):
        parse_split(data, parse_taxonomy(taxonomy_data()), "development", "development.json")


def test_empty_description_is_valid() -> None:
    data = split_data("development", [case_data("t-1", "", {})])
    split = parse_split(data, parse_taxonomy(taxonomy_data()), "development", "development.json")
    assert split.cases[0].expected == ()


def test_case_ids_must_be_unique_across_splits(tmp_path: Path) -> None:
    case = case_data("shared-1", "SQL.", {"sql": "mentioned"})
    write_benchmark(tmp_path, [case], [case])
    with pytest.raises(BenchmarkError, match="also appears in development.json"):
        load_benchmark(tmp_path)


def test_malformed_json_reports_its_location(tmp_path: Path) -> None:
    write_benchmark(tmp_path, [])
    (tmp_path / "heldout.json").write_text('{"cases": [}', encoding="utf-8")
    with pytest.raises(BenchmarkError, match=r"heldout\.json: invalid JSON at line 1, column 12"):
        load_benchmark(tmp_path)


def test_missing_files_and_directories_are_reported(tmp_path: Path) -> None:
    with pytest.raises(BenchmarkError, match="benchmark directory not found"):
        load_benchmark(tmp_path / "absent")
    write_benchmark(tmp_path, [])
    (tmp_path / "taxonomy.json").unlink()
    with pytest.raises(BenchmarkError, match=r"taxonomy\.json: file not found"):
        load_benchmark(tmp_path)


def test_fingerprint_ignores_formatting() -> None:
    data = valid_split()
    assert fingerprint(data) == fingerprint(json.loads(json.dumps(data, indent=4)))
    changed = valid_split()
    changed["cases"][0]["expected"][0]["requirement_type"] = "preferred"
    assert fingerprint(changed) != fingerprint(data)


# ---- The committed benchmark ----

REQUIRED_COVERAGE = {
    "boundaries",
    "technical-identifiers",
    "ambiguous-tokens",
    "negation",
    "headings-bullets",
    "mixed-cues",
    "repeated-mentions",
    "punctuation",
    "empty-skill-free",
}


def test_committed_benchmark_shape() -> None:
    benchmark = load_benchmark()
    development, heldout = benchmark.splits["development"], benchmark.splits["heldout"]
    assert len(development.cases) == 40
    assert len(heldout.cases) == 20
    cases = development.cases + heldout.cases
    structured = [c for c in cases if {"multi-line", "multi-sentence"} & set(c.tags)]
    assert len(structured) >= 15
    for split in (development, heldout):
        tags = {tag for case in split.cases for tag in case.tags}
        assert REQUIRED_COVERAGE <= tags, split.split
        assert any(not case.expected for case in split.cases)
        assert any(case.expected for case in split.cases)


def test_committed_benchmark_matches_latest_freeze_entry() -> None:
    benchmark = load_benchmark()
    freeze = json.loads((BENCHMARK_DIR / "FREEZE.json").read_text(encoding="utf-8"))
    entry = freeze["entries"][-1]
    assert entry["corpus_version"] == benchmark.splits["development"].corpus_version
    assert entry["taxonomy"] == {
        "version": benchmark.taxonomy.version,
        "fingerprint": benchmark.taxonomy.fingerprint,
    }
    for name, split in benchmark.splits.items():
        frozen = entry["splits"][name]
        assert frozen["fingerprint"] == split.fingerprint, f"{name} labels changed after freeze"
        assert frozen["case_ids"] == [case.id for case in split.cases]
