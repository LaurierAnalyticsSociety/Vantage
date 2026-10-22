import os
from collections.abc import Iterator
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

import pytest

if TYPE_CHECKING:
    from services.common.database import DatabaseConnection


@pytest.fixture(scope="session")
def isolated_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured; database tests run in CI.")
    parsed = urlsplit(url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "postgres"}:
        pytest.fail("Database tests require a disposable local PostgreSQL server.")
    if not parsed.path.endswith("_test"):
        pytest.fail("The disposable database name must end in _test.")
    pytest.importorskip("psycopg")
    import psycopg
    from psycopg.rows import dict_row

    from services.common.manage import migrate, seed

    with psycopg.connect(url, row_factory=dict_row) as connection:
        migrate(connection)
        seed(connection, "development")
    return url


@pytest.fixture
def database(isolated_database_url: str) -> Iterator["DatabaseConnection"]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(
        isolated_database_url, row_factory=dict_row, autocommit=True
    ) as connection:
        with connection.transaction(force_rollback=True):
            yield connection
