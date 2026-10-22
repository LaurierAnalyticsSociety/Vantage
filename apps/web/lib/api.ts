import { z } from "zod";

const externalUrl = z.string().url().refine((value) => {
  const url = new URL(value);
  return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password;
}, "Expected a safe HTTP URL");

export const programSchema = z.object({
  id: z.string().uuid(), name: z.string(), slug: z.string(), catalog_year: z.string(),
  institution: z.string(), description: z.string().nullable(),
  source_url: externalUrl.nullable(), is_synthetic: z.boolean(),
});

export const programDetailSchema = programSchema.extend({
  courses: z.array(z.object({
    id: z.string().uuid(), code: z.string(), title: z.string(),
    requirement_type: z.string(), source_url: externalUrl.nullable(),
  })),
});

const evidenceSchema = z.object({
  code: z.string(), title: z.string(), coverage_level: z.string(),
  evidence_excerpt: z.string(), evidence_url: externalUrl,
});

export const curriculumSkillSchema = z.object({
  id: z.string().uuid(), name: z.string(), category: z.string(),
  supporting_courses: z.array(evidenceSchema),
});

export const jobSchema = z.object({
  id: z.string().uuid(), title: z.string(), company_name: z.string(),
  source_url: externalUrl, apply_url: externalUrl.nullable(), source_name: z.string(),
  is_synthetic: z.boolean(), location_raw: z.string().nullable(),
  employment_type: z.string(), work_mode: z.string(), role: z.string().nullable(),
  last_seen_at: z.string(), posted_at: z.string().nullable(),
  salary_min: z.union([z.string(), z.number()]).nullable(),
  salary_max: z.union([z.string(), z.number()]).nullable(),
  salary_currency: z.string().nullable(), salary_period: z.string().nullable(),
});

export const jobDetailSchema = jobSchema.extend({
  description_text: z.string().nullable(),
  skills: z.array(z.object({
    id: z.string().uuid(), name: z.string(), requirement_type: z.string(),
    confidence: z.number(), evidence_excerpt: z.string().nullable(),
  })),
});

export const jobPageSchema = z.object({
  items: z.array(jobSchema), next_cursor: z.string().nullable(),
});

export const alignmentSchema = z.object({
  job_id: z.string().uuid(), program_id: z.string().uuid(),
  status: z.enum(["scored", "insufficient_evidence"]), alignment_percent: z.number().nullable(),
  score_version: z.string(), disclaimer: z.string(),
  matched_skills: z.array(z.object({
    skill: z.string(), requirement_type: z.string(), coverage_level: z.string(),
    supporting_courses: z.array(evidenceSchema),
  })),
  unmapped_job_skills: z.array(z.string()),
});

export const metadataSchema = z.object({
  dataset_mode: z.enum(["empty", "synthetic", "observed", "mixed"]),
  active_jobs: z.number(), last_success_at: z.string().nullable(),
  observation_start: z.string().nullable(), provinces: z.array(z.string()),
  employment_types: z.array(z.string()), work_modes: z.array(z.string()),
  roles: z.array(z.string()), limitations: z.string(),
});

export type Program = z.infer<typeof programSchema>;
export type Job = z.infer<typeof jobSchema>;

export async function api<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const response = await fetch(`${baseUrl}${path}`, {
    cache: "no-store", signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) throw new Error("The data service is unavailable. Please try again.");
  const payload: unknown = await response.json();
  return schema.parse(payload);
}

export function queryString(values: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) if (value) query.set(key, value);
  const encoded = query.toString();
  return encoded ? `?${encoded}` : "";
}

export function displayDate(value: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    dateStyle: "medium", timeZone: "America/Toronto",
  }).format(new Date(value));
}
