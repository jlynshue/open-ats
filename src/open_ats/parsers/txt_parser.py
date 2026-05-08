"""Plain-text resume parser.

Plain text has no structural markup, so this parser uses heuristics to
recognise headings (ALL CAPS lines, "Section:" lines, lines followed by
``===``/``---`` underlines) and bullets (``-``/``*``/``•``/numbered),
normalises the document into markdown, and delegates to
:class:`MarkdownParser`.

Acceptance criteria are documented in PRD §FR-1.4 (``docs/PRD.md``).
"""

from __future__ import annotations

import re
from pathlib import Path

from open_ats.models import Resume
from open_ats.parsers.base import Parser, ResumeParseError, classify_section_heading
from open_ats.parsers.markdown_parser import MarkdownParser

# Lines we consider section-heading candidates if they match.
_ALL_CAPS_RE = re.compile(r"^[A-Z][A-Z0-9 &/\-]*[A-Z0-9]$")
_TRAILING_COLON_RE = re.compile(r"^[A-Z][A-Za-z &/\-]+:$")
_UNDERLINE_RE = re.compile(r"^([=\-]){3,}$")
# Bullets: -, *, •, or "1." / "1)" numbered.
_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+)$")
# Conservative caps on heading line length (drops body-text false positives).
_MAX_HEADING_LEN = 60


class TxtParser:
    """Concrete :class:`Parser` for ``.txt`` resumes."""

    def __init__(self) -> None:
        self._markdown = MarkdownParser()

    def parse(self, path: Path) -> Resume:
        """Read ``path`` and return a populated :class:`Resume`.

        Raises:
            ResumeParseError: file unreadable, empty, or whitespace-only.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ResumeParseError(
                f"Could not read TXT file: {path}", cause=exc
            ) from exc
        if not text.strip():
            raise ResumeParseError("TXT file is empty or whitespace-only.")

        rendered = _render_text_as_markdown(text)
        resume = self._markdown.parse_text(rendered, source_path=path)
        resume.source_format = "txt"
        return resume


# Module-level singleton — Parser protocol satisfied at import.
default_txt_parser: Parser = TxtParser()


# ─── Internals ────────────────────────────────────────────────────────


def _render_text_as_markdown(text: str) -> str:
    """Convert plain text into markdown that MarkdownParser can chew on.

    Strategy:
      1. Treat the first non-empty line as the candidate's name (H1) only
         if it contains no @ or digit — otherwise leave it as plain body
         and let MarkdownParser's "first non-heading line" fallback pick it.
      2. Detect headings via three signals:
         - line followed by an underline of ``=`` (H1) or ``-`` (H2)
         - ALL CAPS short line on its own
         - Title-case line ending with ``:`` (drop the colon in output)
         The line must classify into a known SectionType to avoid
         false-positives on emphatic body text.
      3. Detect bullets via :data:`_BULLET_RE` and rewrite to ``- ``.
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
    """Heuristic: 2–5 words, capitalised, no email/phone/URL chars."""
    if any(ch in line for ch in "@/|") or any(ch.isdigit() for ch in line):
        return False
    words = line.split()
    if not 2 <= len(words) <= 5:
        return False
    return all(w[:1].isupper() for w in words if w)


def _is_known_section(heading: str) -> bool:
    """True if ``heading`` classifies into something other than OTHER."""
    from open_ats.models import SectionType

    return classify_section_heading(heading) is not SectionType.OTHER


def _titlecase(text: str) -> str:
    """Render an ALL-CAPS or already-titled heading in Title Case."""
    return " ".join(w.capitalize() for w in text.split())


__all__ = ["TxtParser", "default_txt_parser"]
