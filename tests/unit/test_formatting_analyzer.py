"""Unit tests for the formatting analyzer (FR-5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from open_ats.analyzers.formatting import FormattingAnalyzer
from open_ats.models import (
    AnalyzerResult,
    Contact,
    ExperienceEntry,
    JobDescription,
    ParserWarning,
    Resume,
)


@pytest.fixture
def analyzer() -> FormattingAnalyzer:
    return FormattingAnalyzer()


@pytest.fixture
def jd() -> JobDescription:
    return JobDescription()


def _make_resume(**overrides: object) -> Resume:
    base: dict[str, object] = {
        "source_format": "markdown",
        "contact": Contact(full_name="Pat Tester", email="pat@example.com"),
        "experience": [],
        "skills": [],
        "sections": [],
        "summary": None,
        "parser_warnings": [],
    }
    base.update(overrides)
    return Resume.model_validate(base)


# ─── Penalty: tables ─────────────────────────────────────────────────


def test_table_warning_subtracts_ten(
    analyzer: FormattingAnalyzer, jd: JobDescription
) -> None:
    resume = _make_resume(
        parser_warnings=[ParserWarning(code="formatting.table_detected", message="x")]
    )
    result = analyzer.analyze(resume, jd)
    assert result.score == 90.0
    assert any("formatting.table" in i for i in result.issues)


# ─── Penalty: missing contact ────────────────────────────────────────


def test_missing_email_subtracts_fifteen(
    analyzer: FormattingAnalyzer, jd: JobDescription
) -> None:
    resume = _make_resume(contact=Contact(full_name="No Email"))
    result = analyzer.analyze(resume, jd)
    assert result.score == 85.0


def test_missing_name_subtracts_fifteen(
    analyzer: FormattingAnalyzer, jd: JobDescription
) -> None:
    resume = _make_resume(contact=Contact(email="x@example.com"))
    result = analyzer.analyze(resume, jd)
    assert result.score == 85.0


def test_missing_both_subtracts_thirty(
    analyzer: FormattingAnalyzer, jd: JobDescription
) -> None:
    resume = _make_resume(contact=Contact())
    result = analyzer.analyze(resume, jd)
    assert result.score == 70.0


# ─── Penalty: date inconsistency ─────────────────────────────────────


def test_consistent_dates_no_penalty(
    analyzer: FormattingAnalyzer, jd: JobDescription
) -> None:
    resume = _make_resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                start_date="2021-03",
                end_date="2022-09",
                bullets=["did things"],
            ),
            ExperienceEntry(
                title="B",
                company="Y",
                start_date="2018-09",
                end_date="2021-02",
                bullets=["did more things"],
            ),
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert result.score == 100.0


def test_mixed_date_formats_subtracts_five(
    analyzer: FormattingAnalyzer, jd: JobDescription
) -> None:
    resume = _make_resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                start_date="March 2021",  # word
                end_date="Present",
                bullets=["x"],
            ),
            ExperienceEntry(
                title="B",
                company="Y",
                start_date="2018-09",  # iso
                end_date="2021-02",
                bullets=["y"],
            ),
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert any("date_inconsistency" in i for i in result.issues)
    assert result.score < 100.0


# ─── Penalty: special-char inconsistency ─────────────────────────────


def test_em_dash_and_hyphen_inconsistency(
    analyzer: FormattingAnalyzer, jd: JobDescription
) -> None:
    resume = _make_resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                bullets=[
                    "Built thing — using em-dash",
                    "Shipped thing - using hyphen",
                ],
            )
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert any("special_chars" in i for i in result.issues)


# ─── Penalty: long lines ─────────────────────────────────────────────


def test_long_line_penalty(analyzer: FormattingAnalyzer, jd: JobDescription) -> None:
    long_bullet = "x" * 150
    resume = _make_resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                bullets=[long_bullet],
            )
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert any("long_lines" in i for i in result.issues)


# ─── Adversarial fixture (Sprint 7 grading threshold #3) ─────────────


def test_adversarial_fixture_flags_all_issue_types(
    analyzer: FormattingAnalyzer,
    jd: JobDescription,
    resumes_dir: Path,
) -> None:
    """tests/fixtures/resumes/adversarial.md seeds every penalty type."""
    from open_ats.parsers import parse_resume

    resume = parse_resume(resumes_dir / "adversarial.md")
    result = analyzer.analyze(resume, jd)
    issue_codes = " ".join(result.issues)

    # Adversarial fixture has: missing email, mixed dates, em-dash + hyphen, long line
    assert "missing_email" in issue_codes
    assert "date_inconsistency" in issue_codes
    assert "special_chars" in issue_codes
    assert "long_lines" in issue_codes


# ─── Score floor ─────────────────────────────────────────────────────


def test_score_never_negative(analyzer: FormattingAnalyzer, jd: JobDescription) -> None:
    """Even with stacked penalties, score floors at 0."""
    long_lines = ["x" * 150 for _ in range(20)]
    resume = _make_resume(
        contact=Contact(),  # missing both email + name → -30
        parser_warnings=[ParserWarning(code="formatting.table_detected", message="x")],
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                start_date="March 2020",
                end_date="2022-01",
                bullets=long_lines,
            )
        ],
    )
    result = analyzer.analyze(resume, jd)
    assert result.score >= 0.0


# ─── Result shape ────────────────────────────────────────────────────


def test_result_shape(analyzer: FormattingAnalyzer, jd: JobDescription) -> None:
    resume = _make_resume()
    result = analyzer.analyze(resume, jd)
    assert isinstance(result, AnalyzerResult)
    assert result.analyzer == "formatting"
    assert 0.0 <= result.score <= 100.0
    assert "starting_score" in result.sub_scores
    assert "total_penalty" in result.sub_scores


def test_clean_resume_scores_full(
    analyzer: FormattingAnalyzer, jd: JobDescription
) -> None:
    """A resume with email, name, consistent ISO dates, no tables, no
    long lines → score 100."""
    resume = _make_resume(
        experience=[
            ExperienceEntry(
                title="Engineer",
                company="Acme",
                start_date="2020-01",
                end_date="2022-12",
                bullets=["Did things"],
            ),
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert result.score == 100.0
