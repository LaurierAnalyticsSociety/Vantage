-- Bind :program_id in application code; this is a named parameter, not literal SQL.
select distinct s.id, s.name, s.category
from vantage.program_courses pc
join vantage.course_skills cs on cs.course_id = pc.course_id
join vantage.skills s on s.id = cs.skill_id
where pc.program_id = :program_id
  and pc.requirement_type = 'required'
  and cs.verification_status = 'verified'
  and cs.coverage_level in ('introduced', 'practiced', 'assessed')
order by s.name;
