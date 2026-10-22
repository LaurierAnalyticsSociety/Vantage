import Link from "next/link";
import { z } from "zod";
import { EmptyState, SyntheticNotice } from "@/components/ui";
import { alignmentSchema, api, displayDate, jobDetailSchema, programSchema } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobDetailPage({ params, searchParams }: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ program_id?: string }>;
}) {
  const { id } = await params;
  const { program_id } = await searchParams;
  const [job, programs] = await Promise.all([
    api(`/api/v1/jobs/${encodeURIComponent(id)}`, jobDetailSchema),
    api("/api/v1/programs", z.array(programSchema)),
  ]);
  const program = programs.find((item) => item.id === program_id);
  const alignment = program ? await api(
    `/api/v1/jobs/${job.id}/alignment?program_id=${program.id}`, alignmentSchema,
  ) : null;

  return <><p className="breadcrumb"><Link href={`/jobs${program ? `?program_id=${program.id}` : ""}`}>Explore jobs</Link> / Posting detail</p>
    <header className="page-heading"><p className="eyebrow">{job.company_name}</p><h1>{job.title}</h1>
      <p className="lead">{job.location_raw || "Location not reported"} · {job.work_mode}</p>
      <p className="fine-print">Last observed {displayDate(job.last_seen_at)} · {job.source_name}</p>
      <a className="button" href={job.apply_url || job.source_url} target="_blank" rel="noopener noreferrer">{job.is_synthetic ? "Illustrative posting URL ↗" : "Original employer posting ↗"}</a></header>
    {job.is_synthetic && <SyntheticNotice />}
    <div className="grid"><section className="panel"><h2>Posting details</h2><p className="description">{job.description_text || "No description provided."}</p>
      <h3>Reported compensation</h3><p>{job.salary_min !== null && job.salary_max !== null ? `${job.salary_currency || ""} ${job.salary_min}–${job.salary_max} / ${job.salary_period || "period unreported"}` : "Not reported"}</p>
      <h3>Extracted job skills</h3>{job.skills.length ? job.skills.map((skill) => <div className="evidence" key={skill.id}><h3>{skill.name} · {skill.requirement_type}</h3><p>{skill.evidence_excerpt}</p></div>) : <p>No skill evidence available.</p>}</section>
      <section className="panel"><p className="eyebrow">Experimental · coursework overlap</p><h2>Curriculum alignment</h2>
        <form action={`/jobs/${job.id}`}><label>Program and calendar year<select name="program_id" defaultValue={program?.id || ""}><option value="">Choose a program</option>
          {programs.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.catalog_year}</option>)}</select></label><p><button className="button" type="submit">View alignment</button></p></form>
        {!alignment ? <p>Select a program to see documented overlap.</p> : <>
          <h3>{program?.name} · {program?.catalog_year}</h3>
          {alignment.alignment_percent === null ? <EmptyState title="Insufficient evidence">There is not enough documented evidence to calculate an alignment percentage.</EmptyState>
            : <p className="score">{alignment.alignment_percent}%</p>}
          <p className="fine-print">{alignment.disclaimer}</p>
          <h3>Documented overlaps</h3>{alignment.matched_skills.length === 0 && <p>No verified required-course overlap documented.</p>}
          {alignment.matched_skills.map((skill) => <div className="evidence" key={skill.skill}><h3>{skill.skill} · {skill.coverage_level}</h3>
            {skill.supporting_courses.map((course) => <p key={course.code}><strong>{course.code}</strong> · {course.title}<br />{course.evidence_excerpt}<br /><a href={course.evidence_url} target="_blank" rel="noopener noreferrer">{job.is_synthetic ? "Illustrative course evidence ↗" : "Course evidence ↗"}</a></p>)}</div>)}
          <h3>Requirements without verified curriculum coverage</h3><p>{alignment.unmapped_job_skills.join(", ") || "None among the extracted requirements."}</p>
          <p className="fine-print">Electives and unverified course evidence are excluded. Method: {alignment.score_version}.</p>
        </>}
      </section></div>
  </>;
}
