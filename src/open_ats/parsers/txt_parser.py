"""Plain-text resume parser.

Plain text has no structural markup, so this parser leans on the shared
:mod:`open_ats.parsers._heuristic` module to detect headings (ALL CAPS,
``Section:``, lines followed by ``===``/``---`` underlines) and bullets
(``-``/``*``/``•``/numbered), then delegates to :class:`MarkdownParser`.

The PDF parser (Sprint 3) reuses the same heuristic against pdfplumber-
extracted text — keeping the rules in one place pays off there.

Acceptance criteria are documented in PRD §FR-1.4 (``docs/PRD.md``).
"""

from __future__ import annotations

from pathlib import Path

from open_ats.models import Resume
from open_ats.parsers._heuristic import text_to_markdown
from open_ats.parsers.base import Parser, ResumeParseError
from open_ats.parsers.markdown_parser import MarkdownParser


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

        rendered = text_to_markdown(text)
        resume = self._markdown.parse_text(rendered, source_path=path)
        resume.source_format = "txt"
        return resume


# Module-level singleton — Parser protocol satisfied at import.
default_txt_parser: Parser = TxtParser()


__all__ = ["TxtParser", "default_txt_parser"]
