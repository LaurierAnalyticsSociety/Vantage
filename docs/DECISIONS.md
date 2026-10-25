# Architecture decisions

## 2026-10-21 — Runnable foundation

Use **Vantage** as the working name. Preserve the supplied `PROJECT.md` verbatim. The initialized milestone is a runnable synthetic vertical slice rather than the complete eight-week P0 product. Web and API run locally; PostgreSQL is the user's dedicated empty hosted Supabase development project (`bsosjttkryawucbhrrdo`). No new cloud resource is provisioned.

## 2026-10-21 — Repository and dependencies

Use npm workspaces without an additional monorepo build system, Node 22.23.1, and Python 3.13.2 with a root virtual environment. Share Python tooling in one package with independently runnable API and worker entrypoints. Use Next.js App Router, Tailwind, FastAPI/Pydantic, and Psycopg. Add Scrapy, Playwright for collection, pandas, spaCy, Recharts, and Cytoscape only when their corresponding capabilities are implemented. Browser testing uses Playwright separately from collection.

Use webpack for production builds so compilation does not require Turbopack's local port binding in restricted development environments. Keep ESLint 9 while the included React lint plugin requires its context APIs; ESLint 10 was incompatible with the current plugin during verification.

## 2026-10-21 — SQL, migrations, and access

Use the private `vantage` schema and keep it outside the Supabase Data API's exposed schemas. API and worker use separate PostgreSQL logins inheriting narrowly granted group roles. Administrative credentials are used only by setup commands. Hosted URLs require TLS. API connections also default to read-only transactions.

Use `supabase/migrations` as the sole migration directory, adapting the blueprint's `database/migrations` layout to Supabase conventions. The Python migration command applies versioned SQL atomically under an advisory lock and records the standard `supabase_migrations.schema_migrations` ledger, which Supabase CLI commands can inspect. Applied migration contents are immutable. There is no dashboard-only schema setup and no automatic destructive rollback.

Enforce employer/source consistency with a composite foreign key. Triggers enforce academic-year consistency and immutable program/course years; new years require new records. Observation inserts must connect a job and scrape run from the same source. Use UUIDs, timezone-aware dates, source-scoped unique identities, and indexed joins as specified.

## 2026-10-21 — Demonstration boundaries

The seed is explicitly synthetic: two invented employers, four postings, one program, three courses, and five skills. Sources and academic provenance carry `is_synthetic`; job responses inherit this marker from their source. Demonstration institutions and course codes never assert real Laurier curriculum coverage. Example.org URLs are intentionally illustrative, not official evidence.

Seeding is development-only and refuses a database containing observed sources. Fixture ingestion is development-only, selects synthetic sources, performs no HTTP requests, and never closes jobs. Live collectors and closure reconciliation require a future implementation with source review and successful-run safeguards. All seeded sources remain disabled and pending access review.

## Deferred product decisions

Choose real programs and source allowlists after reviewing official evidence and access permissions. Require an explicit calendar-year context in links. Display raw compatible salary ranges with their currency/period; do not annualize. Keep numerical alignment experimental until evaluated. Public release licensing, production hosting budgets, and refresh schedules remain undecided.

## 2026-10-21 — Optional encrypted environment files

At the user's request, configure AGWA/git-crypt for `.env` and `.env.*`, with plaintext exceptions for example templates. Keep these files ignored by default; the explicit tracking helper verifies ciphertext in the index. Initialize a local symmetric key without choosing GPG recipients or making commits. Key exports must go outside the repository. This permits explicitly selected encrypted environment files while preserving the specification's prohibition on plaintext credentials in Git.

## 2026-10-21 — Contributor handoff boundary

The current initialization task prepares the repository so contributors can begin work. It includes dependency locks, setup tooling, environment templates, documentation, and CI configuration. Starting application services, bootstrapping the hosted database, seeding data, and running collectors are separate opt-in activities. Hosted credentials are not a prerequisite for preparing a contributor checkout. Preserve the existing synthetic scaffold while keeping further product development outside this initialization task.

## 2026-10-25 — Rule-based job-skill extraction

Fixture ingestion now produces `job_skills` with the deterministic standard-library extractor `skill-rules-v1` (see `services/ingestion/extraction/README.md`). Within each source's ingestion transaction it replaces the complete annotation set for every processed synthetic job, so stale evidence is removed and extraction failures roll back the source's writes. A purely negated requirement is recorded as `mentioned`; "preferred but not required" stays `preferred`. Confidence is a heuristic weight for identification certainty — uniform for unambiguous matches, lower only for ambiguous tokens such as R and Go — not requirement strength or measured accuracy. The seed keeps its `fixture-v1` annotations so CI and seeded databases work without ingestion; removing them requires a follow-up CI/setup change. The schema, taxonomy, and matching formula are unchanged.
