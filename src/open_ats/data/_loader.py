"""YAML word-list loader for ``src/open_ats/data/*.yaml``.

Internal helper. Each list lives in its own YAML, keyed by the list's
purpose (``verbs`` / ``markers`` / ``phrases``). The loader reads the
file once and caches the result; each list is small (≤100 entries) so
this is functionally just a deferred import.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import cast

import yaml

_DATA_DIR = Path(__file__).resolve().parent


@cache
def load_action_verbs() -> tuple[str, ...]:
    """Strong action verbs (PRD §10.1)."""
    return _load_list("action_verbs.yaml", "verbs")


@cache
def load_weak_verbs() -> tuple[str, ...]:
    """Weak verbs (PRD §10.2)."""
    return _load_list("weak_verbs.yaml", "verbs")


@cache
def load_passive_markers() -> tuple[str, ...]:
    """Passive-voice markers (PRD §10.3)."""
    return _load_list("passive_markers.yaml", "markers")


@cache
def load_hedging_phrases() -> tuple[str, ...]:
    """Hedging language (PRD §10.4)."""
    return _load_list("hedging.yaml", "phrases")


def _load_list(filename: str, key: str) -> tuple[str, ...]:
    path = _DATA_DIR / filename
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = payload.get(key) or []
    if not isinstance(raw, list):
        return ()
    return tuple(s for s in raw if isinstance(s, str) and s.strip())


__all__ = [
    "load_action_verbs",
    "load_hedging_phrases",
    "load_passive_markers",
    "load_weak_verbs",
]


def _check_minimums() -> dict[str, int]:
    """Diagnostic helper — returns counts so tests can assert PRD minimums."""
    return {
        "action_verbs": len(load_action_verbs()),
        "weak_verbs": len(load_weak_verbs()),
        "passive_markers": len(load_passive_markers()),
        "hedging_phrases": len(load_hedging_phrases()),
    }


# Re-exported as a public surface for tests that just want counts.
counts = _check_minimums

# Make ``cast`` import non-redundant for mypy strict in callers.
_ = cast
