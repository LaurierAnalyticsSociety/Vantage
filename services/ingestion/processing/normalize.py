import hashlib
import re
from html.parser import HTMLParser

from pydantic import HttpUrl

from services.ingestion.contracts.raw_job import RawJob, canonical_url


class PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "br", "li", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def plain_text(value: str | None) -> str | None:
    if value is None:
        return None
    parser = PlainText()
    parser.feed(value)
    return re.sub(r"[ \t]+", " ", "".join(parser.parts)).strip()


def normalize(job: RawJob) -> RawJob:
    return job.model_copy(
        update={
            "source_url": HttpUrl(canonical_url(str(job.source_url))),
            "apply_url": HttpUrl(canonical_url(str(job.apply_url))) if job.apply_url else None,
            "description_text": plain_text(job.description_text),
        }
    )


def content_hash(job: RawJob) -> str:
    # Retrieval time and provider payload are not content changes.
    return hashlib.sha256(job.model_dump_json(exclude={"retrieved_at"}).encode()).hexdigest()
