import hashlib
from datetime import datetime
from typing import Any, Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


def canonical_url(value: str) -> str:
    parts = urlsplit(value)
    query = sorted(
        (key, item)
        for key, item in parse_qsl(parts.query)
        if not key.lower().startswith("utm_") and key.lower() not in {"gclid", "fbclid"}
    )
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(query), "")
    )


class RawJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=1, max_length=200)
    external_id: str | None = None
    company_name: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=500)
    source_url: HttpUrl
    apply_url: HttpUrl | None = None
    location_raw: str | None = None
    description_text: str | None = Field(default=None, max_length=200_000)
    posted_at: datetime | None = None
    employment_type_raw: str | None = None
    work_mode_raw: str | None = None
    salary_raw: str | None = None
    retrieved_at: datetime
    source_payload: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @field_validator("source_key", "company_name", "title")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Required text cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def timezone_required(self) -> Self:
        for value in (self.posted_at, self.retrieved_at):
            if value is not None and value.tzinfo is None:
                raise ValueError("Timestamps must include a timezone")
        return self

    @property
    def stable_key(self) -> str:
        return (
            self.external_id
            or hashlib.sha256(canonical_url(str(self.source_url)).encode()).hexdigest()
        )
