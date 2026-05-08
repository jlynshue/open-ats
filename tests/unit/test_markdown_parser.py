"""Unit tests for the Markdown resume parser (FR-1.1).

Each test maps to one acceptance criterion in the Sprint 1 contract
(``.context/sprints/01-contract.md``) or the PRD (``docs/PRD.md``
§FR-1.1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from open_ats.models import (
    ParserWarning,
    Resume,
    SectionType,
)
from open_ats.parsers import (
    MarkdownParser,
    ResumeParseError,
    UnsupportedFormatError,
    parse_resume,
    supported_extensions,
)
from open_ats.parsers.markdown_parser import default_markdown_parser

# ─── Expected values per fixture ──────────────────────────────────────


EXPECTED_CONTACTS = {
    "entry_level.md": {
        "full_name": "Avery Chen",
        "email": "avery.chen.entry@example.com",
    },
    "mid_level.md": {
        "full_name": "Jordan Patel",
        "email": "jordan.patel.mid@example.com",
    },
    "executive.md": {
        "full_name": "Morgan Reyes",
        "email": "morgan.reyes.exec@example.com",
    },
}

ALL_FIXTURES = (
    "entry_level.md",
    "mid_level.md",
    "executive.md",
    "no_email.md",
    "minimal.md",
)


# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def parser() -> MarkdownParser:
    return MarkdownParser()


# ─── Grading threshold #2 — All 5 fixtures parse ──────────────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_all_fixtures_parse_without_raising(
    fixture: str, resumes_dir: Path, parser: MarkdownParser
) -> None:
    """Every shipped Markdown fixture parses to a Resume."""
    resume = parser.parse(resumes_dir / fixture)
    assert isinstance(resume, Resume)
    assert resume.source_format == "markdown"


# ─── Grading threshold #3 — Contact accuracy ──────────────────────────


@pytest.mark.parametrize("fixture", list(EXPECTED_CONTACTS))
def test_contact_full_name_extracted(
    fixture: str, resumes_dir: Path, parser: MarkdownParser
) -> None:
    """Full name on each standard fixture matches expected value exactly."""
    resume = parser.parse(resumes_dir / fixture)
    assert resume.contact.full_name == EXPECTED_CONTACTS[fixture]["full_name"]


@pytest.mark.parametrize("fixture", list(EXPECTED_CONTACTS))
def test_contact_email_extracted(
    fixture: str, resumes_dir: Path, parser: MarkdownParser
) -> None:
    """Email on each standard fixture matches expected value exactly."""
    resume = parser.parse(resumes_dir / fixture)
    assert resume.contact.email == EXPECTED_CONTACTS[fixture]["email"]


def test_phone_extraction(resumes_dir: Path, parser: MarkdownParser) -> None:
    resume = parser.parse(resumes_dir / "entry_level.md")
    assert resume.contact.phone is not None
    assert "555" in resume.contact.phone


def test_linkedin_normalised_to_https(
    resumes_dir: Path, parser: MarkdownParser
) -> None:
    """LinkedIn URLs in fixtures are bare; parser must add https:// prefix."""
    resume = parser.parse(resumes_dir / "entry_level.md")
    assert resume.contact.linkedin is not None
    assert str(resume.contact.linkedin).startswith("https://linkedin.com/in/")


def test_github_normalised_to_https(resumes_dir: Path, parser: MarkdownParser) -> None:
    resume = parser.parse(resumes_dir / "entry_level.md")
    assert resume.contact.github is not None
    assert str(resume.contact.github).startswith("https://github.com/")


# ─── Grading threshold #4 — No-email fixture ──────────────────────────


def test_no_email_fixture_emits_warning(
    resumes_dir: Path, parser: MarkdownParser
) -> None:
    """no_email.md parses with email=None and an email_missing warning."""
    resume = parser.parse(resumes_dir / "no_email.md")
    assert resume.contact.email is None
    codes = [w.code for w in resume.parser_warnings]
    assert "contact.email_missing" in codes


def test_no_email_fixture_other_fields_intact(
    resumes_dir: Path, parser: MarkdownParser
) -> None:
    """Missing email doesn't poison the rest of the parse."""
    resume = parser.parse(resumes_dir / "no_email.md")
    assert resume.contact.full_name == "Sam Rivera"
    assert resume.contact.linkedin is not None
    assert len(resume.experience) >= 1


# ─── Grading threshold #5 — Minimal fixture ───────────────────────────


def test_minimal_fixture_emits_too_short_warning(
    resumes_dir: Path, parser: MarkdownParser
) -> None:
    """minimal.md (well under 200 words) triggers resume.too_short."""
    resume = parser.parse(resumes_dir / "minimal.md")
    codes = [w.code for w in resume.parser_warnings]
    assert "resume.too_short" in codes
    assert resume.word_count < 200


def test_minimal_fixture_at_least_one_section(
    resumes_dir: Path, parser: MarkdownParser
) -> None:
    """Minimal still surfaces at least one detected section."""
    resume = parser.parse(resumes_dir / "minimal.md")
    assert len(resume.sections) >= 1


# ─── Grading threshold #6 — Section detection ≥4/5 ───────────────────


@pytest.mark.parametrize("fixture", list(EXPECTED_CONTACTS))
def test_section_detection_at_least_four(
    fixture: str, resumes_dir: Path, parser: MarkdownParser
) -> None:
    """Each standard fixture surfaces ≥4 of {SUMMARY, EXPERIENCE, EDUCATION, SKILLS, PROJECTS}."""
    resume = parser.parse(resumes_dir / fixture)
    target_types = {
        SectionType.SUMMARY,
        SectionType.EXPERIENCE,
        SectionType.EDUCATION,
        SectionType.SKILLS,
        SectionType.PROJECTS,
    }
    detected = {s.type for s in resume.sections} & target_types
    assert len(detected) >= 4, f"{fixture}: detected only {detected} of {target_types}"


# ─── Section content checks ──────────────────────────────────────────


def test_experience_entries_extracted(
    resumes_dir: Path, parser: MarkdownParser
) -> None:
    """mid_level.md has 3 experience blocks, each with bullets."""
    resume = parser.parse(resumes_dir / "mid_level.md")
    assert len(resume.experience) == 3
    for entry in resume.experience:
        assert entry.title and entry.title != "(unknown)"
        assert entry.company and entry.company != "(unknown)"
        assert len(entry.bullets) >= 2


def test_education_extracted(resumes_dir: Path, parser: MarkdownParser) -> None:
    resume = parser.parse(resumes_dir / "entry_level.md")
    assert len(resume.education) >= 1
    edu = resume.education[0]
    assert "Computer Science" in edu.degree
    assert edu.gpa == 3.7


def test_skills_extracted(resumes_dir: Path, parser: MarkdownParser) -> None:
    resume = parser.parse(resumes_dir / "entry_level.md")
    skills_lower = {s.casefold() for s in resume.skills}
    # Spot-check a few from each category.
    assert "python" in skills_lower
    assert "fastapi" in skills_lower
    assert "git" in skills_lower


def test_summary_extracted(resumes_dir: Path, parser: MarkdownParser) -> None:
    resume = parser.parse(resumes_dir / "mid_level.md")
    assert resume.summary is not None
    assert "Software engineer" in resume.summary


def test_word_count_reasonable(resumes_dir: Path, parser: MarkdownParser) -> None:
    """Word count rejects markdown formatting markers but counts real words."""
    resume = parser.parse(resumes_dir / "executive.md")
    # Executive resume is the longest fixture; sanity bound rather than exact.
    assert 400 < resume.word_count < 1500


# ─── Grading threshold #11 — Determinism ──────────────────────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_parse_is_deterministic(
    fixture: str, resumes_dir: Path, parser: MarkdownParser
) -> None:
    """Parsing the same file twice yields byte-identical model_dump_json."""
    a = parser.parse(resumes_dir / fixture)
    b = parser.parse(resumes_dir / fixture)
    assert a.model_dump_json() == b.model_dump_json()


def test_parse_text_matches_parse_path(
    resumes_dir: Path, parser: MarkdownParser
) -> None:
    """parse_text and parse(path) produce equivalent Resumes for the same content."""
    text = (resumes_dir / "entry_level.md").read_text()
    via_text = parser.parse_text(text)
    via_path = parser.parse(resumes_dir / "entry_level.md")
    # source_path differs (None vs the path) — compare everything else.
    via_text_dict = via_text.model_dump()
    via_path_dict = via_path.model_dump()
    via_text_dict.pop("source_path")
    via_path_dict.pop("source_path")
    assert via_text_dict == via_path_dict


# ─── Grading threshold #12 — Format dispatch ──────────────────────────


def test_unsupported_format_raises(tmp_path: Path) -> None:
    """parse_resume() rejects extensions with no registered parser.

    Sprint 3 wired .pdf in, so .rtf takes over as the canary unsupported
    format. (FR-1 covers .md/.docx/.pdf/.txt; .rtf has no roadmap entry.)
    """
    fake = tmp_path / "resume.rtf"
    fake.write_bytes(b"{\\rtf1}")
    with pytest.raises(UnsupportedFormatError) as excinfo:
        parse_resume(fake)
    assert ".md" in excinfo.value.supported


def test_unsupported_format_message_lists_supported() -> None:
    err = UnsupportedFormatError(".rtf", [".md", ".markdown"])
    assert ".rtf" in str(err)
    assert ".md" in str(err)


def test_no_extension_raises_unsupported_format(tmp_path: Path) -> None:
    fake = tmp_path / "resume"
    fake.write_text("# Name")
    with pytest.raises(UnsupportedFormatError):
        parse_resume(fake)


def test_supported_extensions_listed() -> None:
    exts = supported_extensions()
    assert ".md" in exts
    assert ".markdown" in exts


# ─── Error handling ──────────────────────────────────────────────────


def test_empty_file_raises_resume_parse_error(
    tmp_path: Path, parser: MarkdownParser
) -> None:
    empty = tmp_path / "empty.md"
    empty.write_text("")
    with pytest.raises(ResumeParseError):
        parser.parse(empty)


def test_whitespace_only_raises_resume_parse_error(
    tmp_path: Path, parser: MarkdownParser
) -> None:
    ws = tmp_path / "whitespace.md"
    ws.write_text("   \n   \n\t\n")
    with pytest.raises(ResumeParseError):
        parser.parse(ws)


def test_malformed_email_emits_warning_not_crash(
    tmp_path: Path, parser: MarkdownParser
) -> None:
    """A bare ``@`` token shouldn't be mistaken for a real email and shouldn't crash."""
    bad = tmp_path / "bad.md"
    bad.write_text(
        "# Test User\n\n"
        "Some prose with a stray @ sign here.\n\n"
        "## Summary\n\nSomething.\n\n"
        "## Experience\n\n"
        "**Engineer** — Acme Co\n"
        "2020 – Present\n"
        "- Did things.\n"
    )
    resume = parser.parse(bad)
    assert resume.contact.email is None
    codes = [w.code for w in resume.parser_warnings]
    assert "contact.email_missing" in codes


def test_resume_parse_error_carries_cause() -> None:
    inner = ValueError("boom")
    err = ResumeParseError("wrapper", cause=inner)
    assert err.cause is inner


# ─── Heading edge cases ──────────────────────────────────────────────


def test_h2_only_resume_parses(tmp_path: Path, parser: MarkdownParser) -> None:
    """A resume that uses no H1 (name in plain text) still gets a name."""
    md = tmp_path / "h2.md"
    md.write_text(
        "Plain Text Name\n\n"
        "plain.text@example.com\n\n"
        "## Summary\n\nA summary.\n\n"
        "## Experience\n\n"
        "**Engineer** — Acme\n"
        "2022 – Present\n"
        "- Did things.\n"
        "- Did more things.\n"
    )
    resume = parser.parse(md)
    assert resume.contact.full_name == "Plain Text Name"


def test_section_heading_aliases(tmp_path: Path, parser: MarkdownParser) -> None:
    """'Work Experience' and 'Professional Summary' map to canonical types."""
    md = tmp_path / "aliases.md"
    md.write_text(
        "# Test\n\ntest@example.com\n\n"
        "## Professional Summary\n\nx.\n\n"
        "## Work Experience\n\n"
        "**Eng** — Acme\n"
        "2020 – 2022\n"
        "- Built things\n"
    )
    resume = parser.parse(md)
    types = {s.type for s in resume.sections}
    assert SectionType.SUMMARY in types
    assert SectionType.EXPERIENCE in types


def test_unknown_section_classified_as_other(
    tmp_path: Path, parser: MarkdownParser
) -> None:
    md = tmp_path / "other.md"
    md.write_text("# Test\n\ntest@example.com\n\n## Hobbies\n\nReading, hiking.\n")
    resume = parser.parse(md)
    types = {s.type for s in resume.sections}
    assert SectionType.OTHER in types


# ─── Smoke test for ParserWarning model ──────────────────────────────


def test_parser_warning_model_round_trip() -> None:
    w = ParserWarning(code="test.code", message="hello", severity="info")
    payload = w.model_dump()
    restored = ParserWarning.model_validate(payload)
    assert restored == w


def test_resume_dump_is_json_serialisable(
    resumes_dir: Path, parser: MarkdownParser
) -> None:
    resume = parser.parse(resumes_dir / "mid_level.md")
    payload = resume.model_dump_json()
    parsed = json.loads(payload)
    assert parsed["contact"]["full_name"] == "Jordan Patel"


# ─── Default-singleton sanity ────────────────────────────────────────


def test_default_markdown_parser_is_module_singleton() -> None:
    """Importing the default singleton is cheap and stable."""
    assert default_markdown_parser is not None
    # Two imports should return the same object.
    from open_ats.parsers.markdown_parser import default_markdown_parser as again

    assert default_markdown_parser is again
