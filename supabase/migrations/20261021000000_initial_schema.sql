-- Core identities
create schema vantage;
revoke all on schema vantage from public;
set local search_path = vantage, pg_catalog;

create table companies (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text not null unique,
    industry text,
    careers_url text,
    created_at timestamptz not null default now()
);

create table job_sources (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id),
    source_type text not null check (source_type in ('greenhouse', 'lever', 'html', 'custom_api')),
    base_url text not null,
    adapter_key text not null,
    config jsonb not null default '{}'::jsonb,
    enabled boolean not null default false,
    is_synthetic boolean not null default false,
    access_review_status text not null default 'pending'
        check (access_review_status in ('pending', 'approved', 'blocked')),
    last_success_at timestamptz,
    created_at timestamptz not null default now(),
    unique (company_id, base_url)
);

create table scrape_runs (
    id uuid primary key default gen_random_uuid(),
    source_id uuid not null references job_sources(id),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null default 'running'
        check (status in ('running', 'success', 'partial', 'failed')),
    fetched_count integer not null default 0 check (fetched_count >= 0),
    inserted_count integer not null default 0 check (inserted_count >= 0),
    updated_count integer not null default 0 check (updated_count >= 0),
    error_count integer not null default 0 check (error_count >= 0),
    error_summary text,
    adapter_version text
);

create table job_roles (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    name text not null,
    category text not null
);

create table jobs (
    id uuid primary key default gen_random_uuid(),
    source_id uuid not null references job_sources(id),
    company_id uuid not null references companies(id),
    source_key text not null,
    external_id text,
    title text not null,
    description_text text,
    source_url text not null,
    apply_url text,
    role_id uuid references job_roles(id),
    employment_type text not null default 'unknown'
        check (employment_type in ('internship', 'co_op', 'new_grad', 'full_time', 'part_time', 'unknown')),
    work_mode text not null default 'unknown'
        check (work_mode in ('onsite', 'hybrid', 'remote', 'unknown')),
    location_raw text,
    city text,
    province text,
    country text,
    salary_raw text,
    salary_min numeric(14,2),
    salary_max numeric(14,2),
    salary_currency char(3),
    salary_period text check (salary_period in ('hour', 'month', 'year', 'other')),
    posted_at timestamptz,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    status text not null default 'active'
        check (status in ('active', 'inactive', 'unknown')),
    missing_successful_runs integer not null default 0
        check (missing_successful_runs >= 0),
    content_hash text,
    updated_at timestamptz not null default now(),
    unique (source_id, source_key),
    check (salary_min is null or salary_min >= 0),
    check (salary_max is null or salary_max >= 0),
    check (salary_min is null or salary_max is null or salary_min <= salary_max)
);

create table job_observations (
    id bigint generated always as identity primary key,
    job_id uuid not null references jobs(id) on delete cascade,
    scrape_run_id uuid not null references scrape_runs(id) on delete cascade,
    observed_at timestamptz not null default now(),
    content_hash text,
    unique (job_id, scrape_run_id)
);

-- Skill taxonomy and job evidence
create table skills (
    id uuid primary key default gen_random_uuid(),
    slug text not null unique,
    name text not null,
    category text not null
);

create table skill_aliases (
    id uuid primary key default gen_random_uuid(),
    skill_id uuid not null references skills(id) on delete cascade,
    alias text not null,
    normalized_alias text not null unique
);

create table job_skills (
    job_id uuid not null references jobs(id) on delete cascade,
    skill_id uuid not null references skills(id) on delete cascade,
    requirement_type text not null default 'mentioned'
        check (requirement_type in ('required', 'preferred', 'mentioned')),
    confidence numeric(4,3) not null default 1.000
        check (confidence between 0 and 1),
    evidence_excerpt text,
    extraction_version text not null,
    extracted_at timestamptz not null default now(),
    primary key (job_id, skill_id)
);

-- Academic sources; store verified provenance
create table curriculum_sources (
    id uuid primary key default gen_random_uuid(),
    source_url text not null unique,
    is_synthetic boolean not null default false,
    source_type text not null
        check (source_type in ('academic_calendar', 'course_description', 'course_outline', 'other_official')),
    catalog_year text,
    title text,
    last_checked_at timestamptz,
    created_at timestamptz not null default now()
);

create table programs (
    id uuid primary key default gen_random_uuid(),
    institution text not null default 'Wilfrid Laurier University',
    name text not null,
    slug text not null,
    degree_type text,
    catalog_year text not null,
    source_id uuid references curriculum_sources(id),
    description text,
    unique (slug, catalog_year)
);

create table courses (
    id uuid primary key default gen_random_uuid(),
    code text not null,
    title text not null,
    catalog_year text not null,
    description text,
    source_id uuid references curriculum_sources(id),
    unique (code, catalog_year)
);

create table program_courses (
    program_id uuid not null references programs(id) on delete cascade,
    course_id uuid not null references courses(id) on delete cascade,
    requirement_type text not null
        check (requirement_type in ('required', 'choice_group', 'concentration', 'elective')),
    choice_group text,
    suggested_year smallint check (suggested_year between 1 and 6),
    notes text,
    primary key (program_id, course_id)
);

create table course_skills (
    course_id uuid not null references courses(id) on delete cascade,
    skill_id uuid not null references skills(id) on delete cascade,
    coverage_level text not null
        check (coverage_level in ('mentioned', 'introduced', 'practiced', 'assessed')),
    evidence_excerpt text not null,
    evidence_url text not null,
    verification_status text not null default 'pending'
        check (verification_status in ('pending', 'verified', 'rejected')),
    extraction_method text not null default 'manual'
        check (extraction_method in ('manual', 'rules', 'model_assisted')),
    verified_at timestamptz,
    primary key (course_id, skill_id)
);

create table program_roles (
    program_id uuid not null references programs(id) on delete cascade,
    role_id uuid not null references job_roles(id) on delete cascade,
    relevance text not null default 'related'
        check (relevance in ('primary', 'related', 'exploratory')),
    rationale text,
    primary key (program_id, role_id)
);

-- Frequently used filters, joins and diagnostics
create index jobs_active_role_idx on jobs (role_id, last_seen_at desc)
    where status = 'active';
create index jobs_company_idx on jobs (company_id);
create index jobs_location_idx on jobs (province, city);
create index jobs_employment_idx on jobs (employment_type, work_mode);
create index jobs_posted_idx on jobs (posted_at desc);
create index jobs_source_status_idx on jobs (source_id, status);
create index jobs_fts_idx on jobs using gin (
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description_text, ''))
);
create index job_skills_by_skill_idx on job_skills (skill_id, requirement_type);
create index course_skills_by_skill_idx on course_skills (skill_id, verification_status);
create index program_courses_by_course_idx on program_courses (course_id);
create index scrape_runs_source_time_idx on scrape_runs (source_id, started_at desc);
create index job_observations_by_job_time_idx on job_observations (job_id, observed_at desc);
