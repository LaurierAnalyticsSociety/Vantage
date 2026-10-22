import Link from "next/link";
import { z } from "zod";
import { EmptyState, SyntheticNotice } from "@/components/ui";
import { api, displayDate, metadataSchema, programSchema } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const result = await Promise.allSettled([
    api("/api/v1/programs", z.array(programSchema)),
    api("/api/v1/metadata", metadataSchema),
  ]);
  const programs = result[0].status === "fulfilled" ? result[0].value : null;
  const metadata = result[1].status === "fulfilled" ? result[1].value : null;

  return <>
    <section className="hero"><p className="eyebrow">A clearer view of what comes next</p>
      <h1>Connect your coursework<br />to your next opportunity.</h1>
      <p className="lead">Explore how documented course skills relate to what employers request.
        Every connection should come with evidence you can inspect.</p>
      <div className="tags"><span>Program-aware exploration</span><span>Explainable skill overlap</span><span>No account required</span></div>
    </section>
    {metadata && ["synthetic", "mixed"].includes(metadata.dataset_mode) && <SyntheticNotice />}
    <div className="section-heading"><div><p className="eyebrow">Start with your curriculum</p><h2>Choose a program and calendar year</h2></div>
      <p>{metadata?.last_success_at ? `Last refresh ${displayDate(metadata.last_success_at)}` : "No successful collection recorded yet"}</p></div>
    {programs === null ? <EmptyState title="The data service is unavailable">Start the API and configure the development database, then refresh this page.</EmptyState>
      : programs.length === 0 ? <EmptyState title="No programs available yet">Import evidence-backed curriculum data, or load the synthetic development seed.</EmptyState>
      : <div className="grid">{programs.map((program) => <article className="panel" key={program.id}>
        <p className="eyebrow">{program.is_synthetic ? "Synthetic demonstration" : program.institution}</p>
        <h2>{program.name}</h2><p>Academic calendar {program.catalog_year}</p><p>{program.description}</p>
        <Link className="button" href={`/programs/${program.slug}?catalog_year=${encodeURIComponent(program.catalog_year)}`}>Explore program →</Link>
      </article>)}</div>}
    <div className="section-heading"><div><p className="eyebrow">Evidence before assumptions</p><h2>A starting point for exploration</h2></div></div>
    <div className="grid"><article className="panel"><h3>See the connection</h3><p>Follow a job requirement back to a skill and the course evidence behind it. Electives are excluded from default program alignment.</p></article>
      <article className="panel"><h3>Understand the limits</h3><p>Coursework overlap does not establish personal proficiency or hiring eligibility. <Link href="/methodology">Read the methodology</Link>.</p></article></div>
  </>;
}
