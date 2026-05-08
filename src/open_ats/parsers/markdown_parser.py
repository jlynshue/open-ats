"""Markdown resume parser.

Parses CommonMark-flavored Markdown resumes into the :class:`Resume`
model. Heuristic-driven (no AST library dep) — section detection
relies on ATX headings (``# H1``, ``## H2``, ``### H3``) and the
classifier in :mod:`open_ats.parsers.base`.

Acceptance criteria are documented in PRD §FR-1.1 (``docs/PRD.md``).
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from open_ats.models import (
    Contact,
    EducationEntry,
    ExperienceEntry,
    ParserWarning,
    Resume,
    Section,
    SectionType,
)
from open_ats.parsers.base import (
    Parser,
    ResumeParseError,
    classify_section_heading,
    extract_email,
    extract_github,
    extract_linkedin,
    extract_phone,
)

# ATX heading detector: 1–6 leading hashes, then space, then text.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
# Bullet detector: leading `-`, `*`, or `+` followed by space.
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+)$")
# How many lines from the top to scan for contact info before the first
# section heading appears.
_CONTACT_SCAN_LINES = 30
# Threshold below which we consider a resume "too short" and emit a
# ``resume.too_short`` warning. Calibrated against typical entry-level
# resumes (~400 words minimum).
_TOO_SHORT_WORD_COUNT = 200


class MarkdownParser:
    """Concrete :class:`Parser` for ``.md`` resumes."""

    def parse(self, path: Path) -> Resume:
        """Read ``path`` and return a populated :class:`Resume`.

        Raises:
            ResumeParseError: file unreadable, empty, or whitespace-only.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover — exercised via integration
            raise ResumeParseError(
                f"Could not read resume file: {path}", cause=exc
            ) from exc
        return self.parse_text(text, source_path=path)

    def parse_text(self, text: str, *, source_path: Path | None = None) -> Resume:
        """Parse already-loaded markdown text. Useful for tests + CLI piping."""
        if not text.strip():
            raise ResumeParseError("Resume file is empty or whitespace-only.")

        warnings: list[ParserWarning] = []
        lines = text.splitlines()

        # 1. Find the index of the first heading. Everything above is the
        #    pre-section header region (name, contact, sometimes summary).
        first_heading_idx = _find_first_heading_index(lines)
        header_region = (
            lines[:first_heading_idx]
            if first_heading_idx
            else lines[:_CONTACT_SCAN_LINES]
        )
        header_text = "\n".join(header_region)

        # 2. Build the Contact. The first non-empty line is conventionally
        #    the candidate's full name (often as an H1 in well-formed
        #    resumes; we don't require it).
        full_name = _extract_full_name(lines)
        contact = _build_contact(header_text, full_name=full_name, warnings=warnings)

        # 3. Walk the body, slicing it into Section objects per heading.
        sections = _parse_sections(lines, first_heading_idx)

        # 4. Map detected sections to typed fields where applicable.
        summary = _summary_from_sections(sections)
        experience = _experience_from_sections(sections)
        education = _education_from_sections(sections)
        skills = _skills_from_sections(sections)

        # 5. Compute word count and emit any whole-document warnings.
        word_count = _count_words(text)
        if word_count < _TOO_SHORT_WORD_COUNT:
            warnings.append(
                ParserWarning(
                    code="resume.too_short",
                    message=(
                        f"Resume word count is {word_count} "
                        f"(below {_TOO_SHORT_WORD_COUNT}); section detection may degrade."
                    ),
                    severity="warning",
                )
            )

        return Resume(
            source_path=source_path,
            source_format="markdown",
            contact=contact,
            summary=summary,
            experience=experience,
            education=education,
            skills=skills,
            sections=sections,
            word_count=word_count,
            parser_warnings=warnings,
        )


# Module-level singleton — Parser protocol satisfied at import.
default_markdown_parser: Parser = MarkdownParser()


# ─── Internals ────────────────────────────────────────────────────────


def _find_first_heading_index(lines: list[str]) -> int:
    """Return the line index of the first non-H1 ATX heading, or 0 if none.

    Why "non-H1": resumes commonly use an H1 for the candidate's name
    ("# Avery Chen") which is part of the contact header, not a section.
    Section headings are typically H2 or H3.
    """
    for idx, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match and len(match.group(1)) >= 2:
            return idx
    return 0


def _extract_full_name(lines: list[str]) -> str | None:
    """Return the candidate's name — the first H1 if present, else first
    non-empty non-heading line."""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        match = _HEADING_RE.match(stripped)
        if match and len(match.group(1)) == 1:
            return match.group(2).strip()
        # Fall back to the first non-empty line that isn't a heading.
        if not stripped.startswith("#"):
            return stripped
    return None


def _build_contact(
    header_text: str,
    *,
    full_name: str | None,
    warnings: list[ParserWarning],
) -> Contact:
    """Assemble a Contact, degrading gracefully on validation failures."""
    email_str = extract_email(header_text)
    phone = extract_phone(header_text)
    linkedin = extract_linkedin(header_text)
    github = extract_github(header_text)
    location = _guess_location(header_text)

    fields: dict[str, object] = {
        "full_name": full_name,
        "phone": phone,
        "location": location,
    }

    # Try to set typed fields one at a time; if Pydantic rejects a value
    # (e.g., an invalid email or URL), drop it and emit a warning rather
    # than crashing the parse.
    for field, value, warning_code in [
        ("email", email_str, "contact.email_invalid"),
        ("linkedin", linkedin, "contact.linkedin_invalid"),
        ("github", github, "contact.github_invalid"),
    ]:
        if value is None:
            continue
        try:
            Contact(**{field: value})  # type: ignore[arg-type]
        except ValidationError:
            warnings.append(
                ParserWarning(
                    code=warning_code,
                    message=f"Discarded malformed {field}: {value!r}",
                )
            )
        else:
            fields[field] = value

    if email_str is None:
        warnings.append(
            ParserWarning(
                code="contact.email_missing",
                message="No email address found in the resume header.",
            )
        )
    if full_name is None:
        warnings.append(
            ParserWarning(
                code="contact.name_missing",
                message="No candidate name found in the resume header.",
            )
        )

    return Contact(**fields)  # type: ignore[arg-type]


def _guess_location(header_text: str) -> str | None:
    """Best-effort city/state extraction from the header region.

    Looks for a line of the form ``City, ST`` (US two-letter state) or
    ``City, Country``. Conservative — returns None if uncertain.
    """
    for raw_line in header_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Skip lines that look like contact pipes (email | phone | link).
        if (
            "@" in line
            or "linkedin.com" in line.lower()
            or "github.com" in line.lower()
        ):
            continue
        # ``City, ST`` (2-letter US state) or "City, Country".
        if re.match(
            r"^[A-Z][A-Za-z .'\-]+,\s*(?:[A-Z]{2}|[A-Z][A-Za-z]+)$",
            line,
        ):
            return line
    return None


def _parse_sections(lines: list[str], start_idx: int) -> list[Section]:
    """Slice the lines from ``start_idx`` onward into Section objects.

    Each H2/H3+ heading begins a new section; the body of that section
    runs until the next heading of equal-or-shallower depth (or end of
    document).
    """
    sections: list[Section] = []
    if start_idx >= len(lines):
        return sections

    current_heading: str | None = None
    current_depth: int | None = None
    current_body_lines: list[str] = []

    def flush() -> None:
        if current_heading is None:
            return
        body = "\n".join(current_body_lines).strip()
        bullets = _extract_bullets(current_body_lines)
        section_type = classify_section_heading(current_heading)
        sections.append(
            Section(
                type=section_type,
                raw_heading=current_heading,
                body=body,
                bullets=bullets,
            )
        )

    for line in lines[start_idx:]:
        match = _HEADING_RE.match(line)
        if match and len(match.group(1)) >= 2:
            depth = len(match.group(1))
            heading_text = match.group(2).strip()
            # Treat any H2 or shallower-depth heading as a new section.
            # Deeper headings (H4+) inside a section count as part of the body.
            if current_depth is None or depth <= current_depth + 1:
                flush()
                current_heading = heading_text
                current_depth = depth
                current_body_lines = []
                continue
        if current_heading is not None:
            current_body_lines.append(line)

    flush()
    return sections


def _extract_bullets(body_lines: list[str]) -> list[str]:
    """Return list of bullet text (without the leading marker)."""
    bullets: list[str] = []
    for line in body_lines:
        match = _BULLET_RE.match(line)
        if match:
            bullets.append(match.group(1).strip())
    return bullets


def _summary_from_sections(sections: list[Section]) -> str | None:
    for section in sections:
        if section.type == SectionType.SUMMARY:
            return section.body or None
    return None


def _experience_from_sections(sections: list[Section]) -> list[ExperienceEntry]:
    """Lightweight Experience extraction.

    Sprint 1 implementation: each H3 (or bold line) inside the EXPERIENCE
    section becomes one ``ExperienceEntry`` with all bullets between it
    and the next entry. Title/company/dates parsing is intentionally
    naive here — Sprint 2+ will refine using DOCX/PDF cues.
    """
    entries: list[ExperienceEntry] = []
    exp = next((s for s in sections if s.type == SectionType.EXPERIENCE), None)
    if exp is None:
        return entries

    # Split the section body on ATX H3 headings or **bold** entry titles.
    blocks = _split_experience_blocks(exp.body)
    for block in blocks:
        title, company, location, start_date, end_date, bullets = (
            _parse_experience_block(block)
        )
        if not title and not company:
            continue
        entries.append(
            ExperienceEntry(
                title=title or "(unknown)",
                company=company or "(unknown)",
                location=location,
                start_date=start_date,
                end_date=end_date,
                bullets=bullets,
            )
        )
    return entries


def _split_experience_blocks(body: str) -> list[str]:
    """Split an Experience section body into per-role blocks.

    Splits on H3 headings and on lines beginning with ``**...**`` (a
    common "bold title" convention).
    """
    blocks: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        is_h3 = bool(_HEADING_RE.match(line) and line.startswith("### "))
        is_bold_title = bool(re.match(r"^\*\*[^*]+\*\*", line.strip()))
        if (is_h3 or is_bold_title) and current:
            blocks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [b for b in blocks if b]


def _parse_experience_block(
    block: str,
) -> tuple[str, str, str | None, str | None, str | None, list[str]]:
    """Best-effort title/company/dates extraction from one Experience block."""
    lines = block.splitlines()
    title = ""
    company = ""
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            bullets.append(bullet_match.group(1).strip())
            continue
        # First non-bullet line: assume it's the title/company/location row.
        if not title:
            # Strip H3/bold markers: "### **Senior Engineer** — Acme" or "**Senior Engineer** — Acme"
            cleaned = re.sub(r"^#{1,6}\s+", "", line)
            cleaned = cleaned.replace("**", "")
            # Common formats:
            #   "Title — Company, Location"
            #   "Title at Company"
            parts = re.split(r"\s+[—–-]\s+", cleaned, maxsplit=1)
            if len(parts) == 2:
                title = parts[0].strip()
                company_loc = parts[1].strip()
                if "," in company_loc:
                    company_part, _, loc_part = company_loc.partition(",")
                    company = company_part.strip()
                    location = loc_part.strip() or None
                else:
                    company = company_loc
            else:
                title = cleaned
            continue
        # Second non-bullet line: assume it's a date range like "March 2023 – Present"
        if start_date is None:
            date_parts = re.split(r"\s+[–—-]\s+|\s+to\s+", line, maxsplit=1)
            if len(date_parts) == 2:
                start_date = date_parts[0].strip()
                end_date = date_parts[1].strip().rstrip("|").strip()
                # Strip any trailing location after a `|` separator
                if "|" in end_date:
                    end_date, _, loc_after = end_date.partition("|")
                    end_date = end_date.strip()
                    if location is None:
                        location = loc_after.strip() or None
            else:
                start_date = line

    return title, company, location, start_date, end_date, bullets


def _education_from_sections(sections: list[Section]) -> list[EducationEntry]:
    """Lightweight Education extraction.

    Each non-empty paragraph (separated by a blank line) inside the
    Education section maps to one EducationEntry. Degree and institution
    are split on ``—`` or ``,``.
    """
    entries: list[EducationEntry] = []
    edu = next((s for s in sections if s.type == SectionType.EDUCATION), None)
    if edu is None:
        return entries

    paragraphs = re.split(r"\n\s*\n", edu.body)
    for paragraph in paragraphs:
        first_line = paragraph.splitlines()[0].strip() if paragraph.strip() else ""
        if not first_line:
            continue
        cleaned = re.sub(r"^\*\*|\*\*$", "", first_line.replace("**", ""))
        parts = re.split(r"\s+[—–-]\s+|,\s+", cleaned, maxsplit=1)
        if len(parts) == 2:
            degree = parts[0].strip()
            institution = parts[1].strip()
        else:
            degree = cleaned
            institution = ""
        gpa = _extract_gpa(paragraph)
        start_year, end_year = _extract_year_range(paragraph)
        entries.append(
            EducationEntry(
                degree=degree,
                institution=institution,
                gpa=gpa,
                start_year=start_year,
                end_year=end_year,
            )
        )
    return entries


def _extract_gpa(text: str) -> float | None:
    match = re.search(r"GPA[:\s]+(\d\.\d{1,2})", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _extract_year_range(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"\b(19|20)\d{2}\b\s*[–—-]\s*\b(19|20)\d{2}\b", text)
    if match:
        years = re.findall(r"\b(?:19|20)\d{2}\b", match.group(0))
        if len(years) == 2:
            return int(years[0]), int(years[1])
    single = re.search(r"\b(19|20)\d{2}\b", text)
    if single:
        return None, int(single.group(0))
    return None, None


def _skills_from_sections(sections: list[Section]) -> list[str]:
    """Extract a flat list of skill tokens from the Skills section.

    Strategy: for each line, strip a leading category label like
    ``**Languages:**``, then split the remainder on commas and ``;``.
    Also flattens bullet-listed skills. Deduplicates while preserving
    first-seen order.
    """
    skills_section = next((s for s in sections if s.type == SectionType.SKILLS), None)
    if skills_section is None:
        return []

    raw_items: list[str] = []
    for raw_line in skills_section.body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        bullet = _BULLET_RE.match(line)
        if bullet:
            line = bullet.group(1).strip()
        # Strip the "**Category:**" prefix.
        line = re.sub(r"^\*\*[^*]+:\*\*\s*", "", line)
        line = re.sub(r"^[A-Za-z][\w /]+:\s*", "", line)
        for token in re.split(r"[,;]\s*", line):
            token = token.strip().rstrip(".")
            if token:
                raw_items.append(token)

    seen: set[str] = set()
    deduped: list[str] = []
    for item in raw_items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _count_words(text: str) -> int:
    """Return a simple whitespace word count, ignoring markdown markers."""
    cleaned = re.sub(r"[#*_`>\[\]()|]+", " ", text)
    return len([t for t in cleaned.split() if t])


__all__ = ["MarkdownParser", "default_markdown_parser"]
