# Operations runbook

Contributor preparation ends with dependency installation, environment templates, and repository tooling; see [contributor setup](../README.md#contributor-setup). The database bootstrap and service startup below are optional runtime procedures, separate from preparing the repository for handoff. Hosted credentials are unnecessary for contributor setup.

## Hosted development bootstrap

The development project reference is `bsosjttkryawucbhrrdo`. Configure its administrative session-pooler PostgreSQL URL in root `.env` as `MIGRATION_DATABASE_URL`, with TLS required. MCP authorization alone does not provide the application's database password.

Run `npm run db:migrate`, then `npm run db:roles`, `npm run db:seed`, and `npm run ingest:fixture`. Migrations run atomically and serialize concurrent setup calls. The migration command detects edits to previously applied files recorded by this runner. Never reset remote migration history to force a changed migration through.

Role provisioning creates `vantage_api` inheriting `vantage_reader` and `vantage_ingestion` inheriting `vantage_writer`. Passwords are generated, not committed or printed, and connection strings are saved to a mode-0600 root `.env`. Existing login roles are preserved; configure their existing credentials rather than rotating them implicitly. The hosted pooler username includes the project reference. Future migrations must explicitly grant needed privileges on new objects.

## Resume interrupted initialization

Use Node 22.23.1 from `.nvmrc` and Python 3.13.2. From the repository root, reinstall with `npm ci`, then `npm run setup`; setup preserves existing environment files. Keep `package-lock.json` and both Python locks unchanged when recovering an installation. A registry DNS failure requires restored network access, not a dependency-version change.

Psycopg is required even when the database is not configured. Confirm `.venv/bin/python -m pip check` succeeds after setup. API tests skipped because Psycopg is missing do not establish API readiness; the full Python type check also requires `psycopg` and `psycopg_pool`.

Run `npm run secrets:init` to initialize Git on `main` and git-crypt. If an agent sandbox denies creation of `.git`, run this command in your normal local terminal. Environment files remain ignored until explicitly selected for encrypted tracking; initialization creates no commit.

If you choose to run the hosted demo, configure `MIGRATION_DATABASE_URL` locally before the hosted bootstrap commands above. Supabase API keys do not supply the PostgreSQL password. Keep the root `.env` owner-only (`chmod 600 .env`), and never paste its contents into setup logs.

For full validation, start a working Docker daemon and use a disposable PostgreSQL 17 database whose name ends in `_test`. Supply its loopback connection URL as `TEST_DATABASE_URL` for database tests. For browser tests, also set `APP_ENV=test`, `DATABASE_URL` to that same local database, and `CI=true` so Playwright starts its own servers. Run the full test suite first so its database fixture applies migrations and the synthetic seed, then run `npm run test:e2e`. These overrides belong to the test process, not the hosted development `.env`.

Run `npm run check` after dependencies are complete. Browser and development smoke checks require permission to bind localhost ports; a sandbox `listen EPERM` leaves those checks unverified even when the production build passes. Embedded PostgreSQL checks can supplement validation of migration SQL but do not replace the Psycopg integration tests, browser workflows, or hosted readiness check.

## Start and verify

Run `npm run dev`. Verify `/health`, then `/api/v1/metadata`. The first checks process/configuration state; the second exercises database access. Visit the web app and follow program → jobs → job detail. The current fixture produces a 75% experimental alignment for the synthetic Data Analyst Intern.

Synthetic seed commands do not overwrite existing rows or enable collectors. Repeated fixture ingestion updates four source-scoped jobs and creates new observations for successful runs without duplicates. No network collector or scheduler is configured.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Process healthy but data endpoints return 503 | Database URL, TLS, credentials, pooler hostname, migrations, role grants |
| Data displays as empty | Seed/import state; empty coverage must not become invented metrics |
| Role bootstrap reports an existing login | Supply its existing connection URL locally; passwords are not silently reset |
| Migration reports an altered applied file | Restore the applied file and create a new forward migration |
| Hosted CLI fails writing telemetry in a sandbox | The application setup does not depend on CLI state; for manual CLI use, `SUPABASE_TELEMETRY_DISABLED=1` avoids telemetry writes |
| Browser test cannot find Chromium | Install via `npx playwright install chromium` in the web workspace |

Error responses expose a request ID and safe message, not SQL or credentials. Correlate request IDs with server logs. Worker completion emits a structured event with counts. Database setup errors deliberately avoid dumping connection strings.

## Future live ingestion and deployment

Before enabling a real source, complete the source registry review, replace/isolate demonstration data, implement adapter retries and resource limits, record failed/partial runs, and test closure reconciliation using fully successful checks only. The fixture worker is not a production collector.

Future frontend deployment needs only the API URL. API/worker secrets remain server-side. Configure an explicit CORS allowlist and keep `vantage` outside exposed Supabase schemas. No production deployment or scheduled collection runs are created by this scaffold.

## Recovery

Migrations are forward-only; an error rolls back the current atomic setup transaction. Restore a managed backup when recovery requires reversing committed data/schema changes, or ship a reviewed compensating migration. Do not automatically drop application schemas, reset a hosted database, or delete source observations during recovery.
