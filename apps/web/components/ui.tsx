import Link from "next/link";
import { displayDate, type Job } from "@/lib/api";

export function EmptyState({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="panel empty-state"><h2>{title}</h2><p>{children}</p></div>;
}

export function SyntheticNotice() {
  return <aside className="notice"><strong>Synthetic demo data.</strong> These employers, jobs,
    courses, and evidence are illustrative. They do not describe real openings or Laurier curricula.</aside>;
}

export function JobCard({ job, programId }: { job: Job; programId?: string }) {
  const destination = `/jobs/${job.id}${programId ? `?program_id=${encodeURIComponent(programId)}` : ""}`;
  return <article className="panel job-card">
    <div className="eyebrow">{job.company_name}{job.is_synthetic ? " · Demo" : ""}</div>
    <h2><Link href={destination}>{job.title}<span aria-hidden="true"> ↗</span></Link></h2>
    <p>{job.location_raw || "Location not reported"}</p>
    <div className="tags"><span>{job.employment_type.replaceAll("_", " ")}</span>
      <span>{job.work_mode}</span>{job.role && <span>{job.role.replaceAll("-", " ")}</span>}</div>
    <p className="fine-print">Observed {displayDate(job.last_seen_at)} · {job.source_name}</p>
  </article>;
}
