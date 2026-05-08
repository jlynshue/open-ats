"""Unit tests for the PDF resume parser (FR-1.3).

Each test maps to one acceptance criterion in the Sprint 3 contract
(``.context/sprints/03-contract.md``) or PRD §FR-1.3.

Test fixtures (.pdf) are generated from the markdown originals by
``tests/fixtures/_build_binary_fixtures.py`` and checked into git.

Three fixtures exercise the three FR-1.3 paths:
- ``single_column.pdf`` — happy path, ≥3 sections + contact
- ``multi_column.pdf`` — degraded but functional, ≥2 sections + contact
- ``image_based.pdf`` — empty extraction, raises the FR-1.3 error verbatim
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from open_ats.models import Resume, SectionType
from open_ats.parsers import (
    PdfParser,
    ResumeParseError,
    parse_resume,
)
from open_ats.parsers.pdf_parser import IMAGE_BASED_MESSAGE, default_pdf_parser

SINGLE_COLUMN = "single_column.pdf"
MULTI_COLUMN = "multi_column.pdf"
IMAGE_BASED = "image_based.pdf"
TEXT_FIXTURES = (SINGLE_COLUMN, MULTI_COLUMN)


@pytest.fixture
def parser() -> PdfParser:
    return PdfParser()


# ─── Threshold #2 — PDF dispatch ─────────────────────────────────────


@pytest.mark.parametrize("fixture", TEXT_FIXTURES)
def test_dispatcher_routes_pdf(fixture: str, resumes_dir: Path) -> None:
    """parse_resume() routes .pdf through PdfParser and tags source_format."""
    resume = parse_resume(resumes_dir / fixture)
    assert isinstance(resume, Resume)
    assert resume.source_format == "pdf"


# ─── Threshold #3 — Single-column coverage ───────────────────────────


def test_single_column_contact(resumes_dir: Path, parser: PdfParser) -> None:
    resume = parser.parse(resumes_dir / SINGLE_COLUMN)
    assert resume.contact.full_name == "Avery Chen"
    assert resume.contact.email == "avery.chen.entry@example.com"


def test_single_column_sections_at_least_three(
    resumes_dir: Path, parser: PdfParser
) -> None:
    resume = parser.parse(resumes_dir / SINGLE_COLUMN)
    targets = {
        SectionType.SUMMARY,
        SectionType.EXPERIENCE,
        SectionType.EDUCATION,
        SectionType.SKILLS,
        SectionType.PROJECTS,
    }
    detected = {s.type for s in resume.sections} & targets
    assert len(detected) >= 3, f"single_column: detected only {detected}"


# ─── Threshold #4 — Multi-column coverage (degradation acceptable) ───


def test_multi_column_contact(resumes_dir: Path, parser: PdfParser) -> None:
    resume = parser.parse(resumes_dir / MULTI_COLUMN)
    # Contact survives column interleaving because it lives in the header.
    assert resume.contact.full_name == "Avery Chen"
    assert resume.contact.email == "avery.chen.entry@example.com"


def test_multi_column_sections_at_least_two(
    resumes_dir: Path, parser: PdfParser
) -> None:
    """Multi-column degrades cleanly: ≥2 of the canonical sections."""
    resume = parser.parse(resumes_dir / MULTI_COLUMN)
    targets = {
        SectionType.SUMMARY,
        SectionType.EXPERIENCE,
        SectionType.EDUCATION,
        SectionType.SKILLS,
        SectionType.PROJECTS,
    }
    detected = {s.type for s in resume.sections} & targets
    assert len(detected) >= 2, f"multi_column: detected only {detected}"


# ─── Threshold #5 — Image-based PDF raises verbatim FR-1.3 message ──


def test_image_based_raises_resume_parse_error(
    resumes_dir: Path, parser: PdfParser
) -> None:
    with pytest.raises(ResumeParseError) as excinfo:
        parser.parse(resumes_dir / IMAGE_BASED)
    assert IMAGE_BASED_MESSAGE in str(excinfo.value)


def test_image_based_message_matches_fr_1_3_verbatim() -> None:
    """The exact phrase the PRD requires."""
    assert (
        IMAGE_BASED_MESSAGE
        == "PDF appears to be image-based; please convert to text-based PDF"
    )


def test_image_based_dispatcher_path(resumes_dir: Path) -> None:
    """Routing through parse_resume() also raises (not just direct .parse)."""
    with pytest.raises(ResumeParseError) as excinfo:
        parse_resume(resumes_dir / IMAGE_BASED)
    assert "image-based" in str(excinfo.value)


# ─── Threshold #7 — Performance gate (NFR-1 partial) ─────────────────


def test_single_column_parses_under_two_seconds(
    resumes_dir: Path, parser: PdfParser
) -> None:
    """Single-column 1-page PDF must parse in <2 sec on the test runner.

    The shipped fixture is a single page; this is a budget check, not
    a precise benchmark. Sprint 11 lands the formal benchmark suite.
    """
    start = time.perf_counter()
    parser.parse(resumes_dir / SINGLE_COLUMN)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"parse took {elapsed:.3f}s (>2.0s gate)"


# ─── Threshold #11 — Determinism ─────────────────────────────────────


@pytest.mark.parametrize("fixture", TEXT_FIXTURES)
def test_parse_is_deterministic(
    fixture: str, resumes_dir: Path, parser: PdfParser
) -> None:
    a = parser.parse(resumes_dir / fixture).model_dump_json()
    b = parser.parse(resumes_dir / fixture).model_dump_json()
    assert a == b


# ─── Threshold #12 — Format dispatch closed ──────────────────────────


def test_supported_extensions_after_sprint_3() -> None:
    """All four FR-1 formats now register through the dispatcher."""
    from open_ats.parsers import supported_extensions

    exts = supported_extensions()
    assert ".docx" in exts
    assert ".markdown" in exts
    assert ".md" in exts
    assert ".pdf" in exts
    assert ".txt" in exts


def test_unrecognised_extension_still_unsupported(tmp_path: Path) -> None:
    """An extension we still don't support raises UnsupportedFormatError."""
    from open_ats.parsers import UnsupportedFormatError

    fake = tmp_path / "resume.rtf"
    fake.write_bytes(b"{\\rtf1}")
    with pytest.raises(UnsupportedFormatError):
        parse_resume(fake)


# ─── Error handling ──────────────────────────────────────────────────


def test_corrupt_pdf_raises_resume_parse_error(
    tmp_path: Path, parser: PdfParser
) -> None:
    """Random bytes with a .pdf extension wrap into ResumeParseError."""
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not really a pdf")
    with pytest.raises(ResumeParseError):
        parser.parse(bad)


# ─── Default singleton ───────────────────────────────────────────────


def test_default_singleton_stable() -> None:
    from open_ats.parsers.pdf_parser import default_pdf_parser as again

    assert default_pdf_parser is again


# ─── Source-format tagging ───────────────────────────────────────────


def test_source_format_overridden_to_pdf(resumes_dir: Path, parser: PdfParser) -> None:
    """PdfParser delegates to MarkdownParser internally; the final
    Resume.source_format must reflect the original (pdf)."""
    resume = parser.parse(resumes_dir / SINGLE_COLUMN)
    assert resume.source_format == "pdf"
