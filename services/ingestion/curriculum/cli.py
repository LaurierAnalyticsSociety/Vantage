from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID

import psycopg  #import for postgre-connection
from psycopg.rows import dict_row
from pydantic import ValidationError

from services.common.settings import Settings, require_database_url
from services.ingestion.curriculum.manifest import (
    Course,
    CourseSkill,
    CurriculumManifest,
    CurriculumSource,
    Program,
    validate_manifest,
)


#----------------------------------------------------------------------------
@dataclass(frozen=True)
class ImportPlan:
    source_created: bool
    programs_created: int
    programs_existing: int
    programs_updated: int
    courses_created: int
    courses_existing: int
    courses_updated: int
    relationships_created: int
    relationships_existing: int
    relationships_updated: int
    evidence_created: int
    evidence_unchanged: int
    evidence_reset_to_pending: int

#Load Curriculum Manifest from manifest.py
def load_manifest(path: Path) -> CurriculumManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Manifest file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    except OSError as error:
        raise ValueError(f"Could not read manifest {path}: {error}") from error

    manifest = CurriculumManifest.model_validate(payload)
    validate_manifest(manifest)
    return manifest

# Reads the first matching row from source
def _source_row(connection: psycopg.Connection, source: CurriculumSource) -> dict | None:
    return connection.execute(
        """select id, source_type, catalog_year, title, is_synthetic, last_checked_at
        from vantage.curriculum_sources where source_url = %s""",
        (str(source.source_url),),
    ).fetchone()

# Validates that 1 row and compares with CurriculumSource
def _validate_source(source: CurriculumSource, row: dict) -> None:
    expected = {
        "source_type": source.source_type,
        "catalog_year": source.catalog_year,
        "title": source.title,
        "is_synthetic": source.is_synthetic,
    }
    conflicts = [
        key for key, value in expected.items() if row[key] != value
    ]
    if conflicts:
        raise ValueError(
            f"Source URL already exists with conflicting {', '.join(conflicts)}; "
            "use the original provenance or a distinct source URL."
        )

# checks for duplicate programs in Program
# checks for mismatched program slug
# checks whether program matches source_id
def _existing_program(
    connection: psycopg.Connection, program: Program, source_id: UUID | None
) -> dict | None:
    rows = connection.execute(
        """select id, source_id, slug, institution, name, degree_type, description
        from vantage.programs
        where lower(slug) = %s and catalog_year = %s""",
        (program.slug, program.catalog_year),
    ).fetchall()
    if len(rows) > 1:
        raise ValueError(
            f"Multiple existing programs match {program.slug!r} in {program.catalog_year}."
        )
    row = rows[0] if rows else None
    if row is not None and row["slug"] != program.slug:
        raise ValueError(
            f"Program slug {program.slug!r} collides with existing non-canonical "
            f"identity {row['slug']!r}; resolve the existing record before import."
        )
    if row is not None and (source_id is None or row["source_id"] != source_id):
        raise ValueError(
            f"Program {program.slug!r} in {program.catalog_year} has different "
            "source provenance; refusing to reclassify it."
        )
    return row

# checks for duplicate courses in Course
# checks for mismatched copurse code
# checks whether course matches source_id
def _existing_course(
    connection: psycopg.Connection, course: Course, source_id: UUID | None
) -> dict | None:
    rows = connection.execute(
        """select id, source_id, code, title, description from vantage.courses
        where upper(code) = %s and catalog_year = %s""",
        (course.code, course.catalog_year),
    ).fetchall()
    if len(rows) > 1:
        raise ValueError(
            f"Multiple existing courses match {course.code!r} in {course.catalog_year}."
        )
    row = rows[0] if rows else None
    if row is not None and row["code"] != course.code:
        raise ValueError(
            f"Course code {course.code!r} collides with existing non-canonical "
            f"identity {row['code']!r}; resolve the existing record before import."
        )
    if row is not None and (source_id is None or row["source_id"] != source_id):
        raise ValueError(
            f"Course {course.code!r} in {course.catalog_year} has different "
            "source provenance; refusing to reclassify it."
        )
    return row

#-----------------------------------------------------------------------
def build_import_plan(
    connection: psycopg.Connection, manifest: CurriculumManifest
) -> ImportPlan:

    validate_manifest(manifest)
    source_row = _source_row(connection, manifest.source)
    if source_row is not None:
        _validate_source(manifest.source, source_row)
        source_id = source_row["id"]
    else:
        source_id = None

    #checks for unknown skills in db
    requested_skills = sorted({item.skill_slug for item in manifest.course_skills})
    skill_rows = connection.execute(
        "select id, slug from vantage.skills where slug = any(%s)",
        (requested_skills,),
    ).fetchall()
    skills = {row["slug"]: row["id"] for row in skill_rows}
    unknown_skills = sorted(set(requested_skills) - set(skills))
    if unknown_skills:
        raise ValueError(
            "Unknown canonical skill slug(s): "
            + ", ".join(unknown_skills)
            + ". Add them through the reviewed skill-taxonomy process first."
        )
    
    #fn calls
    programs = {
        program.slug: _existing_program(connection, program, source_id)
        for program in manifest.programs
    }
    courses = {
        course.code: _existing_course(connection, course, source_id)
        for course in manifest.courses
    }

    relationships_created = 0
    relationships_updated = 0
    for relationship in manifest.program_courses:
        program_row = programs[relationship.program_slug]
        course_row = courses[relationship.course_code]
        if program_row is None or course_row is None:
            relationships_created += 1
            continue
        existing = connection.execute(
            """select requirement_type, choice_group, suggested_year, notes
            from vantage.program_courses
            where program_id = %s and course_id = %s""",
            (program_row["id"], course_row["id"]),
        ).fetchone()
        if existing is None:
            relationships_created += 1
        elif (
            existing["requirement_type"] != relationship.requirement_type
            or existing["choice_group"] != relationship.choice_group
            or existing["suggested_year"] != relationship.suggested_year
            or existing["notes"] != relationship.notes
        ):
            relationships_updated += 1

    evidence_created = 0
    evidence_unchanged = 0
    evidence_reset = 0
    for item in manifest.course_skills:
        course_row = courses[item.course_code]
        if course_row is None:
            evidence_created += 1
            continue
        existing = connection.execute(
            """select coverage_level, evidence_excerpt, evidence_url, extraction_method
            from vantage.course_skills where course_id = %s and skill_id = %s""",
            (course_row["id"], skills[item.skill_slug]),
        ).fetchone()
        if existing is None:
            evidence_created += 1
        elif _evidence_matches(existing, item):
            evidence_unchanged += 1
        else:
            evidence_reset += 1

    programs_updated = 0
    for program in manifest.programs:
        row = programs[program.slug]
        if row is not None and (
            row["institution"] != program.institution
            or row["name"] != program.name
            or row["degree_type"] != program.degree_type
            or row["description"] != program.description
        ):
            programs_updated += 1

    courses_updated = 0
    for course in manifest.courses:
        row = courses[course.code]
        if row is not None and (
            row["title"] != course.title or row["description"] != course.description
        ):
            courses_updated += 1

    #Import stats returned
    return ImportPlan(
        source_created=source_row is None,
        programs_created=sum(row is None for row in programs.values()),
        programs_existing=sum(row is not None for row in programs.values()),
        programs_updated=programs_updated,
        courses_created=sum(row is None for row in courses.values()),
        courses_existing=sum(row is not None for row in courses.values()),
        courses_updated=courses_updated,
        relationships_created=relationships_created,
        relationships_existing=len(manifest.program_courses) - relationships_created,
        relationships_updated=relationships_updated,
        evidence_created=evidence_created,
        evidence_unchanged=evidence_unchanged,
        evidence_reset_to_pending=evidence_reset,
    )


def _evidence_matches(existing: dict, evidence: CourseSkill) -> bool:
    return (
        existing["coverage_level"] == evidence.coverage_level
        and existing["evidence_excerpt"] == evidence.evidence_excerpt
        and existing["evidence_url"] == str(evidence.evidence_url)
        and existing["extraction_method"] == evidence.extraction_method
    )

#insert source
def _upsert_source(
    connection: psycopg.Connection, source: CurriculumSource
) -> UUID:
    inserted = connection.execute(
        """insert into vantage.curriculum_sources
        (source_url, source_type, catalog_year, title, is_synthetic, last_checked_at)
        values (%s, %s, %s, %s, %s, %s)
        on conflict (source_url) do update set
            last_checked_at = case
                when excluded.last_checked_at is null
                    then curriculum_sources.last_checked_at
                when curriculum_sources.last_checked_at is null
                    then excluded.last_checked_at
                else greatest(curriculum_sources.last_checked_at, excluded.last_checked_at)
            end
        where curriculum_sources.source_type = excluded.source_type
          and curriculum_sources.catalog_year = excluded.catalog_year
          and curriculum_sources.title is not distinct from excluded.title
          and curriculum_sources.is_synthetic = excluded.is_synthetic
        returning id""",
        (
            str(source.source_url),
            source.source_type,
            source.catalog_year,
            source.title,
            source.is_synthetic,
            source.last_checked_at,
        ),
    ).fetchone()
    if inserted is not None:
        return inserted["id"]

    existing = connection.execute(
        """select id, source_type, catalog_year, title, is_synthetic
        from vantage.curriculum_sources where source_url = %s for update""",
        (str(source.source_url),),
    ).fetchone()
    if existing is None:
        raise ValueError("Curriculum source disappeared during import; retry the operation.")
    _validate_source(source, existing)
    return existing["id"]

#insert program
def _upsert_program(
    connection: psycopg.Connection, program: Program, source_id: UUID
) -> UUID:
    row = connection.execute(
        """insert into vantage.programs
        (institution, name, slug, degree_type, catalog_year, source_id, description)
        values (%s, %s, %s, %s, %s, %s, %s)
        on conflict (slug, catalog_year) do update set
            institution = excluded.institution,
            name = excluded.name,
            degree_type = excluded.degree_type,
            description = excluded.description
        where programs.source_id = excluded.source_id
        returning id""",
        (
            program.institution,
            program.name,
            program.slug,
            program.degree_type,
            program.catalog_year,
            source_id,
            program.description,
        ),
    ).fetchone()
    if row is None:
        raise ValueError(
            f"Program {program.slug!r} has conflicting source provenance; import aborted."
        )
    return row["id"]

#inserts course
def _upsert_course(
    connection: psycopg.Connection, course: Course, source_id: UUID
) -> UUID:
    row = connection.execute(
        """insert into vantage.courses
        (code, title, catalog_year, description, source_id)
        values (%s, %s, %s, %s, %s)
        on conflict (code, catalog_year) do update set
            title = excluded.title,
            description = excluded.description
        where courses.source_id = excluded.source_id
        returning id""",
        (course.code, course.title, course.catalog_year, course.description, source_id),
    ).fetchone()
    if row is None:
        raise ValueError(
            f"Course {course.code!r} has conflicting source provenance; import aborted."
        )
    return row["id"]

#-------------------------------------------------------------------
#create table records
def import_manifest(
    connection: psycopg.Connection, manifest: CurriculumManifest
) -> ImportPlan:
    with connection.transaction():
        plan = build_import_plan(connection, manifest)
        source_id = _upsert_source(connection, manifest.source)
        program_ids = {
            program.slug: _upsert_program(connection, program, source_id)
            for program in manifest.programs
        }
        course_ids = {
            course.code: _upsert_course(connection, course, source_id)
            for course in manifest.courses
        }

        for relationship in manifest.program_courses:
            connection.execute(
                """insert into vantage.program_courses
                (program_id, course_id, requirement_type, choice_group, suggested_year, notes)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (program_id, course_id) do update set
                    requirement_type = excluded.requirement_type,
                    choice_group = excluded.choice_group,
                    suggested_year = excluded.suggested_year,
                    notes = excluded.notes""",
                (
                    program_ids[relationship.program_slug],
                    course_ids[relationship.course_code],
                    relationship.requirement_type,
                    relationship.choice_group,
                    relationship.suggested_year,
                    relationship.notes,
                ),
            )

        skill_rows = connection.execute(
            "select id, slug from vantage.skills where slug = any(%s)",
            (sorted({item.skill_slug for item in manifest.course_skills}),),
        ).fetchall()
        skill_ids = {row["slug"]: row["id"] for row in skill_rows}
        for evidence in manifest.course_skills:
            connection.execute(
                """insert into vantage.course_skills
                (course_id, skill_id, coverage_level, evidence_excerpt, evidence_url,
                 verification_status, extraction_method, verified_at)
                values (%s, %s, %s, %s, %s, 'pending', %s, null)
                on conflict (course_id, skill_id) do update set
                    coverage_level = excluded.coverage_level,
                    evidence_excerpt = excluded.evidence_excerpt,
                    evidence_url = excluded.evidence_url,
                    verification_status = 'pending',
                    extraction_method = excluded.extraction_method,
                    verified_at = null
                where course_skills.coverage_level is distinct from excluded.coverage_level
                   or course_skills.evidence_excerpt is distinct from excluded.evidence_excerpt
                   or course_skills.evidence_url is distinct from excluded.evidence_url
                   or course_skills.extraction_method is distinct from 
                   excluded.extraction_method""",
                (
                    course_ids[evidence.course_code],
                    skill_ids[evidence.skill_slug],
                    evidence.coverage_level,
                    evidence.evidence_excerpt,
                    str(evidence.evidence_url),
                    evidence.extraction_method,
                ),
            )
    return plan


def review_evidence(
    connection: psycopg.Connection,
    *,
    course_code: str,
    catalog_year: str,
    skill_slug: str,
    status: str,
) -> dict:
    if status not in {"verified", "rejected"}:
        raise ValueError("Review status must be 'verified' or 'rejected'.")
    with connection.transaction():
        course_rows = connection.execute(
            """select id from vantage.courses
            where upper(code) = %s and catalog_year = %s""",
            (course_code.strip().upper(), catalog_year),
        ).fetchall()
        if len(course_rows) != 1:
            raise ValueError(
                f"Expected one course {course_code!r} in {catalog_year}; found "
                f"{len(course_rows)}."
            )
        skill = connection.execute(
            "select id from vantage.skills where slug = %s",
            (skill_slug.strip().lower(),),
        ).fetchone()
        if skill is None:
            raise ValueError(f"Unknown canonical skill slug: {skill_slug}.")
        row = connection.execute(
            """update vantage.course_skills set
                verification_status = %s,
                verified_at = case when %s = 'verified' then now() else null end
            where course_id = %s and skill_id = %s
            returning verification_status, verified_at""",
            (status, status, course_rows[0]["id"], skill["id"]),
        ).fetchone()
        if row is None:
            raise ValueError(
                f"No evidence assertion exists for {course_code.strip().upper()} "
                f"/ {catalog_year} / {skill_slug.strip().lower()}."
            )
        return row

#set migration db url
def _admin_connection() -> psycopg.Connection:
    settings = Settings()
    url = require_database_url(settings.migration_database_url)
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=10)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate, preview, import, and review curriculum manifests."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "dry-run", "import"):
        subparser = commands.add_parser(command)
        subparser.add_argument("manifest", type=Path)
    review = commands.add_parser("review")
    review.add_argument("--course-code", required=True)
    review.add_argument("--catalog-year", required=True)
    review.add_argument("--skill-slug", required=True)
    review.add_argument("--status", choices=("verified", "rejected"), required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        with _admin_connection() as connection:
            if arguments.command == "review":
                result = review_evidence(
                    connection,
                    course_code=arguments.course_code,
                    catalog_year=arguments.catalog_year,
                    skill_slug=arguments.skill_slug,
                    status=arguments.status,
                )
                print(
                    f"{arguments.course_code.strip().upper()} / {arguments.catalog_year} / "
                    f"{arguments.skill_slug.strip().lower()}: {result['verification_status']}"
                )
                return 0

            manifest = load_manifest(arguments.manifest)
            if arguments.command == "import":
                plan = import_manifest(connection, manifest)
            else:
                plan = build_import_plan(connection, manifest)
            if arguments.command == "validate":
                print("Manifest and database references are valid.")
                return 0

            if arguments.command == "dry-run":
                print("Import plan (no writes performed):")
            else:
                print("Import complete:")
            print(json.dumps(asdict(plan), indent=2, sort_keys=True))
            return 0
    except (OSError, ValueError, ValidationError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except psycopg.Error:
        print(
            "ERROR: Curriculum database operation failed. Check the administrative "
            "database configuration, schema, and permissions.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
