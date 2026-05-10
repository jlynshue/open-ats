"""Keyword-database loader for ``keyword_databases/*.yaml``.

Internal helper used by :mod:`open_ats.analyzers.keyword`. Loading is
cheap (a single YAML file is ~5 KB and ~70 entries today). Synonym
resolution is case-insensitive; the canonical spelling preserves the
casing declared in YAML.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from open_ats.models import KeywordCategory

# Repo-relative location of the bundled keyword databases. The CLI may
# override via ``--config``; tests load directly by Path.
_DEFAULT_DB_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent / "keyword_databases"
)


@dataclass(frozen=True)
class DatabaseEntry:
    """One canonical keyword + its synonyms + its category."""

    canonical: str
    category: KeywordCategory
    synonyms: tuple[str, ...] = ()


@dataclass
class KeywordDatabase:
    """In-memory index over one or more keyword databases.

    Lookups are case-insensitive. ``classify`` returns the category of a
    matched token; ``canonical`` returns the canonical spelling. Both
    return None if the token isn't found.
    """

    entries: tuple[DatabaseEntry, ...] = field(default_factory=tuple)
    # Case-insensitive lookup index: lowercase token → DatabaseEntry.
    _index: dict[str, DatabaseEntry] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        index: dict[str, DatabaseEntry] = {}
        for entry in self.entries:
            index[entry.canonical.casefold()] = entry
            for syn in entry.synonyms:
                index[syn.casefold()] = entry
        self._index = index

    def classify(self, token: str) -> KeywordCategory | None:
        entry = self._index.get(token.casefold())
        return entry.category if entry else None

    def canonical(self, token: str) -> str | None:
        entry = self._index.get(token.casefold())
        return entry.canonical if entry else None

    def lookup(self, token: str) -> DatabaseEntry | None:
        return self._index.get(token.casefold())

    def entries_in(self, category: KeywordCategory) -> list[DatabaseEntry]:
        return [e for e in self.entries if e.category == category]

    def __len__(self) -> int:
        return len(self.entries)


def load_database(path: Path) -> KeywordDatabase:
    """Load a single database YAML."""
    return _from_yaml_text(path.read_text(encoding="utf-8"))


def load_default_database() -> KeywordDatabase:
    """Load the bundled software-engineering database."""
    seed = _DEFAULT_DB_DIR / "software_engineering.yaml"
    if not seed.exists():
        return KeywordDatabase()
    return load_database(seed)


def load_databases(paths: Iterable[Path]) -> KeywordDatabase:
    """Merge multiple database YAML files into one in-memory database.

    Later files do NOT override earlier entries with the same canonical
    casefold; first declaration wins (deterministic behavior).
    """
    seen: set[str] = set()
    merged: list[DatabaseEntry] = []
    for path in paths:
        for entry in load_database(path).entries:
            key = entry.canonical.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)
    return KeywordDatabase(entries=tuple(merged))


def _from_yaml_text(text: str) -> KeywordDatabase:
    payload = yaml.safe_load(text) or {}
    if not isinstance(payload, dict):
        return KeywordDatabase()

    entries: list[DatabaseEntry] = []
    _ingest(payload.get("hard_skills"), KeywordCategory.HARD_SKILL, entries)
    _ingest(payload.get("soft_skills"), KeywordCategory.SOFT_SKILL, entries)
    _ingest(payload.get("industry_terms"), KeywordCategory.INDUSTRY_TERM, entries)
    _ingest(payload.get("action_verbs"), KeywordCategory.ACTION_VERB, entries)
    return KeywordDatabase(entries=tuple(entries))


def _ingest(
    raw: object,
    category: KeywordCategory,
    out: list[DatabaseEntry],
) -> None:
    """Append entries from a YAML list of strings or {name, synonyms}."""
    if not isinstance(raw, list):
        return
    for item in raw:
        if isinstance(item, str):
            if item.strip():
                out.append(DatabaseEntry(canonical=item.strip(), category=category))
            continue
        if isinstance(item, dict):
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            raw_syns = item.get("synonyms") or []
            synonyms = tuple(
                s.strip() for s in raw_syns if isinstance(s, str) and s.strip()
            )
            out.append(
                DatabaseEntry(
                    canonical=name.strip(),
                    category=category,
                    synonyms=synonyms,
                )
            )


__all__ = [
    "DatabaseEntry",
    "KeywordDatabase",
    "load_database",
    "load_databases",
    "load_default_database",
]
