# Skill-extraction benchmark: development

> Synthetic benchmark results on hand-authored descriptions. These are not real-world accuracy or calibrated confidence; the corpus author also wrote the labels.

- Extractor version: `skill-rules-v1`
- Corpus version: `bench-1`
- development: 40 cases, fingerprint `sha256:05126eadceebea107b23a8ec068c3c394cdbfffa1ab5e5d260dc47e1fbc0da6a`
- Taxonomy: `bench-tax-1`, fingerprint `sha256:e69c0d1373576724a7b21851958acc1a9a97f5c66f8a35b52f94226fa496ef16`
- Expected labels: 81; predicted labels: 79; duplicate predictions: 0

## Aggregate

| | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Skill identification |  | 77 | 2 | 4 | 0.975 | 0.951 | 0.963 |
| Exact label |  | 58 | 21 | 23 | 0.734 | 0.716 | 0.725 |

Identification counts distinct (case, skill) pairs; exact label counts distinct (case, skill, category) tuples, so a wrong category is one FP and one FN. N/A marks an undefined ratio.

## Per category (exact label)

| | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| required | 33 | 25 | 6 | 8 | 0.806 | 0.758 | 0.781 |
| preferred | 24 | 13 | 1 | 11 | 0.929 | 0.542 | 0.684 |
| mentioned | 24 | 20 | 14 | 4 | 0.588 | 0.833 | 0.690 |

## Category confusion (identified skills; rows expected, columns predicted)

| Expected \ Predicted | required | preferred | mentioned |
|---|---:|---:|---:|
| required | 25 | 0 | 8 |
| preferred | 6 | 13 | 4 |
| mentioned | 0 | 1 | 20 |

Missed skills: 4; spurious skills: 2.

## Per skill

| Skill | Support | ID TP | ID FP | ID FN | ID F1 | Exact TP | Exact FP | Exact FN | Exact F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| aws | 6 | 6 | 0 | 0 | 1.000 | 5 | 1 | 1 | 0.833 |
| c | 1 | 0 | 0 | 1 | 0.000 | 0 | 0 | 1 | 0.000 |
| cpp | 3 | 3 | 0 | 0 | 1.000 | 3 | 0 | 0 | 1.000 |
| csharp | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| docker | 12 | 12 | 0 | 0 | 1.000 | 9 | 3 | 3 | 0.750 |
| dotnet | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| excel | 4 | 4 | 0 | 0 | 1.000 | 3 | 1 | 1 | 0.750 |
| git | 5 | 5 | 0 | 0 | 1.000 | 3 | 2 | 2 | 0.600 |
| go | 3 | 1 | 0 | 2 | 0.500 | 1 | 0 | 2 | 0.500 |
| java | 6 | 6 | 0 | 0 | 1.000 | 4 | 2 | 2 | 0.667 |
| javascript | 0 | 0 | 1 | 0 | 0.000 | 0 | 1 | 0 | 0.000 |
| kubernetes | 5 | 5 | 0 | 0 | 1.000 | 3 | 2 | 2 | 0.600 |
| nodejs | 0 | 0 | 0 | 0 | N/A | 0 | 0 | 0 | N/A |
| postgresql | 1 | 1 | 0 | 0 | 1.000 | 1 | 0 | 0 | 1.000 |
| power-bi | 2 | 2 | 0 | 0 | 1.000 | 1 | 1 | 1 | 0.500 |
| python | 13 | 13 | 0 | 0 | 1.000 | 11 | 2 | 2 | 0.846 |
| r | 2 | 1 | 0 | 1 | 0.667 | 1 | 0 | 1 | 0.667 |
| spark | 0 | 0 | 1 | 0 | 0.000 | 0 | 1 | 0 | 0.000 |
| sql | 8 | 8 | 0 | 0 | 1.000 | 6 | 2 | 2 | 0.750 |
| tableau | 5 | 5 | 0 | 0 | 1.000 | 2 | 3 | 3 | 0.400 |
| typescript | 3 | 3 | 0 | 0 | 1.000 | 3 | 0 | 0 | 1.000 |

## Case differences (18 of 40 cases)

### dev-001

```text
Requirements
- Python
- SQL

Nice to have
- Docker
```

- Expected: docker=preferred, python=required, sql=required
- Predicted: docker=mentioned, python=mentioned, sql=mentioned
- Missing: —
- Spurious: —
- Wrong category: docker expected preferred, predicted mentioned, python expected required, predicted mentioned, sql expected required, predicted mentioned

### dev-002

```text
## Required skills
- Java
- Git
## Preferred skills
- Kubernetes
```

- Expected: git=required, java=required, kubernetes=preferred
- Predicted: git=mentioned, java=mentioned, kubernetes=mentioned
- Missing: —
- Spurious: —
- Wrong category: git expected required, predicted mentioned, java expected required, predicted mentioned, kubernetes expected preferred, predicted mentioned

### dev-003

```text
**Preferred qualifications**
- Tableau
- Power BI
```

- Expected: power-bi=preferred, tableau=preferred
- Predicted: power-bi=mentioned, tableau=mentioned
- Missing: —
- Spurious: —
- Wrong category: power-bi expected preferred, predicted mentioned, tableau expected preferred, predicted mentioned

### dev-006

```text
We don't sponsor visas, and SQL is required.
```

- Expected: sql=required
- Predicted: sql=mentioned
- Missing: —
- Spurious: —
- Wrong category: sql expected required, predicted mentioned

### dev-007

```text
This is not a remote position and Docker is required.
```

- Expected: docker=required
- Predicted: docker=mentioned
- Missing: —
- Spurious: —
- Wrong category: docker expected required, predicted mentioned

### dev-008

```text
No relocation is offered, so strong Python skills are required.
```

- Expected: python=required
- Predicted: python=mentioned
- Missing: —
- Spurious: —
- Wrong category: python expected required, predicted mentioned

### dev-009

```text
Applicants without a degree are welcome, and Java is required.
```

- Expected: java=required
- Predicted: java=mentioned
- Missing: —
- Spurious: —
- Wrong category: java expected required, predicted mentioned

### dev-012

```text
Python is required and Tableau or Power BI is a plus.
```

- Expected: power-bi=preferred, python=required, tableau=preferred
- Predicted: power-bi=preferred, python=required, tableau=required
- Missing: —
- Spurious: —
- Wrong category: tableau expected preferred, predicted required

### dev-013

```text
Must have SQL, with Docker and Kubernetes preferred.
```

- Expected: docker=preferred, kubernetes=preferred, sql=required
- Predicted: docker=required, kubernetes=preferred, sql=required
- Missing: —
- Spurious: —
- Wrong category: docker expected preferred, predicted required

### dev-014

```text
Java is essential and Git or Docker would be an asset.
```

- Expected: docker=preferred, git=preferred, java=required
- Predicted: docker=preferred, git=required, java=required
- Missing: —
- Spurious: —
- Wrong category: git expected preferred, predicted required

### dev-015

```text
TypeScript is mandatory, while AWS and Docker are desirable.
```

- Expected: aws=preferred, docker=preferred, typescript=required
- Predicted: aws=required, docker=preferred, typescript=required
- Missing: —
- Spurious: —
- Wrong category: aws expected preferred, predicted required

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

### dev-031

```text
SQL is required, Excel is preferred, and our team also uses Tableau.
```

- Expected: excel=preferred, sql=required, tableau=mentioned
- Predicted: excel=required, sql=required, tableau=preferred
- Missing: —
- Spurious: —
- Wrong category: excel expected preferred, predicted required, tableau expected mentioned, predicted preferred

### dev-039

```text
Backend Developer (synthetic)
We build services in Go. Docker is required, and Kubernetes would be a plus.
We don't offer relocation.
- Benefits include AWS certification support.
```

- Expected: aws=mentioned, docker=required, go=mentioned, kubernetes=preferred
- Predicted: aws=mentioned, docker=required, kubernetes=required
- Missing: go=mentioned
- Spurious: —
- Wrong category: kubernetes expected preferred, predicted required
