import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import psycopg
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.app.routes.public import router
from services.common.database import DatabaseConnection, DatabasePool
from services.common.settings import Settings, require_database_url

logger = logging.getLogger("vantage.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        pool: DatabasePool | None = None
        if configuration.database_url.get_secret_value():
            url = require_database_url(configuration.database_url)
            pool = DatabasePool(
                url,
                connection_class=DatabaseConnection,
                min_size=0,
                max_size=5,
                open=False,
                timeout=5,
                kwargs={
                    "row_factory": dict_row,
                    "connect_timeout": 5,
                    "options": "-c statement_timeout=10000 -c default_transaction_read_only=on",
                },
            )
            pool.open()
        application.state.pool = pool
        try:
            yield
        finally:
            if pool is not None:
                pool.close()

    application = FastAPI(title="Vantage API", version="0.1.0", lifespan=lifespan)
    application.state.pool = None
    application.add_middleware(
        CORSMiddleware,
        allow_origins=configuration.cors_origins,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type"],
    )

    @application.middleware("http")
    async def request_identity(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", str(uuid4())),
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return error_response(
            request, error.status_code, f"http_{error.status_code}", str(error.detail)
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(
            request, 422, "invalid_request", "Check the supplied query and path values."
        )

    @application.exception_handler(psycopg.Error)
    @application.exception_handler(PoolTimeout)
    async def database_error(request: Request, error: Exception) -> JSONResponse:
        logger.warning("database_unavailable request_id=%s", request.state.request_id)
        return error_response(
            request, 503, "database_unavailable", "Database temporarily unavailable."
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error("request_failed request_id=%s", request.state.request_id)
        return error_response(request, 500, "internal_error", "Request could not be completed.")

    application.include_router(router)
    return application


app = create_app()
