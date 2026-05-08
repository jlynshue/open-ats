"""Parser protocol, exception types, and shared extraction helpers.

Each format-specific parser (Markdown, DOCX, PDF, TXT) implements the
:class:`Parser` protocol. Helpers in this module (contact regex,
section-name normalisation) are shared across all parsers so the
heuristics evolve in one place.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from open_ats.models import Resume, SectionType

# ─── Exceptions ───────────────────────────────────────────────────────


class ResumeParseError(Exception):
    """Raised when a resume cannot be parsed at all (corrupt, empty, etc.)."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class UnsupportedFormatError(Exception):
    """Raised when ``parse_resume`` is called with an unsupported file extension."""

    def __init__(self, extension: str, supported: list[str]) -> None:
        self.extension = extension
        self.supported = supported
        super().__init__(
            f"Unsupported resume format '{extension}'. "
            f"Supported formats: {', '.join(supported)}."
        )


# ─── Parser protocol ──────────────────────────────────────────────────


@runtime_checkable
class Parser(Protocol):
    """Common interface every format-specific parser implements."""

    def parse(self, path: Path) -> Resume:
        """Read the file at ``path`` and return a populated :class:`Resume`.

        Raises:
            ResumeParseError: file is unreadable, empty, or otherwise unparseable.
        """
        ...


# ─── Contact extraction regexes ───────────────────────────────────────
#
# These are intentionally conservative. Each parser is responsible for
# scoping the search region (typically the first ~20 lines / pre-first-
# section block) before applying them so we don't pull a hiring-manager
# email out of the body.

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"""
    (?<![\d.])               # not preceded by a digit (avoids matching mid-number)
    (?:\+?\d{1,2}[\s.-]?)?   # optional country code
    \(?\d{3}\)?[\s.-]?       # area code
    \d{3}[\s.-]?\d{4}        # local number
    (?![\d.])                # not followed by a digit
    """,
    re.VERBOSE,
)
LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+/?", re.IGNORECASE
)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+/?", re.IGNORECASE)


def extract_email(text: str) -> str | None:
    """Return the first email address in ``text`` or None."""
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    """Return the first phone number in ``text`` or None."""
    match = PHONE_RE.search(text)
    return match.group(0).strip() if match else None


def extract_linkedin(text: str) -> str | None:
    """Return the first LinkedIn profile URL in ``text`` (https-normalised)."""
    match = LINKEDIN_RE.search(text)
    if not match:
        return None
    return _ensure_https(match.group(0))


def extract_github(text: str) -> str | None:
    """Return the first GitHub profile URL in ``text`` (https-normalised)."""
    match = GITHUB_RE.search(text)
    if not match:
        return None
    return _ensure_https(match.group(0))


def _ensure_https(url: str) -> str:
    """Prepend https:// to a bare URL like ``linkedin.com/in/foo``."""
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


# ─── Section-name normalisation ───────────────────────────────────────
#
# Maps common heading text variants to a canonical SectionType. The
# matcher is whitespace- and case-insensitive and accepts substrings
# (so "Work Experience" → EXPERIENCE).
#
# Values are tuples of substrings; a heading matches if any tuple
# entry is a substring of the (lower-cased, stripped) heading text.

_SECTION_ALIASES: dict[SectionType, tuple[str, ...]] = {
    SectionType.SUMMARY: (
        "summary",
        "professional summary",
        "executive summary",
        "profile",
        "objective",
        "about me",
    ),
    SectionType.EXPERIENCE: (
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "work history",
        "career history",
    ),
    SectionType.EDUCATION: ("education", "academic", "academic background"),
    SectionType.SKILLS: (
        "skills",
        "technical skills",
        "core competencies",
        "expertise",
    ),
    SectionType.PROJECTS: ("projects", "personal projects", "side projects"),
    SectionType.CERTIFICATIONS: ("certifications", "certificates", "licenses"),
    SectionType.PUBLICATIONS: ("publications", "papers", "research"),
    SectionType.AWARDS: ("awards", "honors", "achievements", "recognition"),
}


def classify_section_heading(heading: str) -> SectionType:
    """Map a raw heading string to a :class:`SectionType`.

    Returns :attr:`SectionType.OTHER` if no alias matches. Comparison is
    case-insensitive and uses substring matching, so "Selected Open Source"
    or "Earlier Career" will both map to OTHER (they're not in the alias
    list); "Work Experience" maps to EXPERIENCE.
    """
    norm = heading.strip().lower()
    if not norm:
        return SectionType.OTHER
    for section_type, aliases in _SECTION_ALIASES.items():
        for alias in aliases:
            if alias in norm:
                return section_type
    return SectionType.OTHER


__all__ = [
    "EMAIL_RE",
    "GITHUB_RE",
    "LINKEDIN_RE",
    "PHONE_RE",
    "Parser",
    "ResumeParseError",
    "UnsupportedFormatError",
    "classify_section_heading",
    "extract_email",
    "extract_github",
    "extract_linkedin",
    "extract_phone",
]
