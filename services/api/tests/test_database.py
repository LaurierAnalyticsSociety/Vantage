from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

if TYPE_CHECKING:
    from services.common.database import DatabaseConnection

pytestmark = pytest.mark.database


def demo_id(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, "https://vantage.example/demo/" + value))


def test_migrations_and_seed_are_repeatable(database: "DatabaseConnection") -> None:
    from services.common.manage import migrate, seed

    assert migrate(database) == 0
    seed(database, "development")
    row = database.execute("select count(*) as count from vantage.jobs").fetchone()
    assert row is not None and row["count"] == 4
    with pytest.raises(ValueError, match="only in development"):
        seed(database, "production")


def test_employer_mismatch_is_rejected(database: "DatabaseConnection") -> None:
    import psycopg

    with pytest.raises(psycopg.errors.ForeignKeyViolation), database.transaction():
        database.execute(
            "update vantage.jobs set company_id=%s where id=%s",
            (demo_id("maple"), demo_id("analyst-intern")),
        )


def test_catalog_year_cannot_be_changed_under_existing_requirements(
    database: "DatabaseConnection",
) -> None:
    import psycopg

    with pytest.raises(psycopg.errors.CheckViolation), database.transaction():
        database.execute("update vantage.courses set catalog_year='2025/26'")


def test_optional_and_unverified_evidence_is_excluded(database: "DatabaseConnection") -> None:
    from services.api.app.queries.catalog import curriculum_skills

    skills = curriculum_skills(
        database, uuid5(NAMESPACE_URL, "https://vantage.example/demo/program")
    )
    assert {skill.name for skill in skills} == {"Python", "SQL", "Excel"}


def test_reader_can_select_but_cannot_write(database: "DatabaseConnection") -> None:
    import psycopg

    database.execute("set local role vantage_reader")
    assert database.execute("select id from vantage.jobs limit 1").fetchone()
    with pytest.raises(psycopg.errors.InsufficientPrivilege), database.transaction():
        database.execute("update vantage.jobs set title='unauthorized'")


def test_public_role_has_no_application_schema_access(database: "DatabaseConnection") -> None:
    row = database.execute(
        """select exists (
            select 1 from pg_namespace n,
            lateral aclexplode(coalesce(n.nspacl, acldefault('n', n.nspowner))) a
            where n.nspname = 'vantage' and a.grantee = 0 and a.privilege_type = 'USAGE'
        ) as allowed"""
    ).fetchone()
    assert row is not None and row["allowed"] is False


def test_repeated_fixture_ingestion_updates_without_duplicates(
    database: "DatabaseConnection",
) -> None:
    from services.ingestion.cli import ingest_fixture

    assert ingest_fixture(database) == {"inserted": 0, "updated": 4}
    assert ingest_fixture(database) == {"inserted": 0, "updated": 4}
    jobs = database.execute("select count(*) as count from vantage.jobs").fetchone()
    assert jobs is not None and jobs["count"] == 4
    observations = database.execute(
        "select count(*) as count from vantage.job_observations"
    ).fetchone()
    assert observations is not None and observations["count"] == 8


def test_api_filters_pagination_and_alignment(isolated_database_url: str) -> None:
    from services.api.app.main import create_app
    from services.common.settings import Settings

    settings = Settings.model_construct(
        database_url=SecretStr(isolated_database_url), app_env="test"
    )
    app = create_app(settings)
    with TestClient(app) as client:
        first = client.get("/api/v1/jobs?page_size=2").json()
        assert len(first["items"]) == 2
        second = client.get(
            "/api/v1/jobs",
            params={
                "page_size": 2,
                "cursor": first["next_cursor"],
            },
        ).json()
        assert not ({job["id"] for job in first["items"]} & {job["id"] for job in second["items"]})
        assert client.get("/api/v1/jobs?work_mode=teleportation").status_code == 422
        assert client.get("/api/v1/jobs?page_size=1000").status_code == 422
        assert client.get("/api/v1/jobs?cursor=broken").status_code == 422
        remote = client.get("/api/v1/jobs?work_mode=remote").json()
        assert len(remote["items"]) == 1
        result = client.get(
            f"/api/v1/jobs/{demo_id('analyst-intern')}/alignment",
            params={
                "program_id": demo_id("program"),
            },
        ).json()
        assert result["status"] == "scored"
        assert result["alignment_percent"] == pytest.approx(75)
        assert {skill["skill"] for skill in result["matched_skills"]} == {"Python", "SQL", "Excel"}
        assert "source_payload" not in client.get("/api/v1/jobs").text
