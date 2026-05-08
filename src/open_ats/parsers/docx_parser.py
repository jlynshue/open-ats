"""DOCX resume parser.

Converts a ``.docx`` file into markdown-flavored text using
``python-docx`` to inspect paragraph styles, then delegates the heavy
lifting to :class:`MarkdownParser`. Keeping the parsing brain in one
place means heading classification, contact extraction, experience
splitting, etc. evolve in a single module.

Acceptance criteria are documented in PRD §FR-1.2 (``docs/PRD.md``).
"""

from __future__ import annotations

from pathlib import Path

import docx
from docx.document import Document as DocumentT
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from open_ats.models import ParserWarning, Resume
from open_ats.parsers.base import Parser, ResumeParseError
from open_ats.parsers.markdown_parser import MarkdownParser

# Heading paragraph-style names → markdown heading depth.
# Word's default styles are "Heading 1", "Heading 2", … Some templates
# also use "Title" (always treated as H1) and "Subtitle" (H2).
_HEADING_DEPTH: dict[str, int] = {
    "Title": 1,
    "Subtitle": 2,
    "Heading 1": 1,
    "Heading 2": 2,
    "Heading 3": 3,
    "Heading 4": 4,
    "Heading 5": 5,
    "Heading 6": 6,
}

# Style names that indicate a bulleted (or numbered) list paragraph.
# python-docx exposes the style; presence of a numbering element on the
# paragraph also counts.
_BULLET_STYLES = frozenset(
    {
        "List Bullet",
        "List Bullet 2",
        "List Bullet 3",
        "List Number",
        "List Number 2",
        "List Number 3",
        "List Paragraph",
    }
)


class DocxParser:
    """Concrete :class:`Parser` for ``.docx`` resumes."""

    def __init__(self) -> None:
        self._markdown = MarkdownParser()

    def parse(self, path: Path) -> Resume:
        """Read ``path`` and return a populated :class:`Resume`.

        Raises:
            ResumeParseError: file cannot be opened, is empty, or python-docx
                cannot read its package format.
        """
        try:
            document: DocumentT = docx.Document(str(path))
        except Exception as exc:  # python-docx raises a variety of types
            raise ResumeParseError(
                f"Could not read DOCX file: {path}", cause=exc
            ) from exc

        rendered, has_table = _render_document_as_markdown(document)
        if not rendered.strip():
            raise ResumeParseError("DOCX file produced no extractable text.")

        resume = self._markdown.parse_text(rendered, source_path=path)
        # Post-process: report the source format honestly and surface
        # DOCX-specific warnings (tables, etc.).
        resume.source_format = "docx"
        if has_table:
            resume.parser_warnings.append(
                ParserWarning(
                    code="formatting.table_detected",
                    message=(
                        "DOCX contains a table. Tables can confuse downstream "
                        "ATS readers; consider replacing with plain paragraphs."
                    ),
                    severity="warning",
                )
            )
        return resume


# Module-level singleton — Parser protocol satisfied at import.
default_docx_parser: Parser = DocxParser()


# ─── Internals ────────────────────────────────────────────────────────


def _render_document_as_markdown(document: DocumentT) -> tuple[str, bool]:
    """Walk ``document`` body in order and emit markdown.

    Returns:
        (markdown_text, has_table). ``has_table`` is True if any table
        was encountered in the body — the caller surfaces it as a
        ParserWarning rather than rejecting the document.
    """
    lines: list[str] = []
    has_table = False

    for block in _iter_block_items(document):
        if isinstance(block, Paragraph):
            rendered = _render_paragraph(block)
            if rendered is None:
                continue
            lines.append(rendered)
        elif isinstance(block, Table):
            has_table = True
            for row_text in _render_table_rows(block):
                lines.append(row_text)

    # Coalesce excess blank lines so MarkdownParser sees a clean structure.
    return _normalise_blank_lines("\n".join(lines)), has_table


def _iter_block_items(document: DocumentT) -> list[Paragraph | Table]:
    """Yield top-level paragraphs and tables in document order.

    python-docx doesn't expose a body-order iterator natively for
    paragraphs+tables interleaved; walk the underlying XML.
    """
    body = document.element.body
    blocks: list[Paragraph | Table] = []
    for child in body.iterchildren():
        tag = child.tag
        if tag == qn("w:p"):
            blocks.append(Paragraph(child, document))
        elif tag == qn("w:tbl"):
            blocks.append(Table(child, document))
    return blocks


def _render_paragraph(paragraph: Paragraph) -> str | None:
    """Convert one paragraph into either a markdown heading, bullet, or body line.

    Returns ``None`` for paragraphs with no extractable text (entirely
    empty lines collapse during normalisation; we keep one blank as a
    paragraph break).
    """
    text = paragraph.text.strip()
    style_name = (paragraph.style.name if paragraph.style is not None else "") or ""

    depth = _HEADING_DEPTH.get(style_name)
    if depth is not None and text:
        return f"{'#' * depth} {text}"

    if _is_bullet(paragraph, style_name) and text:
        return f"- {_render_runs_with_bold(paragraph)}"

    if not text:
        # Preserve paragraph breaks; downstream normaliser collapses runs.
        return ""

    return _render_runs_with_bold(paragraph)


def _render_runs_with_bold(paragraph: Paragraph) -> str:
    """Render a paragraph's runs preserving bold via ``**...**`` markers.

    Why we care: experience-block titles in markdown resumes are
    typically formatted as ``**Senior Engineer** — Acme Cloud``. When a
    DOCX uses bold runs for the title, preserving that signal lets the
    downstream MarkdownParser split experience entries correctly.

    Adjacent runs of the same boldness are merged. Whitespace inside
    bold runs that has no neighboring text is dropped from the bold
    span (``**Title** — Co`` rather than ``**Title **— Co``).
    """
    pieces: list[str] = []
    for run in paragraph.runs:
        if not run.text:
            continue
        if run.bold:
            text = run.text
            leading_ws_len = len(text) - len(text.lstrip())
            trailing_ws_len = len(text) - len(text.rstrip())
            leading = text[:leading_ws_len]
            trailing = text[len(text) - trailing_ws_len :] if trailing_ws_len else ""
            core = text[
                leading_ws_len : (
                    len(text) - trailing_ws_len if trailing_ws_len else len(text)
                )
            ]
            if core:
                pieces.append(f"{leading}**{core}**{trailing}")
            else:
                pieces.append(text)
        else:
            pieces.append(run.text)
    rendered = "".join(pieces).strip()
    return rendered or paragraph.text.strip()


def _is_bullet(paragraph: Paragraph, style_name: str) -> bool:
    """Return True if ``paragraph`` is rendered as a bullet/numbered list."""
    if style_name in _BULLET_STYLES:
        return True
    # Numbering element on the paragraph properties also indicates a list.
    paragraph_props = paragraph._p.find(qn("w:pPr"))
    if paragraph_props is not None and paragraph_props.find(qn("w:numPr")) is not None:
        return True
    return False


def _render_table_rows(table: Table) -> list[str]:
    """Render a Word table as a sequence of " | "-joined plain lines.

    We don't try to preserve table semantics — the caller has already
    flagged the resume; here we just surface the cell text so contact
    info / dates aren't lost.
    """
    rendered: list[str] = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        joined = " | ".join(c for c in cells if c)
        if joined:
            rendered.append(joined)
    return rendered


def _normalise_blank_lines(text: str) -> str:
    """Collapse runs of ≥3 blank lines down to 2.

    MarkdownParser is happy with single blank lines as paragraph
    separators; multi-blank runs from DOCX add no signal.
    """
    out: list[str] = []
    blank_run = 0
    for line in text.splitlines():
        if line.strip() == "":
            blank_run += 1
            if blank_run <= 1:
                out.append("")
        else:
            blank_run = 0
            out.append(line)
    return "\n".join(out)


__all__ = ["DocxParser", "default_docx_parser"]
