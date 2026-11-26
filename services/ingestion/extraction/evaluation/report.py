"""Run the extractor over benchmark splits and render deterministic reports."""

import json
from collections.abc import Sequence
from typing import Any

from services.ingestion.extraction.evaluation.corpus import Benchmark, BenchmarkError, Split
from services.ingestion.extraction.evaluation.metrics import REQUIREMENT_TYPES, evaluate
from services.ingestion.extraction.skills import EXTRACTION_VERSION, Extractor, RequirementType

REPORT_FORMAT = "vantage-skill-benchmark-report"
DECIMALS = 6
CAVEAT = (
    "Synthetic benchmark results on hand-authored descriptions. These are not real-world "
    "accuracy or calibrated confidence; the corpus author also wrote the labels."
)
DENOMINATORS = {
    "identification": "distinct (case_id, skill) pairs; precision = TP/(TP+FP), "
    "recall = TP/(TP+FN), F1 = 2TP/(2TP+FP+FN)",
    "exact_label": "distinct (case_id, skill, requirement_type) tuples; a wrong category is one "
    "FP and one FN",
    "per_skill.support": "expected cases containing the skill",
    "per_category.support": "expected tuples with the category",
    "undefined": "null when a denominator is zero, including F1 when TP = FP = FN = 0",
}


def run(benchmark: Benchmark, splits: Sequence[Split], extractor: Extractor) -> dict[str, Any]:
    taxonomy = benchmark.taxonomy
    expected: dict[str, dict[str, RequirementType]] = {}
    predicted: dict[str, list[tuple[str, RequirementType]]] = {}
    details = []
    for split in splits:
        for case in benchmark.splits[split].cases:
            gold = dict(case.expected)
            results = extractor(case.description, taxonomy.index)
            guesses = [(taxonomy.key_for(item.skill_id), item) for item in results]
            expected[case.id] = gold
            predicted[case.id] = [(key, item.requirement_type) for key, item in guesses]
            labels = {key: item.requirement_type for key, item in guesses}
            missing = [(key, label) for key, label in gold.items() if key not in labels]
            spurious = [(key, label) for key, label in labels.items() if key not in gold]
            wrong = [
                (key, gold[key], label)
                for key, label in labels.items()
                if key in gold and gold[key] != label
            ]
            details.append(
                {
                    "id": case.id,
                    "split": split,
                    "tags": list(case.tags),
                    "status": "differs" if missing or spurious or wrong else "match",
                    "description": case.description,
                    "expected": _labels(gold.items()),
                    "predicted": [
                        {
                            "skill": key,
                            "requirement_type": item.requirement_type,
                            "confidence": item.confidence,
                            "evidence_excerpt": item.evidence_excerpt,
                        }
                        for key, item in sorted(
                            guesses, key=lambda pair: (pair[0], pair[1].requirement_type)
                        )
                    ],
                    "missing": _labels(missing),
                    "spurious": _labels(spurious),
                    "wrong_category": [
                        {"skill": key, "expected": gold_label, "predicted": label}
                        for key, gold_label, label in sorted(wrong)
                    ],
                }
            )
    if len({case["id"] for case in details}) != len(details):  # pragma: no cover - validated
        raise BenchmarkError("Case IDs must be unique across the evaluated splits.")
    metrics = evaluate(expected, predicted, taxonomy.keys)
    return _rounded(
        {
            "format": REPORT_FORMAT,
            "format_version": 1,
            "synthetic": True,
            "caveat": CAVEAT,
            "split": splits[0] if len(splits) == 1 else "all",
            "extractor_version": EXTRACTION_VERSION,
            "corpus": {
                "version": benchmark.splits[splits[0]].corpus_version,
                "splits": {
                    split: {
                        "fingerprint": benchmark.splits[split].fingerprint,
                        "cases": len(benchmark.splits[split].cases),
                    }
                    for split in splits
                },
            },
            "taxonomy": {"version": taxonomy.version, "fingerprint": taxonomy.fingerprint},
            "denominators": DENOMINATORS,
            **metrics,
            "cases": sorted(details, key=lambda case: str(case["id"])),
        }
    )


def _labels(items: Any) -> list[dict[str, str]]:
    return [{"skill": key, "requirement_type": label} for key, label in sorted(items)]


def _rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, DECIMALS)
    if isinstance(value, dict):
        return {key: _rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rounded(item) for item in value]
    return value


def render_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _metric(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def _row(name: str, block: dict[str, Any], support: object = "") -> str:
    cells = [
        name,
        str(support),
        str(block["tp"]),
        str(block["fp"]),
        str(block["fn"]),
        _metric(block["precision"]),
        _metric(block["recall"]),
        _metric(block["f1"]),
    ]
    return "| " + " | ".join(cells) + " |"


HEADER = (
    "| | Support | TP | FP | FN | Precision | Recall | F1 |\n"
    "|---|---:|---:|---:|---:|---:|---:|---:|"
)


def _format_labels(items: list[dict[str, str]]) -> str:
    return ", ".join(f"{item['skill']}={item['requirement_type']}" for item in items) or "—"


def render_summary(report: dict[str, Any]) -> str:
    corpus = report["corpus"]
    lines = [
        f"# Skill-extraction benchmark: {report['split']}",
        "",
        f"> {report['caveat']}",
        "",
        f"- Extractor version: `{report['extractor_version']}`",
        f"- Corpus version: `{corpus['version']}`",
    ]
    for split, info in corpus["splits"].items():
        lines.append(f"- {split}: {info['cases']} cases, fingerprint `{info['fingerprint']}`")
    lines += [
        f"- Taxonomy: `{report['taxonomy']['version']}`, "
        f"fingerprint `{report['taxonomy']['fingerprint']}`",
        f"- Expected labels: {report['counts']['expected_labels']}; predicted labels: "
        f"{report['counts']['predicted_labels']}; duplicate predictions: "
        f"{report['counts']['duplicate_predictions']}",
        "",
        "## Aggregate",
        "",
        HEADER,
        _row("Skill identification", report["identification"]),
        _row("Exact label", report["exact_label"]),
        "",
        "Identification counts distinct (case, skill) pairs; exact label counts distinct "
        "(case, skill, category) tuples, so a wrong category is one FP and one FN. "
        "N/A marks an undefined ratio.",
        "",
        "## Per category (exact label)",
        "",
        HEADER,
    ]
    for category in REQUIREMENT_TYPES:
        block = report["per_category"][category]
        lines.append(_row(category, block, block["support"]))
    confusion = report["category_confusion"]
    lines += [
        "",
        "## Category confusion (identified skills; rows expected, columns predicted)",
        "",
        "| Expected \\ Predicted | " + " | ".join(REQUIREMENT_TYPES) + " |",
        "|---|" + "---:|" * len(REQUIREMENT_TYPES),
    ]
    for row in REQUIREMENT_TYPES:
        cells = [str(confusion["matrix"][row][column]) for column in REQUIREMENT_TYPES]
        lines.append(f"| {row} | " + " | ".join(cells) + " |")
    lines += [
        "",
        f"Missed skills: {confusion['missed_skills']}; spurious skills: "
        f"{confusion['spurious_skills']}.",
        "",
        "## Per skill",
        "",
        "| Skill | Support | ID TP | ID FP | ID FN | ID F1 | Exact TP | Exact FP | Exact FN "
        "| Exact F1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for skill, block in report["per_skill"].items():
        ident, exact = block["identification"], block["exact_label"]
        lines.append(
            f"| {skill} | {block['support']} | {ident['tp']} | {ident['fp']} | {ident['fn']} | "
            f"{_metric(ident['f1'])} | {exact['tp']} | {exact['fp']} | {exact['fn']} | "
            f"{_metric(exact['f1'])} |"
        )
    differing = [case for case in report["cases"] if case["status"] == "differs"]
    lines += [
        "",
        f"## Case differences ({len(differing)} of {len(report['cases'])} cases)",
        "",
    ]
    if not differing:
        lines.append("All cases match their expected labels.")
    for case in differing:
        wrong = ", ".join(
            f"{item['skill']} expected {item['expected']}, predicted {item['predicted']}"
            for item in case["wrong_category"]
        )
        lines += [
            f"### {case['id']}",
            "",
            "```text",
            case["description"],
            "```",
            "",
            f"- Expected: {_format_labels(case['expected'])}",
            f"- Predicted: {_format_labels(case['predicted'])}",
            f"- Missing: {_format_labels(case['missing'])}",
            f"- Spurious: {_format_labels(case['spurious'])}",
            f"- Wrong category: {wrong or '—'}",
            "",
        ]
    return "\n".join(lines).rstrip("\n") + "\n"
