import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from services.ingestion.curriculum.cli import load_manifest
from services.ingestion.curriculum.manifest import CurriculumManifest, validate_manifest

MANIFEST_PATH = Path(__file__).parents[1] / "curriculum" / "manifest_test.json"


def manifest_payload() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_synthetic_manifest_is_valid_and_has_only_explicit_requirements() -> None:
    manifest = load_manifest(MANIFEST_PATH)

    assert manifest.source.is_synthetic is True
    assert {item.requirement_type for item in manifest.program_courses} == {
        "required",
        "choice_group",
        "concentration",
        "elective",
    }
    assert all(item.evidence_excerpt for item in manifest.course_skills)
    assert all(item.evidence_url for item in manifest.course_skills)


# --------------------------------------------------------------------------
# tests
def test_models_forbid_unknown_fields() -> None:
    payload = manifest_payload()
    payload["unexpected"] = "not accepted"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CurriculumManifest.model_validate(payload)


# injecting duplicate courses
@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda payload: payload["courses"].append(payload["courses"][0]),
            "Duplicate course code",
        ),
        (
            lambda payload: payload["programs"].append(payload["programs"][0]),
            "Duplicate program slug",
        ),
        (
            lambda payload: payload["program_courses"].append(payload["program_courses"][0]),
            "Duplicate program-course requirement",
        ),
        (
            lambda payload: payload["course_skills"].append(payload["course_skills"][0]),
            "Duplicate course-skill evidence",
        ),
    ],
)
def test_duplicate_identities_and_relationships_are_rejected(mutate: Any, message: str) -> None:
    payload = manifest_payload()
    mutate(payload)
    manifest = CurriculumManifest.model_validate(payload)

    with pytest.raises(ValueError, match=message):
        validate_manifest(manifest)


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    [
        ("program_courses", "program_slug", "unknown-program", "Unknown program"),
        ("program_courses", "course_code", "UNKNOWN101", "Unknown course"),
        ("course_skills", "course_code", "UNKNOWN101", "Unknown course"),
    ],
)
def test_relationships_must_reference_declared_records(
    section: str, field: str, value: str, message: str
) -> None:
    payload = manifest_payload()
    payload[section][0][field] = value
    manifest = CurriculumManifest.model_validate(payload)

    with pytest.raises(ValueError, match=message):
        validate_manifest(manifest)


def test_catalog_years_must_agree() -> None:
    payload = manifest_payload()
    payload["courses"][0]["catalog_year"] = "2025/26"

    with pytest.raises(ValidationError, match="catalog_year must match the manifest"):
        CurriculumManifest.model_validate(payload)


def test_choice_group_relationship_requires_group_name() -> None:
    payload = manifest_payload()
    payload["program_courses"][1].pop("choice_group")

    with pytest.raises(ValidationError, match="require a choice_group identifier"):
        CurriculumManifest.model_validate(payload)


def test_evidence_url_and_excerpt_are_required() -> None:
    payload = manifest_payload()
    payload["course_skills"][0].pop("evidence_url")

    with pytest.raises(ValidationError):
        CurriculumManifest.model_validate(payload)

    payload = manifest_payload()
    payload["course_skills"][0]["evidence_excerpt"] = "  "
    with pytest.raises(ValidationError, match="must not be blank"):
        CurriculumManifest.model_validate(payload)


def test_naive_source_check_timestamp_is_rejected() -> None:
    payload = manifest_payload()
    payload["source"]["last_checked_at"] = "2026-11-01T10:00:00"

    with pytest.raises(ValidationError, match="must include a timezone"):
        CurriculumManifest.model_validate(payload)


def test_cli_manifest_loader_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON at line"):
        load_manifest(path)
