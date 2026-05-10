"""Formatting analyzer (FR-5).

Penalty-based score per PRD §FR-5: starts at 100, subtract penalties
per detected ATS-breaking issue (tables, date inconsistency, special-
character inconsistency, missing contact, excessive line length).
Issues land in :attr:`AnalyzerResult.issues` with human-readable
strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from open_ats.models import (
    AnalyzerResult,
    JobDescription,
    ParserWarning,
    Resume,
)

_TABLE_PENALTY = 10
_DATE_INCONSISTENCY_PENALTY = 5
_SPECIAL_CHAR_PENALTY_PER_OFFENSE = 1
_SPECIAL_CHAR_PENALTY_CAP = 10
_MISSING_CONTACT_PENALTY = 15  # email OR name missing → −15 per missing
_LINE_LENGTH_PENALTY_CAP = 3
_LINE_LENGTH_THRESHOLD = 120


@dataclass(frozen=True)
class _Penalty:
    code: str
    message: str
    amount: int


class FormattingAnalyzer:
    """Concrete :class:`Analyzer` for formatting validation."""

    name = "formatting"

    def analyze(self, resume: Resume, jd: JobDescription) -> AnalyzerResult:
        penalties: list[_Penalty] = []

        if _has_table_warning(resume.parser_warnings):
            penalties.append(
                _Penalty(
                    "formatting.table",
                    "Resume contains tables; ATS readers may misorder content.",
                    _TABLE_PENALTY,
                )
            )

        if _missing_contact_email(resume):
            penalties.append(
                _Penalty(
                    "formatting.missing_email",
                    "No email address detected in the resume header.",
                    _MISSING_CONTACT_PENALTY,
                )
            )
        if _missing_contact_name(resume):
            penalties.append(
                _Penalty(
                    "formatting.missing_name",
                    "No candidate name detected in the resume header.",
                    _MISSING_CONTACT_PENALTY,
                )
            )

        date_shapes = _date_shape_counts(resume)
        if len(date_shapes) > 1:
            penalties.append(
                _Penalty(
                    "formatting.date_inconsistency",
                    (
                        "Mixed date formats across roles: "
                        f"{sorted(date_shapes.keys())}. Pick one format."
                    ),
                    _DATE_INCONSISTENCY_PENALTY,
                )
            )

        char_offenses = _special_char_offenses(resume)
        if char_offenses:
            amount = min(
                _SPECIAL_CHAR_PENALTY_PER_OFFENSE * len(char_offenses),
                _SPECIAL_CHAR_PENALTY_CAP,
            )
            penalties.append(
                _Penalty(
                    "formatting.special_chars",
                    (
                        "Inconsistent use of non-ASCII separators: "
                        f"{sorted(char_offenses)}."
                    ),
                    amount,
                )
            )

        long_line_count = _count_long_lines(resume)
        if long_line_count > 0:
            amount = min(long_line_count, _LINE_LENGTH_PENALTY_CAP)
            penalties.append(
                _Penalty(
                    "formatting.long_lines",
                    f"{long_line_count} line(s) exceed {_LINE_LENGTH_THRESHOLD} characters.",
                    amount,
                )
            )

        total_penalty = sum(p.amount for p in penalties)
        score = max(0.0, 100.0 - total_penalty)

        return AnalyzerResult(
            analyzer=self.name,
            score=round(score, 2),
            sub_scores={
                "starting_score": 100.0,
                "total_penalty": float(total_penalty),
            },
            issues=[f"[{p.code}] {p.message} (-{p.amount})" for p in penalties],
            metadata={
                "penalty_count": len(penalties),
                "long_line_count": long_line_count,
                "date_shapes": sorted(date_shapes.keys()),
                "special_char_offenses": sorted(char_offenses),
            },
        )


# Module-level singleton.
default_formatting_analyzer = FormattingAnalyzer()


# ─── Detection helpers ──────────────────────────────────────────────


def _has_table_warning(warnings: list[ParserWarning]) -> bool:
    return any(w.code == "formatting.table_detected" for w in warnings)


def _missing_contact_email(resume: Resume) -> bool:
    return resume.contact.email is None


def _missing_contact_name(resume: Resume) -> bool:
    return not resume.contact.full_name


def _date_shape_counts(resume: Resume) -> dict[str, int]:
    """Group experience dates by their shape; >1 distinct shape signals
    inconsistency.

    Shape categories (deliberately coarse):
      - "iso_year_month" — ``2023-03``
      - "month_year_word" — ``March 2023`` / ``Mar 2023``
      - "year_only" — ``2023``
      - "present" — ``Present`` / ``Now``
      - "unknown" — anything else (ignored for the inconsistency check)
    """
    counts: dict[str, int] = {}
    for entry in resume.experience:
        for raw in (entry.start_date, entry.end_date):
            if not raw:
                continue
            shape = _date_shape(raw.strip())
            if shape == "unknown":
                continue
            counts[shape] = counts.get(shape, 0) + 1
    return counts


_ISO_RE = re.compile(r"^\d{4}-\d{1,2}$")
_YEAR_ONLY_RE = re.compile(r"^\d{4}$")
_MONTH_YEAR_WORD_RE = re.compile(
    r"^(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}$",
    re.IGNORECASE,
)
_PRESENT_RE = re.compile(r"^(?:present|current|now)$", re.IGNORECASE)


def _date_shape(text: str) -> str:
    if _ISO_RE.match(text):
        return "iso_year_month"
    if _MONTH_YEAR_WORD_RE.match(text):
        return "month_year_word"
    if _YEAR_ONLY_RE.match(text):
        return "year_only"
    if _PRESENT_RE.match(text):
        return "present"
    return "unknown"


# Special characters considered potentially ATS-hostile when used
# inconsistently. Detection: count occurrences in the resume body; if
# both an em-dash and a hyphen serving as separator appear, that's an
# offense (one canonical form per resume, not both).
_SPECIAL_PAIRS: tuple[tuple[str, str], ...] = (
    ("—", "-"),  # em-dash vs hyphen
    ("–", "-"),  # en-dash vs hyphen
    ("•", "-"),  # bullet vs hyphen-bullet
    ("“", '"'),  # curly vs straight double-quote
    ("”", '"'),
    ("‘", "'"),
    ("’", "'"),
)


def _special_char_offenses(resume: Resume) -> set[str]:
    """Return the set of special-char offenses found in the resume body.

    An offense is "this resume uses both `—` and `-` as separators",
    which downstream ATS engines may render inconsistently.
    """
    body = _resume_body_text(resume)
    offenses: set[str] = set()
    for special, ascii_alt in _SPECIAL_PAIRS:
        if special in body and ascii_alt in body:
            offenses.add(special)
    return offenses


def _count_long_lines(resume: Resume) -> int:
    """Count lines exceeding :data:`_LINE_LENGTH_THRESHOLD` characters."""
    body = _resume_body_text(resume)
    return sum(1 for line in body.splitlines() if len(line) > _LINE_LENGTH_THRESHOLD)


def _resume_body_text(resume: Resume) -> str:
    """Concatenated body for character-level checks.

    Combines summary + experience bullets + section bullets + skills.
    """
    parts: list[str] = []
    if resume.summary:
        parts.append(resume.summary)
    for entry in resume.experience:
        parts.append(entry.title)
        parts.append(entry.company)
        parts.extend(entry.bullets)
    for section in resume.sections:
        parts.append(section.body)
    parts.extend(resume.skills)
    return "\n".join(parts)


__all__ = ["FormattingAnalyzer", "default_formatting_analyzer"]
