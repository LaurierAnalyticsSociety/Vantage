from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr


@pytest.fixture
def client() -> Iterator[TestClient]:
    pytest.importorskip("psycopg")
    from services.api.app.main import create_app
    from services.common.settings import Settings

    settings = Settings.model_construct(database_url=SecretStr(""), app_env="test")
    with TestClient(create_app(settings)) as session:
        yield session


def test_process_health_works_without_database_secrets(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database_configured": False}
    assert response.headers["x-request-id"]


def test_unconfigured_database_has_safe_error(client: TestClient) -> None:
    response = client.get("/api/v1/jobs")
    assert response.status_code == 503
    assert set(response.json()) == {"code", "message", "request_id"}
    assert "postgres" not in response.text.lower()


def test_openapi_exposes_read_only_endpoints(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    for path, operations in schema["paths"].items():
        assert set(operations) == {"get"}, path
    assert "/api/v1/jobs/{job_id}/alignment" in schema["paths"]
