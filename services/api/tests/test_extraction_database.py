from collections.abc import Iterator
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from services.ingestion.contracts.raw_job import RawJob

if TYPE_CHECKING:
    from services.common.database import DatabaseConnection
    from services.ingestion.extraction import ExtractedSkill, Taxonomy

pytestmark = pytest.mark.database

EXPECTED = {
    "Data Analyst Intern": {("SQL", "required"), ("Python", "required"), ("Excel", "preferred")},
    "Junior Reporting Analyst": {("SQL", "required"), ("Excel", "required")},
    "Software Developer Co-op": {
        ("Python", "required"),
        ("Docker", "preferred"),
        ("JavaScript", "mentioned"),
    },
    "Graduate Application Developer": {("JavaScript", "required"), ("SQL", "preferred")},
}


def demo_id(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, "https://vantage.example/demo/" + value)


class ChangedFixture:
    """Offline fixture with per-title overrides; never performs HTTP requests."""

    def __init__(self, changes: dict[str, dict[str, object]]) -> None:
        self.changes = changes

    def fetch(self) -> Iterator[RawJob]:
        from services.ingestion.adapters.fixture import FixtureAdapter

        for job in FixtureAdapter().fetch():
            yield job.model_copy(update=self.changes.get(job.external_id or "", {}))


def annotations(database: "DatabaseConnection") -> dict[str, set[tuple[str, str]]]:
    rows = database.execute(
        """select j.title, s.name, js.requirement_type from vantage.jobs j
        left join vantage.job_skills js on js.job_id = j.id
        left join vantage.skills s on s.id = js.skill_id"""
    ).fetchall()
    result: dict[str, set[tuple[str, str]]] = {}
    for row in rows:
        skills = result.setdefault(row["title"], set())
        if row["name"] is not None:
            skills.add((row["name"], row["requirement_type"]))
    return result


def count(database: "DatabaseConnection", table: str) -> int:
    row = database.execute(f"select count(*) as count from vantage.{table}").fetchone()
    assert row is not None
    return int(row["count"])


def test_fixture_ingestion_replaces_seed_annotations_with_extracted_evidence(
    database: "DatabaseConnection",
) -> None:
    from services.ingestion.cli import ingest_fixture
    from services.ingestion.extraction import EXTRACTION_VERSION

    ingest_fixture(database)
    assert annotations(database) == EXPECTED
    rows = database.execute(
        "select extraction_version, confidence, evidence_excerpt from vantage.job_skills"
    ).fetchall()
    assert {row["extraction_version"] for row in rows} == {EXTRACTION_VERSION}
    assert all(0 < row["confidence"] <= 1 and row["evidence_excerpt"] for row in rows)


def test_repeated_ingestion_creates_no_duplicate_annotations(
    database: "DatabaseConnection",
) -> None:
    from services.ingestion.cli import ingest_fixture

    ingest_fixture(database)
    first = count(database, "job_skills")
    ingest_fixture(database)
    assert count(database, "job_skills") == first == 10
    assert annotations(database) == EXPECTED


def test_removed_requirement_leaves_no_stale_annotation(database: "DatabaseConnection") -> None:
    from services.ingestion.cli import ingest_fixture

    ingest_fixture(database)
    ingest_fixture(
        database,
        adapter=ChangedFixture(
            {
                "analyst-intern": {
                    "description_text": "Synthetic demonstration posting. SQL is required. "
                    "Python is required. This is not a real job opening."
                }
            }
        ),
    )
    result = annotations(database)
    assert result["Data Analyst Intern"] == {("SQL", "required"), ("Python", "required")}
    assert result["Junior Reporting Analyst"] == EXPECTED["Junior Reporting Analyst"]


def test_missing_description_produces_empty_annotation_set(
    database: "DatabaseConnection",
) -> None:
    from services.ingestion.cli import ingest_fixture

    ingest_fixture(database, adapter=ChangedFixture({"analyst-intern": {"description_text": None}}))
    result = annotations(database)
    assert result["Data Analyst Intern"] == set()
    assert result["Junior Reporting Analyst"] == EXPECTED["Junior Reporting Analyst"]


def test_extraction_failure_rolls_back_the_source_transaction(
    database: "DatabaseConnection",
) -> None:
    from services.ingestion.cli import ingest_fixture
    from services.ingestion.extraction import ExtractionError, extract_skills

    def failing(text: str | None, taxonomy: "Taxonomy") -> "list[ExtractedSkill]":
        if text and "JavaScript is required" in text:
            raise ExtractionError("Synthetic extraction failure.")
        return extract_skills(text, taxonomy)

    before = {
        table: count(database, table) for table in ("scrape_runs", "job_observations", "job_skills")
    }
    seeded = annotations(database)
    # Maple is processed first; its first job is written before the second job fails.
    with pytest.raises(ExtractionError):
        ingest_fixture(
            database,
            adapter=ChangedFixture({"developer-intern": {"title": "Changed Co-op Title"}}),
            extractor=failing,
        )
    assert {table: count(database, table) for table in before} == before
    assert annotations(database) == seeded
    row = database.execute(
        "select title from vantage.jobs where id = %s", (demo_id("developer-intern"),)
    ).fetchone()
    assert row is not None and row["title"] == "Software Developer Co-op"
    versions = database.execute("select distinct extraction_version from vantage.job_skills")
    assert {item["extraction_version"] for item in versions.fetchall()} == {"fixture-v1"}


def test_extracted_annotations_preserve_all_fixture_alignment_scores(
    database: "DatabaseConnection",
) -> None:
    from services.api.app.queries.catalog import curriculum_skills, job
    from services.api.app.services.matching import calculate_alignment
    from services.ingestion.cli import ingest_fixture

    program = demo_id("program")
    jobs = ("analyst-intern", "reporting-analyst", "developer-intern", "graduate-developer")

    def scores() -> dict[str, float | None]:
        curriculum = curriculum_skills(database, program)
        results = {}
        for key in jobs:
            detail = job(database, demo_id(key))
            alignment = calculate_alignment(detail.id, program, detail.skills, curriculum)
            results[key] = alignment.alignment_percent
        return results

    seeded = scores()
    ingest_fixture(database)
    assert (
        scores()
        == seeded
        == {
            "analyst-intern": 75.0,
            "reporting-analyst": 67.5,
            "developer-intern": 38.2,
            "graduate-developer": 33.3,
        }
    )
    analyst = calculate_alignment(
        demo_id("analyst-intern"),
        demo_id("program"),
        job(database, demo_id("analyst-intern")).skills,
        curriculum_skills(database, demo_id("program")),
    )
    assert {skill.skill for skill in analyst.matched_skills} == {"Python", "SQL", "Excel"}
