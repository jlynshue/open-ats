"""Content-quality analyzer (FR-6).

Sub-scores (PRD §FR-6 weights):
  - 40% action-verb strength: % of bullets starting with a strong verb
  - 30% passive-voice absence: 100 − passive_density × 100
  - 20% hedging-language absence: 100 − hedging_density × 100
  - 10% word-count fitness: 100 if 400 ≤ words ≤ 800; linear decay outside

Heuristic-based — no spaCy. Passive-voice detection combines the
:mod:`open_ats.data.passive_markers` literal phrases with a regex over
``(was|were|is|are|been|...)\\s+\\w+(ed|en)\\b`` for higher recall on
patterns the marker list misses. Documented in
``.context/sprints/07-evaluation.md`` with the recall measurement
against the hand-tagged 30-sentence golden set.
"""

from __future__ import annotations

import re

from open_ats.data._loader import (
    load_action_verbs,
    load_hedging_phrases,
    load_passive_markers,
)
from open_ats.models import AnalyzerResult, JobDescription, Resume

_ACTION_VERB_WEIGHT = 0.40
_PASSIVE_WEIGHT = 0.30
_HEDGING_WEIGHT = 0.20
_WORD_COUNT_WEIGHT = 0.10

# Word-count fitness curve (PRD §10 bullet).
_IDEAL_LOW = 400
_IDEAL_HIGH = 800
_HARD_LOW = 100
_HARD_HIGH = 1500

_AUX_PARTICIPLE_RE = re.compile(
    r"\b(was|were|is|are|been|being|has\s+been|had\s+been|have\s+been)"
    r"\s+\w+(?:ed|en)\b",
    re.IGNORECASE,
)
# Sentence boundary — fairly permissive; doesn't try to handle
# abbreviations like "Dr." since resumes rarely contain them.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class ContentQualityAnalyzer:
    """Concrete :class:`Analyzer` for content-quality scoring."""

    name = "content_quality"

    def analyze(self, resume: Resume, jd: JobDescription) -> AnalyzerResult:
        bullets = _all_bullets(resume)
        sentences = _all_sentences(bullets)

        action_strength = _action_verb_strength(bullets)
        passive_density = _passive_density(sentences)
        hedging_density = _hedging_density(bullets)
        word_count = resume.word_count
        word_count_fitness = _word_count_fitness(word_count)

        passive_subscore = max(0.0, 100.0 - passive_density * 100.0)
        hedging_subscore = max(0.0, 100.0 - hedging_density * 100.0)

        overall = (
            _ACTION_VERB_WEIGHT * action_strength
            + _PASSIVE_WEIGHT * passive_subscore
            + _HEDGING_WEIGHT * hedging_subscore
            + _WORD_COUNT_WEIGHT * word_count_fitness
        )
        overall = max(0.0, min(100.0, overall))

        return AnalyzerResult(
            analyzer=self.name,
            score=round(overall, 2),
            sub_scores={
                "action_verb_strength": round(action_strength, 2),
                "passive_voice_absence": round(passive_subscore, 2),
                "hedging_absence": round(hedging_subscore, 2),
                "word_count_fitness": round(word_count_fitness, 2),
            },
            issues=_issues(bullets, sentences, word_count),
            metadata={
                "bullet_count": len(bullets),
                "sentence_count": len(sentences),
                "passive_sentence_count": _passive_sentence_count(sentences),
                "hedging_bullet_count": _hedging_bullet_count(bullets),
                "word_count": word_count,
            },
        )


# Module-level singleton.
default_content_quality_analyzer = ContentQualityAnalyzer()


# ─── Public detection (used by tests) ────────────────────────────────


def is_passive_sentence(sentence: str) -> bool:
    """Return True if ``sentence`` looks passive.

    Combines literal-marker matching against ``passive_markers.yaml``
    with the auxiliary+participle regex. Both signals are ORed so the
    function leans towards higher recall (the test golden set measures
    recall ≥ 80%).
    """
    text = sentence.casefold()
    for marker in load_passive_markers():
        if marker.casefold() in text:
            return True
    if _AUX_PARTICIPLE_RE.search(sentence):
        return True
    return False


# ─── Internals ──────────────────────────────────────────────────────


def _all_bullets(resume: Resume) -> list[str]:
    out: list[str] = []
    for entry in resume.experience:
        out.extend(entry.bullets)
    for section in resume.sections:
        out.extend(section.bullets)
    return out


def _all_sentences(bullets: list[str]) -> list[str]:
    sentences: list[str] = []
    for bullet in bullets:
        # A bullet may itself contain multiple sentences; split.
        for piece in _SENTENCE_SPLIT_RE.split(bullet.strip()):
            piece = piece.strip()
            if piece:
                sentences.append(piece)
    return sentences


def _action_verb_strength(bullets: list[str]) -> float:
    """% of bullets that start with a strong action verb."""
    if not bullets:
        return 0.0
    strong = frozenset(v.casefold() for v in load_action_verbs())
    matches = 0
    for bullet in bullets:
        first = _first_word(bullet)
        if first and first.casefold() in strong:
            matches += 1
    return 100.0 * matches / len(bullets)


def _first_word(bullet: str) -> str | None:
    stripped = bullet.lstrip("- *+•").strip()
    if not stripped:
        return None
    match = re.match(r"[A-Za-z']+", stripped)
    return match.group(0) if match else None


def _passive_density(sentences: list[str]) -> float:
    if not sentences:
        return 0.0
    return _passive_sentence_count(sentences) / len(sentences)


def _passive_sentence_count(sentences: list[str]) -> int:
    return sum(1 for s in sentences if is_passive_sentence(s))


def _hedging_density(bullets: list[str]) -> float:
    if not bullets:
        return 0.0
    return _hedging_bullet_count(bullets) / len(bullets)


def _hedging_bullet_count(bullets: list[str]) -> int:
    phrases = [p.casefold() for p in load_hedging_phrases()]
    count = 0
    for bullet in bullets:
        text = bullet.casefold()
        if any(p in text for p in phrases):
            count += 1
    return count


def _word_count_fitness(words: int) -> float:
    """Plateau-with-linear-decay curve.

    100 between IDEAL_LOW and IDEAL_HIGH; falls linearly to 0 at
    HARD_LOW (below) or HARD_HIGH (above); 0 outside the hard range.
    """
    if _IDEAL_LOW <= words <= _IDEAL_HIGH:
        return 100.0
    if words < _HARD_LOW or words > _HARD_HIGH:
        return 0.0
    if words < _IDEAL_LOW:
        return 100.0 * (words - _HARD_LOW) / (_IDEAL_LOW - _HARD_LOW)
    # words > IDEAL_HIGH
    return 100.0 * (_HARD_HIGH - words) / (_HARD_HIGH - _IDEAL_HIGH)


def _issues(bullets: list[str], sentences: list[str], word_count: int) -> list[str]:
    out: list[str] = []
    passive_count = _passive_sentence_count(sentences)
    if sentences and passive_count / len(sentences) >= 0.20:
        out.append(
            f"[content_quality.passive_voice_high] "
            f"{passive_count}/{len(sentences)} sentences look passive — "
            f"prefer active constructions."
        )
    hedging_count = _hedging_bullet_count(bullets)
    if bullets and hedging_count / len(bullets) >= 0.15:
        out.append(
            f"[content_quality.hedging_high] "
            f"{hedging_count}/{len(bullets)} bullets contain hedging "
            f"language — quantify outcomes instead."
        )
    if word_count < _IDEAL_LOW:
        out.append(
            f"[content_quality.too_short] Resume is {word_count} words; "
            f"target {_IDEAL_LOW}+ for a competitive submission."
        )
    if word_count > _IDEAL_HIGH:
        out.append(
            f"[content_quality.too_long] Resume is {word_count} words; "
            f"target ≤ {_IDEAL_HIGH} unless you're an executive with "
            f"a long career."
        )
    return out


__all__ = [
    "ContentQualityAnalyzer",
    "default_content_quality_analyzer",
    "is_passive_sentence",
]
