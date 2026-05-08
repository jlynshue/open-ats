"""Plain-text → markdown heuristic shared by TXT and PDF parsers.

Both formats arrive at the parser as flat text with no structural
markup. We promote candidate lines to markdown headings (``#``/``##``)
when they classify into a known :class:`open_ats.models.SectionType`,
and normalise bullet markers (``-``/``*``/``•``/``1.``) to ``- ``.

This module is internal to :mod:`open_ats.parsers`. The public surface
is the single :func:`text_to_markdown` function.
"""

from __future__ import annotations

import re

from open_ats.models import SectionType
from open_ats.parsers.base import classify_section_heading

# Heading-shape patterns.
_ALL_CAPS_RE = re.compile(r"^[A-Z][A-Z0-9 &/\-]*[A-Z0-9]$")
_TRAILING_COLON_RE = re.compile(r"^[A-Z][A-Za-z &/\-]+:$")
_UNDERLINE_RE = re.compile(r"^([=\-]){3,}$")

# Bullet markers (-, *, •, "1." / "1)" numbered).
_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$")

# Conservative heading-line length cap. Longer ALL-CAPS or trailing-colon
# strings are usually emphatic body text, not headings.
_MAX_HEADING_LEN = 60


def text_to_markdown(text: str) -> str:
    """Convert plain text into markdown that :class:`MarkdownParser` can parse.

    Strategy:
      1. Treat the first non-empty line as the candidate's name (H1) only
         if it contains no @-sign or digit — otherwise leave it as plain
         body and let ``MarkdownParser``'s "first non-heading line"
         fallback pick it up.
      2. Detect section headings via three signals:
         - line followed by an underline of ``=`` (H1) or ``-`` (H2)
         - ALL-CAPS short line on its own
         - Title-case line ending with ``:`` (drop the colon in output)
         The candidate must classify into a known :class:`SectionType`
         to avoid false-positives on emphatic body text.
      3. Rewrite bullets matched by :data:`_BULLET_RE` to ``- ``.
      4. Pass everything else through unchanged.
    """
    lines = text.splitlines()
    out: list[str] = []
    name_emitted = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Name-as-H1 (only if the very first non-empty line looks like one).
        if not name_emitted and stripped:
            if _looks_like_name(stripped):
                out.append(f"# {stripped}")
                name_emitted = True
                i += 1
                continue
            # First non-empty line wasn't a name — stop trying.
            name_emitted = True

        # Underline-style heading (line followed by === or ---).
        if (
            stripped
            and i + 1 < len(lines)
            and _UNDERLINE_RE.match(lines[i + 1].strip())
            and len(stripped) <= _MAX_HEADING_LEN
        ):
            depth = 1 if lines[i + 1].strip().startswith("=") else 2
            out.append(f"{'#' * depth} {stripped}")
            i += 2
            continue

        # ALL CAPS or "Title-case:" heading — only accept if the heading
        # text classifies into a real section type.
        candidate = stripped
        is_caps = (
            candidate
            and len(candidate) <= _MAX_HEADING_LEN
            and _ALL_CAPS_RE.match(candidate) is not None
        )
        is_titled = (
            candidate
            and len(candidate) <= _MAX_HEADING_LEN
            and _TRAILING_COLON_RE.match(candidate) is not None
        )
        if is_caps or is_titled:
            heading_text = candidate.rstrip(":")
            if _is_known_section(heading_text):
                out.append(f"## {_titlecase(heading_text)}")
                i += 1
                continue

        # Bullet rewrite.
        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            out.append(f"- {bullet_match.group(1).strip()}")
            i += 1
            continue

        out.append(line)
        i += 1

    return "\n".join(out)


def _looks_like_name(line: str) -> bool:
    """Heuristic: 2–5 capitalised words, no email/phone/URL characters."""
    if any(ch in line for ch in "@/|") or any(ch.isdigit() for ch in line):
        return False
    words = line.split()
    if not 2 <= len(words) <= 5:
        return False
    return all(w[:1].isupper() for w in words if w)


def _is_known_section(heading: str) -> bool:
    """True if ``heading`` classifies into something other than OTHER."""
    return classify_section_heading(heading) is not SectionType.OTHER


def _titlecase(text: str) -> str:
    """Render an ALL-CAPS or already-titled heading in Title Case."""
    return " ".join(w.capitalize() for w in text.split())


__all__ = ["text_to_markdown"]
