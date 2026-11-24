import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from services.common.database import get_connection
from services.ingestion.curriculum.cli import (
    build_import_plan,
    import_manifest,
    review_evidence,
)
from services.ingestion.curriculum.manifest import CurriculumManifest

if TYPE_CHECKING:
    from services.common.database import DatabaseConnection

pytestmark = pytest.mark.database
MANIFEST_PATH = Path(__file__).parents[2] / "ingestion" / "curriculum" / "manifest_test.json"


def example_manifest() -> CurriculumManifest:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    suffix = uuid4().hex[:10]
    payload["source"]["source_url"] = (
        f"https://example.org/vantage/curriculum-cli-tests/{suffix}/calendar"
    )
    for program in payload["programs"]:
        program["slug"] = f"{program['slug']}-{suffix}"
    for course in payload["courses"]:
        course["code"] = f"{course['code']}{suffix.upper()}"
    for relationship in payload["program_courses"]:
        relationship["program_slug"] = f"{relationship['program_slug']}-{suffix}"
        relationship["course_code"] = f"{relationship['course_code']}{suffix.upper()}"
    for evidence in payload["course_skills"]:
        evidence["course_code"] = f"{evidence['course_code']}{suffix.upper()}"
        evidence["evidence_url"] = (
            f"https://example.org/vantage/curriculum-cli-tests/{suffix}/"
            f"courses/{evidence['course_code']}"
        )
    return CurriculumManifest.model_validate(payload)


def manifest_for_year(
    manifest: CurriculumManifest, year: str, source_url: str
) -> CurriculumManifest:
    payload: dict[str, Any] = manifest.model_dump(mode="json")
    payload["catalog_year"] = year
    payload["source"]["catalog_year"] = year
    payload["source"]["source_url"] = source_url
    for program in payload["programs"]:
        program["catalog_year"] = year
    for course in payload["courses"]:
        course["catalog_year"] = year
    return CurriculumManifest.model_validate(payload)


def evidence_row(
    database: "DatabaseConnection", course_code: str, skill_slug: str
) -> dict[str, Any]:
    row = database.execute(
        """select cs.verification_status, cs.verified_at, cs.evidence_excerpt
        from vantage.course_skills cs
        join vantage.courses c on c.id = cs.course_id
        join vantage.skills s on s.id = cs.skill_id
        where c.code = %s and c.catalog_year = %s and s.slug = %s""",
        (course_code, "2026/27", skill_slug),
    ).fetchone()
    assert row is not None
    return row


def test_import_is_repeatable_and_keeps_all_requirement_types(
    database: "DatabaseConnection",
) -> None:
    manifest = example_manifest()
    program_slug = manifest.programs[0].slug
    course_codes = [course.code for course in manifest.courses]

    first = import_manifest(database, manifest)
    second = import_manifest(database, manifest)

    assert first.source_created is True
    assert first.programs_created == 1
    assert first.courses_created == 5
    assert first.relationships_created == 5
    assert first.evidence_created == 5
    assert second.source_created is False
    assert second.programs_created == 0
    assert second.programs_updated == 0
    assert second.courses_created == 0
    assert second.courses_updated == 0
    assert second.relationships_created == 0
    assert second.evidence_created == 0
    assert second.evidence_unchanged == 5
    assert second.relationships_updated == 0

    source = database.execute(
        """select is_synthetic from vantage.curriculum_sources
        where source_url = %s""",
        (str(manifest.source.source_url),),
    ).fetchone()
    assert source is not None
    assert source["is_synthetic"] is True

    relationships = database.execute(
        """select pc.requirement_type, pc.choice_group, count(*) as count
        from vantage.program_courses pc
        join vantage.programs p on p.id = pc.program_id
        where p.slug = %s and p.catalog_year = '2026/27'
        group by pc.requirement_type, pc.choice_group""",
        (program_slug,),
    ).fetchall()
    assert {row["requirement_type"] for row in relationships} == {
        "required",
        "choice_group",
        "concentration",
        "elective",
    }
    assert sum(row["count"] for row in relationships) == 5
    assert all(
        row["verification_status"] == "pending"
        for row in [
            evidence_row(database, course_codes[0], "python"),
            evidence_row(database, course_codes[1], "sql"),
            evidence_row(database, course_codes[2], "sql"),
            evidence_row(database, course_codes[3], "python"),
            evidence_row(database, course_codes[4], "sql"),
        ]
    )


def test_unknown_skill_is_rejected_before_any_import_writes(
    database: "DatabaseConnection",
) -> None:
    payload = example_manifest().model_dump(mode="json")
    payload["course_skills"][0]["skill_slug"] = "not-in-the-taxonomy"
    manifest = CurriculumManifest.model_validate(payload)

    with pytest.raises(ValueError, match="Unknown canonical skill slug"):
        import_manifest(database, manifest)

    source = database.execute(
        "select 1 from vantage.curriculum_sources where source_url = %s",
        (str(manifest.source.source_url),),
    ).fetchone()
    program = database.execute(
        """select 1 from vantage.programs
        where slug = %s and catalog_year = '2026/27'""",
        (manifest.programs[0].slug,),
    ).fetchone()
    assert source is None
    assert program is None


def test_dry_run_plan_reports_creates_without_persisting_records(
    database: "DatabaseConnection",
) -> None:
    manifest = example_manifest()
    plan = build_import_plan(database, manifest)

    assert plan.source_created is True
    assert plan.programs_created == 1
    assert plan.courses_created == 5
    assert plan.relationships_created == 5
    assert plan.evidence_created == 5
    source = database.execute(
        """select 1 from vantage.curriculum_sources
        where source_url = %s""",
        (str(manifest.source.source_url),),
    ).fetchone()
    assert source is None


def test_database_failure_rolls_back_the_entire_import(
    database: "DatabaseConnection",
) -> None:
    database.execute(
        """create function pg_temp.fail_curriculum_course_insert() returns trigger
        language plpgsql as $$
        begin
            raise exception 'intentional curriculum import test failure';
        end;
        $$"""
    )
    database.execute(
        """create trigger fail_curriculum_course_insert
        before insert on vantage.courses
        for each row execute function pg_temp.fail_curriculum_course_insert()"""
    )

    manifest = example_manifest()
    with pytest.raises(psycopg.Error, match="intentional curriculum import test failure"):
        import_manifest(database, manifest)

    source = database.execute(
        """select 1 from vantage.curriculum_sources
        where source_url = %s""",
        (str(manifest.source.source_url),),
    ).fetchone()
    program = database.execute(
        """select 1 from vantage.programs
        where slug = %s and catalog_year = '2026/27'""",
        (manifest.programs[0].slug,),
    ).fetchone()
    assert source is None
    assert program is None


def test_changed_evidence_requires_review_and_unchanged_evidence_preserves_it(
    database: "DatabaseConnection",
) -> None:
    manifest = example_manifest()
    course_code = manifest.courses[0].code
    import_manifest(database, manifest)

    verified = review_evidence(
        database,
        course_code=course_code,
        catalog_year="2026/27",
        skill_slug="python",
        status="verified",
    )
    original_timestamp = verified["verified_at"]
    assert original_timestamp is not None

    import_manifest(database, manifest)
    unchanged = evidence_row(database, course_code, "python")
    assert unchanged["verification_status"] == "verified"
    assert unchanged["verified_at"] == original_timestamp

    payload = manifest.model_dump(mode="json")
    payload["course_skills"][0]["evidence_excerpt"] = (
        "Changed synthetic evidence requires a new review."
    )
    changed_manifest = CurriculumManifest.model_validate(payload)
    changed_plan = import_manifest(database, changed_manifest)
    changed = evidence_row(database, course_code, "python")
    assert changed_plan.evidence_reset_to_pending == 1
    assert changed["verification_status"] == "pending"
    assert changed["verified_at"] is None

    review_evidence(
        database,
        course_code=course_code,
        catalog_year="2026/27",
        skill_slug="python",
        status="rejected",
    )
    import_manifest(database, changed_manifest)
    rejected = evidence_row(database, course_code, "python")
    assert rejected["verification_status"] == "rejected"
    assert rejected["verified_at"] is None


def test_conflicting_source_provenance_is_rejected(
    database: "DatabaseConnection",
) -> None:
    manifest = example_manifest()
    import_manifest(database, manifest)

    payload = manifest.model_dump(mode="json")
    payload["source"]["title"] = "Different source identity"
    conflicting = CurriculumManifest.model_validate(payload)

    with pytest.raises(ValueError, match="conflicting title"):
        import_manifest(database, conflicting)

    source = database.execute(
        """select title from vantage.curriculum_sources
        where source_url = %s""",
        (str(manifest.source.source_url),),
    ).fetchone()
    assert source is not None
    assert source["title"] == manifest.source.title

    payload = manifest.model_dump(mode="json")
    payload["source"]["is_synthetic"] = False
    marker_conflict = CurriculumManifest.model_validate(payload)
    with pytest.raises(ValueError, match="conflicting is_synthetic"):
        import_manifest(database, marker_conflict)


def test_catalog_years_import_as_distinct_programs_and_courses(
    database: "DatabaseConnection",
) -> None:
    manifest = example_manifest()
    import_manifest(
        database,
        manifest_for_year(manifest, "2026/27", "https://example.org/calendar/26"),
    )
    import_manifest(
        database,
        manifest_for_year(manifest, "2027/28", "https://example.org/calendar/27"),
    )

    programs = database.execute(
        """select catalog_year from vantage.programs
        where slug = %s order by catalog_year""",
        (manifest.programs[0].slug,),
    ).fetchall()
    courses = database.execute(
        """select catalog_year from vantage.courses
        where code = %s order by catalog_year""",
        (manifest.courses[0].code,),
    ).fetchall()
    assert [row["catalog_year"] for row in programs] == ["2026/27", "2027/28"]
    assert [row["catalog_year"] for row in courses] == ["2026/27", "2027/28"]


def test_verified_required_evidence_is_visible_in_program_skills_api(
    database: "DatabaseConnection",
) -> None:
    from services.api.app.main import create_app
    from services.common.settings import Settings

    manifest = example_manifest()
    course_codes = [course.code for course in manifest.courses]
    import_manifest(database, manifest)
    program = database.execute(
        """select id from vantage.programs
        where slug = %s and catalog_year = '2026/27'""",
        (manifest.programs[0].slug,),
    ).fetchone()
    assert program is not None
    app = create_app(Settings.model_construct(database_url=SecretStr(""), app_env="test"))
    app.dependency_overrides[get_connection] = lambda: database

    with TestClient(app) as client:
        base_url = f"/api/v1/programs/{program['id']}"
        pending_response = client.get(f"{base_url}/skills")
        assert pending_response.status_code == 200
        assert pending_response.json() == []

        review_evidence(
            database,
            course_code=course_codes[0],
            catalog_year="2026/27",
            skill_slug="python",
            status="rejected",
        )
        rejected_response = client.get(f"{base_url}/skills")
        assert rejected_response.json() == []

        for course_code, skill_slug in [
            (course_codes[0], "python"),
            (course_codes[1], "sql"),
            (course_codes[2], "sql"),
            (course_codes[3], "python"),
            (course_codes[4], "sql"),
        ]:
            review_evidence(
                database,
                course_code=course_code,
                catalog_year="2026/27",
                skill_slug=skill_slug,
                status="verified",
            )
        program_response = client.get(base_url)
        response = client.get(f"{base_url}/skills")

    assert response.status_code == 200
    assert program_response.json()["is_synthetic"] is True
    skills = response.json()
    assert [skill["name"] for skill in skills] == ["Python"]
    assert [course["code"] for course in skills[0]["supporting_courses"]] == [course_codes[0]]
