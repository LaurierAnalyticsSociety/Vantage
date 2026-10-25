"""Deterministic, rule-based job-skill extraction against the canonical taxonomy.

The rules are intentionally conservative heuristics, documented in the package README.
Confidence is a design weight for identification certainty, not measured accuracy.
"""

import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import UUID

if TYPE_CHECKING:
    import psycopg

EXTRACTION_VERSION = "skill-rules-v1"
EXCERPT_LIMIT = 240

RequirementType = Literal["required", "preferred", "mentioned"]
STRENGTH: dict[RequirementType, int] = {"mentioned": 0, "preferred": 1, "required": 2}

# Certainty that the skill was identified correctly, independent of requirement strength:
# the matching formula already weights required/preferred/mentioned separately.
MATCH_CONFIDENCE = 0.9
AMBIGUOUS_CONFIDENCE = 0.6

# Aliases that are also ordinary words or letters; single-letter aliases are always included.
AMBIGUOUS_ALIASES = frozenset({"r", "go", "c"})

# Identifier characters: "C" must not match inside "C++", nor "JS" inside "Node.js".
LEFT_BOUNDARY = r"(?<![\w+#.])"
RIGHT_BOUNDARY = r"(?![\w+#])(?!\.\w)"

REQUIRED_CUE = re.compile(
    r"\b(?:required|requires?|requirements?|must(?:\s+have)?|mandatory|essential"
    r"|needed|(?:you|will|we)\s+need|minimum\s+qualifications?)\b",
    re.IGNORECASE,
)
PREFERRED_CUE = re.compile(
    r"\b(?:preferred|preferably|preferable|nice[\s-]to[\s-]have|an?\s+(?:\w+\s+)?asset"
    r"|bonus|an?\s+(?:\w+\s+)?plus|ideally|desirable|desired)\b",
    re.IGNORECASE,
)
NEGATION = re.compile(
    r"\b(?:not|no|never|without|isn't|aren't|don't|doesn't|won't|cannot)\b", re.IGNORECASE
)
SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
CLAUSE_BREAK = re.compile(r";|\s(?:but|however|although|though|whereas)\b", re.IGNORECASE)
BULLET = re.compile(r"^(?:[-*•·▪]|\d{1,2}[.)])\s+")
HEADING = re.compile(r"^([^:]{1,60}):\s*(.*)$")
HEADING_WORDS = 6

# Context that makes an ambiguous alias read as a technology rather than an ordinary word.
QUALIFIER_AFTER = re.compile(
    r"^\s+(?:programming|language|lang|scripts?|scripting|packages?|libraries|modules?)\b"
    r"|^\s*\(programming language\)",
    re.IGNORECASE,
)
QUALIFIER_BEFORE = re.compile(
    r"\b(?:programming|coding|coded|written|developed|proficiency|proficient|experience"
    r"|experienced|fluency|fluent|skills?|knowledge)\s+(?:in|with|of)\s+$",
    re.IGNORECASE,
)
LIST_SEPARATOR = re.compile(r"^[\s,/]*(?:(?:and|or|&)[\s,/]*)?$", re.IGNORECASE)
WORD_COMPOUND_AFTER = re.compile(r"^[&-]\w")
WORD_COMPOUND_BEFORE = re.compile(r"\w[&-]$")


class ExtractionError(ValueError):
    """Raised when the taxonomy or extraction cannot produce trustworthy evidence."""


@dataclass(frozen=True)
class SkillAlias:
    skill_id: UUID
    skill_name: str
    alias: str


@dataclass(frozen=True)
class ExtractedSkill:
    skill_id: UUID
    skill_name: str
    requirement_type: RequirementType
    confidence: float
    evidence_excerpt: str
    extraction_version: str = EXTRACTION_VERSION


def normalize_alias(value: str) -> str:
    return " ".join(value.split()).casefold()


class Taxonomy:
    """Alias index compiled once into a single longest-first, boundary-aware pattern."""

    def __init__(self, aliases: Iterable[SkillAlias]) -> None:
        self.aliases: dict[str, SkillAlias] = {}
        self.spellings: dict[str, set[str]] = {}
        for alias in aliases:
            key = normalize_alias(alias.alias)
            if not key:
                raise ExtractionError("Skill aliases cannot be blank.")
            existing = self.aliases.get(key)
            if existing is not None and existing.skill_id != alias.skill_id:
                raise ExtractionError(f"Alias {alias.alias!r} resolves to more than one skill.")
            self.aliases.setdefault(key, alias)
            self.spellings.setdefault(key, set()).add(" ".join(alias.alias.split()))
        alternatives = sorted(self.aliases, key=lambda key: (-len(key), key))
        body = "|".join(r"\s+".join(map(re.escape, key.split())) for key in alternatives)
        self.pattern = (
            re.compile(f"{LEFT_BOUNDARY}(?:{body}){RIGHT_BOUNDARY}", re.IGNORECASE)
            if alternatives
            else None
        )

    def is_ambiguous(self, key: str) -> bool:
        return key in AMBIGUOUS_ALIASES or (len(key) == 1 and key.isalpha())


@dataclass(frozen=True)
class _Candidate:
    alias: SkillAlias
    key: str
    start: int
    end: int


@dataclass(frozen=True)
class _Cue:
    start: int
    end: int
    requirement: RequirementType
    negated: bool = False


Extractor = Callable[[str | None, Taxonomy], list[ExtractedSkill]]


def extract_skills(text: str | None, taxonomy: Taxonomy) -> list[ExtractedSkill]:
    """Return one strongest annotation per canonical skill, ordered by skill name."""
    if not text or not text.strip() or taxonomy.pattern is None:
        return []
    best: dict[UUID, tuple[tuple[int, float, int], ExtractedSkill]] = {}
    position = 0
    for sentence, inherited in _sentences(text):
        for clause_start, clause in _clauses(sentence):
            cues = _cues(clause)
            for candidate in _accepted(_candidates(clause, taxonomy), clause, taxonomy):
                requirement = _classify(candidate, cues, inherited)
                ambiguous = taxonomy.is_ambiguous(candidate.key)
                confidence = AMBIGUOUS_CONFIDENCE if ambiguous else MATCH_CONFIDENCE
                skill = ExtractedSkill(
                    skill_id=candidate.alias.skill_id,
                    skill_name=candidate.alias.skill_name,
                    requirement_type=requirement,
                    confidence=confidence,
                    evidence_excerpt=_excerpt(
                        sentence, clause_start + candidate.start, clause_start + candidate.end
                    ),
                )
                # Strongest category, then confidence, then earliest evidence wins.
                rank = (STRENGTH[requirement], confidence, -position)
                position += 1
                current = best.get(skill.skill_id)
                if current is None or rank > current[0]:
                    best[skill.skill_id] = (rank, skill)
    return sorted((skill for _, skill in best.values()), key=lambda skill: skill.skill_name)


def load_taxonomy(connection: "psycopg.Connection[dict[str, object]]") -> Taxonomy:
    rows = connection.execute(
        """select s.id as skill_id, s.name as skill_name, s.name as alias from vantage.skills s
        union
        select s.id, s.name, a.alias from vantage.skill_aliases a
        join vantage.skills s on s.id = a.skill_id
        order by skill_name, alias"""
    ).fetchall()
    return Taxonomy(
        SkillAlias(
            skill_id=UUID(str(row["skill_id"])),
            skill_name=str(row["skill_name"]),
            alias=str(row["alias"]),
        )
        for row in rows
    )


def _sentences(text: str) -> Iterator[tuple[str, RequirementType | None]]:
    """Yield whitespace-collapsed sentences with any requirement inherited from a heading."""
    section: RequirementType | None = None
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        bullet = BULLET.match(line)
        content = line[bullet.end() :] if bullet else line
        heading = HEADING.match(content)
        if heading and len(heading.group(1).split()) <= HEADING_WORDS:
            section = _heading_requirement(heading.group(1))
            content = heading.group(2)
            if not content:
                continue
            inherited = section
        elif bullet:
            inherited = section
        else:
            # Any unbulleted line ends a heading's list and never inherits its requirement.
            section = inherited = None
        for sentence in SENTENCE_BREAK.split(content):
            if sentence:
                yield sentence, inherited


def _heading_requirement(label: str) -> RequirementType | None:
    cues = _cues(label)
    if not cues:
        return None
    cue = cues[0]
    return "mentioned" if cue.negated else cue.requirement


def _clauses(sentence: str) -> Iterator[tuple[int, str]]:
    start = 0
    for separator in CLAUSE_BREAK.finditer(sentence):
        yield start, sentence[start : separator.start()]
        start = separator.end()
    yield start, sentence[start:]


def _cues(clause: str) -> list[_Cue]:
    cues = [
        _Cue(match.start(), match.end(), "preferred") for match in PREFERRED_CUE.finditer(clause)
    ]
    previous_end = 0
    for match in REQUIRED_CUE.finditer(clause):
        # A negation between the previous cue and this one cancels the requirement.
        negated = NEGATION.search(clause, previous_end, match.start()) is not None
        cues.append(_Cue(match.start(), match.end(), "required", negated))
        previous_end = match.end()
    return sorted(cues, key=lambda cue: cue.start)


def _candidates(clause: str, taxonomy: Taxonomy) -> list[_Candidate]:
    assert taxonomy.pattern is not None
    found = []
    for match in taxonomy.pattern.finditer(clause):
        key = normalize_alias(match.group())
        alias = taxonomy.aliases.get(key)
        # Case-insensitive regex matching and casefold() can disagree on unusual Unicode
        # (e.g. "İ"); an unresolvable match is dropped rather than guessed or crashed on.
        if alias is not None:
            found.append(_Candidate(alias, key, match.start(), match.end()))
    return found


def _accepted(candidates: list[_Candidate], clause: str, taxonomy: Taxonomy) -> list[_Candidate]:
    accepted = [item for item in candidates if not taxonomy.is_ambiguous(item.key)]
    pending = [
        item
        for item in candidates
        if taxonomy.is_ambiguous(item.key) and _plausible_ambiguous(item, clause, taxonomy)
    ]
    # Coordinated lists ("Python, R, or SQL") may chain through other accepted mentions.
    progress = True
    while progress:
        progress = False
        for item in list(pending):
            if _has_qualifier(item, clause) or _listed_with(item, accepted, clause):
                accepted.append(item)
                pending.remove(item)
                progress = True
    return sorted(accepted, key=lambda item: item.start)


def _plausible_ambiguous(item: _Candidate, clause: str, taxonomy: Taxonomy) -> bool:
    text = clause[item.start : item.end]
    if text not in taxonomy.spellings[item.key] or not text[0].isupper():
        return False
    if WORD_COMPOUND_AFTER.match(clause[item.end :]) or WORD_COMPOUND_BEFORE.search(
        clause[: item.start]
    ):
        return False  # R&D, R-squared, go-to
    if not clause[: item.start].strip() and not _has_qualifier(item, clause):
        return False  # "Go to ..." and other clause-initial ordinary words
    return True


def _has_qualifier(item: _Candidate, clause: str) -> bool:
    return bool(
        QUALIFIER_AFTER.match(clause[item.end :]) or QUALIFIER_BEFORE.search(clause[: item.start])
    )


def _listed_with(item: _Candidate, accepted: list[_Candidate], clause: str) -> bool:
    for other in accepted:
        if other.end <= item.start:
            between = clause[other.end : item.start]
        else:
            between = clause[item.end : other.start]
        if LIST_SEPARATOR.match(between):
            return True
    return False


def _classify(
    candidate: _Candidate, cues: list[_Cue], inherited: RequirementType | None
) -> RequirementType:
    if cues:
        # The nearest cue in the clause applies; ties resolve to the weaker category.
        def distance(cue: _Cue) -> tuple[int, int]:
            gap = max(cue.start - candidate.end, candidate.start - cue.end, 0)
            weight = 0 if cue.negated else STRENGTH[cue.requirement]
            return gap, weight

        cue = min(cues, key=distance)
        return "mentioned" if cue.negated else cue.requirement
    return inherited or "mentioned"


def _excerpt(sentence: str, start: int, end: int) -> str:
    if len(sentence) <= EXCERPT_LIMIT:
        return sentence
    budget = EXCERPT_LIMIT - 2
    left = max(0, min(start - (budget - (end - start)) // 2, len(sentence) - budget))
    right = left + budget
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(sentence) else ""
    return prefix + sentence[left:right].strip() + suffix
