from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest

from services.api.app.schemas.models import CourseEvidence, CurriculumSkill, JobSkill
from services.api.app.services.matching import calculate_alignment
from services.ingestion.adapters.fixture import FixtureAdapter
from services.ingestion.extraction import (
    EXTRACTION_VERSION,
    ExtractionError,
    SkillAlias,
    Taxonomy,
    extract_skills,
)
from services.ingestion.extraction.skills import (
    AMBIGUOUS_CONFIDENCE,
    EXCERPT_LIMIT,
    MATCH_CONFIDENCE,
)
from services.ingestion.processing.normalize import normalize


def skill_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, "https://vantage.example/test-skill/" + name)


def taxonomy(aliases: dict[str, list[str]]) -> Taxonomy:
    return Taxonomy(
        SkillAlias(skill_id(name), name, alias)
        for name, names in aliases.items()
        for alias in [name, *names]
    )


# Mirrors the seed taxonomy; edge-case skills exist only in this isolated test taxonomy.
SEED = taxonomy(
    {
        "Python": ["Python 3"],
        "SQL": [],
        "Excel": ["Microsoft Excel"],
        "Docker": [],
        "JavaScript": ["JS"],
    }
)
TECHNICAL = taxonomy(
    {
        "C++": [],
        "C#": [],
        ".NET": [],
        "Node.js": [],
        "JavaScript": ["JS"],
        "C": [],
        "R": [],
        "Go": ["Golang"],
        "Python": [],
        "SQL": [],
        "Docker": [],
    }
)


def found(text: str | None, index: Taxonomy = TECHNICAL) -> dict[str, str]:
    return {skill.skill_name: skill.requirement_type for skill in extract_skills(text, index)}


def test_fixture_descriptions_produce_acceptance_annotations() -> None:
    results = {
        job.title: found(job.description_text, SEED)
        for job in map(normalize, FixtureAdapter().fetch())
    }
    assert results == {
        "Data Analyst Intern": {"SQL": "required", "Python": "required", "Excel": "preferred"},
        "Junior Reporting Analyst": {"SQL": "required", "Excel": "required"},
        "Software Developer Co-op": {
            "Python": "required",
            "Docker": "preferred",
            "JavaScript": "mentioned",
        },
        "Graduate Application Developer": {"JavaScript": "required", "SQL": "preferred"},
    }


def test_fixture_confidence_is_uniform_across_requirement_types() -> None:
    skills = [
        skill
        for job in map(normalize, FixtureAdapter().fetch())
        for skill in extract_skills(job.description_text, SEED)
    ]
    assert {skill.requirement_type for skill in skills} == {"required", "preferred", "mentioned"}
    assert {skill.confidence for skill in skills} == {MATCH_CONFIDENCE}
    assert {skill.extraction_version for skill in skills} == {EXTRACTION_VERSION}


def test_fixture_alignment_scores_match_seed_annotations() -> None:
    # Mirrors the seed's verified required-course coverage and its confidence-1 annotations.
    curriculum = [
        CurriculumSkill(
            id=skill_id(name),
            name=name,
            category="Synthetic",
            supporting_courses=[
                CourseEvidence.model_validate(
                    {
                        "code": "DEMO101",
                        "title": "Synthetic course",
                        "coverage_level": level,
                        "evidence_excerpt": "Synthetic evidence.",
                        "evidence_url": "https://example.org/vantage/synthetic-curriculum",
                    }
                )
            ],
        )
        for name, level in [("Python", "practiced"), ("SQL", "assessed"), ("Excel", "introduced")]
    ]
    expected = {
        "Data Analyst Intern": 75.0,
        "Junior Reporting Analyst": 67.5,
        "Software Developer Co-op": 38.2,
        "Graduate Application Developer": 33.3,
    }
    for job in map(normalize, FixtureAdapter().fetch()):
        extracted = extract_skills(job.description_text, SEED)
        scores = [
            calculate_alignment(
                uuid4(),
                uuid4(),
                [
                    JobSkill(
                        id=skill.skill_id,
                        name=skill.skill_name,
                        requirement_type=skill.requirement_type,
                        confidence=confidence,
                    )
                    for skill in extracted
                ],
                curriculum,
            ).alignment_percent
            for confidence in (1.0, extracted[0].confidence)
        ]
        assert scores == [expected[job.title]] * 2


def test_aliases_resolve_to_canonical_skills() -> None:
    skills = extract_skills("Experience with Python 3, MS tools and Microsoft Excel.", SEED)
    assert [(skill.skill_name, skill.skill_id) for skill in skills] == [
        ("Excel", skill_id("Excel")),
        ("Python", skill_id("Python")),
    ]
    assert found("Familiar with js and node tooling.", SEED) == {"JavaScript": "mentioned"}


@pytest.mark.parametrize(
    "text",
    [
        "We use SQLite and NoSQL stores.",
        "Parse JSON payloads.",
        "Excellent communication skills.",
        "Pythonic thinking and dockerized builds.",
        "Visit example.js.org for details.",
    ],
)
def test_aliases_require_word_boundaries(text: str) -> None:
    assert found(text, SEED) == {}


def test_technical_identifiers_match_exactly() -> None:
    assert found("Experience with C++, C# and .NET is required.") == {
        "C++": "required",
        "C#": "required",
        ".NET": "required",
    }
    assert found("Build services in Node.js.") == {"Node.js": "mentioned"}
    assert found("Ship ASP.NET pages.") == {}


def test_node_js_never_counts_as_javascript_shorthand() -> None:
    assert found("Build services in Node.js.", SEED) == {}


def test_c_requires_list_or_language_context() -> None:
    assert found("Write C/C++ firmware.") == {"C": "mentioned", "C++": "mentioned"}
    assert found("Proficiency in C is required.") == {"C": "required"}
    assert found("Grade of C or higher in a statistics course.") == {}
    assert found("See Appendix C for details.") == {}


@pytest.mark.parametrize(
    "text",
    [
        "Go to our careers page to apply.",
        "Our go-to analytics partner.",
        "Ready to go when you are.",
        "Work on the go with our team.",
        "Experience supporting R&D teams.",
        "Report the R-squared values.",
        "Analysis using r and a calculator.",
        "Plan A or plan R.",
        "Let's Go!",
    ],
)
def test_ambiguous_tokens_reject_ordinary_words(text: str) -> None:
    assert found(text) == {}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Python or R is required.", {"Python": "required", "R": "required"}),
        ("Use Python, R, and SQL.", {"Python": "mentioned", "R": "mentioned", "SQL": "mentioned"}),
        ("Experience with R is preferred.", {"R": "preferred"}),
        ("Build services in the Go language.", {"Go": "mentioned"}),
        ("Golang is a plus.", {"Go": "preferred"}),
        (
            "Python, Go, or R scripts are welcome.",
            {"Python": "mentioned", "Go": "mentioned", "R": "mentioned"},
        ),
    ],
)
def test_ambiguous_tokens_match_with_documented_context(
    text: str, expected: dict[str, str]
) -> None:
    assert found(text) == expected


def test_only_ambiguous_token_matches_have_lower_confidence() -> None:
    skills = {
        skill.skill_name: skill for skill in extract_skills("Python or R is required.", TECHNICAL)
    }
    assert skills["R"].confidence == AMBIGUOUS_CONFIDENCE
    assert skills["Python"].confidence == MATCH_CONFIDENCE
    golang = extract_skills("Golang is required.", TECHNICAL)
    assert golang[0].confidence == MATCH_CONFIDENCE


@pytest.mark.parametrize(
    "text",
    [
        "Python is required.",
        "Python is preferred.",
        "Python is used here.",
        "Python is not required.",
        "Requirements:\n- Python",
    ],
)
def test_confidence_does_not_depend_on_requirement_strength(text: str) -> None:
    assert [skill.confidence for skill in extract_skills(text, SEED)] == [MATCH_CONFIDENCE]


def test_duplicate_mentions_keep_strongest_category_and_its_evidence() -> None:
    skills = extract_skills(
        "SQL appears in our stack. SQL is preferred. Strong SQL is required. SQL again.", SEED
    )
    assert len(skills) == 1
    assert skills[0].requirement_type == "required"
    assert skills[0].evidence_excerpt == "Strong SQL is required."


def test_equal_duplicates_keep_earliest_evidence() -> None:
    skills = extract_skills("SQL is required. Advanced SQL is also required.", SEED)
    assert skills[0].evidence_excerpt == "SQL is required."


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Python is not required.", "mentioned"),
        ("No prior Python experience is required.", "mentioned"),
        ("Python isn't required for this role.", "mentioned"),
        ("Python is preferred but not required.", "preferred"),
        ("Python preferred, not required.", "preferred"),
        ("Python is a nice-to-have.", "preferred"),
        ("Python would be an asset.", "preferred"),
        ("Knowledge of Python is a strong plus.", "preferred"),
        ("You must have Python experience.", "required"),
        ("Python is mandatory.", "required"),
        ("Python is used across the team.", "mentioned"),
        ("Python helps meet business needs.", "mentioned"),
    ],
)
def test_requirement_context_and_negation(text: str, expected: str) -> None:
    assert found(text, SEED) == {"Python": expected}


def test_nearest_cue_classifies_each_skill_in_shared_sentence() -> None:
    assert found("SQL is required and Docker is preferred.") == {
        "SQL": "required",
        "Docker": "preferred",
    }
    assert found("SQL is required but Docker is not required.") == {
        "SQL": "required",
        "Docker": "mentioned",
    }
    assert found("SQL, Python, and Docker are required.") == {
        "SQL": "required",
        "Python": "required",
        "Docker": "required",
    }


def test_section_headings_apply_to_their_list_items() -> None:
    text = """About the team: we value SQL dashboards.
Requirements:
- Python
- SQL
Nice to have:
- Docker
We are a small team that ships analytics products and occasionally writes JS for internal tools.
- Node.js
"""
    skills = {skill.skill_name: skill for skill in extract_skills(text, TECHNICAL)}
    assert {name: skill.requirement_type for name, skill in skills.items()} == {
        "Python": "required",
        "SQL": "required",
        "Docker": "preferred",
        "JavaScript": "mentioned",
        "Node.js": "mentioned",
    }
    assert skills["Python"].evidence_excerpt == "Python"


def test_unbulleted_line_ends_heading_context() -> None:
    text = "Requirements:\n- Python\nBenefits\nFree Docker training for staff"
    assert found(text, SEED) == {"Python": "required", "Docker": "mentioned"}


def test_only_bulleted_lines_inherit_heading_context() -> None:
    assert found("Requirements:\nPython\nSQL", SEED) == {"Python": "mentioned", "SQL": "mentioned"}
    assert found("Nice to have:\n1. Docker\n* SQL", SEED) == {
        "Docker": "preferred",
        "SQL": "preferred",
    }


def test_unicode_casefold_mismatch_is_skipped_without_crashing() -> None:
    # Case-insensitive regex matches "İ" as "i", but casefold() expands it to "i̇".
    assert extract_skills("JavaScrİpt is required.", SEED) == []
    assert found("JavaScrİpt and JavaScript are required.", SEED) == {"JavaScript": "required"}


def test_explicit_clause_cue_overrides_heading() -> None:
    text = "Requirements:\n- Python is not required\n- SQL"
    assert found(text, SEED) == {"Python": "mentioned", "SQL": "required"}


@pytest.mark.parametrize("text", [None, "", "   \n\t", "No recognized skills here."])
def test_empty_or_skill_free_input_produces_no_annotations(text: str | None) -> None:
    assert extract_skills(text, SEED) == []


def test_empty_taxonomy_produces_no_annotations() -> None:
    assert extract_skills("Python is required.", Taxonomy([])) == []


def test_excerpts_are_bounded_and_contain_the_mention() -> None:
    filler = "Synthetic filler text about collaboration " * 20
    skills = extract_skills(f"{filler} Docker is preferred {filler}.", SEED)
    excerpt = skills[0].evidence_excerpt
    assert len(excerpt) <= EXCERPT_LIMIT
    assert "Docker is preferred" in excerpt
    assert excerpt.startswith("…") and excerpt.endswith("…")


def test_conflicting_alias_ownership_is_rejected() -> None:
    with pytest.raises(ExtractionError, match="more than one skill"):
        Taxonomy([SkillAlias(skill_id("A"), "A", "js"), SkillAlias(skill_id("B"), "B", "JS")])


def test_extraction_is_deterministic() -> None:
    text = "Python or R is required. Docker preferred. C/C++ is mentioned."
    assert extract_skills(text, TECHNICAL) == extract_skills(text, TECHNICAL)
