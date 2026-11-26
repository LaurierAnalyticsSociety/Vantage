# Error analysis: skill-rules-v1 → skill-rules-v2

Corpus `bench-1` (frozen in `FREEZE.json`, no errata), taxonomy `bench-tax-1`. Baseline reports (`reports/baseline/`) come from the unchanged merged `skill-rules-v1`; final reports (`reports/final/`) from `skill-rules-v2`. Rules were tuned against development only. Held-out was evaluated once for the baseline and once for the final report. No label or split membership changed.

These are synthetic benchmark results on hand-authored descriptions, not real-world accuracy or calibrated confidence.

## Metrics

| Split | Metric | Baseline P / R / F1 (TP/FP/FN) | Final P / R / F1 (TP/FP/FN) |
| --- | --- | --- | --- |
| Development (40) | Identification | 0.975 / 0.951 / 0.963 (77/2/4) | 0.975 / 0.951 / 0.963 (77/2/4) |
| Development (40) | Exact label | 0.734 / 0.716 / 0.725 (58/21/23) | 0.975 / 0.951 / 0.963 (77/2/4) |
| Held-out (20) | Identification | 1.000 / 1.000 / 1.000 (38/0/0) | 1.000 / 1.000 / 1.000 (38/0/0) |
| Held-out (20) | Exact label | 0.947 / 0.947 / 0.947 (36/2/2) | 1.000 / 1.000 / 1.000 (38/0/0) |

Development exact-label F1 by category: required 0.781 → 1.000 (support 33), preferred 0.684 → 0.979 (24), mentioned 0.690 → 0.894 (24). Identification is unchanged on both splits because the three changes affect only category assignment, never which skills are matched.

## Changed predictions

Every changed case went from differing to matching. No case went from matching to differing on either split.

### A. Headings without a trailing colon (commit `f397390`)

**Failure.** `_sentences` recognized a heading only with a colon, so the bullets under `Requirements`, `## Required skills`, or `**Preferred qualifications**` were classified on their own wording and fell to `mentioned`.

| Case | Before | After |
| --- | --- | --- |
| dev-001 `Requirements` / `Nice to have` | python, sql, docker → mentioned | python, sql required; docker preferred |
| dev-002 `## Required skills` / `## Preferred skills` | java, git, kubernetes → mentioned | java, git required; kubernetes preferred |
| dev-003 `**Preferred qualifications**` | tableau, power-bi → mentioned | both preferred |

**Counterexamples (unchanged, still pass):** dev-004 (`Benefits` list: no cue, so not a heading) and dev-005 (`Python is required.` followed by perk bullets: a sentence that names a skill is not a heading).

**Semantics.** After removing a Markdown `#` marker or whole-line `**`/`__` emphasis, an unbulleted line is a heading only if it has at most six words, no terminal `.`/`!`/`?`, names no taxonomy skill, and contains a required/preferred cue. Like colon headings, it governs only the bulleted lines that follow.

### B. Negation scope across clauses (commit `094e59c`)

**Failure.** A negation anywhere between the previous required cue and this one cancelled it, including a negation in an unrelated earlier clause.

| Case | Before | After |
| --- | --- | --- |
| dev-006 `We don't sponsor visas, and SQL is required.` | sql mentioned | sql required |
| dev-007 `This is not a remote position and Docker is required.` | docker mentioned | docker required |
| dev-008 `No relocation is offered, so strong Python skills are required.` | python mentioned | python required |
| dev-009 `Applicants without a degree are welcome, and Java is required.` | java mentioned | java required |

**Counterexamples (unchanged, still pass):** dev-010 (`No prior Python experience is required.` stays mentioned) and dev-011 (`Docker and Kubernetes are not required, and Git is required.`: Docker and Kubernetes mentioned, Git required).

**Semantics.** A negation cancels a required cue only within the cue's own segment. Segments break at commas and at *and/so/yet/while*, except inside a coordinated skill list, so `No Python and SQL experience is required` still negates both skills.

### C. Cue assignment in coordinated skill groups (commit `aea7d10`)

**Failure.** The nearest cue anywhere in the clause won, so a cue governing one skill group was assigned to an adjacent group that was closer to it in characters.

| Case | Before | After |
| --- | --- | --- |
| dev-012 `Python is required and Tableau or Power BI is a plus.` | tableau required | tableau preferred |
| dev-013 `Must have SQL, with Docker and Kubernetes preferred.` | docker required | docker preferred |
| dev-014 `Java is essential and Git or Docker would be an asset.` | git required | git preferred |
| dev-015 `TypeScript is mandatory, while AWS and Docker are desirable.` | aws required | aws preferred |
| dev-031 `SQL is required, Excel is preferred, and our team also uses Tableau.` | excel required; tableau preferred | excel preferred; tableau mentioned |
| dev-039 `… Docker is required, and Kubernetes would be a plus.` | kubernetes required | kubernetes preferred (Go still missed; see below) |

**Counterexamples (unchanged, still pass):** dev-016 (`SQL, Python, and Docker are required.`: a shared cue over one list) and dev-017 (`Python required, Docker preferred, Git a plus.`: mixed categories in one sentence).

**Semantics.** A skill takes the nearest cue in its own segment (the same segments as B). If its segment has no cue, only cues from segments that name no skill of their own apply. A list-introducing cue therefore still governs its list (`Must have experience with dashboards, SQL, and Excel`), while a cue already attached to another group does not leak.

### Held-out

| Case | Before | After |
| --- | --- | --- |
| ho-010 `Required qualifications` (no colon) with two bullets | sql, tableau → mentioned | both required |

This is the same mechanism as A, in wording not used during tuning. It was seen in the baseline held-out report but not used to choose or adjust any rule: A was selected and specified from dev-001 to dev-003 alone. No other held-out case changed.

## Remaining errors

The 6 remaining development errors (2 FP, 4 FN) are all identification errors. Held-out has none.

| Case | Error | Cause | Status |
| --- | --- | --- | --- |
| dev-018 `Languages: Go, Java` | go missed | After an inline label is stripped, Go is clause-initial, and the ambiguity policy rejects clause-initial ambiguous tokens without a following qualifier. | Not changed. Relaxing it is an ambiguity-policy change and would risk `Note: Go to the portal`. |
| dev-019 `Tech stack: C, C++ and Python` | c missed | Same mechanism as dev-018. | Not changed. |
| dev-020 `Nice to have: R, SQL` | r missed | Same mechanism as dev-018. | Not changed. |
| dev-039 `We build services in Go.` | go missed | `build services in` is not a documented language qualifier, and Go is not in a coordinated list. | Not changed; conservative by design. |
| dev-022 `Help spark new ideas …` | spurious spark | The benchmark alias `Spark` matches the verb `spark` case-insensitively. Only R, Go, C, and single letters get ambiguity handling. | Not changed. This is a taxonomy-curation question (whether `Spark` should be treated as ambiguous), outside this assignment. |
| dev-024 `…careers.example.org/js-portal.` | spurious javascript | `/` is not an identifier character, so `js` inside a URL path matches. | Not changed. Possible boundary work: URL and path detection. |

## Tradeoffs and known limits of the new rules

- **Lexical list detection.** In `We use Tableau, and SQL is required`, the `, and` between two skills reads as a coordinated list, so Tableau shares the required cue. That was also the v1 result, so it is not a regression. Telling the two apart needs syntactic parsing.
- **Short cue lines before bullets become headings.** A six-word-or-shorter line with a cue, no skill, and no terminal punctuation (for example `Must live in Toronto`) now passes its category to the following bullets. Sentence-like lines ending in `.` are excluded.
- **Negation within a segment is still lexical.** `No travel is required for SQL work` still makes SQL mentioned.
- **Ceiling effect on held-out.** Held-out was already at 0.947 exact-label F1, so it mainly checks for regressions. One author wrote the descriptions, labels, and rules, so held-out is not an independent sample.
