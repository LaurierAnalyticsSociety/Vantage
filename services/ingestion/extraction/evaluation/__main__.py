"""Offline benchmark evaluation command.

    python -m services.ingestion.extraction.evaluation --split development

Exit status: 0 when the run completes (imperfect scores included), 1 when exact-label F1 is
below ``--min-exact-f1`` or undefined, 2 for invalid arguments or benchmark input.
No database, network, credentials, or production taxonomy are used.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from services.ingestion.extraction.evaluation.corpus import (
    BENCHMARK_DIR,
    SPLITS,
    BenchmarkError,
    Split,
    load_benchmark,
)
from services.ingestion.extraction.evaluation.report import render_json, render_summary, run
from services.ingestion.extraction.skills import extract_skills

EXIT_OK, EXIT_THRESHOLD, EXIT_INVALID = 0, 1, 2


def _threshold(value: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{value!r} is not a number.") from error
    if not 0.0 <= number <= 1.0:
        raise argparse.ArgumentTypeError(f"{value} must be between 0 and 1.")
    return number


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="python -m services.ingestion.extraction.evaluation",
        description="Evaluate the rule-based skill extractor on the synthetic offline benchmark.",
    )
    result.add_argument(
        "--split", choices=[*SPLITS, "all"], required=True, help="benchmark split to evaluate"
    )
    result.add_argument(
        "--benchmark-dir",
        type=Path,
        default=BENCHMARK_DIR,
        help="directory holding taxonomy.json, development.json, and heldout.json",
    )
    result.add_argument("--json-out", type=Path, help="write the JSON report to this file")
    result.add_argument("--summary-out", type=Path, help="write the Markdown summary to this file")
    result.add_argument(
        "--min-exact-f1",
        type=_threshold,
        metavar="F1",
        help="fail with status 1 when exact-label F1 is below this value (0 to 1)",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    splits = cast(tuple[Split, ...], SPLITS if args.split == "all" else (args.split,))
    try:
        report = run(load_benchmark(args.benchmark_dir), splits, extract_skills)
    except BenchmarkError as error:
        print(f"error: invalid benchmark input: {error}", file=sys.stderr)
        return EXIT_INVALID
    summary = render_summary(report)
    for path, content in ((args.json_out, render_json(report)), (args.summary_out, summary)):
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    sys.stdout.write(summary)
    if args.min_exact_f1 is not None:
        f1 = report["exact_label"]["f1"]
        if f1 is None or f1 < args.min_exact_f1:
            shown = "undefined" if f1 is None else f"{f1:.6f}"
            print(
                f"error: exact-label F1 {shown} is below the minimum {args.min_exact_f1}.",
                file=sys.stderr,
            )
            return EXIT_THRESHOLD
        print(f"Exact-label F1 {f1:.6f} meets the minimum {args.min_exact_f1}.", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
