# Vantage

A foundation for the Laurier Analytics Society curriculum-to-career platform. [PROJECT.md](PROJECT.md) is the original product specification, copied unchanged. This repository implements a **synthetic development workflow**, not a released job-market dataset.

The web application supports program selection, curriculum evidence, job search, and an explained experimental alignment score. The worker runs offline fixtures only. Real collectors, verified Laurier mappings, comparison/trends dashboards, and production deployment are subsequent milestones.

## Contributor setup

Requirements: Node **22.23.1**, npm 10+, Python **3.13.2**, and package-registry access. Commands target macOS/Linux.

```sh
nvm use
npm ci
npm run setup
```

Setup installs the Python development dependencies, creates a virtual environment, and copies environment templates **without overwriting existing files**. This prepares the checkout for contributors; it does not start services, connect to Supabase, apply migrations, or load data. Database credentials and Docker are unnecessary for this setup step.

Read [AGENTS.md](AGENTS.md), [PROJECT.md](PROJECT.md), and [architecture decisions](docs/DECISIONS.md) before contributing. Run `npm run check` for lint, formatting, type checks, core tests, and the frontend build. Database tests require separate local test configuration; browser tests start services and are a separate opt-in check.

Repository maintainers can initialize Git and optional environment-file encryption with `npm run secrets:init`; see [environment-file encryption](docs/SECRETS.md). Contributors cloning an encrypted repository should follow its unlock instructions instead.

## Optional: run the synthetic demo

When ready to run the demo, configure a dedicated empty development database. The initial maintainer's hosted Supabase project reference is `bsosjttkryawucbhrrdo`; coordinate access with the maintainer rather than assuming it is available to every contributor. Docker is unnecessary for hosted development.

Edit root `.env` and set `MIGRATION_DATABASE_URL` using the development project's administrative PostgreSQL **session pooler** connection string, including `?sslmode=require`. Get it from the project's Connect panel. This is a database password, separate from MCP authentication. Only then run:

```sh
npm run db:migrate
npm run db:roles
npm run db:seed
npm run ingest:fixture
npm run dev
```

`db:roles` creates dedicated API/worker logins and writes their generated connection URLs directly to ignored root `.env`; it never prints passwords. Existing logins are preserved. The API receives read access; the worker receives restricted write access. Leave `APP_ENV=development` for synthetic seeding and fixture ingestion.

- Web: <http://localhost:3000>
- API process health: <http://localhost:8000/health>
- API documentation: <http://localhost:8000/docs>

The frontend template contains only `NEXT_PUBLIC_API_BASE_URL`. Never put database URLs or privileged keys in frontend environment files. Server configuration is loaded explicitly from root `.env`, regardless of the current working directory.

Without a database connection, process health works and the homepage displays an unavailable-data state. There is no silent fallback that presents invented records as real data. `/health` indicates configuration, not database readiness; a successful `/api/v1/metadata` request verifies connectivity and schema availability.

## Development commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start local API and web application |
| `npm run lint` | Python and frontend lint checks |
| `npm run format:check` | Python formatting check |
| `npm run typecheck` | Python and TypeScript checks |
| `npm test` | Core tests and database tests when configured |
| `npm run test:database` | Database tests only; requires disposable local PostgreSQL |
| `npm run test:e2e` | Browser workflow against a seeded development database |
| `npm run build` | Production frontend build; no database needed |
| `npm run check` | Lint, formatting, typing, tests, and build |

Install the browser before running browser tests: `cd apps/web && npx playwright install chromium`. CI provisions PostgreSQL 17, applies migrations and seed, and runs the full checks and browser workflow independently of hosted credentials. Database tests require `TEST_DATABASE_URL` with a local hostname and a database name ending in `_test`; never point them at your hosted development project.

JavaScript dependencies are locked by `package-lock.json`. Python runtime dependencies are pinned in `requirements.lock`; development dependencies in `requirements-dev.lock`. To update Python locks, resolve the project and development extras in a clean Python 3.13 environment, run `pip check`, freeze exact versions, and review both locks together.

## Repository

The application and services follow the structure in the specification: `apps/web`, `services/api`, and `services/ingestion`. Shared server settings and database management live in `services/common`. SQL migrations have one canonical location, `supabase/migrations`; synthetic seeds and reusable queries live under `database`.

Public API operations are GET-only under `/api/v1`: metadata, programs, program detail/skills, jobs, job detail, and job alignment. The jobs endpoint supports full-text search, role, province, work arrangement, employment type, and cursor pagination (20 records by default, maximum 100). Other proposed endpoints remain unimplemented.

## Supabase MCP

MCP connects the coding agent to Supabase; the application connects using PostgreSQL credentials. Configure and authenticate the MCP server in your own Codex environment. The supplied project reference is recorded above. No MCP credentials are stored in this repository.

## Contributor documentation

- [Architecture decisions](docs/DECISIONS.md)
- [Source registry](docs/SOURCES.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)
- [Matching method](docs/MATCHING.md)
- [Operations runbook](docs/RUNBOOK.md)
- [Environment-file encryption](docs/SECRETS.md)

Licensing and public release approval remain open decisions. No production deployment or live source collection is configured.
