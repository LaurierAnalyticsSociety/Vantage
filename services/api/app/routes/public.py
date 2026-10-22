from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from services.api.app.queries import catalog
from services.api.app.schemas.models import (
    Alignment,
    CurriculumSkill,
    EmploymentType,
    Health,
    JobDetail,
    JobPage,
    Metadata,
    Program,
    ProgramDetail,
    WorkMode,
)
from services.api.app.services.matching import calculate_alignment
from services.common.database import DatabaseConnection, get_connection

router = APIRouter()
DB = Annotated[DatabaseConnection, Depends(get_connection)]


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    return Health(database_configured=request.app.state.pool is not None)


@router.get("/api/v1/metadata", response_model=Metadata)
def metadata(connection: DB) -> Metadata:
    row = connection.execute("""
        select count(*) as active_jobs, min(j.first_seen_at) as observation_start,
        bool_or(s.is_synthetic) as has_synthetic, bool_or(not s.is_synthetic) as has_observed
        from vantage.jobs j join vantage.job_sources s on s.id = j.source_id
        where j.status = 'active'
    """).fetchone()
    assert row is not None
    freshness = connection.execute(
        "select max(last_success_at) as last_success_at from vantage.job_sources"
    ).fetchone()
    filters = connection.execute("""select
        array_agg(distinct employment_type) as employment_types,
        array_agg(distinct work_mode) as work_modes,
        array_remove(array_agg(distinct province), null) as provinces
        from vantage.jobs where status = 'active'""").fetchone()
    assert filters is not None and freshness is not None
    roles = connection.execute("select slug from vantage.job_roles order by slug").fetchall()
    mode = "empty"
    if row["has_synthetic"] and row["has_observed"]:
        mode = "mixed"
    elif row["has_synthetic"]:
        mode = "synthetic"
    elif row["has_observed"]:
        mode = "observed"
    return Metadata.model_validate(
        {
            **row,
            **freshness,
            **{key: value or [] for key, value in filters.items()},
            "roles": [role["slug"] for role in roles],
            "dataset_mode": mode,
            "limitations": "Observed source coverage only. Synthetic records are illustrative, "
            "not real opportunities or verified Laurier curriculum. Alignment is experimental.",
        }
    )


@router.get("/api/v1/programs", response_model=list[Program])
def list_programs(
    connection: DB,
    catalog_year: Annotated[str | None, Query(max_length=20)] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> list[Program]:
    return catalog.programs(connection, catalog_year, search)


@router.get("/api/v1/programs/{program_id}", response_model=ProgramDetail)
def get_program(program_id: UUID, connection: DB) -> ProgramDetail:
    return catalog.program(connection, program_id)


@router.get("/api/v1/programs/{program_id}/skills", response_model=list[CurriculumSkill])
def get_program_skills(
    program_id: UUID, connection: DB, required_only: bool = True
) -> list[CurriculumSkill]:
    return catalog.curriculum_skills(connection, program_id, required_only)


@router.get("/api/v1/jobs", response_model=JobPage)
def list_jobs(
    connection: DB,
    q: Annotated[str | None, Query(max_length=200)] = None,
    role: Annotated[str | None, Query(max_length=100)] = None,
    province: Annotated[str | None, Query(max_length=100)] = None,
    work_mode: WorkMode | None = None,
    employment_type: EmploymentType | None = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> JobPage:
    return catalog.jobs(
        connection,
        q=q,
        role=role,
        province=province,
        work_mode=work_mode,
        employment_type=employment_type,
        page_size=page_size,
        cursor=cursor,
    )


@router.get("/api/v1/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: UUID, connection: DB) -> JobDetail:
    return catalog.job(connection, job_id)


@router.get("/api/v1/jobs/{job_id}/alignment", response_model=Alignment)
def get_alignment(job_id: UUID, program_id: UUID, connection: DB) -> Alignment:
    detail = catalog.job(connection, job_id)
    curriculum = catalog.curriculum_skills(connection, program_id, required_only=True)
    return calculate_alignment(job_id, program_id, detail.skills, curriculum)
