"""Job description parser.

Parses plain-text and markdown job descriptions into a
:class:`JobDescription` model with `requirements`, `responsibilities`,
`preferences`, and a list of keyword candidates.

Sprint 4 uses rule-based keyword extraction (proper nouns, acronyms,
multi-word title-case phrases, hyphenated compound terms). This is the
intentional simplest implementation that meets FR-2's precision-≥80%
gate without dragging in spaCy + a model download. Sprint 5's keyword
analyzer will introduce spaCy where its synonym normalisation and
lemmatisation pay off — for *matching* rather than candidate
generation.

Acceptance criteria are documented in PRD §FR-2 (``docs/PRD.md``).
"""

from __future__ import annotations

import re
from pathlib import Path

from open_ats.models import JobDescription, Keyword, KeywordCategory, ParserWarning
from open_ats.parsers.base import ResumeParseError

# JD section classification — substring matches on the lower-cased,
# colon-stripped heading text. Order matters: preferences must be checked
# before requirements because "preferred qualifications" contains
# "qualifications".
_PREFERENCE_ALIASES: tuple[str, ...] = (
    "nice to have",
    "nice-to-have",
    "bonus",
    "preferred",
    "preference",
    "plus",
    "great if",
    "great to have",
)
_REQUIREMENT_ALIASES: tuple[str, ...] = (
    "requirements",
    "required",
    "must have",
    "must-have",
    "qualifications",
    "what we're looking for",
    "what we are looking for",
    "what you'll need",
    "what you will need",
)
_RESPONSIBILITY_ALIASES: tuple[str, ...] = (
    "responsibilities",
    "what you'll do",
    "what you will do",
    "what you'll own",
    "what you will own",
    "the role",
    "your role",
    "the opportunity",
)
# Sections we recognise but deliberately drop (not in JobDescription).
_BENEFIT_ALIASES: tuple[str, ...] = (
    "benefits",
    "perks",
    "what we offer",
    "compensation",
)

_TOO_SHORT_THRESHOLD = 200
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+)$")
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
# A "heading-shape" plain-text line: short, on its own, not a bullet,
# not blank, not punctuation-heavy. We also accept lines ending in ``:``.
_HEADING_LEN_CAP = 60

# Keyword candidate patterns ─────────────────────────────────────────
_ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,5}\b")
_PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-z]+[A-Za-z+#.]*\b")
_TITLE_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b")
_HYPHEN_COMPOUND_RE = re.compile(r"\b[a-z]+(?:-[a-z]+){1,3}\b")

# Stop-words that pass the proper-noun shape but aren't useful as
# keyword candidates. Curated from real fixtures; expand as new
# false positives appear.
_STOP_KEYWORDS: frozenset[str] = frozenset(
    s.casefold()
    for s in (
        # Pronouns / articles
        "the",
        "this",
        "that",
        "these",
        "those",
        "we",
        "you",
        "i",
        "they",
        "our",
        "your",
        "their",
        "a",
        "an",
        # Auxiliaries / modals
        "is",
        "are",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "must",
        # Conjunctions / prepositions
        "and",
        "or",
        "but",
        "for",
        "with",
        "without",
        "about",
        "as",
        "at",
        "by",
        "in",
        "into",
        "of",
        "on",
        "to",
        "from",
        "up",
        "down",
        "out",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        # Calendar
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        # Generic JD prose
        "role",
        "team",
        "company",
        "us",
        "join",
        "work",
        "working",
        "experience",
        "position",
        "candidate",
        "applicant",
        "applicants",
        "employees",
        "employee",
        "office",
        "hours",
        "year",
        "years",
        "month",
        "months",
        "day",
        "days",
        "week",
        "weeks",
        # Boilerplate
        "equal",
        "opportunity",
        "employer",
        "diverse",
        "inclusive",
        "background",
        "backgrounds",
        "encouraged",
        "encourage",
        "applications",
        # Section labels we don't want as keywords
        "requirements",
        "required",
        "responsibilities",
        "qualifications",
        "preferred",
        "bonus",
        "benefits",
        "perks",
        # Common verbs that JD bullets start with
        "build",
        "carry",
        "lead",
        "drive",
        "drove",
        "design",
        "ship",
        "run",
        "hire",
        "mentor",
        "partner",
        "author",
        "set",
        "shape",
        "champion",
        "sponsor",
        "investigate",
        "contribute",
        "pair",
        "participate",
        "write",
        "read",
        "review",
        "monitor",
        "manage",
        "deliver",
        "deliver",
        "translate",
        "implement",
        # Generic adjectives / hedging
        "comfort",
        "comfortable",
        "track",
        "record",
        "ability",
        "demonstrated",
        "comprehensive",
        "competitive",
        "unlimited",
        "deep",
        "fluent",
        "fluency",
        "strong",
        "excellent",
        "great",
        "good",
        "best",
        "willing",
        "able",
        "solid",
        "clear",
        "open",
        "nice",
        "generous",
        "proven",
        "fluent",
        # Generic role descriptors
        "familiarity",
        "exposure",
        "internship",
        "internships",
        "production",
        "software",
        "healthcare",
        "design",
        # Common sentence-start English words missed by lowercase-vocab
        "hands",
        "our",
        "your",
        "their",
        "his",
        "her",
        "its",
        "prior",
        "front",
        "back",
        "deep",
        # Benefits language
        "sabbatical",
        "compensation",
        "bonus",
        "perks",
        # Locations (often appear in JDs but aren't ATS keywords)
        "remote",
        "hybrid",
        "onsite",
        "boston",
        "toronto",
        "austin",
        "francisco",
        "york",
        "seattle",
        "denver",
        "chicago",
        "london",
        "berlin",
        "paris",
        "amsterdam",
        "zurich",
        # Filler from headers
        "what",
        "do",
        "own",
        "need",
        "looking",
        "hiring",
        "looking for",
        "about",
        "summary",
        "overview",
        "we're",
        "you'll",
        "you'll",
        # Single uppercase letters surface as "acronyms" of length 1
        # (already filtered by len<2 check) — listed for clarity:
        "a",
        "i",
    )
)


# Multi-word phrases that look proper-noun-ish but are not useful
# keyword candidates (locations, generic role titles, employment terms).
_STOP_PHRASES: frozenset[str] = frozenset(
    s.casefold()
    for s in (
        "new york",
        "new grad",
        "san francisco",
        "los angeles",
        "tech lead",
        "tech leads",
        "vice president",
        "senior software engineer",
        "software engineer",
        "senior backend engineer",
        "senior data scientist",
        "senior product designer",
        "data scientist",
        "product designer",
        "design critique",
        "open source",
        "fortune 500",
        "fortune",
        "computer engineering",
        "computer science",
    )
)


class JdParser:
    """Concrete parser for plain-text and markdown job descriptions.

    JD parsing is uniform across formats — JDs come as plain text or
    markdown almost universally, so there's no per-format dispatch.
    """

    def parse(self, source: Path | str) -> JobDescription:
        """Parse a JD from a file path or raw text string.

        Raises:
            ResumeParseError: empty / whitespace-only input.
        """
        if isinstance(source, Path):
            try:
                raw_text = source.read_text(encoding="utf-8")
            except OSError as exc:
                raise ResumeParseError(
                    f"Could not read JD file: {source}", cause=exc
                ) from exc
            source_path: Path | None = source
        else:
            raw_text = source
            source_path = None

        if not raw_text.strip():
            raise ResumeParseError("Job description is empty or whitespace-only.")

        warnings: list[ParserWarning] = []
        if len(raw_text) < _TOO_SHORT_THRESHOLD:
            warnings.append(
                ParserWarning(
                    code="jd.too_short",
                    message=(
                        f"Job description is {len(raw_text)} characters "
                        f"(below {_TOO_SHORT_THRESHOLD}); section detection "
                        f"may degrade."
                    ),
                    severity="warning",
                )
            )

        title, company = _extract_title_and_company(raw_text)
        requirements, responsibilities, preferences = _split_sections(raw_text)
        keywords = _extract_keyword_candidates(raw_text)

        return JobDescription(
            source_path=source_path,
            title=title,
            company=company,
            requirements=requirements,
            responsibilities=responsibilities,
            preferences=preferences,
            keywords=keywords,
            raw_text=raw_text,
            parser_warnings=warnings,
        )


# Module-level singleton for convenience.
default_jd_parser = JdParser()


def parse_job_description(source: Path | str) -> JobDescription:
    """Top-level entry point — accepts either a file path or raw JD text."""
    return default_jd_parser.parse(source)


# ─── Title + company extraction ─────────────────────────────────────


def _extract_title_and_company(raw: str) -> tuple[str | None, str | None]:
    """Extract title and company from the JD header (first non-empty line)."""
    title: str | None = None
    company: str | None = None

    for raw_line in raw.splitlines():
        line = raw_line.strip().lstrip("#").strip()
        if not line:
            continue
        if _classify_jd_heading(line) is not None:
            break
        title, company = _split_title_line(line)
        break

    if company is None:
        # Fallback: scan first 30 lines for "About <Company>".
        for raw_line in raw.splitlines()[:30]:
            stripped = raw_line.strip()
            match = re.match(
                r"^About\s+([A-Z][\w &.,\-]+?)$",
                stripped,
            )
            if match and "company" not in match.group(1).lower():
                company = match.group(1).strip()
                break

    return title, company


def _split_title_line(line: str) -> tuple[str | None, str | None]:
    """Split a header like "Title — Company" or "Title at Company"."""
    parts = re.split(r"\s+[—–-]\s+", line, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    parts = re.split(r"\s+at\s+", line, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return line, None


# ─── Section splitting ──────────────────────────────────────────────


def _split_sections(raw: str) -> tuple[list[str], list[str], list[str]]:
    """Walk JD lines, accumulating bullets per section type.

    A line is treated as a heading if any of:
      - markdown ``# Heading`` syntax
      - text on its own line, ≤60 chars, not starting with a bullet
        marker, that classifies into a JD section kind via
        :func:`_classify_jd_heading`.

    Bullets following a heading line accumulate into that section
    until the next recognised heading.
    """
    requirements: list[str] = []
    responsibilities: list[str] = []
    preferences: list[str] = []

    current_kind: str | None = None

    def append(bullet: str) -> None:
        if not current_kind:
            return
        target = {
            "requirements": requirements,
            "responsibilities": responsibilities,
            "preferences": preferences,
        }.get(current_kind)
        if target is None:
            return
        target.append(bullet)

    lines = raw.splitlines()
    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        # Markdown heading?
        md = _MARKDOWN_HEADING_RE.match(stripped)
        if md:
            current_kind = _classify_jd_heading(md.group(1).strip())
            continue

        # Plain-text heading shape: short, no leading bullet, classifies.
        if (
            len(stripped) <= _HEADING_LEN_CAP
            and not _BULLET_RE.match(stripped)
            and _classify_jd_heading(stripped) is not None
        ):
            current_kind = _classify_jd_heading(stripped)
            continue

        # Bullet?
        bullet = _BULLET_RE.match(line)
        if bullet:
            append(bullet.group(1).strip())
            continue

        # Body prose under a heading. We don't accumulate it as a bullet
        # (would inflate counts); JD text typically uses bullets, and
        # body prose like "We're hiring..." is descriptive, not a
        # requirement.

    return requirements, responsibilities, preferences


def _classify_jd_heading(heading: str) -> str | None:
    """Map a heading text to one of {preferences, requirements, responsibilities, benefits}.

    Returns ``None`` if no alias matches. Order matters — preferences are
    checked before requirements (because "preferred qualifications"
    contains "qualifications").
    """
    norm = heading.strip().lower().rstrip(":")
    if not norm:
        return None

    def matches(aliases: tuple[str, ...]) -> bool:
        return any(alias in norm for alias in aliases)

    if matches(_PREFERENCE_ALIASES):
        return "preferences"
    if matches(_REQUIREMENT_ALIASES):
        return "requirements"
    if matches(_RESPONSIBILITY_ALIASES):
        return "responsibilities"
    if matches(_BENEFIT_ALIASES):
        return "benefits"
    return None


# ─── Keyword candidate extraction ───────────────────────────────────


def _extract_keyword_candidates(text: str) -> list[Keyword]:
    """Pull keyword candidates from the JD body via rule-based passes.

    Returns a list of :class:`Keyword`, deduplicated by canonical
    spelling, with ``match_count`` reflecting how many times the
    canonical appeared (case-insensitive). All candidates default to
    :attr:`KeywordCategory.HARD_SKILL` — Sprint 5's keyword analyzer
    will reclassify against the keyword databases.
    """
    # Identify the title-line region (first non-empty line); we never
    # extract keyword candidates from it. This drops "Senior Software
    # Engineer", "Acme Cloud", etc.
    skip_start, skip_end = _title_line_span(text)

    # Build a "lowercase-vocabulary" — the set of lowercased tokens that
    # appear non-capitalised somewhere in the body. A capitalised token
    # whose lowercased form appears in this set is probably a sentence-
    # start English word, not a tech proper noun.
    lowercase_vocab = _lowercase_vocabulary(text)

    counts: dict[str, int] = {}
    canonical_for_key: dict[str, str] = {}

    def add(canonical: str, span: tuple[int, int]) -> None:
        if _in_skip(span, skip_start, skip_end):
            return
        token = canonical.strip()
        if "\n" in token or len(token) < 2:
            return
        key = token.casefold()
        if key in _STOP_KEYWORDS or key in _STOP_PHRASES:
            return
        if key not in counts:
            counts[key] = 0
            canonical_for_key[key] = token
        counts[key] += 1

    # Multi-word title-case first so we don't double-count component
    # proper nouns. Spans claimed here block the proper-noun pass even
    # when the phrase is dropped, so component words don't slip through
    # individually.
    seen_spans: list[tuple[int, int]] = []
    for match in _TITLE_PHRASE_RE.finditer(text):
        span = match.span()
        if any(_overlaps(span, prev) for prev in seen_spans):
            continue
        seen_spans.append(span)
        # Drop phrases whose first word is a sentence-start English
        # filler ("Our Data Platform" → drop; "our" is a stop word at
        # sentence start).
        first_word = match.group(0).split(maxsplit=1)[0]
        if _is_sentence_start(text, span[0]) and (
            first_word.casefold() in lowercase_vocab
            or first_word.casefold() in _STOP_KEYWORDS
        ):
            continue
        add(match.group(0), span)

    # Acronyms.
    for match in _ACRONYM_RE.finditer(text):
        add(match.group(0), match.span())

    # Single-word proper nouns NOT covered by a multi-word phrase.
    for match in _PROPER_NOUN_RE.finditer(text):
        span = match.span()
        if any(_overlaps(span, prev) for prev in seen_spans):
            continue
        token = match.group(0)
        # Drop if this is a sentence-start word AND the same word also
        # appears lowercase elsewhere — strong signal it's English prose
        # capitalised by position, not a proper noun.
        if _is_sentence_start(text, span[0]) and token.casefold() in lowercase_vocab:
            continue
        add(token, span)

    # Hyphenated lowercase compounds.
    for match in _HYPHEN_COMPOUND_RE.finditer(text):
        add(match.group(0), match.span())

    keywords: list[Keyword] = []
    for key, count in counts.items():
        keywords.append(
            Keyword(
                canonical=canonical_for_key[key],
                category=KeywordCategory.HARD_SKILL,
                match_count=count,
            )
        )
    keywords.sort(key=lambda k: (-k.match_count, k.canonical.casefold()))
    return keywords


def _title_line_span(text: str) -> tuple[int, int]:
    """Return the (start, end) byte span of the JD's title line.

    Title is the first non-empty line. Returns (0, 0) if the text is
    blank.
    """
    idx = 0
    n = len(text)
    while idx < n and text[idx] in " \t\r\n":
        idx += 1
    start = idx
    while idx < n and text[idx] != "\n":
        idx += 1
    return start, idx


def _in_skip(span: tuple[int, int], skip_start: int, skip_end: int) -> bool:
    return span[0] >= skip_start and span[1] <= skip_end


def _lowercase_vocabulary(text: str) -> frozenset[str]:
    """Return the set of word stems that appear lowercased in ``text``."""
    stems: set[str] = set()
    for token in re.findall(r"\b[a-z]{2,}\b", text):
        stems.add(token)
    return frozenset(stems)


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return not (a[1] <= b[0] or b[1] <= a[0])


def _is_sentence_start(text: str, idx: int) -> bool:
    """True if position ``idx`` looks like the first character of a sentence
    or a paragraph/bullet line."""
    if idx == 0:
        return True
    j = idx - 1
    crossed_newline = False
    while j >= 0 and text[j] in " \t\r\n":
        if text[j] == "\n":
            crossed_newline = True
        j -= 1
    if j < 0:
        return True
    if crossed_newline:
        # Top of a new line is conceptually a sentence/paragraph boundary
        # in JD/resume text — even when the previous line ended without
        # punctuation (e.g., a heading).
        return True
    return text[j] in ".!?"


__all__ = ["JdParser", "default_jd_parser", "parse_job_description"]
