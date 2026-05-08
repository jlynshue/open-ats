"""Resume and job-description parsers (Markdown, DOCX, PDF, TXT).

Public surface:

- :func:`parse_resume` — extension-dispatched entry point used by the CLI.
- :class:`Parser` — protocol every concrete parser implements.
- :class:`ResumeParseError`, :class:`UnsupportedFormatError` — public exceptions.
- :class:`MarkdownParser` — concrete parser landed in Sprint 1.
- :class:`DocxParser`, :class:`TxtParser` — landed in Sprint 2.

The PDF parser lands in Sprint 3 and registers itself through this
module's dispatcher.
"""

from __future__ import annotations

from pathlib import Path

from open_ats.models import Resume
from open_ats.parsers.base import (
    Parser,
    ResumeParseError,
    UnsupportedFormatError,
)
from open_ats.parsers.docx_parser import DocxParser, default_docx_parser
from open_ats.parsers.markdown_parser import MarkdownParser, default_markdown_parser
from open_ats.parsers.txt_parser import TxtParser, default_txt_parser

# Extension → Parser registry. Keep keys lowercase, dot-prefixed.
# Sprint 3 adds .pdf.
_PARSERS: dict[str, Parser] = {
    ".md": default_markdown_parser,
    ".markdown": default_markdown_parser,
    ".docx": default_docx_parser,
    ".txt": default_txt_parser,
}


def supported_extensions() -> list[str]:
    """Return the sorted list of supported resume file extensions."""
    return sorted(_PARSERS.keys())


def parse_resume(path: Path | str) -> Resume:
    """Dispatch to the format-specific parser for ``path``.

    Raises:
        UnsupportedFormatError: extension has no registered parser yet.
        ResumeParseError: file is unreadable, empty, or otherwise unparseable.
    """
    resolved = Path(path)
    suffix = resolved.suffix.lower()
    parser = _PARSERS.get(suffix)
    if parser is None:
        raise UnsupportedFormatError(suffix or "(no extension)", supported_extensions())
    return parser.parse(resolved)


__all__ = [
    "DocxParser",
    "MarkdownParser",
    "Parser",
    "ResumeParseError",
    "TxtParser",
    "UnsupportedFormatError",
    "parse_resume",
    "supported_extensions",
]
