"""Unit tests for the plain-text resume parser (FR-1.4).

Each test maps to one acceptance criterion in the Sprint 2 contract
(``.context/sprints/02-contract.md``) or PRD §FR-1.4. TXT is the
lossiest format — section detection threshold is ≥2 (vs ≥3 for DOCX,
≥4 for Markdown).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from open_ats.models import Resume, SectionType
from open_ats.parsers import (
    ResumeParseError,
    TxtParser,
    parse_resume,
)
from open_ats.parsers.txt_parser import default_txt_parser

EXPECTED_CONTACTS = {
    "entry_level.txt": {
        "full_name": "Avery Chen",
        "email": "avery.chen.entry@example.com",
    },
    "mid_level.txt": {
        "full_name": "Jordan Patel",
        "email": "jordan.patel.mid@example.com",
    },
    "executive.txt": {
        "full_name": "Morgan Reyes",
        "email": "morgan.reyes.exec@example.com",
    },
}

ALL_FIXTURES = tuple(EXPECTED_CONTACTS.keys())


@pytest.fixture
def parser() -> TxtParser:
    return TxtParser()


# ─── Threshold #3 — TXT dispatch ─────────────────────────────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_dispatcher_routes_txt(fixture: str, resumes_dir: Path) -> None:
    """parse_resume() routes .txt through TxtParser and tags source_format."""
    resume = parse_resume(resumes_dir / fixture)
    assert isinstance(resume, Resume)
    assert resume.source_format == "txt"


# ─── Threshold #5 — TXT coverage ─────────────────────────────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_contact_extracted(fixture: str, resumes_dir: Path, parser: TxtParser) -> None:
    resume = parser.parse(resumes_dir / fixture)
    assert resume.contact.full_name == EXPECTED_CONTACTS[fixture]["full_name"]
    assert resume.contact.email == EXPECTED_CONTACTS[fixture]["email"]


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_section_detection_at_least_two(
    fixture: str, resumes_dir: Path, parser: TxtParser
) -> None:
    """≥2 of {SUMMARY, EXPERIENCE, EDUCATION, SKILLS, PROJECTS} per fixture."""
    resume = parser.parse(resumes_dir / fixture)
    targets = {
        SectionType.SUMMARY,
        SectionType.EXPERIENCE,
        SectionType.EDUCATION,
        SectionType.SKILLS,
        SectionType.PROJECTS,
    }
    detected = {s.type for s in resume.sections} & targets
    assert len(detected) >= 2, f"{fixture}: detected only {detected}"


# ─── Heading detection — heuristic styles ────────────────────────────


def test_all_caps_heading_recognised(tmp_path: Path, parser: TxtParser) -> None:
    """ALL CAPS short line on its own → recognised as a section heading
    when the text matches a known section name."""
    txt = tmp_path / "caps.txt"
    txt.write_text(
        "Test User\n"
        "test@example.com\n"
        "\n"
        "EXPERIENCE\n"
        "\n"
        "Engineer at Acme — 2020 to 2023\n"
        "- Built things\n"
        "\n"
        "EDUCATION\n"
        "\n"
        "B.S. CS — University of X — 2020\n"
    )
    resume = parser.parse(txt)
    types = {s.type for s in resume.sections}
    assert SectionType.EXPERIENCE in types
    assert SectionType.EDUCATION in types


def test_trailing_colon_heading_recognised(tmp_path: Path, parser: TxtParser) -> None:
    """``Section:`` with a trailing colon recognised as heading."""
    txt = tmp_path / "colon.txt"
    txt.write_text(
        "Test User\n"
        "test@example.com\n"
        "\n"
        "Summary:\n"
        "A short professional summary.\n"
        "\n"
        "Experience:\n"
        "Engineer at Acme — 2020 to 2023\n"
        "- Built things\n"
    )
    resume = parser.parse(txt)
    types = {s.type for s in resume.sections}
    assert SectionType.SUMMARY in types
    assert SectionType.EXPERIENCE in types


def test_underline_heading_recognised(tmp_path: Path, parser: TxtParser) -> None:
    """Heading underlined with ``===`` (H1) or ``---`` (H2)."""
    txt = tmp_path / "underline.txt"
    txt.write_text(
        "Test User\n"
        "test@example.com\n"
        "\n"
        "Experience\n"
        "----------\n"
        "Engineer at Acme — 2020 to 2023\n"
        "- Built things\n"
    )
    resume = parser.parse(txt)
    types = {s.type for s in resume.sections}
    assert SectionType.EXPERIENCE in types


def test_emphatic_caps_body_text_not_misclassified_as_heading(
    tmp_path: Path, parser: TxtParser
) -> None:
    """An ALL CAPS phrase that doesn't match a known section name is
    NOT promoted to a heading (avoids body-text false positives)."""
    txt = tmp_path / "shout.txt"
    txt.write_text(
        "Test User\n"
        "test@example.com\n"
        "\n"
        "EXPERIENCE\n"
        "\n"
        "Engineer at Acme — built things FAST and WELL.\n"
        "- Did stuff\n"
    )
    resume = parser.parse(txt)
    headings = [s.raw_heading for s in resume.sections]
    assert not any("FAST" in h or "WELL" in h for h in headings)


def test_bullet_styles_recognised(tmp_path: Path, parser: TxtParser) -> None:
    """``-``, ``*``, ``•``, and numbered (``1.``) all count as bullets."""
    txt = tmp_path / "bullets.txt"
    txt.write_text(
        "Test User\n"
        "test@example.com\n"
        "\n"
        "EXPERIENCE\n"
        "\n"
        "Engineer at Acme — 2020 to 2023\n"
        "- Hyphen bullet\n"
        "* Star bullet\n"
        "• Unicode bullet\n"
        "1. Numbered bullet\n"
    )
    resume = parser.parse(txt)
    exp_section = next(s for s in resume.sections if s.type == SectionType.EXPERIENCE)
    bullet_text = " ".join(exp_section.bullets)
    assert "Hyphen bullet" in bullet_text
    assert "Star bullet" in bullet_text
    assert "Unicode bullet" in bullet_text
    assert "Numbered bullet" in bullet_text


# ─── Determinism ─────────────────────────────────────────────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_parse_is_deterministic(
    fixture: str, resumes_dir: Path, parser: TxtParser
) -> None:
    a = parser.parse(resumes_dir / fixture).model_dump_json()
    b = parser.parse(resumes_dir / fixture).model_dump_json()
    assert a == b


# ─── Error handling ──────────────────────────────────────────────────


def test_empty_txt_raises_resume_parse_error(tmp_path: Path, parser: TxtParser) -> None:
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    with pytest.raises(ResumeParseError):
        parser.parse(empty)


def test_whitespace_only_txt_raises_resume_parse_error(
    tmp_path: Path, parser: TxtParser
) -> None:
    ws = tmp_path / "ws.txt"
    ws.write_text("\n\n  \t\n")
    with pytest.raises(ResumeParseError):
        parser.parse(ws)


# ─── Default singleton ───────────────────────────────────────────────


def test_default_singleton_stable() -> None:
    from open_ats.parsers.txt_parser import default_txt_parser as again

    assert default_txt_parser is again


# ─── Source-format tagging ───────────────────────────────────────────


def test_source_format_overridden_to_txt(tmp_path: Path, parser: TxtParser) -> None:
    """Even though TxtParser delegates to MarkdownParser internally, the
    final Resume.source_format must reflect the original (txt)."""
    txt = tmp_path / "src.txt"
    txt.write_text(
        "Test User\n" "test@example.com\n" "\n" "EXPERIENCE\n" "\n" "- Did things\n"
    )
    resume = parser.parse(txt)
    assert resume.source_format == "txt"
