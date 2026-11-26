# Skill-extraction benchmark: development

> Synthetic benchmark results on hand-authored descriptions. These are not real-world accuracy or calibrated confidence; the corpus author also wrote the labels.

- Extractor version: `skill-rules-v2`
- Corpus version: `bench-1`
- development: 40 cases, fingerprint `sha256:05126eadceebea107b23a8ec068c3c394cdbfffa1ab5e5d260dc47e1fbc0da6a`
- Taxonomy: `bench-tax-1`, fingerprint `sha256:e69c0d1373576724a7b21851958acc1a9a97f5c66f8a35b52f94226fa496ef16`
- Expected labels: 81; predicted labels: 79; duplicate predictions: 0

## Aggregate

| | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Skill identification |  | 77 | 2 | 4 | 0.975 | 0.951 | 0.963 |
| Exact label |  | 77 | 2 | 4 | 0.975 | 0.951 | 0.963 |

Identification counts distinct (case, skill) pairs; exact label counts distinct (case, skill, category) tuples, so a wrong category is one FP and one FN. N/A marks an undefined ratio.

## Per category (exact label)

| | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| required | 33 | 33 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| preferred | 24 | 23 | 0 | 1 | 1.000 | 0.958 | 0.979 |
| mentioned | 24 | 21 | 2 | 3 | 0.913 | 0.875 | 0.894 |

## Category confusion (identified skills; rows expected, columns predicted)

| Expected \ Predicted | required | preferred | mentioned |
|---|---:|---:|---:|
| required | 33 | 0 | 0 |
| preferred | 0 | 23 | 0 |
| mentioned | 0 | 0 | 21 |

Missed skills: 4; spurious skills: 2.

## Per skill

| Skill | Support | ID TP | ID FP | ID FN | ID F1 | Exact TP | Exact FP | Exact FN | Exact F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws | 6 | 6 | 0 | 0 | 1.000 | 6 | 0 | 0 | 1.000 |
| c | 1 | 0 | 0 | 1 | 0.000 | 0 | 0 | 1 | 0.000 |
| cpp | 3 | 3 | 0 | 0 | 1.000 | 3 | 0 | 0 | 1.000 |
| csharp | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| docker | 12 | 12 | 0 | 0 | 1.000 | 12 | 0 | 0 | 1.000 |
| dotnet | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| excel | 4 | 4 | 0 | 0 | 1.000 | 4 | 0 | 0 | 1.000 |
| git | 5 | 5 | 0 | 0 | 1.000 | 5 | 0 | 0 | 1.000 |
| go | 3 | 1 | 0 | 2 | 0.500 | 1 | 0 | 2 | 0.500 |
| java | 6 | 6 | 0 | 0 | 1.000 | 6 | 0 | 0 | 1.000 |
| javascript | 0 | 0 | 1 | 0 | 0.000 | 0 | 1 | 0 | 0.000 |
| kubernetes | 5 | 5 | 0 | 0 | 1.000 | 5 | 0 | 0 | 1.000 |
| nodejs | 0 | 0 | 0 | 0 | N/A | 0 | 0 | 0 | N/A |
| postgresql | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| power-bi | 2 | 2 | 0 | 0 | 1.000 | 2 | 0 | 0 | 1.000 |
| python | 13 | 13 | 0 | 0 | 1.000 | 13 | 0 | 0 | 1.000 |
| r | 2 | 1 | 0 | 1 | 0.667 | 1 | 0 | 1 | 0.667 |
| spark | 0 | 0 | 1 | 0 | 0.000 | 0 | 1 | 0 | 0.000 |
| sql | 8 | 8 | 0 | 0 | 1.000 | 8 | 0 | 0 | 1.000 |
| tableau | 5 | 5 | 0 | 0 | 1.000 | 5 | 0 | 0 | 1.000 |
| typescript | 3 | 3 | 0 | 0 | 1.000 | 3 | 0 | 0 | 1.000 |

## Case differences (6 of 40 cases)

### dev-018

```text
Languages: Go, Java
```

- Expected: go=mentioned, java=mentioned
- Predicted: java=mentioned
- Missing: go=mentioned
- Spurious: —
- Wrong category: —

### dev-019

```text
Tech stack: C, C++ and Python
```

- Expected: c=mentioned, cpp=mentioned, python=mentioned
- Predicted: cpp=mentioned, python=mentioned
- Missing: c=mentioned
- Spurious: —
- Wrong category: —

### dev-020

```text
Nice to have: R, SQL
```

- Expected: r=preferred, sql=preferred
- Predicted: sql=preferred
- Missing: r=preferred
- Spurious: —
- Wrong category: —

### dev-022

```text
Help spark new ideas with our Pythonic style guide and gitlab-style reviews.
```

- Expected: —
- Predicted: spark=mentioned
- Missing: —
- Spurious: spark=mentioned
- Wrong category: —

### dev-024

```text
Upload resumes as .docx files to careers.example.org/js-portal.
```

- Expected: —
- Predicted: javascript=mentioned
- Missing: —
- Spurious: javascript=mentioned
- Wrong category: —

### dev-039

```text
Backend Developer (synthetic)
We build services in Go. Docker is required, and Kubernetes would be a plus.
We don't offer relocation.
- Benefits include AWS certification support.
```

- Expected: aws=mentioned, docker=required, go=mentioned, kubernetes=preferred
- Predicted: aws=mentioned, docker=required, kubernetes=preferred
- Missing: go=mentioned
- Spurious: —
- Wrong category: —
