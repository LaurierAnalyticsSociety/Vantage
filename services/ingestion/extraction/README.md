# Skill extraction

`skills.py` is a typed, deterministic, rule-based extractor (`skill-rules-v1`). It resolves job-description text to canonical `vantage.skills` IDs using the skill names and `vantage.skill_aliases`, and returns one annotation per skill with a requirement type, bounded heuristic confidence, evidence excerpt, and extraction version. It uses only the Python standard library; spaCy and model dependencies remain deferred until evaluated against labeled permitted descriptions.

## Usage

Fixture ingestion runs extraction automatically (`npm run ingest:fixture`). Inside each synthetic source's ingestion transaction, the worker loads the taxonomy, extracts skills for every processed job, deletes that job's existing `job_skills` rows, and inserts the new set. Removed requirements therefore leave no stale evidence, repeated runs create no duplicates, a missing description yields an empty set, and an extraction error rolls back that source's job, run, observation, and annotation writes together.

```python
from services.ingestion.extraction import SkillAlias, Taxonomy, extract_skills, load_taxonomy

taxonomy = load_taxonomy(connection)  # or Taxonomy([SkillAlias(skill_id, "SQL", "SQL"), ...])
skills = extract_skills(description_text, taxonomy)
```

The SQL seed still inserts `fixture-v1` annotations so a seeded database works before ingestion; fixture ingestion replaces them with `skill-rules-v1` rows.

## Rules

**Matching.** All aliases compile into one case-insensitive pattern, longest alias first, so `Node.js` wins over `JS` and `Python 3` over `Python`. Boundaries treat `+`, `#`, and `.` as identifier characters: `C` does not match inside `C++`, `JS` does not match inside `Node.js` (even when Node.js is absent from the taxonomy), `.NET` does not match inside `ASP.NET`, and `SQL` does not match `SQLite`. A sentence-ending period is not part of an identifier. An alias owned by two different skills is rejected with `ExtractionError`.

**Segmentation.** Text is split into lines, sentences, and clauses. Clauses break at `;` and at contrast words (`but`, `however`, `although`, `though`, `whereas`). The evidence excerpt is the whole sentence, capped at 240 characters around the mention.

**Requirement type.** Within a clause, the cue nearest to the skill applies; ties resolve to the weaker category.

- Required cues: *required*, *requires*, *requirement(s)*, *must (have)*, *mandatory*, *essential*, *needed*, *you/we/will need*, *minimum qualifications*.
- Preferred cues: *preferred*, *preferably*, *nice to have*, *a (strong) asset*, *a (big) plus*, *bonus*, *ideally*, *desirable*, *desired*.
- A negation (*not*, *no*, *never*, *without*, *isn't*, *don't*, …) between the previous cue and a required cue cancels it. A purely negated requirement — "Python is not required", "No prior Python experience is required" — is classified as **mentioned**, never required.
- "Docker is preferred but not required" stays **preferred**: the contrast word separates the clauses, and the preferred cue is unaffected.
- A short heading ending in a colon (`Requirements:`, `Nice to have:`, `Preferred qualifications:`) applies only to the bulleted or numbered lines (`-`, `*`, `•`, `1.`, `1)`) that follow it. Any unbulleted line — including a short heading without a colon such as `Benefits` — ends the heading's context. An explicit cue in the item overrides the heading.
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

## Limitations

- No accuracy has been measured. The four synthetic fixtures and unit-test sentences exercise behavior only; they are not evidence of real-world precision or recall. A labeled evaluation set from permitted descriptions is still required before relying on extraction for analytics.
- The production taxonomy contains only the five synthetic seed skills. Technical identifiers (C++, C#, .NET, Node.js) and ambiguous tokens (R, Go, C) are covered by isolated test taxonomies until reviewed taxonomy additions exist.
- Cue and negation detection are lexical and clause-wide, not syntactic. A cue about something else in the same clause can be attributed to a skill: "Must be eligible to work in Canada and familiar with Excel" marks Excel required. A negation elsewhere earlier in a clause ("We don't sponsor visas, and SQL is required") downgrades the requirement to mentioned. Long-range or implied requirements are not resolved, and abbreviations such as "e.g." may split sentences.
- Evidence for a heading-inherited requirement is only the bullet text (for example "Python"); the heading that made it required or preferred is not included in the excerpt, so the displayed evidence does not fully explain its classification.
- HTML list items converted to plain text lose their bullet markers, so they do not inherit heading context and are classified from their own wording only.
- Eligibility constraints, years of experience, and proficiency levels are not extracted.
