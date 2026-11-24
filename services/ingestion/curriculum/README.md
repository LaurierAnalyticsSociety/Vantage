# Curriculum manifest workflow

This local Python CLI validates, previews, imports, and reviews curriculum records from a
structured JSON file. It does not crawl sources, infer required courses from a departmental
course list, create canonical skills, or approve evidence during import.

The included [manifest_test.json](manifest_test.json) is entirely synthetic. It does not describe
a Laurier program or course and uses `example.org` URLs. It exercises required, choice-group,
concentration, and elective relationships, plus existing canonical `python` and `sql` skills.

## Database configuration

The tool is a trusted manual administration command. It connects using the server-side
`MIGRATION_DATABASE_URL` already loaded by `services.common.settings.Settings`, not the API or
worker login. In development, the value is read from the root `.env`; in test/production it must
be injected as a server environment variable. Use a dedicated development or disposable local
database, never a production database for tests. The URL must use TLS when it points to a hosted
database.

## Commands

Run commands from the repository root with its Python environment:

```sh
python -m services.ingestion.curriculum.cli validate services/ingestion/curriculum/manifest_test.json
python -m services.ingestion.curriculum.cli dry-run services/ingestion/curriculum/manifest_test.json
python -m services.ingestion.curriculum.cli import services/ingestion/curriculum/manifest_test.json
python -m services.ingestion.curriculum.cli import services/ingestion/curriculum/manifest_test.json
python -m services.ingestion.curriculum.cli review --course-code CURR101 --catalog-year 2026/27 --skill-slug python --status verified
python -m services.ingestion.curriculum.cli review --course-code CURR101 --catalog-year 2026/27 --skill-slug python --status rejected
```

`validate` checks the manifest and its references against the database, including that every
skill slug already exists in `vantage.skills`. `dry-run` reports records to create/update, existing
relationships, unchanged evidence, and evidence that would be reset to pending; it performs no
writes.
`import` performs validation and writes all records within one transaction. Invalid input,
unknown skills, provenance conflicts, or database failures leave no partial import.

The importer preserves the database's canonical skill taxonomy. Add a new skill only through
the separately reviewed taxonomy process; a misspelled or unknown slug is an error. Re-running an
unchanged manifest is safe: entity/relationship identities are reused, and an existing
verified/rejected evidence decision remains unchanged. If evidence excerpt, URL, coverage, or
extraction method changes, that assertion returns to `pending` and `verified_at` is cleared.
New assertions are always pending.

`review` identifies one assertion by course code, catalog year, and canonical skill slug. A
reviewer must explicitly choose `verified` or `rejected`; verification records the current
timestamp, while rejection clears the verification timestamp. The command does not create an
assertion and cannot review an unknown course, year, or skill.

The existing public program-skills API only includes verified, non-mentioned evidence from
required courses by default. Verifying evidence attached to an elective, choice group, or
concentration does not make it compulsory or expose it in the default required-only response.

## Manifest contract

The strict Pydantic models in `manifest.py` reject undeclared fields. A manifest contains:

- A catalog-year-specific source URL, source type, explicit catalog year, synthetic marker, and
  optional title/check timestamp.
- One or more programs and courses, each carrying the same explicit catalog year.
- Explicit program-to-course relationships, including the program slug, course code, and
  `required`, `choice_group`, `concentration`, or `elective` category. Choice-group relationships
  also require a group identifier.
- Course-skill assertions with a canonical existing skill slug, coverage, non-empty evidence
  excerpt, evidence URL, and extraction method.

Program slugs and course codes must be unique within the catalog year. Relationships and evidence
must refer to declared programs/courses; duplicate or conflicting identities are rejected.
Source and evidence URLs are required. No relationship is inferred from a course list.

The schema has one provenance source for each manifest. Reusing an existing source URL with
different source type, catalog year, title, or synthetic status is rejected. Existing program or
course identities cannot be silently moved to another source. New catalog years use distinct
program/course identities and do not overwrite records from prior years.

## Tests

Curriculum manifest structure and CLI behavior are covered under
`services/ingestion/tests`. Database import, transaction, review, catalog-year, and API visibility
tests are under `services/api/tests` and use the repository's isolated local `_test` database
fixture. Run them with:

```sh
python -m pytest services/ingestion/tests services/api/tests
```
