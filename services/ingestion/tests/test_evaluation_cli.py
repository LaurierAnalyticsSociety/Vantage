"""Evaluation command: exit status, determinism, offline operation, and committed reports."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from services.common.settings import ROOT
from services.ingestion.extraction import EXTRACTION_VERSION, ExtractedSkill, Taxonomy
from services.ingestion.extraction.evaluation.__main__ import main
from services.ingestion.extraction.evaluation.corpus import (
    BENCHMARK_DIR,
    BenchmarkError,
    load_benchmark,
)
from services.ingestion.extraction.evaluation.report import render_json, render_summary, run
from services.ingestion.extraction.skills import extract_skills
from services.ingestion.tests.benchmark_helpers import case_data, write_benchmark

REPORTS = BENCHMARK_DIR / "reports"


@pytest.fixture
def perfect(tmp_path: Path) -> Path:
    return write_benchmark(
        tmp_path / "perfect",
        [
            case_data(
                "p-1",
                "Python is required. SQL is a plus.",
                {"python": "required", "sql": "preferred"},
            )
        ],
        [case_data("p-2", "Docker is used here.", {"docker": "mentioned"})],
    )


@pytest.fixture
def imperfect(tmp_path: Path) -> Path:
    return write_benchmark(
        tmp_path / "imperfect",
        [
            case_data("i-1", "Python is required.", {"python": "preferred"}),
            case_data("i-2", "We use Docker.", {}),
        ],
    )


def test_valid_imperfect_run_reports_results_and_succeeds(
    imperfect: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--split", "development", "--benchmark-dir", str(imperfect)]) == 0
    output = capsys.readouterr().out
    assert "## Case differences (2 of 2 cases)" in output
    assert "python expected preferred, predicted required" in output
    assert "- Spurious: docker=mentioned" in output


def test_threshold_pass_and_fail(perfect: Path, imperfect: Path) -> None:
    assert main(["--split", "all", "--benchmark-dir", str(perfect), "--min-exact-f1", "1"]) == 0
    assert (
        main(["--split", "development", "--benchmark-dir", str(imperfect), "--min-exact-f1", "0.5"])
        == 1
    )
    assert (
        main(["--split", "development", "--benchmark-dir", str(imperfect), "--min-exact-f1", "0"])
        == 0
    )


def test_undefined_f1_fails_any_threshold(tmp_path: Path) -> None:
    directory = write_benchmark(tmp_path, [case_data("e-1", "", {})])
    assert main(["--split", "development", "--benchmark-dir", str(directory)]) == 0
    assert (
        main(["--split", "development", "--benchmark-dir", str(directory), "--min-exact-f1", "0"])
        == 1
    )


@pytest.mark.parametrize("value", ["1.5", "-0.1", "high"])
def test_invalid_threshold_is_a_usage_error(value: str, perfect: Path) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--split", "development", "--benchmark-dir", str(perfect), "--min-exact-f1", value])
    assert raised.value.code == 2


def test_invalid_input_fails_with_actionable_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = write_benchmark(tmp_path, [case_data("x-1", "SQL", {"mysql": "required"})])
    assert main(["--split", "development", "--benchmark-dir", str(directory)]) == 2
    error = capsys.readouterr().err
    assert "error: invalid benchmark input: development.json:" in error
    assert "unknown skill key 'mysql'" in error


def test_outputs_are_deterministic(perfect: Path, tmp_path: Path) -> None:
    outputs = []
    for attempt in ("a", "b"):
        json_out, summary_out = tmp_path / attempt / "r.json", tmp_path / attempt / "r.md"
        args = ["--split", "all", "--benchmark-dir", str(perfect)]
        assert main([*args, "--json-out", str(json_out), "--summary-out", str(summary_out)]) == 0
        outputs.append((json_out.read_bytes(), summary_out.read_bytes()))
    assert outputs[0] == outputs[1]
    report = json.loads(outputs[0][0])
    assert report["split"] == "all"
    assert report["extractor_version"] == EXTRACTION_VERSION
    assert set(report["corpus"]["splits"]) == {"development", "heldout"}
    assert report["taxonomy"]["fingerprint"].startswith("sha256:")
    assert report["exact_label"]["f1"] == 1.0
    assert b"\r\n" not in outputs[0][0]


def test_report_records_case_differences_and_evidence(imperfect: Path) -> None:
    report = run(load_benchmark(imperfect), ["development"], extract_skills)
    first = report["cases"][0]
    assert first["id"] == "i-1"
    assert first["wrong_category"] == [
        {"skill": "python", "expected": "preferred", "predicted": "required"}
    ]
    assert first["predicted"][0]["evidence_excerpt"] == "Python is required."
    assert report["identification"]["fp"] == 1
    assert report["exact_label"] == {
        "tp": 0,
        "fp": 2,
        "fn": 1,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
    }


def test_extractor_results_outside_the_taxonomy_are_rejected(perfect: Path) -> None:
    from uuid import uuid4

    def rogue(text: str | None, taxonomy: Taxonomy) -> list[ExtractedSkill]:
        return [ExtractedSkill(uuid4(), "Rogue", "mentioned", 0.9, "x")]

    with pytest.raises(BenchmarkError, match="outside the taxonomy"):
        run(load_benchmark(perfect), ["development"], rogue)


def test_evaluator_runs_offline_without_database_modules(tmp_path: Path, perfect: Path) -> None:
    script = (
        "import socket, sys\n"
        "def blocked(*args, **kwargs):\n"
        "    raise RuntimeError('network access attempted')\n"
        "socket.socket = blocked\n"
        "socket.create_connection = blocked\n"
        "from services.ingestion.extraction.evaluation.__main__ import main\n"
        f"code = main(['--split', 'all', '--benchmark-dir', {str(perfect)!r}])\n"
        "loaded = sorted(m for m in sys.modules if m.split('.')[0] in {'psycopg', 'httpx'}"
        " or m.startswith('services.common') or m == 'services.ingestion.cli')\n"
        "print('LOADED', loaded)\n"
        "sys.exit(code)\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if "DATABASE" not in key and "SUPABASE" not in key
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "LOADED []" in result.stdout


def committed_reports() -> list[Path]:
    return sorted(REPORTS.glob("*/*.json"))


@pytest.mark.parametrize(
    "path", committed_reports(), ids=lambda path: f"{path.parent.name}/{path.stem}"
)
def test_committed_reports_match_frozen_corpus(path: Path) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    benchmark = load_benchmark()
    assert report["taxonomy"]["fingerprint"] == benchmark.taxonomy.fingerprint
    for split, info in report["corpus"]["splits"].items():
        assert info["fingerprint"] == benchmark.splits[split].fingerprint


@pytest.mark.parametrize(
    "path", committed_reports(), ids=lambda path: f"{path.parent.name}/{path.stem}"
)
def test_committed_reports_reproduce_for_their_extractor_version(path: Path) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report["extractor_version"] != EXTRACTION_VERSION:
        pytest.skip(f"report records {report['extractor_version']}; reproduce from its commit")
    regenerated = run(load_benchmark(), [report["split"]], extract_skills)
    assert render_json(regenerated) == path.read_text(encoding="utf-8")
    assert render_summary(regenerated) == path.with_suffix(".md").read_text(encoding="utf-8")
