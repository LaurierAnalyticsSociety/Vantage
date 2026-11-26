# Benchmark annotation guide

This guide defines how expected labels in the synthetic skill-extraction benchmark are written. It was written before any benchmark case was authored, and labels follow it rather than extractor output. **No label is ever produced or adjusted from predictions.**

The benchmark is entirely synthetic: every description is hand-authored for this repository, every case carries `"synthetic": true`, and benchmark scores are not real-world accuracy or calibrated confidence.

## What is labeled

For each case, list every canonical skill from the isolated benchmark taxonomy (`taxonomy.json`) that a careful human reader would say the description names **as a technology or tool**, and give it one requirement category:

| Category | Meaning |
| --- | --- |
| `required` | The posting states the skill is required, essential, mandatory, needed, a must, or a minimum qualification, directly or through a heading that governs it. |
| `preferred` | The posting states the skill is preferred, an asset, a plus, a bonus, desirable, ideal, or nice to have. |
| `mentioned` | The skill is named without a requirement or preference, or a requirement for it is explicitly negated. |

Each skill appears at most once per case. Skills absent from the taxonomy are not labeled, even if they are real technologies (for example SQLite, MySQL, SAS).

## Rules

1. **Label the reader's interpretation, not a rule's.** Ask what a hiring reader would record for the posting. A skill that an extractor is designed to miss conservatively (for example a standalone `R is required.`) still receives its true label; the miss is then a visible false negative.
2. **Ordinary words are not skills.** `Go to the page`, `go-getter`, `R&D`, a `C average`, `spark new ideas`, `excellent`, `Pythonic`, `Javanese`, and file names or URLs such as `config.js` or `/js-portal` are not mentions.
3. **Canonical resolution.** Aliases resolve to their canonical key (`Python 3` → `python`, `JS` → `javascript`, `Golang` → `go`, `Postgres` → `postgresql`). A product never implies another: `PostgreSQL` does not imply `sql`, and `Node.js` does not imply `javascript`.
4. **Strongest mention wins.** If a skill appears several times, record the strongest category stated anywhere: required > preferred > mentioned.
5. **Negation.** A negated requirement (`Python is not required`, `No Java knowledge needed`, `Not required: C++`) is `mentioned`. A negation applies only to what it grammatically governs: in `We don't sponsor visas, and SQL is required`, SQL is `required`. `Preferred but not required` is `preferred`.
6. **Headings.** A heading governs the contiguous list beneath it, with or without a trailing colon and regardless of Markdown (`##`) or bold (`**…**`) decoration, until the next heading, a blank line, or a prose paragraph. A heading that states no requirement (`Benefits`, `Responsibilities`, `Perks`, `Languages`) leaves its items `mentioned`. An explicit cue inside an item overrides its heading.
7. **Coordination.** A cue applies to the skills it grammatically governs. In `SQL, Python, and Docker are required` all three are required; in `Python is required and Tableau or Power BI is a plus`, Tableau and Power BI are preferred. Alternatives (`Python or R is required`) each take the stated category.
8. **Elliptical cues.** In `Excel is not required, but SQL is`, the elided predicate is `required`, so SQL is `required`.
9. **Eligibility, years, and proficiency** are not extracted; they do not change a category except through an explicit cue.
10. **Skill-free and empty text** has an empty expected list.

## Notes and ambiguity

When a reasonable reader could disagree, the case's `note` field records the interpretation chosen. Prefer authoring unambiguous cases; genuine ambiguity is kept visible rather than resolved in the extractor's favor.

## Errata

After the freeze, a label changes only to fix a demonstrated violation of this guide. Each change is recorded in `FREEZE.json` with the case ID, old and new label, and reason, under a new freeze entry. Labels are never changed to raise scores.
