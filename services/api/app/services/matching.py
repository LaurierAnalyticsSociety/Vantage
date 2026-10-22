from uuid import UUID

from services.api.app.schemas.models import Alignment, CurriculumSkill, JobSkill, MatchedSkill

REQUIREMENT_WEIGHTS = {"required": 3.0, "preferred": 1.5, "mentioned": 1.0}
COVERAGE_WEIGHTS = {"mentioned": 0.0, "introduced": 0.35, "practiced": 0.70, "assessed": 1.0}


def calculate_alignment(
    job_id: UUID, program_id: UUID, job_skills: list[JobSkill], curriculum: list[CurriculumSkill]
) -> Alignment:
    documented = {skill.id: skill for skill in curriculum}
    denominator = numerator = 0.0
    matches: list[MatchedSkill] = []
    unmapped: list[str] = []
    for requirement in job_skills:
        if requirement.confidence <= 0:
            continue
        weight = REQUIREMENT_WEIGHTS[requirement.requirement_type] * requirement.confidence
        denominator += weight
        skill = documented.get(requirement.id)
        if skill is None or not skill.supporting_courses:
            unmapped.append(requirement.name)
            continue
        strongest = max(
            skill.supporting_courses, key=lambda course: COVERAGE_WEIGHTS[course.coverage_level]
        )
        coverage = COVERAGE_WEIGHTS[strongest.coverage_level]
        if coverage == 0:
            unmapped.append(requirement.name)
            continue
        numerator += weight * coverage
        matches.append(
            MatchedSkill(
                skill=requirement.name,
                requirement_type=requirement.requirement_type,
                coverage_level=strongest.coverage_level,
                supporting_courses=skill.supporting_courses,
            )
        )
    sufficient = denominator > 0 and bool(documented)
    return Alignment(
        job_id=job_id,
        program_id=program_id,
        status="scored" if sufficient else "insufficient_evidence",
        alignment_percent=round(100 * numerator / denominator, 1) if sufficient else None,
        matched_skills=matches,
        unmapped_job_skills=unmapped,
    )
