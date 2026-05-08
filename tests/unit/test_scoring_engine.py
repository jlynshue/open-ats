"""Unit tests for the minimal Sprint-5 scoring engine."""

from __future__ import annotations

import pytest

from open_ats.models import AnalyzerResult, Rating
from open_ats.scoring.engine import (
    ScoringEngine,
    derive_rating,
    keyword_only_config,
)


def _result(score: float, sub: dict[str, float] | None = None) -> AnalyzerResult:
    return AnalyzerResult(
        analyzer="keyword",
        score=score,
        sub_scores=sub or {"hard_skills": score},
    )


# ─── Rating thresholds (PRD §8) ──────────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [
        (100.0, Rating.EXCELLENT),
        (80.0, Rating.EXCELLENT),
        (79.99, Rating.GOOD),
        (70.0, Rating.GOOD),
        (69.99, Rating.FAIR),
        (60.0, Rating.FAIR),
        (59.99, Rating.POOR),
        (0.0, Rating.POOR),
    ],
)
def test_derive_rating(value: float, expected: Rating) -> None:
    assert derive_rating(value) == expected


# ─── Engine output shape ─────────────────────────────────────────────


def test_engine_produces_one_category_per_analyzer() -> None:
    engine = ScoringEngine()
    result = _result(80.0)
    score = engine.score([result], keyword_only_config())
    assert len(score.categories) == 1
    assert score.categories[0].name == "keyword"
    assert score.categories[0].score == 80.0


def test_engine_uses_config_weights() -> None:
    engine = ScoringEngine()
    config = keyword_only_config()
    result = _result(50.0)
    score = engine.score([result], config)
    # Weight on "keyword" is 1.0 → contribution == score.
    assert score.categories[0].weight == 1.0
    assert score.categories[0].contribution == 50.0
    assert score.overall == 50.0


def test_engine_overall_clamped_to_0_100() -> None:
    """Even if a future analyzer returned >100, engine clamps."""
    engine = ScoringEngine()
    out_of_range_score = AnalyzerResult(analyzer="keyword", score=99.5)
    score = engine.score([out_of_range_score], keyword_only_config())
    assert 0.0 <= score.overall <= 100.0


def test_engine_rating_matches_overall() -> None:
    engine = ScoringEngine()
    score = engine.score([_result(72.0)], keyword_only_config())
    assert score.rating == Rating.GOOD


# ─── Formula audit completeness (threshold #11) ──────────────────────


def test_formula_audit_includes_subscores() -> None:
    engine = ScoringEngine()
    result = _result(
        70.0,
        sub={
            "hard_skills": 70.0,
            "soft_skills": 80.0,
            "action_verbs": 50.0,
            "industry_terms": 90.0,
        },
    )
    score = engine.score([result], keyword_only_config())
    audit_steps = {entry.step for entry in score.formula_audit}
    assert "keyword.hard_skills" in audit_steps
    assert "keyword.soft_skills" in audit_steps
    assert "keyword.action_verbs" in audit_steps
    assert "keyword.industry_terms" in audit_steps
    assert "keyword.contribution" in audit_steps
    assert "overall" in audit_steps


def test_formula_audit_overall_reconstructs_from_contributions() -> None:
    """Sum of CategoryScore contributions must equal Score.overall (within rounding)."""
    engine = ScoringEngine()
    result = _result(83.5)
    score = engine.score([result], keyword_only_config())
    sum_contributions = sum(c.contribution for c in score.categories)
    assert abs(sum_contributions - score.overall) <= 0.5


# ─── Empty input ─────────────────────────────────────────────────────


def test_engine_rejects_empty_results() -> None:
    engine = ScoringEngine()
    with pytest.raises(ValueError):
        engine.score([], keyword_only_config())
