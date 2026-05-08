"""JSON report generation.

Renders a :class:`ScanResult` to deterministic, byte-stable JSON via
Pydantic's ``model_dump_json`` with sorted keys. The reporter is the
canonical machine-readable form (PRD §11.1).
"""

from __future__ import annotations

import json
from pathlib import Path

from open_ats.models import ScanResult


def render_json(result: ScanResult, *, indent: int = 2) -> str:
    """Return ``result`` as a JSON string with sorted keys.

    Pydantic v2's ``model_dump_json`` doesn't expose ``sort_keys``, so
    we round-trip through ``json.dumps`` to enforce stable byte output
    across platforms and Python versions.
    """
    payload = json.loads(result.model_dump_json())
    return json.dumps(payload, indent=indent, sort_keys=True, ensure_ascii=False)


def write_json(result: ScanResult, path: Path, *, indent: int = 2) -> None:
    """Write ``result`` to ``path`` as deterministic JSON."""
    path.write_text(render_json(result, indent=indent) + "\n", encoding="utf-8")


__all__ = ["render_json", "write_json"]
