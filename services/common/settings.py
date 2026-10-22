import os
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # CI/production use injected variables and must not read a locked encrypted .env.
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env"
        if os.environ.get("APP_ENV", "development") == "development"
        else None,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: SecretStr = SecretStr("")
    ingestion_database_url: SecretStr = SecretStr("")
    migration_database_url: SecretStr = SecretStr("")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    scraper_user_agent: str = "Vantage-development"
    max_concurrent_requests: int = Field(default=3, ge=1, le=10)


def require_database_url(secret: SecretStr, *, hosted: bool = True) -> str:
    from urllib.parse import parse_qs, urlparse

    url = secret.get_secret_value()
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql") or not parsed.hostname:
        raise ValueError("Configure a PostgreSQL connection URL in the local environment file.")
    local = parsed.hostname in ("localhost", "127.0.0.1", "::1", "postgres")
    if (
        hosted
        and not local
        and parse_qs(parsed.query).get("sslmode", [""])[0]
        not in ("require", "verify-ca", "verify-full")
    ):
        raise ValueError("Hosted PostgreSQL URLs must include sslmode=require or stronger.")
    return url
