# Skill extraction

`skills.py` is a typed, deterministic, rule-based extractor (`skill-rules-v2`; see [version history](#version-history)). It resolves job-description text to canonical `vantage.skills` IDs using the skill names and `vantage.skill_aliases`, and returns one annotation per skill with a requirement type, bounded heuristic confidence, evidence excerpt, and extraction version. It uses only the Python standard library; spaCy and model dependencies remain deferred until evaluated against labeled permitted descriptions.

## Usage

Fixture ingestion runs extraction automatically (`npm run ingest:fixture`). Inside each synthetic source's ingestion transaction, the worker loads the taxonomy, extracts skills for every processed job, deletes that job's existing `job_skills` rows, and inserts the new set. Removed requirements therefore leave no stale evidence, repeated runs create no duplicates, a missing description yields an empty set, and an extraction error rolls back that source's job, run, observation, and annotation writes together.

```python
from services.ingestion.extraction import SkillAlias, Taxonomy, extract_skills, load_taxonomy

taxonomy = load_taxonomy(connection)  # or Taxonomy([SkillAlias(skill_id, "SQL", "SQL"), ...])
skills = extract_skills(description_text, taxonomy)
```

The SQL seed still inserts `fixture-v1` annotations so a seeded database works before ingestion; fixture ingestion replaces them with `skill-rules-v2` rows.

## Rules

**Matching.** All aliases compile into one case-insensitive pattern, longest alias first, so `Node.js` wins over `JS` and `Python 3` over `Python`. Boundaries treat `+`, `#`, and `.` as identifier characters: `C` does not match inside `C++`, `JS` does not match inside `Node.js` (even when Node.js is absent from the taxonomy), `.NET` does not match inside `ASP.NET`, and `SQL` does not match `SQLite`. A sentence-ending period is not part of an identifier. An alias owned by two different skills is rejected with `ExtractionError`.

**Segmentation.** Text is split into lines, sentences, and clauses. Clauses break at `;` and at contrast words (`but`, `however`, `although`, `though`, `whereas`). The evidence excerpt is the whole sentence, capped at 240 characters around the mention.

**Requirement type.** Within a clause, the nearest eligible cue applies; ties resolve to the weaker category. *(v2)* Eligible cues are those in the skill's own segment (see negation below for segment breaks). If the skill's segment has no cue, only cues from segments that name no skill of their own are eligible, so a cue introducing a list still applies ("Must have experience with dashboards, SQL, and Excel") but a cue already governing another skill group does not leak ("Python is required and Tableau or Power BI is a plus" makes Tableau preferred; "SQL is required, Excel is preferred, and our team also uses Tableau" leaves Tableau mentioned). Skills joined in one coordinated list share its cue ("SQL, Python, and Docker are required").

- Required cues: *required*, *requires*, *requirement(s)*, *must (have)*, *mandatory*, *essential*, *needed*, *you/we/will need*, *minimum qualifications*.
- Preferred cues: *preferred*, *preferably*, *nice to have*, *a (strong) asset*, *a (big) plus*, *bonus*, *ideally*, *desirable*, *desired*.
- A negation (*not*, *no*, *never*, *without*, *isn't*, *don't*, …) cancels a required cue only when it lies in the cue's own **segment** and after any previous required cue. *(v2)* Segments break a clause at commas and at *and*, *so*, *yet*, and *while*, except where those join a coordinated skill list (accepted skills separated only by `,`, `/`, *and*, *or*, `&`). So "We don't sponsor visas, and SQL is required" keeps SQL required, while "No Python and SQL experience is required" and "No Python, SQL, or Docker experience is needed" negate every listed skill. A purely negated requirement — "Python is not required", "No prior Python experience is required" — is classified as **mentioned**, never required.
- "Docker is preferred but not required" stays **preferred**: the contrast word separates the clauses, and the preferred cue is unaffected.
- A short heading ending in a colon (`Requirements:`, `Nice to have:`, `Preferred qualifications:`) applies only to the bulleted or numbered lines (`-`, `*`, `•`, `1.`, `1)`) that follow it. Any other unbulleted line ends the heading's context. An explicit cue in the item overrides the heading.
- *(v2)* A heading may also omit the colon (`Requirements`, `## Required skills`, `**Nice to have**`, `__Mandatory__`). After removing a leading Markdown `#` marker or whole-line `**`/`__` emphasis, an unbulleted line is such a heading only if it has at most six words, does not end in `.`, `!`, or `?`, names no taxonomy skill, and contains a required or preferred cue. Ordinary lines therefore never become headings: `Benefits` and `## About the team` carry no cue, `Travel is required.` is a sentence, and `Python required` names a skill. Like colon headings, it applies only to the bulleted lines that follow it.
- With no cue, the skill is **mentioned**.

Repeated mentions of one skill keep the strongest category (required > preferred > mentioned), then the higher confidence, then the earliest evidence.

**Confidence** is a bounded design weight for certainty that the skill was identified correctly, not a measured probability and not requirement strength: 0.9 for every unambiguous alias match, whether required, preferred, or mentioned, and 0.6 for an ambiguous-token match (R, Go, C). The matching formula already weights requirement types and multiplies by confidence, so varying confidence by requirement type would double-count it and shift alignment scores. With uniform confidence, all four synthetic fixture jobs keep the alignment scores of the seed's confidence-1 annotations. A regex match whose text cannot be resolved back to a known alias (possible with unusual Unicode case folding, such as `İ`) is dropped rather than guessed.

## Ambiguous tokens

`R`, `Go`, `C`, and any single-letter alias are ordinary words or letters and are matched conservatively. A match requires all of:

1. The text has the alias's stored casing and starts uppercase (`R`, `Go`; never `r` or `go`).
2. It is not part of a word compound: `R&D`, `R-squared`, `go-to` are rejected.
3. It has technology context: an adjacent language qualifier (`R programming`, `Go language`, `R scripts`, `experience with R`, `proficiency in C`), or it appears in a coordinated list (`,`, `/`, `and`, `or`, `&`) with another accepted skill in the same clause (`Python, R, or SQL`, `C/C++`).
4. At the start of a sentence or clause, only a following qualifier counts, so "Go to our careers page" is rejected.

Unambiguous aliases such as `Golang` match normally. These rules deliberately miss some genuine mentions (for example "R is required." standing alone) rather than invent requirements.

## Version history

- `skill-rules-v1` — initial rules (PR #4). Baseline benchmark reports: `benchmark/reports/baseline/`.
- `skill-rules-v2` — hardening driven by demonstrated development-split failures; see the rule changes below and `benchmark/ERROR_ANALYSIS.md`. Matching, ambiguity policy, confidence, evidence excerpts, and deduplication are unchanged.

## Offline evaluation

`benchmark/` holds a versioned synthetic benchmark (`bench-1`): an isolated 21-skill taxonomy with stable keys (`taxonomy.json`), 40 development cases (`development.json`), and 20 held-out cases (`heldout.json`), labeled per [`benchmark/ANNOTATION.md`](benchmark/ANNOTATION.md). The evaluator runs the extractor directly on that taxonomy; it uses no database, network, credentials, or production taxonomy.

```sh
.venv/bin/python -m services.ingestion.extraction.evaluation --split development
.venv/bin/python -m services.ingestion.extraction.evaluation --split heldout \
  --json-out report.json --summary-out report.md --min-exact-f1 0.8
```

`--split` is `development`, `heldout`, or `all`. The Markdown summary prints to stdout. The exit status is 0 for any completed run, including imperfect scores; 1 when `--min-exact-f1` is given and exact-label F1 is below it or undefined; and 2 for invalid arguments or benchmark input, which is reported with the file, JSON location, and fix (unknown fields, duplicate case IDs within or across splits, duplicate or unknown expected skills, invalid categories, conflicting aliases, version mismatches, malformed JSON).

**Metrics.** Skill identification scores distinct `(case_id, skill)` pairs; exact label scores distinct `(case_id, skill, requirement_type)` tuples, so a correctly identified skill with the wrong category is an identification TP but an exact-label FP and FN. Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2TP/(2TP+FP+FN); any zero denominator yields `null` (N/A), including F1 when TP = FP = FN = 0. Duplicate predictions collapse to distinct items and are counted. Per-skill metrics report support as expected cases containing the skill; per-category exact-label metrics report support as expected tuples in the category. The category confusion matrix covers identification TPs only (a skill predicted with several categories counts as its strongest); missed and spurious skills are counted beside it.

**Reports.** JSON reports are deterministic (sorted keys, six-decimal rounding, LF endings, no timestamps) and record the split, extractor version, corpus version and per-split fingerprints, taxonomy fingerprint, and every case's expected labels, predictions with evidence, and differences. Fingerprints are SHA-256 over canonical JSON, so formatting and line endings do not change them. Committed reports live in `benchmark/reports/<stage>/<split>.{json,md}`; tests verify that they match the frozen corpus and, for the current extractor version, regenerate byte-for-byte.

**Split discipline.** Labels and the 40/20 split were frozen and committed (`benchmark/FREEZE.json`) before any evaluator run. Twenty development cases are probes authored to target candidate failure mechanisms; the other 40 cases form 20 stratified pairs, each split one-to-development and one-to-held-out by a salted hash recorded in the freeze file. Tune against development only; run held-out for the baseline and final reports. Moving a held-out case into development requires replacement held-out cases and a new freeze entry. A test fails if any split's fingerprint departs from the latest freeze entry; label errata must be recorded there and never made to raise scores.

**Reproducing a baseline.** Reports from an earlier extractor version are reproduced from the commit that produced them, for example `git worktree add ../vantage-baseline <commit>` and the command above with `--json-out`, then a byte comparison with the committed report.

**Benchmark limitations.** One author wrote the descriptions, labels, and rules, so held-out cases are not an independent sample and share the author's assumptions about phrasing; the probe pool was written with knowledge of the extractor's documented weaknesses. Sixty short cases give wide uncertainty. Scores are synthetic benchmark results, not real-world accuracy or calibrated confidence.

## Limitations

- No accuracy has been measured. The four synthetic fixtures and unit-test sentences exercise behavior only; they are not evidence of real-world precision or recall. A labeled evaluation set from permitted descriptions is still required before relying on extraction for analytics.
- The production taxonomy contains only the five synthetic seed skills. Technical identifiers (C++, C#, .NET, Node.js) and ambiguous tokens (R, Go, C) are covered by isolated test taxonomies until reviewed taxonomy additions exist.
- Cue and negation detection are lexical, not syntactic. List detection is lexical too: in "We use Tableau, and SQL is required" the `, and` between two skills reads as a coordinated list, so Tableau shares the required cue. A cue about something else in the same clause can be attributed to a skill: "Must be eligible to work in Canada and familiar with Excel" marks Excel required. A negation in the same segment that governs something else still cancels a requirement ("No travel is required for SQL work" makes SQL mentioned). Long-range or implied requirements are not resolved, and abbreviations such as "e.g." may split sentences.
- Evidence for a heading-inherited requirement is only the bullet text (for example "Python"); the heading that made it required or preferred is not included in the excerpt, so the displayed evidence does not fully explain its classification.
- HTML list items converted to plain text lose their bullet markers, so they do not inherit heading context and are classified from their own wording only.
- Eligibility constraints, years of experience, and proficiency levels are not extracted.
