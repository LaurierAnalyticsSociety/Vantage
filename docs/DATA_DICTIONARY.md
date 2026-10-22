# Data dictionary

Canonical schema: `vantage`. Definitions live in versioned SQL migrations. All public responses use explicit Pydantic models; worker/provider payloads and source configuration are not serialized publicly.

| Table | Identity and meaning |
| --- | --- |
| `companies` | UUID employer identity; unique slug |
| `job_sources` | Employer-specific source; unique employer/base URL; adapter key/config; disabled by default; access review status; synthetic marker; last successful refresh |
| `scrape_runs` | One collection attempt; running/success/partial/failed; timestamps, counters, adapter version, internal error summary |
| `job_roles` | Canonical role family and unique slug |
| `jobs` | Unique `(source_id, source_key)`; raw display and normalized role/location fields; current activity state; original links; first/last observed times |
| `job_observations` | Unique `(job_id, scrape_run_id)`; observed presence/content hash, not a complete historical revision |
| `skills` | Shared canonical taxonomy with unique slug and category |
| `skill_aliases` | Unique normalized alias linked to a skill |
| `job_skills` | Unique job/skill; required/preferred/mentioned status, confidence from 0 to 1, excerpt, extraction version/time |
| `curriculum_sources` | Unique academic provenance URL; source kind, catalog year, review timestamps, synthetic marker |
| `programs` | Unique slug/catalog year; institution and academic source |
| `courses` | Unique code/catalog year; description and academic source |
| `program_courses` | Program/course requirement relationship: required, choice_group, concentration, elective; optional grouping and suggested year |
| `course_skills` | Course/skill evidence with excerpt and URL; coverage level and pending/verified/rejected review state |
| `program_roles` | Program/role relationship with relevance and rationale |

## Rules

- UUIDs identify entities. Dates are timezone-aware UTC timestamps. Catalog years are explicit labels, such as `2026/27`, and immutable within a program/course record.
- Jobs must share their employer with the referenced source. Observation jobs and runs must share a source. Program/course relationships must share their academic year.
- `posted_at` is the employer's date and can be null. `first_seen_at`/`last_seen_at` reflect observations; seeded demonstration dates are illustrative.
- Missing salaries remain null. Store currency and hour/month/year/other period separately, with nonnegative ordered ranges. No annualization or missing-value substitution is performed.
- `missing_successful_runs` is reserved for future closure reconciliation. Current fixture ingestion resets seen records to active but never closes absent records.
- Default curriculum skills require a compulsory course, verified evidence, and introduced/practiced/assessed coverage. Merely mentioned topics, pending claims, and electives are excluded.
- Synthetic markers distinguish demonstration provenance. These records must not enter published job-market metrics.
- Raw adapter `source_payload` is excluded from serialization and not persisted by the fixture worker. Text is normalized to plain text and rendered through React text nodes.

Reverse-join indexes supplement primary and unique constraints. Active-job cursor pagination uses descending `(last_seen_at, id)`; observations and source runs are time-indexed. Full-text search uses the same English title/description expression as its GIN index.
