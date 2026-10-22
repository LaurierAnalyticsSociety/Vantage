import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from psycopg import sql

from services.api.app.schemas.models import (
    Course,
    CourseEvidence,
    CurriculumSkill,
    Job,
    JobDetail,
    JobPage,
    JobSkill,
    Program,
    ProgramDetail,
)
from services.common.database import DatabaseConnection

PROGRAM_SELECT = """
select p.*, cs.source_url, coalesce(cs.is_synthetic, false) as is_synthetic
from vantage.programs p left join vantage.curriculum_sources cs on cs.id = p.source_id
"""
JOB_SELECT = """
select j.*, c.name as company_name, s.adapter_key as source_name, s.is_synthetic,
       r.slug as role
from vantage.jobs j join vantage.companies c on c.id = j.company_id
join vantage.job_sources s on s.id = j.source_id
left join vantage.job_roles r on r.id = j.role_id
"""


def programs(
    connection: DatabaseConnection, catalog_year: str | None = None, search: str | None = None
) -> list[Program]:
    rows = connection.execute(
        PROGRAM_SELECT
        + """where (%s::text is null or p.catalog_year = %s)
        and (%s::text is null or p.name ilike %s)
        order by p.name, p.catalog_year desc, p.id""",
        (catalog_year, catalog_year, search, f"%{search}%" if search else None),
    ).fetchall()
    return [Program.model_validate(row) for row in rows]


def program(connection: DatabaseConnection, program_id: UUID) -> ProgramDetail:
    row = connection.execute(PROGRAM_SELECT + "where p.id = %s", (program_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Program not found.")
    courses = connection.execute(
        """select c.id, c.code, c.title, pc.requirement_type, cs.source_url
        from vantage.program_courses pc join vantage.courses c on c.id = pc.course_id
        left join vantage.curriculum_sources cs on cs.id = c.source_id
        where pc.program_id = %s order by c.code""",
        (program_id,),
    ).fetchall()
    return ProgramDetail(**row, courses=[Course.model_validate(course) for course in courses])


def curriculum_skills(
    connection: DatabaseConnection, program_id: UUID, required_only: bool = True
) -> list[CurriculumSkill]:
    program(connection, program_id)
    rows = connection.execute(
        """select s.id, s.name, s.category, c.code, c.title,
        cs.coverage_level, cs.evidence_excerpt, cs.evidence_url
        from vantage.program_courses pc
        join vantage.courses c on c.id = pc.course_id
        join vantage.course_skills cs on cs.course_id = c.id
        join vantage.skills s on s.id = cs.skill_id
        where pc.program_id = %s and (not %s or pc.requirement_type = 'required')
          and cs.verification_status = 'verified'
          and cs.coverage_level in ('introduced', 'practiced', 'assessed')
        order by s.name, c.code""",
        (program_id, required_only),
    ).fetchall()
    grouped: dict[UUID, CurriculumSkill] = {}
    for row in rows:
        skill_id = row["id"]
        if skill_id not in grouped:
            grouped[skill_id] = CurriculumSkill(
                id=skill_id, name=row["name"], category=row["category"], supporting_courses=[]
            )
        grouped[skill_id].supporting_courses.append(CourseEvidence.model_validate(row))
    return list(grouped.values())


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        if len(cursor) > 512:
            raise ValueError("Oversized cursor")
        timestamp, identifier = json.loads(base64.urlsafe_b64decode(cursor).decode())
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            raise ValueError("Cursor requires timezone")
        return parsed, UUID(identifier)
    except (ValueError, TypeError, UnicodeError, binascii.Error) as error:
        raise HTTPException(422, "Invalid pagination cursor.") from error


def jobs(
    connection: DatabaseConnection,
    *,
    q: str | None = None,
    role: str | None = None,
    province: str | None = None,
    work_mode: str | None = None,
    employment_type: str | None = None,
    page_size: int = 20,
    cursor: str | None = None,
) -> JobPage:
    clauses = [sql.SQL("j.status = 'active'")]
    parameters: list[object] = []
    for column, value in [
        ("r.slug", role),
        ("j.province", province),
        ("j.work_mode", work_mode),
        ("j.employment_type", employment_type),
    ]:
        if value:
            clauses.append(sql.SQL(column + " = %s"))
            parameters.append(value)
    if q:
        clauses.append(
            sql.SQL(
                "to_tsvector('english', coalesce(j.title, '') || ' ' || "
                "coalesce(j.description_text, '')) @@ plainto_tsquery('english', %s)"
            )
        )
        parameters.append(q)
    if cursor:
        clauses.append(sql.SQL("(j.last_seen_at, j.id) < (%s, %s)"))
        parameters.extend(decode_cursor(cursor))
    parameters.append(page_size + 1)
    rows = connection.execute(
        sql.SQL(JOB_SELECT)
        + sql.SQL("where ")
        + sql.SQL(" and ").join(clauses)
        + sql.SQL(" order by j.last_seen_at desc, j.id desc limit %s"),
        parameters,
    ).fetchall()
    items = [Job.model_validate(row) for row in rows[:page_size]]
    next_cursor = None
    if len(rows) > page_size:
        last = items[-1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps([last.last_seen_at.isoformat(), str(last.id)]).encode()
        ).decode()
    return JobPage(items=items, next_cursor=next_cursor)


def job(connection: DatabaseConnection, job_id: UUID) -> JobDetail:
    row = connection.execute(JOB_SELECT + "where j.id = %s", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Job not found.")
    skills = connection.execute(
        """select s.id, s.name, js.requirement_type, js.confidence, js.evidence_excerpt
        from vantage.job_skills js join vantage.skills s on s.id = js.skill_id
        where js.job_id = %s order by s.name""",
        (job_id,),
    ).fetchall()
    return JobDetail(**row, skills=[JobSkill.model_validate(skill) for skill in skills])
