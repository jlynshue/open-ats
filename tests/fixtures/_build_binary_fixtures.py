"""Regenerate DOCX and TXT resume fixtures from the markdown originals.

Run once per fixture refresh:

    python tests/fixtures/_build_binary_fixtures.py

Reads ``tests/fixtures/resumes/{entry_level,mid_level,executive}.md`` and
writes the same content as ``.docx`` (using python-docx) and ``.txt``
(plain-text demarkdown). The generated files are checked into git so
tests are deterministic without running this script in CI.

This is a *fixtures* utility, not part of the runtime package — it
imports python-docx and may be skipped in environments where the dev
extras are missing.
"""

from __future__ import annotations

import re
from pathlib import Path

import docx
from docx.document import Document as DocumentT

FIXTURES_DIR = Path(__file__).parent / "resumes"
SOURCES = ("entry_level", "mid_level", "executive")

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.+)$")
_BOLD_TITLE_RE = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")


def main() -> None:
    for stem in SOURCES:
        md_path = FIXTURES_DIR / f"{stem}.md"
        if not md_path.exists():
            raise FileNotFoundError(md_path)
        markdown = md_path.read_text(encoding="utf-8")
        _write_docx(markdown, FIXTURES_DIR / f"{stem}.docx")
        _write_txt(markdown, FIXTURES_DIR / f"{stem}.txt")
        print(f"  generated {stem}.docx and {stem}.txt")


def _write_docx(markdown: str, out: Path) -> None:
    document: DocumentT = docx.Document()
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        match = _HEADING_RE.match(line)
        if match:
            depth = len(match.group(1))
            document.add_heading(
                _strip_inline_markdown(match.group(2)), level=min(depth, 9)
            )
            continue
        bullet = _BULLET_RE.match(line)
        if bullet:
            document.add_paragraph(
                _strip_inline_markdown(bullet.group(1)), style="List Bullet"
            )
            continue
        bold_title = _BOLD_TITLE_RE.match(line.lstrip())
        if bold_title:
            paragraph = document.add_paragraph()
            run = paragraph.add_run(_strip_inline_markdown(bold_title.group(1)))
            run.bold = True
            tail = bold_title.group(2)
            if tail:
                paragraph.add_run(" " + _strip_inline_markdown(tail))
            continue
        document.add_paragraph(_strip_inline_markdown(line))
    document.save(str(out))


def _write_txt(markdown: str, out: Path) -> None:
    """Render markdown as plain text suitable for the TXT parser.

    Conversion rules:
      - H1 ``# Name`` → name on its own line (no marker)
      - H2/H3 ``## Foo`` → ``FOO`` (ALL CAPS) on its own line
      - bullets ``- Foo`` → ``- Foo`` (preserved; the TXT parser
        recognises ``-``)
      - **bold** runs → plain text
      - other lines pass through
    """
    out_lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        match = _HEADING_RE.match(line)
        if match:
            depth = len(match.group(1))
            heading = _strip_inline_markdown(match.group(2))
            if depth == 1:
                out_lines.append(heading)
            else:
                out_lines.append(heading.upper())
            continue
        bullet = _BULLET_RE.match(line)
        if bullet:
            out_lines.append(f"- {_strip_inline_markdown(bullet.group(1))}")
            continue
        out_lines.append(_strip_inline_markdown(line))
    out.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


def _strip_inline_markdown(text: str) -> str:
    """Drop **bold** and `code` decorations from a single line."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


if __name__ == "__main__":
    main()
