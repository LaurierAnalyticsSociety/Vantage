set local search_path = vantage, pg_catalog;

-- Composite foreign keys prevent mismatched employer and observation provenance.
alter table job_sources add constraint source_company_identity unique (id, company_id);
alter table jobs add constraint jobs_source_company_fk
    foreign key (source_id, company_id) references job_sources(id, company_id);
alter table jobs add constraint jobs_source_identity unique (id, source_id);
alter table scrape_runs add constraint runs_source_identity unique (id, source_id);

create function vantage.check_program_course_year() returns trigger
language plpgsql set search_path = pg_catalog, vantage as $$
begin
    if (select catalog_year from vantage.programs where id = new.program_id)
       is distinct from
       (select catalog_year from vantage.courses where id = new.course_id) then
        raise exception 'Program and course catalog years must agree' using errcode = '23514';
    end if;
    return new;
end;
$$;
create trigger program_course_year before insert or update on program_courses
for each row execute function vantage.check_program_course_year();

create function vantage.prevent_catalog_year_change() returns trigger
language plpgsql set search_path = pg_catalog, vantage as $$
begin
    if new.catalog_year is distinct from old.catalog_year then
        raise exception 'Create a new version instead of changing a catalog year'
            using errcode = '23514';
    end if;
    return new;
end;
$$;
create trigger program_year_immutable before update on programs
for each row execute function vantage.prevent_catalog_year_change();
create trigger course_year_immutable before update on courses
for each row execute function vantage.prevent_catalog_year_change();

create function vantage.check_observation_source() returns trigger
language plpgsql set search_path = pg_catalog, vantage as $$
begin
    if (select source_id from vantage.jobs where id = new.job_id)
       is distinct from
       (select source_id from vantage.scrape_runs where id = new.scrape_run_id) then
        raise exception 'Observation job and run sources must agree' using errcode = '23514';
    end if;
    return new;
end;
$$;
create trigger observation_source before insert or update on job_observations
for each row execute function vantage.check_observation_source();

create index sources_company_idx on job_sources(company_id);
create index observations_run_idx on job_observations(scrape_run_id);
create index programs_source_idx on programs(source_id);
create index courses_source_idx on courses(source_id);
create index roles_reverse_idx on program_roles(role_id);
create index jobs_cursor_idx on jobs(last_seen_at desc, id desc) where status = 'active';

-- Group roles have no passwords. Login credentials are provisioned separately.
do $$ begin
    if not exists (select 1 from pg_roles where rolname = 'vantage_reader') then
        create role vantage_reader nologin;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'vantage_writer') then
        create role vantage_writer nologin;
    end if;
end $$;
revoke all on all tables in schema vantage from public;
revoke all on all sequences in schema vantage from public;
revoke all on all functions in schema vantage from public;
grant usage on schema vantage to vantage_reader, vantage_writer;
grant select on all tables in schema vantage to vantage_reader, vantage_writer;
grant insert, update on jobs, job_sources, scrape_runs, job_observations, job_skills
    to vantage_writer;
grant delete on job_skills to vantage_writer;
grant usage, select on all sequences in schema vantage to vantage_writer;
alter default privileges in schema vantage revoke all on tables from public;
alter default privileges in schema vantage revoke execute on functions from public;
-- Do not add vantage to the Supabase Data API's exposed schemas.
