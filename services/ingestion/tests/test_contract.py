from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from services.ingestion.adapters.fixture import FixtureAdapter
from services.ingestion.contracts.raw_job import RawJob, canonical_url
from services.ingestion.processing.normalize import content_hash, normalize, plain_text


def raw_job(**changes: object) -> RawJob:
    payload: dict[str, object] = {
        "source_key": "fixture-north",
        "external_id": "123",
        "company_name": "Example",
        "title": "Analyst",
        "source_url": "https://example.org/job/123",
        "retrieved_at": "2026-10-21T12:00:00Z",
    }
    payload.update(changes)
    return RawJob.model_validate(payload)


def test_fixtures_are_complete_and_share_stable_identity() -> None:
    jobs = list(FixtureAdapter().fetch())
    assert len(jobs) == 4
    assert len({(job.source_key, job.stable_key) for job in jobs}) == 4
    assert all(job.source_url.host == "example.org" for job in jobs)


@pytest.mark.parametrize(
    "changes",
    [
        {"title": "  "},
        {"retrieved_at": "2026-10-21T12:00:00"},
        {"source_url": "javascript:alert(1)"},
        {"company_name": ""},
    ],
)
def test_invalid_records_fail_before_ingestion(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        raw_job(**changes)


def test_url_fallback_ignores_tracking_but_preserves_identity_query() -> None:
    first = raw_job(external_id=None, source_url="https://example.org/jobs?id=123&utm_source=test")
    second = raw_job(external_id=None, source_url="https://example.org/jobs?fbclid=x&id=123#top")
    other = raw_job(external_id=None, source_url="https://example.org/jobs?id=124")
    assert first.stable_key == second.stable_key
    assert first.stable_key != other.stable_key
    assert canonical_url(str(first.source_url)) == "https://example.org/jobs?id=123"


def test_markup_is_plain_text_and_script_content_is_removed() -> None:
    assert plain_text("<p>Python &amp; SQL</p><script>alert('x')</script>") == "Python & SQL"
    normalized = normalize(raw_job(description_text="<p>Learn Python</p>"))
    assert normalized.description_text == "Learn Python"


def test_observation_time_does_not_change_content_hash() -> None:
    first = raw_job()
    second = first.model_copy(update={"retrieved_at": datetime.now(UTC) + timedelta(days=1)})
    assert content_hash(first) == content_hash(second)
