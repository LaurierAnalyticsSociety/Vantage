from collections.abc import Iterator
from typing import Any, TypeAlias

from fastapi import HTTPException, Request
from psycopg import Connection
from psycopg_pool import ConnectionPool

# Eager aliases are also runtime constructors (PEP 695 aliases are not callable).
DatabaseConnection: TypeAlias = Connection[dict[str, Any]]  # noqa: UP040
DatabasePool: TypeAlias = ConnectionPool[DatabaseConnection]  # noqa: UP040


def get_connection(request: Request) -> Iterator[DatabaseConnection]:
    pool: DatabasePool | None = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    with pool.connection(timeout=5) as connection:
        yield connection
