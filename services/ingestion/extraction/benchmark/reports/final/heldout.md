# Skill-extraction benchmark: heldout

> Synthetic benchmark results on hand-authored descriptions. These are not real-world accuracy or calibrated confidence; the corpus author also wrote the labels.

- Extractor version: `skill-rules-v2`
- Corpus version: `bench-1`
- heldout: 20 cases, fingerprint `sha256:ea399b13179ea8be2511deeb74e4612814bce3ce8fca07726266552ade4af575`
- Taxonomy: `bench-tax-1`, fingerprint `sha256:e69c0d1373576724a7b21851958acc1a9a97f5c66f8a35b52f94226fa496ef16`
- Expected labels: 38; predicted labels: 38; duplicate predictions: 0

## Aggregate

| | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Skill identification |  | 38 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| Exact label |  | 38 | 0 | 0 | 1.000 | 1.000 | 1.000 |

Identification counts distinct (case, skill) pairs; exact label counts distinct (case, skill, category) tuples, so a wrong category is one FP and one FN. N/A marks an undefined ratio.

## Per category (exact label)

| | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| required | 12 | 12 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| preferred | 12 | 12 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| mentioned | 14 | 14 | 0 | 0 | 1.000 | 1.000 | 1.000 |

## Category confusion (identified skills; rows expected, columns predicted)

| Expected \ Predicted | required | preferred | mentioned |
|---|---:|---:|---:|
| required | 12 | 0 | 0 |
| preferred | 0 | 12 | 0 |
| mentioned | 0 | 0 | 14 |

Missed skills: 0; spurious skills: 0.

## Per skill

| Skill | Support | ID TP | ID FP | ID FN | ID F1 | Exact TP | Exact FP | Exact FN | Exact F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws | 0 | 0 | 0 | 0 | N/A | 0 | 0 | 0 | N/A |
| c | 0 | 0 | 0 | 0 | N/A | 0 | 0 | 0 | N/A |
| cpp | 0 | 0 | 0 | 0 | N/A | 0 | 0 | 0 | N/A |
| csharp | 0 | 0 | 0 | 0 | N/A | 0 | 0 | 0 | N/A |
| docker | 2 | 2 | 0 | 0 | 1.000 | 2 | 0 | 0 | 1.000 |
| dotnet | 0 | 0 | 0 | 0 | N/A | 0 | 0 | 0 | N/A |
| excel | 4 | 4 | 0 | 0 | 1.000 | 4 | 0 | 0 | 1.000 |
| git | 2 | 2 | 0 | 0 | 1.000 | 2 | 0 | 0 | 1.000 |
| go | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| java | 4 | 4 | 0 | 0 | 1.000 | 4 | 0 | 0 | 1.000 |
| javascript | 2 | 2 | 0 | 0 | 1.000 | 2 | 0 | 0 | 1.000 |
| kubernetes | 2 | 2 | 0 | 0 | 1.000 | 2 | 0 | 0 | 1.000 |
| nodejs | 2 | 2 | 0 | 0 | 1.000 | 2 | 0 | 0 | 1.000 |
| postgresql | 0 | 0 | 0 | 0 | N/A | 0 | 0 | 0 | N/A |
| power-bi | 3 | 3 | 0 | 0 | 1.000 | 3 | 0 | 0 | 1.000 |
| python | 4 | 4 | 0 | 0 | 1.000 | 4 | 0 | 0 | 1.000 |
| r | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| spark | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| sql | 6 | 6 | 0 | 0 | 1.000 | 6 | 0 | 0 | 1.000 |
| tableau | 3 | 3 | 0 | 0 | 1.000 | 3 | 0 | 0 | 1.000 |
| typescript | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |

## Case differences (0 of 20 cases)

All cases match their expected labels.
