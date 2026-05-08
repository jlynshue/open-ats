"""PDF resume parser.

PDFs are the lossiest input format. We use ``pdfplumber`` to extract
text page-by-page, surface an explicit error for image-based / scanned
PDFs that yield no text, then run the same heuristic-based
text→markdown converter the TXT parser uses, and finally delegate to
:class:`MarkdownParser` for section/contact/experience extraction.

Acceptance criteria are documented in PRD §FR-1.3 (``docs/PRD.md``).

Multi-column PDFs degrade naturally: pdfplumber returns lines in
y-coordinate order, which interleaves columns. Section detection still
recovers the major headings; experience-block parsing degrades to
single blocks. NFR-1: <2 sec on a 2-page PDF.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from open_ats.models import Resume
from open_ats.parsers._heuristic import text_to_markdown
from open_ats.parsers.base import Parser, ResumeParseError
from open_ats.parsers.markdown_parser import MarkdownParser

# Verbatim message required by the FR-1.3 acceptance criterion.
IMAGE_BASED_MESSAGE = "PDF appears to be image-based; please convert to text-based PDF"


class PdfParser:
    """Concrete :class:`Parser` for ``.pdf`` resumes."""

    def __init__(self) -> None:
        self._markdown = MarkdownParser()

    def parse(self, path: Path) -> Resume:
        """Read ``path`` and return a populated :class:`Resume`.

        Raises:
            ResumeParseError: file cannot be opened, contains no
                extractable text (image-based / scanned), or is empty.
        """
        try:
            extracted_pages = _extract_pages(path)
        except Exception as exc:
            raise ResumeParseError(
                f"Could not read PDF file: {path}", cause=exc
            ) from exc

        joined = "\n\n".join(p for p in extracted_pages if p)
        if not joined.strip():
            raise ResumeParseError(IMAGE_BASED_MESSAGE)

        rendered = text_to_markdown(joined)
        resume = self._markdown.parse_text(rendered, source_path=path)
        resume.source_format = "pdf"
        return resume


# Module-level singleton — Parser protocol satisfied at import.
default_pdf_parser: Parser = PdfParser()


def _extract_pages(path: Path) -> list[str]:
    """Return the per-page extracted text from a PDF.

    Each returned string is whatever pdfplumber's ``extract_text()``
    yields for that page (or empty string for pages with no text). The
    caller decides what to do with all-empty results.
    """
    pages: list[str] = []
    with pdfplumber.open(str(path)) as document:
        for page in document.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return pages


__all__ = ["PdfParser", "default_pdf_parser", "IMAGE_BASED_MESSAGE"]
