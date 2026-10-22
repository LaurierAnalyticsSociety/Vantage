# Source registry

No live source is currently approved or enabled. The fixture worker reads local data only.

| Source | Type | Collection | Review | Limitations |
| --- | --- | --- | --- | --- |
| `fixture-north` | Synthetic custom API shape | Local fixture, no HTTP | Pending; disabled | Invented employer and postings; example.org URLs |
| `fixture-maple` | Synthetic custom API shape | Local fixture, no HTTP | Pending; disabled | Invented employer and postings; example.org URLs |
| Synthetic curriculum | Illustrative academic shape | SQL seed, no HTTP | Synthetic only | Not an official Laurier source; verification flags exercise software only |

Before implementing or enabling a live adapter, record its organization, base URL, source type, adapter key/version, stable identifier, allowed collection method, public-access and terms review, review date, refresh frequency, per-domain rate/concurrency budget, content retention permissions, contact/removal route, and known coverage limitations. An accessible endpoint is not proof of collection permission.

Greenhouse/Lever APIs and Laurier calendar references listed in `PROJECT.md` are candidates, not an approved allowlist. Live job adapters should implement the `Adapter` protocol and yield validated `RawJob` records. Curriculum imports require official program requirements for a specific academic year and manual review of course-skill evidence.

Never collect authenticated academic records, applicant personal data, or material behind access controls. Disabling a source must remain independent of other sources. Review permission changes before resuming collection.
