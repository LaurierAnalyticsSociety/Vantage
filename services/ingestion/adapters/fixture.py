import json
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from services.common.settings import ROOT
from services.ingestion.contracts.raw_job import RawJob


class Adapter(Protocol):
    def fetch(self) -> Iterator[RawJob]: ...


class FixtureAdapter:
    """Offline synthetic adapter. Never performs HTTP requests."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or ROOT / "database/seed/jobs.json"

    def fetch(self) -> Iterator[RawJob]:
        payload = json.loads(self.path.read_text())
        for item in payload:
            yield RawJob.model_validate(item)
