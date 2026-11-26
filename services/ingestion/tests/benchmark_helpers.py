"""Builders for small, isolated benchmark inputs used by evaluator tests."""

import copy
import json
from pathlib import Path
from typing import Any


def taxonomy_data(skills: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "format": "vantage-skill-taxonomy",
        "format_version": 1,
        "taxonomy_version": "test-tax",
        "synthetic": True,
        "skills": skills
        if skills is not None
        else [
            {"key": "python", "name": "Python", "aliases": ["Python 3"]},
            {"key": "sql", "name": "SQL", "aliases": []},
            {"key": "docker", "name": "Docker", "aliases": []},
        ],
    }


def case_data(case_id: str, description: str, expected: dict[str, str]) -> dict[str, Any]:
    return {
        "id": case_id,
        "synthetic": True,
        "provenance": "test",
        "tags": [],
        "description": description,
        "expected": [
            {"skill": skill, "requirement_type": label} for skill, label in expected.items()
        ],
    }


def split_data(split: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "format": "vantage-skill-benchmark",
        "format_version": 1,
        "corpus_version": "test-1",
        "split": split,
        "taxonomy_version": "test-tax",
        "provenance": {"synthetic": True, "method": "test"},
        "cases": copy.deepcopy(cases),
    }


def write_benchmark(
    directory: Path,
    development: list[dict[str, Any]],
    heldout: list[dict[str, Any]] | None = None,
    taxonomy: dict[str, Any] | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "taxonomy.json": taxonomy or taxonomy_data(),
        "development.json": split_data("development", development),
        "heldout.json": split_data("heldout", heldout or []),
    }
    for name, content in files.items():
        (directory / name).write_text(json.dumps(content), encoding="utf-8")
    return directory
