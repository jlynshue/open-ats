"""End-to-end test: spawn ``open-ats scan`` as a subprocess and validate output.

This is the FR-10 / Sprint-5 acceptance gate — the CLI must parse the
inputs, run the analyzer pipeline, score, and emit valid deterministic
JSON, all from a single command invocation.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml


def _run_cli(
    args: list[str], cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``python -m open_ats.cli.main`` with the given args."""
    return subprocess.run(
        [sys.executable, "-m", "open_ats.cli.main", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        check=False,
    )


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def test_cli_help_lists_scan(repo_root: Path) -> None:
    result = _run_cli(["--help"], cwd=repo_root)
    assert result.returncode == 0
    assert "scan" in result.stdout


def test_scan_help_lists_options(repo_root: Path) -> None:
    result = _run_cli(["scan", "--help"], cwd=repo_root)
    assert result.returncode == 0
    assert "--resume" in result.stdout
    assert "--job-description" in result.stdout
    assert "--output" in result.stdout


# ─── Threshold #2 — CLI E2E green ────────────────────────────────────


def test_cli_scan_writes_valid_json(repo_root: Path, tmp_path: Path) -> None:
    """End-to-end happy path: scan a fixture pair, parse the output."""
    out = tmp_path / "report.json"
    result = _run_cli(
        [
            "scan",
            "--resume",
            "tests/fixtures/resumes/mid_level.md",
            "--job-description",
            "tests/fixtures/job_descriptions/mid_level_backend.txt",
            "--output",
            str(out),
        ],
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    payload = json.loads(out.read_text())
    assert "score" in payload
    overall = payload["score"]["overall"]
    assert isinstance(overall, (int, float))
    assert 0.0 <= overall <= 100.0


def test_cli_unsupported_output_format_errors(repo_root: Path, tmp_path: Path) -> None:
    """Sprint 5 supports JSON only; .html (Sprint 9) errors clearly."""
    out = tmp_path / "report.html"
    result = _run_cli(
        [
            "scan",
            "--resume",
            "tests/fixtures/resumes/mid_level.md",
            "--job-description",
            "tests/fixtures/job_descriptions/mid_level_backend.txt",
            "--output",
            str(out),
        ],
        cwd=repo_root,
    )
    assert result.returncode != 0


# ─── Threshold #4 — Determinism (byte-identical JSON) ────────────────


def test_two_runs_produce_byte_identical_json(repo_root: Path, tmp_path: Path) -> None:
    out_a = tmp_path / "a.json"
    out_b = tmp_path / "b.json"
    args_template = [
        "scan",
        "--resume",
        "tests/fixtures/resumes/mid_level.md",
        "--job-description",
        "tests/fixtures/job_descriptions/mid_level_backend.txt",
        "--output",
        "PLACEHOLDER",
    ]
    a_args = list(args_template)
    a_args[-1] = str(out_a)
    b_args = list(args_template)
    b_args[-1] = str(out_b)

    a = _run_cli(a_args, cwd=repo_root)
    b = _run_cli(b_args, cwd=repo_root)
    assert a.returncode == 0
    assert b.returncode == 0
    assert out_a.read_bytes() == out_b.read_bytes()


# ─── Threshold #3 — Golden scores ────────────────────────────────────


def test_golden_scores(repo_root: Path, tmp_path: Path) -> None:
    """Each (resume, JD, expected) tuple is within tolerance of the
    Sprint-5 keyword pipeline's actual output."""
    golden_path = repo_root / "tests/fixtures/golden/scores.yaml"
    cases = yaml.safe_load(golden_path.read_text())["cases"]
    failures: list[str] = []
    for case in cases:
        out = tmp_path / f"{case['name']}.json"
        result = _run_cli(
            [
                "scan",
                "--resume",
                f"tests/fixtures/resumes/{case['resume']}",
                "--job-description",
                f"tests/fixtures/job_descriptions/{case['job_description']}",
                "--output",
                str(out),
            ],
            cwd=repo_root,
        )
        if result.returncode != 0:
            failures.append(
                f"{case['name']}: CLI exit {result.returncode}: {result.stderr}"
            )
            continue
        payload = json.loads(out.read_text())
        actual = payload["score"]["overall"]
        expected = case["expected"]
        tolerance = case.get("tolerance", 5)
        if abs(actual - expected) > tolerance:
            failures.append(
                f"{case['name']}: expected {expected}±{tolerance}, got {actual}"
            )
    assert not failures, "\n".join(failures)


# ─── Threshold #5 — Performance gate ─────────────────────────────────


def test_scan_finishes_under_three_seconds(repo_root: Path, tmp_path: Path) -> None:
    """Cold-start CLI invocation must complete <3 sec on a fixture pair."""
    out = tmp_path / "perf.json"
    start = time.perf_counter()
    result = _run_cli(
        [
            "scan",
            "--resume",
            "tests/fixtures/resumes/mid_level.md",
            "--job-description",
            "tests/fixtures/job_descriptions/mid_level_backend.txt",
            "--output",
            str(out),
        ],
        cwd=repo_root,
    )
    elapsed = time.perf_counter() - start
    assert result.returncode == 0
    assert elapsed < 3.0, f"scan took {elapsed:.2f}s (>3s gate)"
