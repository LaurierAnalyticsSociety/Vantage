-- Excludes synthetic postings. Counts describe the active observed source cohort only.
with cohort as (
    select j.id from vantage.jobs j
    join vantage.job_sources source on source.id = j.source_id
    where j.status = 'active' and not source.is_synthetic
)
select s.name, count(distinct js.job_id) as posting_count,
       (select count(*) from cohort) as denominator,
       round(100.0 * count(distinct js.job_id) /
             nullif((select count(*) from cohort), 0), 1) as posting_share_percent
from cohort
join vantage.job_skills js on js.job_id = cohort.id
join vantage.skills s on s.id = js.skill_id
group by s.id, s.name
order by posting_count desc, s.name;
