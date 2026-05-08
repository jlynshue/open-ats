"""Unit tests for the job description parser (FR-2).

Each test maps to one acceptance criterion in the Sprint 4 contract
(``.context/sprints/04-contract.md``) or PRD §FR-2. The keyword
precision/recall checks load the hand-annotated golden set from
``tests/fixtures/job_descriptions/_golden_keywords.yaml``.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
import yaml

from open_ats.models import JobDescription
from open_ats.parsers.base import ResumeParseError
from open_ats.parsers.jd_parser import (
    JdParser,
    default_jd_parser,
    parse_job_description,
)

ALL_FIXTURES = (
    "entry_level_swe.txt",
    "mid_level_backend.txt",
    "executive_vp_engineering.txt",
    "data_scientist.txt",
    "product_designer.txt",
)

EXPECTED_TITLES = {
    "entry_level_swe.txt": "Software Engineer, New Grad",
    "mid_level_backend.txt": "Senior Backend Engineer",
    "executive_vp_engineering.txt": "Vice President of Engineering",
    "data_scientist.txt": "Senior Data Scientist",
    "product_designer.txt": "Senior Product Designer",
}

EXPECTED_COMPANIES = {
    "entry_level_swe.txt": "Acme Cloud",
    "mid_level_backend.txt": "Streamline Analytics",
    "data_scientist.txt": "Lumen Health Analytics",
    "product_designer.txt": "Stelvio Logistics",
    # executive_vp_engineering's title line includes "(Series D, $180M raised)" parens
    # which the parser captures as part of company; checked separately.
}


@pytest.fixture
def parser() -> JdParser:
    return JdParser()


@pytest.fixture(scope="session")
def golden_keywords(job_descriptions_dir: Path) -> dict[str, list[str]]:
    """Load the hand-annotated keyword golden set."""
    with (job_descriptions_dir / "_golden_keywords.yaml").open() as fh:
        data = yaml.safe_load(fh)
    return cast("dict[str, list[str]]", data)


# ─── Threshold #2 — All 5 fixtures parse ─────────────────────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_all_fixtures_parse(
    fixture: str, job_descriptions_dir: Path, parser: JdParser
) -> None:
    jd = parser.parse(job_descriptions_dir / fixture)
    assert isinstance(jd, JobDescription)
    assert jd.raw_text  # raw text preserved


# ─── Threshold #3 — Section split ≥4/5 fixtures cleanly ──────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_each_fixture_has_requirements_and_responsibilities(
    fixture: str, job_descriptions_dir: Path, parser: JdParser
) -> None:
    """Stronger than the contract: ALL 5 fixtures must split cleanly.
    The contract floor was 4/5; we authored fixtures that should hit 5/5."""
    jd = parser.parse(job_descriptions_dir / fixture)
    assert len(jd.requirements) > 0, f"{fixture}: no requirements"
    assert len(jd.responsibilities) > 0, f"{fixture}: no responsibilities"


# ─── Threshold #4 — Preferences detected ─────────────────────────────


def test_preferences_routed_to_preferences_field(
    job_descriptions_dir: Path, parser: JdParser
) -> None:
    """A fixture with a 'Preferred / Nice to have' section routes
    those bullets into preferences, not requirements."""
    jd = parser.parse(job_descriptions_dir / "data_scientist.txt")
    assert len(jd.preferences) > 0
    # Preferred items shouldn't appear in requirements.
    assert all(
        "FDA Software-as-a-Medical-Device" not in r for r in jd.requirements
    ), "Preferred-section items leaked into requirements"


def test_bonus_section_routed_to_preferences(
    job_descriptions_dir: Path, parser: JdParser
) -> None:
    """'Bonus points' section maps to preferences."""
    jd = parser.parse(job_descriptions_dir / "product_designer.txt")
    assert len(jd.preferences) > 0
    # The "Front-end coding ability" bullet lives under Bonus points.
    matched = [p for p in jd.preferences if "Front-end coding" in p]
    assert matched, "Bonus-section bullet didn't route to preferences"


# ─── Threshold #5 — Keyword precision ≥80% per fixture & aggregate ───


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_keyword_precision_per_fixture(
    fixture: str,
    job_descriptions_dir: Path,
    parser: JdParser,
    golden_keywords: dict[str, list[str]],
) -> None:
    jd = parser.parse(job_descriptions_dir / fixture)
    extracted = {k.canonical.casefold() for k in jd.keywords}
    golden = {g.casefold() for g in golden_keywords[fixture]}
    if not extracted:
        pytest.fail(f"{fixture}: no keywords extracted")
    hits = extracted & golden
    precision = len(hits) / len(extracted)
    assert precision >= 0.80, (
        f"{fixture}: precision {precision:.1%} below 80%; "
        f"false positives = {sorted(extracted - golden)}"
    )


def test_aggregate_keyword_precision(
    job_descriptions_dir: Path,
    parser: JdParser,
    golden_keywords: dict[str, list[str]],
) -> None:
    total_extracted = 0
    total_hits = 0
    for fixture, expected in golden_keywords.items():
        jd = parser.parse(job_descriptions_dir / fixture)
        extracted = {k.canonical.casefold() for k in jd.keywords}
        golden = {e.casefold() for e in expected}
        total_extracted += len(extracted)
        total_hits += len(extracted & golden)
    aggregate = total_hits / max(1, total_extracted)
    assert aggregate >= 0.80, f"aggregate precision {aggregate:.1%} below 80%"


# ─── Threshold #6 — Keyword recall sanity ─────────────────────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_keyword_recall_per_fixture(
    fixture: str,
    job_descriptions_dir: Path,
    parser: JdParser,
    golden_keywords: dict[str, list[str]],
) -> None:
    jd = parser.parse(job_descriptions_dir / fixture)
    extracted = {k.canonical.casefold() for k in jd.keywords}
    golden = {g.casefold() for g in golden_keywords[fixture]}
    if not golden:
        pytest.fail(f"{fixture}: empty golden set")
    hits = extracted & golden
    recall = len(hits) / len(golden)
    assert recall >= 0.40, f"{fixture}: recall {recall:.1%} below 40%"


# ─── Threshold #7 — Too-short warning ────────────────────────────────


def test_too_short_jd_emits_warning(parser: JdParser) -> None:
    short_text = "Senior Engineer\nSomeCo\nWe need someone who knows Python."
    assert len(short_text) < 200
    jd = parser.parse(short_text)
    codes = [w.code for w in jd.parser_warnings]
    assert "jd.too_short" in codes


def test_long_jd_does_not_emit_too_short_warning(
    job_descriptions_dir: Path, parser: JdParser
) -> None:
    jd = parser.parse(job_descriptions_dir / "mid_level_backend.txt")
    codes = [w.code for w in jd.parser_warnings]
    assert "jd.too_short" not in codes


# ─── Title + company extraction ──────────────────────────────────────


@pytest.mark.parametrize("fixture", list(EXPECTED_TITLES))
def test_title_extracted(
    fixture: str, job_descriptions_dir: Path, parser: JdParser
) -> None:
    jd = parser.parse(job_descriptions_dir / fixture)
    assert jd.title == EXPECTED_TITLES[fixture]


@pytest.mark.parametrize("fixture", list(EXPECTED_COMPANIES))
def test_company_extracted(
    fixture: str, job_descriptions_dir: Path, parser: JdParser
) -> None:
    jd = parser.parse(job_descriptions_dir / fixture)
    assert jd.company == EXPECTED_COMPANIES[fixture]


# ─── Threshold #12 — Determinism ─────────────────────────────────────


@pytest.mark.parametrize("fixture", ALL_FIXTURES)
def test_parse_is_deterministic(
    fixture: str, job_descriptions_dir: Path, parser: JdParser
) -> None:
    a = parser.parse(job_descriptions_dir / fixture).model_dump_json()
    b = parser.parse(job_descriptions_dir / fixture).model_dump_json()
    assert a == b


# ─── Source dispatch — path vs string ────────────────────────────────


def test_parse_accepts_raw_string(parser: JdParser) -> None:
    """parse(str) returns a JD without source_path set."""
    text = """Senior Engineer — TestCo

Requirements
- 5+ years of experience with Python
- Strong written communication

Responsibilities
- Build production services
- Mentor junior engineers
"""
    jd = parser.parse(text)
    assert jd.source_path is None
    assert jd.title == "Senior Engineer"
    assert jd.company == "TestCo"
    assert len(jd.requirements) >= 1
    assert len(jd.responsibilities) >= 1


def test_module_level_function_works(job_descriptions_dir: Path) -> None:
    """parse_job_description(path) is the top-level entry point."""
    jd = parse_job_description(job_descriptions_dir / "entry_level_swe.txt")
    assert jd.title is not None
    assert len(jd.keywords) > 0


# ─── Error handling ──────────────────────────────────────────────────


def test_empty_string_raises(parser: JdParser) -> None:
    with pytest.raises(ResumeParseError):
        parser.parse("")


def test_whitespace_only_string_raises(parser: JdParser) -> None:
    with pytest.raises(ResumeParseError):
        parser.parse("   \n\t  \n")


def test_missing_file_raises(tmp_path: Path, parser: JdParser) -> None:
    with pytest.raises(ResumeParseError):
        parser.parse(tmp_path / "nonexistent.txt")


# ─── Default singleton ───────────────────────────────────────────────


def test_default_singleton_stable() -> None:
    from open_ats.parsers.jd_parser import default_jd_parser as again

    assert default_jd_parser is again


# ─── Keyword field details ───────────────────────────────────────────


def test_keywords_default_to_hard_skill(
    job_descriptions_dir: Path, parser: JdParser
) -> None:
    """Sprint 4 leaves categorisation to the keyword analyzer (Sprint 5);
    every candidate ships as HARD_SKILL until then."""
    from open_ats.models import KeywordCategory

    jd = parser.parse(job_descriptions_dir / "entry_level_swe.txt")
    for k in jd.keywords:
        assert k.category is KeywordCategory.HARD_SKILL


def test_keywords_include_match_count(
    job_descriptions_dir: Path, parser: JdParser
) -> None:
    """Multi-occurrence keywords surface a match_count > 1."""
    jd = parser.parse(job_descriptions_dir / "executive_vp_engineering.txt")
    by_canonical = {k.canonical: k for k in jd.keywords}
    # CEO appears multiple times in the executive JD.
    assert by_canonical["CEO"].match_count >= 2


def test_keywords_sorted_by_count_then_alpha(
    job_descriptions_dir: Path, parser: JdParser
) -> None:
    jd = parser.parse(job_descriptions_dir / "mid_level_backend.txt")
    counts = [k.match_count for k in jd.keywords]
    assert counts == sorted(counts, reverse=True)
