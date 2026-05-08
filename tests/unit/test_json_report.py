"""Unit tests for the JSON reporter (PRD §11.1)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from open_ats.models import (
    AnalyzerResult,
    CategoryScore,
    Contact,
    FormulaAuditEntry,
    JobDescription,
    Rating,
    Resume,
    ScanResult,
    Score,
    ScoringConfig,
)
from open_ats.reporting.json_report import render_json, write_json


@pytest.fixture
def scan_result() -> ScanResult:
    return ScanResult(
        scan_id="00000000-0000-0000-0000-000000000000",
        timestamp=datetime(2026, 5, 8, 12, 0, 0, tzinfo=timezone.utc),
        open_ats_version="0.1.0",
        resume_hash="a" * 64,
        jd_hash="b" * 64,
        resume=Resume(
            source_format="markdown",
            contact=Contact(full_name="Test User", email="t@example.com"),
        ),
        job_description=JobDescription(title="Test Role"),
        analyzer_results=[
            AnalyzerResult(
                analyzer="keyword",
                score=72.5,
                sub_scores={"hard_skills": 70.0, "soft_skills": 80.0},
            )
        ],
        score=Score(
            overall=72.5,
            rating=Rating.GOOD,
            categories=[
                CategoryScore(
                    name="keyword",
                    score=72.5,
                    weight=1.0,
                    contribution=72.5,
                    sub_scores={"hard_skills": 70.0, "soft_skills": 80.0},
                ),
            ],
            formula_audit=[
                FormulaAuditEntry(
                    step="overall",
                    formula="sum",
                    inputs={"keyword": 72.5},
                    output=72.5,
                ),
            ],
        ),
        config=ScoringConfig(role_level="mid", weights={"keyword": 1.0}),
    )


def test_render_json_returns_string(scan_result: ScanResult) -> None:
    out = render_json(scan_result)
    assert isinstance(out, str)
    assert out.startswith("{")


def test_render_json_is_valid_json(scan_result: ScanResult) -> None:
    parsed = json.loads(render_json(scan_result))
    assert parsed["score"]["overall"] == 72.5
    assert parsed["score"]["rating"] == "good"


def test_render_json_keys_sorted(scan_result: ScanResult) -> None:
    """Sorted keys are required for byte-stable diffs across runs."""
    out = render_json(scan_result)
    parsed = json.loads(out)
    # Top-level keys appear in alphabetical order in the rendered string.
    keys_in_order = list(parsed.keys())
    assert keys_in_order == sorted(keys_in_order)


def test_render_json_is_deterministic(scan_result: ScanResult) -> None:
    a = render_json(scan_result)
    b = render_json(scan_result)
    assert a == b


def test_write_json_writes_file(tmp_path: Path, scan_result: ScanResult) -> None:
    out = tmp_path / "report.json"
    write_json(scan_result, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert content.endswith("\n")
    parsed = json.loads(content)
    assert parsed["score"]["overall"] == 72.5
