"""Load and strictly validate the synthetic benchmark corpus and its isolated taxonomy.

Standard library only. Nothing here touches a database, the network, or the production
taxonomy; skill identities are stable benchmark keys mapped to deterministic UUIDs.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from services.ingestion.extraction.evaluation.metrics import REQUIREMENT_TYPES
from services.ingestion.extraction.skills import (
    ExtractionError,
    RequirementType,
    SkillAlias,
    Taxonomy,
    normalize_alias,
)

BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "benchmark"
TAXONOMY_FORMAT = "vantage-skill-taxonomy"
CORPUS_FORMAT = "vantage-skill-benchmark"
FORMAT_VERSION = 1
SPLITS = ("development", "heldout")

Split = Literal["development", "heldout"]


class BenchmarkError(ValueError):
    """An invalid benchmark input, with a message naming the file, location, and fix."""


def fingerprint(value: object) -> str:
    """SHA-256 of canonical JSON, independent of formatting and line endings."""
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def benchmark_skill_id(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, "https://vantage.example/benchmark-skill/" + key)


@dataclass(frozen=True)
class BenchmarkSkill:
    key: str
    name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkTaxonomy:
    version: str
    fingerprint: str
    skills: tuple[BenchmarkSkill, ...]
    index: Taxonomy

    def key_for(self, skill_id: UUID) -> str:
        for skill in self.skills:
            if benchmark_skill_id(skill.key) == skill_id:
                return skill.key
        raise BenchmarkError(f"Extractor returned skill ID {skill_id} outside the taxonomy.")

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(skill.key for skill in self.skills)


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    description: str
    tags: tuple[str, ...]
    expected: tuple[tuple[str, RequirementType], ...]
    note: str | None = None


@dataclass(frozen=True)
class BenchmarkSplit:
    split: Split
    corpus_version: str
    taxonomy_version: str
    fingerprint: str
    cases: tuple[BenchmarkCase, ...]


class _Reader:
    """Typed access to parsed JSON that reports precise, actionable locations."""

    def __init__(self, source: str) -> None:
        self.source = source

    def fail(self, path: str, message: str) -> BenchmarkError:
        return BenchmarkError(f"{self.source}: {path}: {message}")

    def fields(
        self, value: object, path: str, required: set[str], optional: frozenset[str] = frozenset()
    ) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise self.fail(path, f"expected an object, found {type(value).__name__}.")
        missing = sorted(required - value.keys())
        if missing:
            raise self.fail(path, f"missing required field(s): {', '.join(missing)}.")
        unknown = sorted(value.keys() - required - optional)
        if unknown:
            allowed = ", ".join(sorted(required | optional))
            raise self.fail(path, f"unknown field(s): {', '.join(unknown)}; allowed: {allowed}.")
        return cast(dict[str, Any], value)

    def text(self, value: object, path: str, *, allow_empty: bool = False) -> str:
        if not isinstance(value, str):
            raise self.fail(path, f"expected a string, found {type(value).__name__}.")
        if not allow_empty and not value.strip():
            raise self.fail(path, "must not be blank.")
        return value

    def items(self, value: object, path: str) -> list[Any]:
        if not isinstance(value, list):
            raise self.fail(path, f"expected an array, found {type(value).__name__}.")
        return value

    def const(self, value: object, path: str, expected: object) -> None:
        if value != expected or type(value) is not type(expected):
            raise self.fail(path, f"must be {json.dumps(expected)}, found {json.dumps(value)}.")


def _read_json(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise BenchmarkError(f"{path}: file not found; check --benchmark-dir.") from error
    except OSError as error:
        raise BenchmarkError(f"{path}: cannot read file ({error.strerror}).") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise BenchmarkError(
            f"{path.name}: invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}."
        ) from error


def parse_taxonomy(data: object, source: str = "taxonomy.json") -> BenchmarkTaxonomy:
    reader = _Reader(source)
    root = reader.fields(
        data,
        "$",
        {"format", "format_version", "taxonomy_version", "synthetic", "skills"},
        frozenset({"description"}),
    )
    reader.const(root["format"], "format", TAXONOMY_FORMAT)
    reader.const(root["format_version"], "format_version", FORMAT_VERSION)
    reader.const(root["synthetic"], "synthetic", True)
    version = reader.text(root["taxonomy_version"], "taxonomy_version")
    skills: list[BenchmarkSkill] = []
    keys: set[str] = set()
    names: dict[str, str] = {}
    owners: dict[str, str] = {}
    for position, raw in enumerate(reader.items(root["skills"], "skills")):
        path = f"skills[{position}]"
        item = reader.fields(raw, path, {"key", "name", "aliases"})
        key = reader.text(item["key"], f"{path}.key")
        if key != key.strip() or key != key.lower() or " " in key:
            raise reader.fail(f"{path}.key", f"{key!r} must be lowercase without spaces.")
        if key in keys:
            raise reader.fail(f"{path}.key", f"duplicate skill key {key!r}.")
        keys.add(key)
        name = reader.text(item["name"], f"{path}.name")
        if name.casefold() in names:
            raise reader.fail(
                f"{path}.name",
                f"skill name {name!r} is already used by {names[name.casefold()]!r}.",
            )
        names[name.casefold()] = key
        aliases = tuple(
            reader.text(alias, f"{path}.aliases[{index}]")
            for index, alias in enumerate(reader.items(item["aliases"], f"{path}.aliases"))
        )
        for index, spelling in enumerate((name, *aliases)):
            where = f"{path}.name" if index == 0 else f"{path}.aliases[{index - 1}]"
            normalized = normalize_alias(spelling)
            owner = owners.setdefault(normalized, key)
            if owner != key:
                raise reader.fail(
                    where,
                    f"alias {spelling!r} (normalized {normalized!r}) already belongs to skill "
                    f"{owner!r}; each alias must resolve to exactly one skill.",
                )
        skills.append(BenchmarkSkill(key, name, aliases))
    if not skills:
        raise reader.fail("skills", "must contain at least one skill.")
    try:
        compiled = Taxonomy(
            SkillAlias(benchmark_skill_id(skill.key), skill.name, alias)
            for skill in skills
            for alias in (skill.name, *skill.aliases)
        )
    except ExtractionError as error:  # pragma: no cover - guarded by the checks above
        raise reader.fail("skills", str(error)) from error
    return BenchmarkTaxonomy(version, fingerprint(data), tuple(skills), compiled)


def parse_split(
    data: object, taxonomy: BenchmarkTaxonomy, expected_split: Split, source: str
) -> BenchmarkSplit:
    reader = _Reader(source)
    root = reader.fields(
        data,
        "$",
        {
            "format",
            "format_version",
            "corpus_version",
            "split",
            "taxonomy_version",
            "provenance",
            "cases",
        },
    )
    reader.const(root["format"], "format", CORPUS_FORMAT)
    reader.const(root["format_version"], "format_version", FORMAT_VERSION)
    reader.const(root["split"], "split", expected_split)
    corpus_version = reader.text(root["corpus_version"], "corpus_version")
    taxonomy_version = reader.text(root["taxonomy_version"], "taxonomy_version")
    if taxonomy_version != taxonomy.version:
        raise reader.fail(
            "taxonomy_version",
            f"{taxonomy_version!r} does not match taxonomy.json version {taxonomy.version!r}.",
        )
    provenance = reader.fields(
        root["provenance"], "provenance", {"synthetic", "method"}, frozenset({"authored", "guide"})
    )
    reader.const(provenance["synthetic"], "provenance.synthetic", True)
    reader.text(provenance["method"], "provenance.method")
    known = set(taxonomy.keys)
    cases: list[BenchmarkCase] = []
    ids: set[str] = set()
    for position, raw in enumerate(reader.items(root["cases"], "cases")):
        path = f"cases[{position}]"
        item = reader.fields(
            raw,
            path,
            {"id", "synthetic", "provenance", "tags", "description", "expected"},
            frozenset({"note"}),
        )
        case_id = reader.text(item["id"], f"{path}.id")
        if case_id in ids:
            raise reader.fail(f"{path}.id", f"duplicate case ID {case_id!r}.")
        ids.add(case_id)
        path = f"cases[{position}] ({case_id})"
        reader.const(item["synthetic"], f"{path}.synthetic", True)
        reader.text(item["provenance"], f"{path}.provenance")
        tags = tuple(
            reader.text(tag, f"{path}.tags[{index}]")
            for index, tag in enumerate(reader.items(item["tags"], f"{path}.tags"))
        )
        description = reader.text(item["description"], f"{path}.description", allow_empty=True)
        note = None
        if "note" in item:
            note = reader.text(item["note"], f"{path}.note")
        expected: dict[str, RequirementType] = {}
        for index, label in enumerate(reader.items(item["expected"], f"{path}.expected")):
            where = f"{path}.expected[{index}]"
            entry = reader.fields(label, where, {"skill", "requirement_type"})
            key = reader.text(entry["skill"], f"{where}.skill")
            if key not in known:
                raise reader.fail(
                    f"{where}.skill",
                    f"unknown skill key {key!r}; add it to taxonomy.json or use one of: "
                    f"{', '.join(sorted(known))}.",
                )
            if key in expected:
                raise reader.fail(
                    f"{where}.skill",
                    f"skill {key!r} is labeled more than once; keep one strongest label.",
                )
            category = entry["requirement_type"]
            if category not in REQUIREMENT_TYPES:
                raise reader.fail(
                    f"{where}.requirement_type",
                    f"invalid category {json.dumps(category)}; use one of: "
                    f"{', '.join(REQUIREMENT_TYPES)}.",
                )
            expected[key] = cast(RequirementType, category)
        cases.append(
            BenchmarkCase(
                id=case_id,
                description=description,
                tags=tags,
                expected=tuple(sorted(expected.items())),
                note=note,
            )
        )
    return BenchmarkSplit(
        split=expected_split,
        corpus_version=corpus_version,
        taxonomy_version=taxonomy_version,
        fingerprint=fingerprint(data),
        cases=tuple(cases),
    )


@dataclass(frozen=True)
class Benchmark:
    taxonomy: BenchmarkTaxonomy
    splits: dict[Split, BenchmarkSplit]


def load_benchmark(directory: Path = BENCHMARK_DIR) -> Benchmark:
    """Load and validate the taxonomy and both splits; case IDs must be unique across splits."""
    if not directory.is_dir():
        raise BenchmarkError(f"{directory}: benchmark directory not found; check --benchmark-dir.")
    taxonomy = parse_taxonomy(_read_json(directory / "taxonomy.json"))
    splits: dict[Split, BenchmarkSplit] = {}
    seen: dict[str, str] = {}
    for split in cast(tuple[Split, ...], SPLITS):
        loaded = parse_split(
            _read_json(directory / f"{split}.json"), taxonomy, split, f"{split}.json"
        )
        for case in loaded.cases:
            if case.id in seen:
                raise BenchmarkError(
                    f"{split}.json: case ID {case.id!r} also appears in {seen[case.id]}.json; "
                    "case IDs must be unique across splits."
                )
            seen[case.id] = split
        splits[split] = loaded
    versions = {loaded.corpus_version for loaded in splits.values()}
    if len(versions) != 1:
        raise BenchmarkError(
            f"Splits disagree on corpus_version ({', '.join(sorted(versions))}); "
            "both splits must come from one frozen corpus."
        )
    return Benchmark(taxonomy, splits)
