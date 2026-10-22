import Link from "next/link";
import { z } from "zod";
import { EmptyState, JobCard, SyntheticNotice } from "@/components/ui";
import { api, jobPageSchema, programSchema, queryString } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobsPage({ searchParams }: {
  searchParams: Promise<{ q?: string; work_mode?: string; employment_type?: string; cursor?: string; program_id?: string }>;
}) {
  const filters = await searchParams;
  const { program_id, ...apiFilters } = filters;
  const [page, programs] = await Promise.all([
    api(`/api/v1/jobs${queryString(apiFilters)}`, jobPageSchema),
    api("/api/v1/programs", z.array(programSchema)),
  ]);
  const selectedProgram = programs.find((program) => program.id === program_id);
  return <><header className="page-heading"><p className="eyebrow">Your next direction</p><h1>Explore opportunities.</h1>
    <p className="lead">Browse observed postings and inspect the coursework evidence behind skill alignment.</p>
    {selectedProgram && <p>Viewing with {selectedProgram.name} · {selectedProgram.catalog_year}. Open a job to inspect alignment.</p>}</header>
    {page.items.some((job) => job.is_synthetic) && <SyntheticNotice />}
    <form className="filters" action="/jobs"><label>Search jobs<input name="q" defaultValue={filters.q} placeholder="Role or skill, e.g. SQL" maxLength={200} /></label>
      <label>Work arrangement<select name="work_mode" defaultValue={filters.work_mode || ""}><option value="">All arrangements</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option></select></label>
      <label>Employment type<select name="employment_type" defaultValue={filters.employment_type || ""}><option value="">All types</option><option value="internship">Internship</option><option value="co_op">Co-op</option><option value="new_grad">New graduate</option><option value="full_time">Full time</option></select></label>
      {selectedProgram && <input type="hidden" name="program_id" value={selectedProgram.id} />}<button className="button" type="submit">Apply filters</button>
    </form>
    {page.items.length === 0 ? <EmptyState title="No matching postings">Try broader filters. An empty result does not mean there are no opportunities in the market.</EmptyState>
      : <div className="grid">{page.items.map((job) => <JobCard key={job.id} job={job} programId={selectedProgram?.id} />)}</div>}
    {page.next_cursor && <p><Link className="button secondary" href={`/jobs${queryString({...filters, cursor: page.next_cursor})}`}>Next page →</Link></p>}
    <p className="fine-print">Sorted by most recently observed. Source coverage is limited; source observations are not employer publication dates.</p>
  </>;
}
