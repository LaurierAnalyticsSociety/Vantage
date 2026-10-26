import json
from datetime import UTC, datetime

import psycopg
from psycopg.rows import dict_row

from services.common.settings import Settings, require_database_url
from services.ingestion.adapters.fixture import Adapter, FixtureAdapter
from services.ingestion.extraction import ExtractedSkill, Extractor, extract_skills, load_taxonomy
from services.ingestion.processing.normalize import content_hash, normalize


def replace_job_skills(
    connection: psycopg.Connection[dict[str, object]], job_id: object, skills: list[ExtractedSkill]
) -> None:
    # The complete annotation set is replaced so removed requirements leave no stale evidence.
    connection.execute("delete from vantage.job_skills where job_id = %s", (job_id,))
    if not skills:
        return
    with connection.cursor() as cursor:
        cursor.executemany(
            """insert into vantage.job_skills
            (job_id, skill_id, requirement_type, confidence, evidence_excerpt, extraction_version)
            values (%s,%s,%s,%s,%s,%s)""",
            [
                (
                    job_id,
                    skill.skill_id,
                    skill.requirement_type,
                    skill.confidence,
                    skill.evidence_excerpt,
                    skill.extraction_version,
                )
                for skill in skills
            ],
        )


def ingest_fixture(
    connection: psycopg.Connection[dict[str, object]],
    adapter: Adapter | None = None,
    extractor: Extractor = extract_skills,
) -> dict[str, int]:
    # Parse the complete fixture before writing: malformed files never cause closures.
    records = [normalize(job) for job in (adapter or FixtureAdapter()).fetch()]
    grouped = sorted({record.source_key for record in records})
    total_inserted = total_updated = 0
    for source_key in grouped:
        with connection.transaction():
            source = connection.execute(
                """select s.id, s.company_id, c.name from vantage.job_sources s
                join vantage.companies c on c.id = s.company_id
                where s.adapter_key = %s and s.is_synthetic = true""",
                (source_key,),
            ).fetchone()
            if source is None:
                raise ValueError("Run the development seed before fixture ingestion.")
            taxonomy = load_taxonomy(connection)
            run = connection.execute(
                """insert into vantage.scrape_runs(source_id, adapter_version)
                values (%s, 'fixture-v1') returning id""",
                (source["id"],),
            ).fetchone()
            assert run is not None
            inserted = updated = 0
            for record in (item for item in records if item.source_key == source_key):
                if record.company_name != source["name"]:
                    raise ValueError("Fixture employer does not match its source.")
                outcome = connection.execute(
                    """insert into vantage.jobs
                    (source_id, company_id, source_key, external_id, title, description_text,
                     source_url, apply_url, location_raw, content_hash, last_seen_at)
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    on conflict (source_id, source_key) do update set
                        title = excluded.title, description_text = excluded.description_text,
                        source_url = excluded.source_url, apply_url = excluded.apply_url,
                        location_raw = excluded.location_raw, content_hash = excluded.content_hash,
                        last_seen_at = greatest(vantage.jobs.last_seen_at, excluded.last_seen_at),
                        missing_successful_runs = 0, status = 'active', updated_at = now()
                    returning id, (xmax = 0) as inserted""",
                    (
                        source["id"],
                        source["company_id"],
                        record.stable_key,
                        record.external_id,
                        record.title,
                        record.description_text,
                        str(record.source_url),
                        str(record.apply_url) if record.apply_url else None,
                        record.location_raw,
                        content_hash(record),
                        datetime.now(UTC),
                    ),
                ).fetchone()
                assert outcome is not None
                inserted += int(bool(outcome["inserted"]))
                updated += int(not outcome["inserted"])
                connection.execute(
                    """insert into vantage.job_observations(job_id, scrape_run_id, content_hash)
                    values (%s,%s,%s) on conflict (job_id, scrape_run_id) do nothing""",
                    (outcome["id"], run["id"], content_hash(record)),
                )
                # Inside the source transaction: an extraction failure rolls back all writes.
                replace_job_skills(
                    connection, outcome["id"], extractor(record.description_text, taxonomy)
                )
            connection.execute(
                """update vantage.scrape_runs set status='success', finished_at=now(),
                fetched_count=%s, inserted_count=%s, updated_count=%s where id=%s""",
                (inserted + updated, inserted, updated, run["id"]),
            )
            connection.execute(
                "update vantage.job_sources set last_success_at=now() where id=%s", (source["id"],)
            )
            total_inserted += inserted
            total_updated += updated
    return {"inserted": total_inserted, "updated": total_updated}


def should_reconcile(status: str, missing_successful_runs: int, threshold: int = 2) -> bool:
    """Policy seam for a future live collector; fixture runs never close jobs."""
    return status == "success" and missing_successful_runs >= threshold


def main() -> None:
    configuration = Settings()
    if configuration.app_env != "development":
        raise SystemExit("Fixture ingestion is available only in development.")
    try:
        url = require_database_url(configuration.ingestion_database_url)
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=10) as connection:
            counts = ingest_fixture(connection)
        print(json.dumps({"event": "fixture_ingestion_complete", **counts}))
    except (ValueError, psycopg.Error):
        raise SystemExit(
            "Fixture ingestion failed; check configuration and apply migrations/seed."
        ) from None


if __name__ == "__main__":
    main()
