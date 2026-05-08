"""Unit tests for the keyword analyzer (FR-3, PRD §8 keyword formula)."""

from __future__ import annotations

from pathlib import Path

import pytest

from open_ats.analyzers._database import (
    DatabaseEntry,
    KeywordDatabase,
    load_default_database,
)
from open_ats.analyzers.keyword import KeywordAnalyzer
from open_ats.models import (
    AnalyzerResult,
    JobDescription,
    Keyword,
    KeywordCategory,
)
from open_ats.parsers import parse_resume
from open_ats.parsers.jd_parser import parse_job_description


@pytest.fixture(scope="module")
def db() -> KeywordDatabase:
    return load_default_database()


@pytest.fixture
def analyzer(db: KeywordDatabase) -> KeywordAnalyzer:
    return KeywordAnalyzer(db)


# ─── Database loading ────────────────────────────────────────────────


def test_default_database_loads_nonempty(db: KeywordDatabase) -> None:
    assert len(db) > 0


def test_database_classify_known_token(db: KeywordDatabase) -> None:
    assert db.classify("Python") == KeywordCategory.HARD_SKILL


def test_database_classify_synonym(db: KeywordDatabase) -> None:
    """`postgres` is a declared synonym for PostgreSQL in the seed YAML."""
    assert db.classify("postgres") == KeywordCategory.HARD_SKILL
    assert db.canonical("postgres") == "PostgreSQL"


def test_database_classify_unknown(db: KeywordDatabase) -> None:
    assert db.classify("notarealthing") is None


def test_database_canonical_preserves_casing(db: KeywordDatabase) -> None:
    """Canonical spelling honours the YAML — even if the lookup is lowercased."""
    assert db.canonical("PYTHON") == "Python"


# ─── Analyzer happy path ─────────────────────────────────────────────


def test_analyzer_returns_analyzer_result_shape(
    analyzer: KeywordAnalyzer,
    resumes_dir: Path,
    job_descriptions_dir: Path,
) -> None:
    resume = parse_resume(resumes_dir / "mid_level.md")
    jd = parse_job_description(job_descriptions_dir / "mid_level_backend.txt")
    result = analyzer.analyze(resume, jd)

    assert isinstance(result, AnalyzerResult)
    assert result.analyzer == "keyword"
    assert 0.0 <= result.score <= 100.0
    assert set(result.sub_scores.keys()) == {
        "hard_skills",
        "soft_skills",
        "action_verbs",
        "industry_terms",
    }
    for sub_value in result.sub_scores.values():
        assert 0.0 <= sub_value <= 100.0


def test_analyzer_metadata_populated(
    analyzer: KeywordAnalyzer,
    resumes_dir: Path,
    job_descriptions_dir: Path,
) -> None:
    resume = parse_resume(resumes_dir / "mid_level.md")
    jd = parse_job_description(job_descriptions_dir / "mid_level_backend.txt")
    result = analyzer.analyze(resume, jd)
    md = result.metadata
    assert md["hard_expected"] >= md["hard_matched"]
    assert md["action_verbs_used"] >= 0


# ─── Sub-score formula sanity ────────────────────────────────────────


def test_subscore_zero_when_nothing_matches(analyzer: KeywordAnalyzer) -> None:
    """A JD with one expected hard skill the resume doesn't have → 0."""
    from open_ats.models import Contact, Resume

    resume = Resume(
        source_format="markdown",
        contact=Contact(full_name="Test"),
        skills=[],
        experience=[],
    )
    jd = JobDescription(
        keywords=[Keyword(canonical="Python", category=KeywordCategory.HARD_SKILL)]
    )
    result = analyzer.analyze(resume, jd)
    # Only hard_skills has expected>0 in this JD; others default to 100.
    assert result.sub_scores["hard_skills"] == 0.0


def test_overall_weights_sum_to_one() -> None:
    """Sanity: PRD weights sum to 1.0 (0.50 + 0.25 + 0.15 + 0.10)."""
    from open_ats.analyzers import keyword as kw_module

    total = (
        kw_module._HARD_WEIGHT
        + kw_module._SOFT_WEIGHT
        + kw_module._ACTION_WEIGHT
        + kw_module._INDUSTRY_WEIGHT
    )
    assert abs(total - 1.0) < 1e-9


def test_overall_reconstruct_from_sub_scores(
    analyzer: KeywordAnalyzer,
    resumes_dir: Path,
    job_descriptions_dir: Path,
) -> None:
    """Threshold #10: weighted sum of sub-scores reproduces overall ±0.5."""
    resume = parse_resume(resumes_dir / "mid_level.md")
    jd = parse_job_description(job_descriptions_dir / "mid_level_backend.txt")
    result = analyzer.analyze(resume, jd)
    expected_overall = (
        0.50 * result.sub_scores["hard_skills"]
        + 0.25 * result.sub_scores["soft_skills"]
        + 0.15 * result.sub_scores["action_verbs"]
        + 0.10 * result.sub_scores["industry_terms"]
    )
    assert abs(result.score - expected_overall) <= 0.5


# ─── Mismatch produces lower score (threshold #12) ───────────────────


def test_mismatch_resume_scores_lower_than_match(
    analyzer: KeywordAnalyzer,
    resumes_dir: Path,
    job_descriptions_dir: Path,
) -> None:
    """A mid-level backend resume should score higher against the
    backend JD than against a designer JD."""
    resume = parse_resume(resumes_dir / "mid_level.md")
    matched_jd = parse_job_description(job_descriptions_dir / "mid_level_backend.txt")
    designer_jd = parse_job_description(job_descriptions_dir / "product_designer.txt")
    matched = analyzer.analyze(resume, matched_jd)
    mismatched = analyzer.analyze(resume, designer_jd)
    assert mismatched.score < matched.score


# ─── Synonym matching ────────────────────────────────────────────────


def test_resume_match_via_synonym() -> None:
    """A resume containing 'postgres' (lowercase) matches a JD calling
    out PostgreSQL via the synonym index."""
    from open_ats.models import Contact, ExperienceEntry, Resume

    db = KeywordDatabase(
        entries=(
            DatabaseEntry(
                canonical="PostgreSQL",
                category=KeywordCategory.HARD_SKILL,
                synonyms=("postgres", "psql"),
            ),
        )
    )
    analyzer = KeywordAnalyzer(db)
    resume = Resume(
        source_format="markdown",
        contact=Contact(full_name="Test"),
        skills=[],
        experience=[
            ExperienceEntry(
                title="Engineer",
                company="A",
                bullets=["Operated postgres at 80K writes/sec"],
            )
        ],
    )
    jd = JobDescription(
        keywords=[Keyword(canonical="PostgreSQL", category=KeywordCategory.HARD_SKILL)]
    )
    result = analyzer.analyze(resume, jd)
    assert result.sub_scores["hard_skills"] == 100.0


# ─── JD candidates outside the database get dropped ──────────────────


def test_unknown_jd_keywords_dropped(analyzer: KeywordAnalyzer) -> None:
    """Sprint 4 leaves JD candidates as HARD_SKILL by default; ones not
    in the database (e.g., company names) shouldn't inflate expected
    counts."""
    from open_ats.models import Contact, Resume

    resume = Resume(
        source_format="markdown",
        contact=Contact(full_name="Test"),
        skills=["Python"],
        experience=[],
    )
    jd = JobDescription(
        keywords=[
            Keyword(canonical="Python", category=KeywordCategory.HARD_SKILL),
            Keyword(canonical="Acme Corp", category=KeywordCategory.HARD_SKILL),
            Keyword(canonical="madeupthing", category=KeywordCategory.HARD_SKILL),
        ]
    )
    result = analyzer.analyze(resume, jd)
    # Only Python is in the seed DB; expected=1, matched=1 → 100.
    assert result.sub_scores["hard_skills"] == 100.0


# ─── Action-verb extraction ──────────────────────────────────────────


def test_action_verbs_detected_at_bullet_start(analyzer: KeywordAnalyzer) -> None:
    """A resume with bullets that start with strong action verbs scores
    high on the action_verbs sub-score."""
    from open_ats.models import Contact, ExperienceEntry, Resume

    bullets = [
        "Led a team of 10",
        "Built the new platform",
        "Reduced latency by 40%",
        "Designed the API",
        "Mentored 3 engineers",
    ]
    resume = Resume(
        source_format="markdown",
        contact=Contact(full_name="Test"),
        experience=[
            ExperienceEntry(title="Eng", company="A", bullets=bullets),
        ],
    )
    jd = JobDescription()
    result = analyzer.analyze(resume, jd)
    # 5 distinct strong verbs out of a target of 10 → 50%.
    assert result.sub_scores["action_verbs"] == 50.0


def test_action_verbs_zero_when_no_bullets(analyzer: KeywordAnalyzer) -> None:
    from open_ats.models import Contact, Resume

    resume = Resume(
        source_format="markdown",
        contact=Contact(full_name="Test"),
        experience=[],
    )
    jd = JobDescription()
    result = analyzer.analyze(resume, jd)
    assert result.sub_scores["action_verbs"] == 0.0


# ─── Determinism ─────────────────────────────────────────────────────


def test_analyzer_is_deterministic(
    analyzer: KeywordAnalyzer,
    resumes_dir: Path,
    job_descriptions_dir: Path,
) -> None:
    resume = parse_resume(resumes_dir / "mid_level.md")
    jd = parse_job_description(job_descriptions_dir / "mid_level_backend.txt")
    a = analyzer.analyze(resume, jd).model_dump_json()
    b = analyzer.analyze(resume, jd).model_dump_json()
    assert a == b


# ─── Database loading edge cases ─────────────────────────────────────


def test_load_database_handles_empty_yaml(tmp_path: Path) -> None:
    from open_ats.analyzers._database import load_database

    f = tmp_path / "empty.yaml"
    f.write_text("")
    db = load_database(f)
    assert len(db) == 0


def test_load_database_handles_malformed_yaml(tmp_path: Path) -> None:
    from open_ats.analyzers._database import load_database

    f = tmp_path / "bad.yaml"
    # YAML scalar instead of mapping — handled gracefully.
    f.write_text("just a string")
    db = load_database(f)
    assert len(db) == 0


def test_load_databases_dedupes_by_canonical(tmp_path: Path) -> None:
    from open_ats.analyzers._database import load_databases

    a = tmp_path / "a.yaml"
    a.write_text("hard_skills: [Python]\n")
    b = tmp_path / "b.yaml"
    b.write_text("hard_skills: [Python, Go]\n")
    db = load_databases([a, b])
    canonicals = {e.canonical for e in db.entries}
    assert canonicals == {"Python", "Go"}
