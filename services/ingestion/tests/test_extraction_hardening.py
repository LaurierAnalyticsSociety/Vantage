"""Regression tests for skill-rules-v2 hardening, one section per demonstrated mechanism.

Each mechanism is checked against its frozen development benchmark cases (failing before,
passing after) plus additional overmatching counterexamples. Held-out cases are never used here.
"""

from uuid import NAMESPACE_URL, uuid5

import pytest

from services.ingestion.extraction import SkillAlias, Taxonomy, extract_skills
from services.ingestion.extraction.evaluation.corpus import load_benchmark
from services.ingestion.extraction.evaluation.report import run

TAXONOMY = Taxonomy(
    SkillAlias(uuid5(NAMESPACE_URL, "https://vantage.example/hardening/" + name), name, alias)
    for name, aliases in {
        "AWS": [],
        "Docker": [],
        "Excel": ["Microsoft Excel"],
        "Git": [],
        "Java": [],
        "Kubernetes": [],
        "Power BI": [],
        "Python": [],
        "R": [],
        "SQL": [],
        "Tableau": [],
        "TypeScript": [],
    }.items()
    for alias in [name, *aliases]
)


def found(text: str) -> dict[str, str]:
    return {skill.skill_name: skill.requirement_type for skill in extract_skills(text, TAXONOMY)}


def development_status(tag: str) -> dict[str, str]:
    benchmark = load_benchmark()
    report = run(benchmark, ["development"], extract_skills)
    return {case["id"]: case["status"] for case in report["cases"] if tag in case["tags"]}


# ---- A. Headings without a trailing colon ----


def test_frozen_development_heading_cases_pass() -> None:
    statuses = development_status("candidate:heading-without-colon")
    assert set(statuses) == {"dev-001", "dev-002", "dev-003", "dev-004", "dev-005"}
    assert set(statuses.values()) == {"match"}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Requirements\n- Python\n- SQL\n\nNice to have\n- Docker",
            {"Python": "required", "SQL": "required", "Docker": "preferred"},
        ),
        (
            "## Required skills\n- Java\n- Git\n## Preferred skills\n- Kubernetes",
            {"Java": "required", "Git": "required", "Kubernetes": "preferred"},
        ),
        (
            "**Preferred qualifications**\n- Tableau\n- Power BI",
            {"Tableau": "preferred", "Power BI": "preferred"},
        ),
        ("Must have\n- TypeScript\n* AWS", {"TypeScript": "required", "AWS": "required"}),
        ("### Nice to have\n1. Git", {"Git": "preferred"}),
        ("__Mandatory__\n- Java", {"Java": "required"}),
        ("Not required\n- Docker", {"Docker": "mentioned"}),
    ],
)
def test_headings_without_colon_apply_to_following_bullets(
    text: str, expected: dict[str, str]
) -> None:
    assert found(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # A heading without a requirement cue leaves its items mentioned.
        ("Benefits\n- Free Docker training\n- Hybrid schedule", {"Docker": "mentioned"}),
        ("## About the team\n- Docker in production", {"Docker": "mentioned"}),
        # A sentence is not a heading, even when it is short and contains a cue.
        (
            "Python is required.\n- Weekly Excel office hours\n- Tableau licences",
            {"Python": "required", "Excel": "mentioned", "Tableau": "mentioned"},
        ),
        ("Travel is required.\n- Docker workshops", {"Docker": "mentioned"}),
        # A line naming a skill is content, not a heading.
        ("Python required\n- Excel workshops", {"Python": "required", "Excel": "mentioned"}),
        # Too long to be a heading.
        ("These are the tools we would prefer you know well\n- Docker", {"Docker": "mentioned"}),
        # Heading context still reaches only bulleted lines.
        ("Requirements\nWe use SQL daily.", {"SQL": "mentioned"}),
    ],
)
def test_ordinary_lines_do_not_become_headings(text: str, expected: dict[str, str]) -> None:
    assert found(text) == expected


def test_colonless_heading_evidence_is_the_bullet_text() -> None:
    skills = extract_skills("## Required skills\n- Java", TAXONOMY)
    assert [(skill.requirement_type, skill.evidence_excerpt) for skill in skills] == [
        ("required", "Java")
    ]


# ---- B. Negation scope across clauses ----


def test_frozen_development_negation_cases_pass() -> None:
    statuses = development_status("candidate:negation-scope")
    assert set(statuses) == {f"dev-{n:03d}" for n in range(6, 12)}
    assert set(statuses.values()) == {"match"}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("We don't sponsor visas, and SQL is required.", {"SQL": "required"}),
        ("This is not a remote position and Docker is required.", {"Docker": "required"}),
        ("No relocation is offered, so strong Python skills are required.", {"Python": "required"}),
        ("Applicants without a degree are welcome, and Java is required.", {"Java": "required"}),
        ("We never outsource testing, yet Git is mandatory.", {"Git": "required"}),
        ("Shifts are not fixed while Excel is essential.", {"Excel": "required"}),
    ],
)
def test_unrelated_earlier_negation_does_not_cancel_requirement(
    text: str, expected: dict[str, str]
) -> None:
    assert found(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("No prior Python experience is required.", {"Python": "mentioned"}),
        ("No Python and SQL experience is required.", {"Python": "mentioned", "SQL": "mentioned"}),
        (
            "No Python, SQL, or Docker experience is needed.",
            {"Python": "mentioned", "SQL": "mentioned", "Docker": "mentioned"},
        ),
        ("Python isn't required for this role.", {"Python": "mentioned"}),
        (
            "Docker and Kubernetes are not required, and Git is required.",
            {"Docker": "mentioned", "Kubernetes": "mentioned", "Git": "required"},
        ),
        (
            "Python is not required, and SQL is required.",
            {"Python": "mentioned", "SQL": "required"},
        ),
        (
            "We use Docker, and no Kubernetes knowledge is needed.",
            {"Docker": "mentioned", "Kubernetes": "mentioned"},
        ),
        ("Python preferred, not required.", {"Python": "preferred"}),
    ],
)
def test_true_negated_requirements_stay_mentioned(text: str, expected: dict[str, str]) -> None:
    assert found(text) == expected
