"""Markdown frontmatter file engine for memory entries."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from owlbear_mcp_memory.models import MemoryEntry

_FRONTMATTER_PARTS = 3


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        return "entry"
    return slug[:40]


class MtimeScanCache:
    """Track directory mtime to skip re-parsing when nothing changed."""

    def __init__(self, memory_dir: Path) -> None:
        self._memory_dir = memory_dir
        self._last_mtime_ns: int | None = None

    def has_changed(self) -> bool:
        """Return True when directory mtime differs from previous check."""
        current = self._memory_dir.stat().st_mtime_ns
        if self._last_mtime_ns is None:
            self._last_mtime_ns = current
            return True
        if current != self._last_mtime_ns:
            self._last_mtime_ns = current
            return True
        return False


class MemoryEngine:
    """Read/write memory entries as markdown files with YAML frontmatter."""

    def __init__(self, memory_dir: Path | str = ".owlbear/memory") -> None:
        self._memory_dir = Path(memory_dir)
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._cache = MtimeScanCache(self._memory_dir)
        self._entries: list[MemoryEntry] = []

    def load(self) -> list[MemoryEntry]:
        """Load all markdown entry files from disk."""
        entries: list[MemoryEntry] = []
        for file_path in sorted(self._memory_dir.glob("*.md")):
            entry = self._load_file(file_path)
            if entry is not None:
                entries.append(entry)
        return entries

    def get_entries(self) -> list[MemoryEntry]:
        """Return cached entries; reload when directory mtime has changed."""
        if self._cache.has_changed():
            self._entries = self.load()
        return list(self._entries)

    def write(self, entry: MemoryEntry) -> Path:
        """Write an entry to disk using YAML frontmatter plus markdown body."""
        existing = self._path_for_entry_id(entry.id)
        if existing is not None:
            target_path = existing
        else:
            slug = _slugify(entry.title)
            target_path = self._memory_dir / f"{slug}-{entry.id[:6]}.md"

        frontmatter = {
            "id": entry.id,
            "title": entry.title,
            "categories": entry.categories,
            "confidence": entry.confidence,
            "state": entry.state,
            "scope_agents": entry.scope_agents,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }
        content = (
            "---\n"
            f"{yaml.safe_dump(frontmatter, default_flow_style=False)}"
            "---\n\n"
            f"{entry.content}\n"
        )

        tmp_path = target_path.with_suffix(".md.tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(target_path)
        return target_path

    def get_entry(self, entry_id: str) -> MemoryEntry:
        """Return a single entry by ID or raise KeyError if missing."""
        for entry in self.get_entries():
            if entry.id == entry_id:
                return entry
        msg = f"Entry {entry_id!r} not found"
        raise KeyError(msg)

    def _path_for_entry_id(self, entry_id: str) -> Path | None:
        for file_path in self._memory_dir.glob("*.md"):
            entry = self._load_file(file_path)
            if entry is not None and entry.id == entry_id:
                return file_path
        return None

    def _load_file(self, file_path: Path) -> MemoryEntry | None:
        raw = file_path.read_text(encoding="utf-8")
        parts = raw.split("---", 2)
        if len(parts) < _FRONTMATTER_PARTS:
            return None
        _, frontmatter_raw, body = parts
        data = yaml.safe_load(frontmatter_raw) or {}
        data["content"] = body.strip()
        return MemoryEntry(**data)
