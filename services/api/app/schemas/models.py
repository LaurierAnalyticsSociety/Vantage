from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl

EmploymentType = Literal["internship", "co_op", "new_grad", "full_time", "part_time", "unknown"]
WorkMode = Literal["onsite", "hybrid", "remote", "unknown"]
RequirementType = Literal["required", "preferred", "mentioned"]
CoverageLevel = Literal["mentioned", "introduced", "practiced", "assessed"]


class Model(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Health(Model):
    status: Literal["ok"] = "ok"
    database_configured: bool


class Error(Model):
    code: str
    message: str
    request_id: str


class Program(Model):
    id: UUID
    name: str
    slug: str
    catalog_year: str
    institution: str
    description: str | None = None
    source_url: HttpUrl | None = None
    is_synthetic: bool = False


class Course(Model):
    id: UUID
    code: str
    title: str
    requirement_type: str
    source_url: HttpUrl | None = None


class ProgramDetail(Program):
    courses: list[Course]


class CourseEvidence(Model):
    code: str
    title: str
    coverage_level: CoverageLevel
    evidence_excerpt: str
    evidence_url: HttpUrl


class CurriculumSkill(Model):
    id: UUID
    name: str
    category: str
    supporting_courses: list[CourseEvidence]


class Job(Model):
    id: UUID
    title: str
    company_name: str
    source_url: HttpUrl
    apply_url: HttpUrl | None = None
    source_name: str
    is_synthetic: bool
    location_raw: str | None = None
    province: str | None = None
    city: str | None = None
    employment_type: EmploymentType
    work_mode: WorkMode
    role: str | None = None
    last_seen_at: datetime
    posted_at: datetime | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    salary_period: str | None = None


class JobSkill(Model):
    id: UUID
    name: str
    requirement_type: RequirementType
    confidence: float
    evidence_excerpt: str | None = None


class JobDetail(Job):
    description_text: str | None = None
    skills: list[JobSkill]


class JobPage(Model):
    items: list[Job]
    next_cursor: str | None = None


class MatchedSkill(Model):
    skill: str
    requirement_type: RequirementType
    coverage_level: CoverageLevel
    supporting_courses: list[CourseEvidence]


class Alignment(Model):
    job_id: UUID
    program_id: UUID
    status: Literal["scored", "insufficient_evidence"]
    alignment_percent: float | None
    score_version: str = "heuristic-v1-experimental"
    matched_skills: list[MatchedSkill]
    unmapped_job_skills: list[str]
    disclaimer: str = (
        "Experimental curriculum alignment describes documented coursework overlap, "
        "not individual proficiency, eligibility, or hiring probability."
    )


class Metadata(Model):
    dataset_mode: Literal["empty", "synthetic", "observed", "mixed"]
    active_jobs: int
    last_success_at: datetime | None
    observation_start: datetime | None
    employment_types: list[str]
    work_modes: list[str]
    provinces: list[str]
    roles: list[str]
    limitations: str
