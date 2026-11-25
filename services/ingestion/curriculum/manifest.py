from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

# Type Checking
CatalogYear = str
RequirementType = Literal["required", "choice_group", "concentration", "elective"]
CoverageLevel = Literal["mentioned", "introduced", "practiced", "assessed"]
SourceType = Literal["academic_calendar", "course_description", "course_outline", "other_official"]
ExtractionMethod = Literal["manual", "rules", "model_assisted"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# CurriculumSource : Referred by Programs & Courses
class CurriculumSource(StrictModel):
    source_url: HttpUrl
    source_type: SourceType  # refers source type
    catalog_year: CatalogYear = Field(pattern=r"^\d{4}/\d{2}$")
    is_synthetic: bool
    title: str | None = None
    last_checked_at: datetime | None = None

    @field_validator("last_checked_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("last_checked_at must include a timezone")
        return value


# Program : Referred by ProgramCourse
#          Refers CurriculumSource
class Program(StrictModel):
    institution: str = Field(min_length=1)
    name: str = Field(min_length=1)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    degree_type: str | None = None
    catalog_year: CatalogYear = Field(pattern=r"^\d{4}/\d{2}$")
    description: str | None = None

    @field_validator("institution", "name", "degree_type", "description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Text values must not be blank")
        return value


# Course : Referred by ProgramCourse & CourseSkill
#         Refers CurriculumSource
class Course(StrictModel):
    code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    catalog_year: CatalogYear = Field(pattern=r"^\d{4}/\d{2}$")
    description: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Course code must not be blank")
        return value

    @field_validator("title", "description")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Text values must not be blank")
        return value


# ProgramCourse : Refers Program and Courses
class ProgramCourse(StrictModel):
    program_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    course_code: str = Field(min_length=1)
    requirement_type: RequirementType
    choice_group: str | None = None
    suggested_year: int | None = Field(default=None, ge=1, le=6)
    notes: str | None = None

    @field_validator("course_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Course code must not be blank")
        return value

    @field_validator("choice_group", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Text values must not be blank")
        return value

    @model_validator(mode="after")
    def validate_choice_group(self) -> Self:
        if self.requirement_type == "choice_group" and self.choice_group is None:
            raise ValueError("choice_group relationships require a choice_group identifier")
        if self.requirement_type != "choice_group" and self.choice_group is not None:
            raise ValueError("choice_group is only valid for choice_group relationships")
        return self


# CourseSkill : Refers to Courses & Skills (job ingestion url)
class CourseSkill(StrictModel):
    course_code: str = Field(min_length=1)
    skill_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    coverage_level: CoverageLevel
    evidence_excerpt: str = Field(min_length=1)
    evidence_url: HttpUrl
    extraction_method: ExtractionMethod = "manual"

    @field_validator("course_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Course code must not be blank")
        return value

    @field_validator("evidence_excerpt")
    @classmethod
    def strip_evidence(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Evidence excerpt must not be blank")
        return value


class CurriculumManifest(StrictModel):
    catalog_year: CatalogYear = Field(pattern=r"^\d{4}/\d{2}$")
    source: CurriculumSource
    programs: list[Program] = Field(min_length=1)
    courses: list[Course] = Field(min_length=1)
    program_courses: list[ProgramCourse]
    course_skills: list[CourseSkill]

    @model_validator(mode="after")
    def validate_catalog_years(self) -> Self:
        if self.source.catalog_year != self.catalog_year:
            raise ValueError("Source catalog_year must match manifest catalog_year")
        for program in self.programs:
            if program.catalog_year != self.catalog_year:
                raise ValueError(f"Program {program.slug!r} catalog_year must match the manifest")
        for course in self.courses:
            if course.catalog_year != self.catalog_year:
                raise ValueError(f"Course {course.code!r} catalog_year must match the manifest")
        return self


def validate_manifest(manifest: CurriculumManifest) -> None:
    program_slugs = [program.slug for program in manifest.programs]
    if len(program_slugs) != len(set(program_slugs)):
        raise ValueError("Duplicate program slug in this catalog year")

    course_codes = [course.code for course in manifest.courses]
    if len(course_codes) != len(set(course_codes)):
        raise ValueError("Duplicate course code in this catalog year")

    program_set = set(program_slugs)
    course_set = set(course_codes)
    relationship_keys: set[tuple[str, str]] = set()
    for relationship in manifest.program_courses:
        if relationship.program_slug not in program_set:
            raise ValueError(f"Unknown program in requirement: {relationship.program_slug}")
        if relationship.course_code not in course_set:
            raise ValueError(f"Unknown course in requirement: {relationship.course_code}")
        key = (relationship.program_slug, relationship.course_code)
        if key in relationship_keys:
            raise ValueError(f"Duplicate program-course requirement: {key[0]} / {key[1]}")
        relationship_keys.add(key)

    evidence_keys: set[tuple[str, str]] = set()
    for evidence in manifest.course_skills:
        if evidence.course_code not in course_set:
            raise ValueError(f"Unknown course in course_skills: {evidence.course_code}")
        key = (evidence.course_code, evidence.skill_slug)
        if key in evidence_keys:
            raise ValueError(f"Duplicate course-skill evidence: {key[0]} / {key[1]}")
        evidence_keys.add(key)
