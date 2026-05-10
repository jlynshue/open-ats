"""Unit tests for the content-quality analyzer (FR-6)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from open_ats.analyzers.content_quality import (
    ContentQualityAnalyzer,
    is_passive_sentence,
)
from open_ats.data._loader import (
    load_action_verbs,
    load_hedging_phrases,
    load_passive_markers,
    load_weak_verbs,
)
from open_ats.models import (
    AnalyzerResult,
    Contact,
    ExperienceEntry,
    JobDescription,
    Resume,
)


@pytest.fixture
def analyzer() -> ContentQualityAnalyzer:
    return ContentQualityAnalyzer()


@pytest.fixture
def jd() -> JobDescription:
    return JobDescription()


def _resume(**overrides: object) -> Resume:
    base: dict[str, object] = {
        "source_format": "markdown",
        "contact": Contact(full_name="T", email="t@example.com"),
        "experience": [],
        "skills": [],
        "sections": [],
        "summary": None,
        "word_count": 500,
    }
    base.update(overrides)
    return Resume.model_validate(base)


# ─── Word lists meet PRD minimums (Sprint 7 threshold #2) ────────────


def test_action_verbs_meets_50() -> None:
    assert len(load_action_verbs()) >= 50


def test_weak_verbs_meets_30() -> None:
    assert len(load_weak_verbs()) >= 30


def test_passive_markers_meets_15() -> None:
    assert len(load_passive_markers()) >= 15


def test_hedging_phrases_meets_10() -> None:
    assert len(load_hedging_phrases()) >= 10


# ─── Passive-voice detection — recall ≥ 80% on golden set ────────────


def test_passive_recall_against_golden(job_descriptions_dir: Path) -> None:
    """Sprint 7 grading threshold #4."""
    golden = (
        job_descriptions_dir.parent / "golden" / "passive_sentences.yaml"
    ).read_text()
    sentences = yaml.safe_load(golden)["sentences"]
    tp = fn = 0
    misses: list[str] = []
    for s in sentences:
        pred = is_passive_sentence(s["text"])
        if s["passive"]:
            if pred:
                tp += 1
            else:
                fn += 1
                misses.append(s["text"])
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    assert recall >= 0.80, f"passive recall {recall:.1%} < 80% gate; missed: {misses}"


def test_passive_marker_phrases_detected() -> None:
    assert is_passive_sentence("I was responsible for code review.")
    assert is_passive_sentence("We were tasked with reducing AWS spend.")
    assert is_passive_sentence("The role had been split before I joined.")


def test_aux_participle_regex_catches_general_passive() -> None:
    assert is_passive_sentence("All endpoints are tested via the new harness.")
    assert is_passive_sentence("The migration was completed in three weeks.")


def test_active_sentences_not_misclassified() -> None:
    assert not is_passive_sentence("Led the redesign of the data pipeline.")
    assert not is_passive_sentence("Reduced p99 latency by 60%.")
    assert not is_passive_sentence("I architected a new event-driven service.")


# ─── Sub-scores ──────────────────────────────────────────────────────


def test_action_verb_strength_high(
    analyzer: ContentQualityAnalyzer, jd: JobDescription
) -> None:
    resume = _resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                bullets=[
                    "Led the migration",
                    "Built the platform",
                    "Mentored 3 engineers",
                ],
            )
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert result.sub_scores["action_verb_strength"] == 100.0


def test_action_verb_strength_low_with_weak_verbs(
    analyzer: ContentQualityAnalyzer, jd: JobDescription
) -> None:
    resume = _resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                bullets=[
                    "Helped with the migration",
                    "Worked on tests",
                    "Assisted senior engineers",
                ],
            )
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert result.sub_scores["action_verb_strength"] == 0.0


def test_passive_voice_drag(
    analyzer: ContentQualityAnalyzer, jd: JobDescription
) -> None:
    resume = _resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                bullets=[
                    "I was responsible for the on-call rotation.",
                    "All services were monitored centrally.",
                    "Was given ownership of the analytics platform.",
                ],
            )
        ]
    )
    result = analyzer.analyze(resume, jd)
    # Every bullet is passive → density 100% → subscore 0.
    assert result.sub_scores["passive_voice_absence"] == 0.0


def test_hedging_drag(analyzer: ContentQualityAnalyzer, jd: JobDescription) -> None:
    resume = _resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                bullets=[
                    "Familiar with Python",
                    "Some experience with Kubernetes",
                    "Working knowledge of distributed systems",
                ],
            )
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert result.sub_scores["hedging_absence"] == 0.0


# ─── Word-count fitness curve ────────────────────────────────────────


def test_word_count_fitness_ideal_band(
    analyzer: ContentQualityAnalyzer, jd: JobDescription
) -> None:
    resume = _resume(word_count=600)
    result = analyzer.analyze(resume, jd)
    assert result.sub_scores["word_count_fitness"] == 100.0


def test_word_count_fitness_above_ideal(
    analyzer: ContentQualityAnalyzer, jd: JobDescription
) -> None:
    resume = _resume(word_count=1000)
    result = analyzer.analyze(resume, jd)
    # 800 → 100, 1500 → 0 → at 1000 we're 5/7 of the way; score ~71.4
    assert 65 < result.sub_scores["word_count_fitness"] < 80


def test_word_count_fitness_below_minimum(
    analyzer: ContentQualityAnalyzer, jd: JobDescription
) -> None:
    resume = _resume(word_count=50)
    result = analyzer.analyze(resume, jd)
    assert result.sub_scores["word_count_fitness"] == 0.0


def test_mid_level_fixture_word_count_fitness_high(
    analyzer: ContentQualityAnalyzer,
    jd: JobDescription,
    resumes_dir: Path,
) -> None:
    """Sprint 7 grading threshold #12."""
    from open_ats.parsers import parse_resume

    resume = parse_resume(resumes_dir / "mid_level.md")
    # mid_level has ~394 words; just below ideal but above hard_low
    result = analyzer.analyze(resume, jd)
    assert result.sub_scores["word_count_fitness"] >= 95.0


# ─── Result shape ────────────────────────────────────────────────────


def test_result_shape(analyzer: ContentQualityAnalyzer, jd: JobDescription) -> None:
    resume = _resume(
        experience=[
            ExperienceEntry(
                title="A",
                company="X",
                bullets=["Built the platform"],
            )
        ]
    )
    result = analyzer.analyze(resume, jd)
    assert isinstance(result, AnalyzerResult)
    assert result.analyzer == "content_quality"
    assert 0.0 <= result.score <= 100.0
    assert set(result.sub_scores.keys()) == {
        "action_verb_strength",
        "passive_voice_absence",
        "hedging_absence",
        "word_count_fitness",
    }


def test_empty_resume_does_not_crash(
    analyzer: ContentQualityAnalyzer, jd: JobDescription
) -> None:
    resume = _resume()
    result = analyzer.analyze(resume, jd)
    assert 0.0 <= result.score <= 100.0
