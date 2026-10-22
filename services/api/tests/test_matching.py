from uuid import UUID, uuid4

import pytest

from services.api.app.schemas.models import CourseEvidence, CurriculumSkill, JobSkill
from services.api.app.services.matching import calculate_alignment


def evidence(skill_id: UUID, level: str = "practiced") -> CurriculumSkill:
    return CurriculumSkill(
        id=skill_id,
        name="Python",
        category="Programming",
        supporting_courses=[
            CourseEvidence.model_validate(
                {
                    "code": "DEMO101",
                    "title": "Synthetic foundations",
                    "coverage_level": level,
                    "evidence_excerpt": "Synthetic practice with Python.",
                    "evidence_url": "https://example.org/evidence",
                }
            )
        ],
    )


def test_weights_preserve_unmapped_requirements_and_explanations() -> None:
    python, docker = uuid4(), uuid4()
    result = calculate_alignment(
        uuid4(),
        uuid4(),
        [
            JobSkill(id=python, name="Python", requirement_type="required", confidence=1),
            JobSkill(id=docker, name="Docker", requirement_type="preferred", confidence=1),
        ],
        [evidence(python)],
    )
    assert result.alignment_percent == pytest.approx(46.7)
    assert result.unmapped_job_skills == ["Docker"]
    assert result.matched_skills[0].supporting_courses[0].code == "DEMO101"


def test_strongest_course_coverage_counts_once() -> None:
    skill = uuid4()
    curriculum = evidence(skill, "introduced")
    curriculum.supporting_courses.extend(evidence(skill, "assessed").supporting_courses)
    result = calculate_alignment(
        uuid4(),
        uuid4(),
        [JobSkill(id=skill, name="Python", requirement_type="required", confidence=0.8)],
        [curriculum],
    )
    assert result.alignment_percent == 100
    assert len(result.matched_skills) == 1


@pytest.mark.parametrize("confidence", [0, 1])
def test_missing_curriculum_never_implies_zero_student_ability(confidence: float) -> None:
    result = calculate_alignment(
        uuid4(),
        uuid4(),
        [JobSkill(id=uuid4(), name="Python", requirement_type="required", confidence=confidence)],
        [],
    )
    assert result.status == "insufficient_evidence"
    assert result.alignment_percent is None


def test_no_extracted_skills_has_no_percentage() -> None:
    result = calculate_alignment(uuid4(), uuid4(), [], [evidence(uuid4())])
    assert result.status == "insufficient_evidence"
    assert result.alignment_percent is None
