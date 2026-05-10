"""Keyword analyzer (FR-3, PRD §8 keyword formula).

Reclassifies the JD's keyword candidates by looking each up in the
keyword database, matches them against the resume content, and
produces sub-scores for hard skills / soft skills / action verbs /
industry terms.

Sub-score formula (PRD §8):

    each_subscore = min(100, 100 * matched_unique / max(1, expected_unique))
    keyword.score = 0.50 * hard_skills
                  + 0.25 * soft_skills
                  + 0.15 * action_verbs
                  + 0.10 * industry_terms

Action verbs are scored differently: we count how many of a
bootstrapped list of strong verbs appear at the start of the resume's
experience bullets (Sprint 7 promotes the bootstrap list to
``src/open_ats/data/action_verbs.yaml``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from open_ats.analyzers._database import KeywordDatabase, load_default_database
from open_ats.data._loader import load_action_verbs
from open_ats.models import (
    AnalyzerResult,
    JobDescription,
    Keyword,
    KeywordCategory,
    Resume,
)

# Sub-score weights per PRD §8 keyword formula.
_HARD_WEIGHT = 0.50
_SOFT_WEIGHT = 0.25
_ACTION_WEIGHT = 0.15
_INDUSTRY_WEIGHT = 0.10


def _action_verb_set() -> frozenset[str]:
    """Lazy-load the canonical action-verb list (PRD §10.1).

    Promoted from a Sprint-5 inline bootstrap to ``src/open_ats/data/
    action_verbs.yaml`` in Sprint 7. The :class:`ContentQualityAnalyzer`
    uses the same source so action-verb judgment stays consistent across
    analyzers.
    """
    return frozenset(v.casefold() for v in load_action_verbs())


# Target count of distinct strong action verbs we expect to see in a
# competitive resume. Calibrated against `tests/fixtures/resumes/*.md`:
# the mid-level fixture uses ~12, executive ~15. 10 is a generous
# baseline; the score caps at 100 once 10 are present.
_ACTION_VERB_TARGET = 10


@dataclass(frozen=True)
class _SubScores:
    hard: float
    soft: float
    action: float
    industry: float


class KeywordAnalyzer:
    """Concrete :class:`Analyzer` for keyword matching."""

    name = "keyword"

    def __init__(self, database: KeywordDatabase | None = None) -> None:
        self._database = database or load_default_database()

    def analyze(self, resume: Resume, jd: JobDescription) -> AnalyzerResult:
        # 1. Reclassify JD candidates via the database; drop unknowns.
        reclassified = _reclassify_jd_keywords(jd.keywords, self._database)

        # 2. Build a haystack from the resume body for substring lookup.
        haystack = _resume_haystack(resume)

        # 3. Per-category match counts.
        hard_expected = _entries_in_category(reclassified, KeywordCategory.HARD_SKILL)
        soft_expected = _entries_in_category(reclassified, KeywordCategory.SOFT_SKILL)
        industry_expected = _entries_in_category(
            reclassified, KeywordCategory.INDUSTRY_TERM
        )

        hard_matched = _count_matches(hard_expected, haystack, self._database)
        soft_matched = _count_matches(soft_expected, haystack, self._database)
        industry_matched = _count_matches(industry_expected, haystack, self._database)

        action_subscore, action_matched_verbs = _action_verb_subscore(resume)

        sub = _SubScores(
            hard=_subscore(hard_matched, len(hard_expected)),
            soft=_subscore(soft_matched, len(soft_expected)),
            action=action_subscore,
            industry=_subscore(industry_matched, len(industry_expected)),
        )

        overall = (
            _HARD_WEIGHT * sub.hard
            + _SOFT_WEIGHT * sub.soft
            + _ACTION_WEIGHT * sub.action
            + _INDUSTRY_WEIGHT * sub.industry
        )

        matched_items = sorted(
            {
                k.canonical
                for k in reclassified
                if _haystack_contains(k, haystack, self._database)
            }
            | set(action_matched_verbs)
        )

        return AnalyzerResult(
            analyzer=self.name,
            score=round(overall, 2),
            sub_scores={
                "hard_skills": round(sub.hard, 2),
                "soft_skills": round(sub.soft, 2),
                "action_verbs": round(sub.action, 2),
                "industry_terms": round(sub.industry, 2),
            },
            matched_items=matched_items,
            metadata={
                "hard_expected": len(hard_expected),
                "hard_matched": hard_matched,
                "soft_expected": len(soft_expected),
                "soft_matched": soft_matched,
                "industry_expected": len(industry_expected),
                "industry_matched": industry_matched,
                "action_verb_target": _ACTION_VERB_TARGET,
                "action_verbs_used": len(action_matched_verbs),
            },
        )


# Module-level singleton convenience.
default_keyword_analyzer = KeywordAnalyzer()


# ─── Internals ───────────────────────────────────────────────────────


def _reclassify_jd_keywords(
    candidates: list[Keyword], db: KeywordDatabase
) -> list[Keyword]:
    """Return JD candidates that match the database, with categories
    rewritten and synonyms attached. Drops unknowns."""
    out: list[Keyword] = []
    seen_canonicals: set[str] = set()
    for candidate in candidates:
        entry = db.lookup(candidate.canonical)
        if entry is None:
            continue
        key = entry.canonical.casefold()
        if key in seen_canonicals:
            # Same canonical mentioned again in JD via different synonym; bump count.
            for k in out:
                if k.canonical.casefold() == key:
                    k.match_count = k.match_count + candidate.match_count
                    break
            continue
        seen_canonicals.add(key)
        out.append(
            Keyword(
                canonical=entry.canonical,
                category=entry.category,
                synonyms=list(entry.synonyms),
                match_count=candidate.match_count,
                matched=False,
            )
        )
    return out


def _entries_in_category(
    keywords: list[Keyword], category: KeywordCategory
) -> list[Keyword]:
    return [k for k in keywords if k.category == category]


def _resume_haystack(resume: Resume) -> str:
    """Build a lowercased searchable string from the resume body.

    Strategy: skills + experience bullets + summary + sections' bullets.
    """
    parts: list[str] = []
    if resume.summary:
        parts.append(resume.summary)
    parts.extend(resume.skills)
    for entry in resume.experience:
        parts.append(entry.title)
        parts.append(entry.company)
        parts.extend(entry.bullets)
    for section in resume.sections:
        parts.extend(section.bullets)
    return "\n".join(parts).casefold()


def _haystack_contains(keyword: Keyword, haystack: str, db: KeywordDatabase) -> bool:
    """True if ``keyword`` (or any of its synonyms) is a substring of haystack."""
    candidates = [keyword.canonical, *keyword.synonyms]
    # Also pull any DB synonyms not currently on the keyword.
    entry = db.lookup(keyword.canonical)
    if entry is not None:
        candidates.extend(entry.synonyms)
    for token in candidates:
        if not token:
            continue
        # Use word boundaries when the token contains no spaces; raw
        # substring match otherwise (multi-word tokens can't sit between
        # \b — `\bSan Francisco\b` works, but `\bLocal area network\b`
        # is needlessly strict).
        if " " in token:
            if token.casefold() in haystack:
                return True
        else:
            if re.search(rf"\b{re.escape(token.casefold())}\b", haystack):
                return True
    return False


def _count_matches(keywords: list[Keyword], haystack: str, db: KeywordDatabase) -> int:
    return sum(1 for k in keywords if _haystack_contains(k, haystack, db))


def _subscore(matched: int, expected: int) -> float:
    """PRD §8 sub-score: 100 * matched / expected, capped at 100."""
    if expected <= 0:
        # No JD signal in this category — don't penalise. Returning 100
        # would inflate the overall; returning 0 would deflate. Convention:
        # neutral 100 (the resume can't be expected to match what isn't asked).
        return 100.0
    return min(100.0, 100.0 * matched / expected)


def _action_verb_subscore(resume: Resume) -> tuple[float, list[str]]:
    """Score the resume's use of strong action verbs at bullet-start.

    Returns ``(subscore, matched_verb_canonicals)``. The score caps at
    100 once :data:`_ACTION_VERB_TARGET` distinct strong verbs appear.
    """
    bullet_starts: list[str] = []
    for entry in resume.experience:
        for bullet in entry.bullets:
            first = _first_word(bullet)
            if first:
                bullet_starts.append(first.casefold())
    for section in resume.sections:
        for bullet in section.bullets:
            first = _first_word(bullet)
            if first:
                bullet_starts.append(first.casefold())

    verbs = _action_verb_set()
    matched: set[str] = set()
    for word in bullet_starts:
        if word in verbs:
            matched.add(word)

    score = min(100.0, 100.0 * len(matched) / max(1, _ACTION_VERB_TARGET))
    # Title-case for readability in matched_items.
    return score, sorted(w.title() for w in matched)


def _first_word(bullet: str) -> str | None:
    stripped = bullet.lstrip("- *+•").strip()
    if not stripped:
        return None
    word_match = re.match(r"[A-Za-z']+", stripped)
    return word_match.group(0) if word_match else None


__all__ = ["KeywordAnalyzer", "default_keyword_analyzer"]
