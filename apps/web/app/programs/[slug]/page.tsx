import Link from "next/link";
import { notFound } from "next/navigation";
import { z } from "zod";
import { EmptyState, SyntheticNotice } from "@/components/ui";
import { api, curriculumSkillSchema, programDetailSchema, programSchema, queryString } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function ProgramPage({ params, searchParams }: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ catalog_year?: string }>;
}) {
  const { slug } = await params;
  const { catalog_year } = await searchParams;
  const programs = await api(`/api/v1/programs${queryString({catalog_year})}`, z.array(programSchema));
  const selected = programs.find((program) => program.slug === slug);
  if (!selected) notFound();
  const [program, skills] = await Promise.all([
    api(`/api/v1/programs/${selected.id}`, programDetailSchema),
    api(`/api/v1/programs/${selected.id}/skills`, z.array(curriculumSkillSchema)),
  ]);

  return <><p className="breadcrumb"><Link href="/">Programs</Link> / {program.catalog_year}</p>
    <header className="page-heading"><p className="eyebrow">{program.institution}</p><h1>{program.name}</h1><p className="lead">{program.description}</p>
      <p>Academic calendar {program.catalog_year}. Requirements may differ by entry year.</p>
      <Link className="button" href={`/jobs?program_id=${program.id}`}>Explore jobs with this program →</Link></header>
    {program.is_synthetic && <SyntheticNotice />}
    <div className="section-heading"><h2>{skills.length} documented required-course skills</h2></div>
    {skills.length === 0 && <EmptyState title="Insufficient curriculum evidence">Verified required-course evidence is needed before calculating alignment.</EmptyState>}
    <div className="grid">{skills.map((skill) => <article className="panel" key={skill.id}><p className="eyebrow">{skill.category}</p><h2>{skill.name}</h2>
      {skill.supporting_courses.map((course) => <div className="evidence" key={course.code}><h3>{course.code} · {course.title}</h3><p>{course.coverage_level} coverage</p>
        <p>{course.evidence_excerpt}</p><a href={course.evidence_url} target="_blank" rel="noopener noreferrer">{program.is_synthetic ? "Illustrative source URL ↗" : "View course evidence ↗"}</a></div>)}</article>)}</div>
    <div className="section-heading"><h2>Course requirement structure</h2></div>
    <div className="panel">{program.courses.map((course) => <p key={course.id}><strong>{course.code}</strong> · {course.title} <span className="fine-print">({course.requirement_type.replaceAll("_", " ")})</span></p>)}</div>
  </>;
}
