"""Markdown frontmatter file engine for memory entries."""

from __future__ import annotations

import logging
import os
import re
import secrets
import string
from contextlib import suppress
from pathlib import Path
from tempfile import mkstemp

import yaml
from pydantic import ValidationError

from owlbear_memory_mcp.models import MemoryEntry

_FRONTMATTER_PARTS = 3
_SUFFIX_ALPHABET = string.ascii_lowercase + string.digits
_SUFFIX_LEN = 6
_LOGGER = logging.getLogger(__name__)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        return "entry"
    return slug[:40]


def _random_suffix(length: int = _SUFFIX_LEN) -> str:
    return "".join(secrets.choice(_SUFFIX_ALPHABET) for _ in range(length))


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
        self._id_to_path: dict[str, Path] = {}

    def load(self) -> list[MemoryEntry]:
        """Load all markdown entry files from disk."""
        entries: list[MemoryEntry] = []
        id_to_path: dict[str, Path] = {}
        for file_path in sorted(self._memory_dir.glob("*.md")):
            entry = self._load_file(file_path)
            if entry is not None:
                entries.append(entry)
                id_to_path[entry.id] = file_path
        self._id_to_path = id_to_path
        return entries

    def get_entries(self) -> list[MemoryEntry]:
        """Return cached entries; reload when directory mtime has changed."""
        if self._cache.has_changed():
            self._entries = self.load()
        return list(self._entries)

    def write(self, entry: MemoryEntry) -> Path:
        """Write an entry to disk using YAML frontmatter plus markdown body."""
        existing = self._id_to_path.get(entry.id)
        if existing is not None:
            target_path = existing
        else:
            slug = _slugify(entry.title)
            target_path = self._memory_dir / f"{slug}-{_random_suffix()}.md"

        frontmatter = {
            "id": entry.id,
            "title": entry.title,
            "categories": list(entry.categories),
            "confidence": entry.confidence,
            "state": str(entry.state),
            "outstanding_count": entry.outstanding_count,
            "unremarkable_count": entry.unremarkable_count,
            "didnt_use_count": entry.didnt_use_count,
            "score": entry.score,
            "scope_agents": entry.scope_agents,
            "source_agent": entry.source_agent,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "approved_at": entry.approved_at,
            "contested_by_task": entry.contested_by_task,
        }
        content = (
            f"---\n{yaml.safe_dump(frontmatter, default_flow_style=False, sort_keys=False)}---\n\n{entry.content}\n"
        )

        fd, tmp_name = mkstemp(dir=str(target_path.parent), suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            tmp_path.replace(target_path)
        except Exception:
            with suppress(OSError):
                tmp_path.unlink()
            raise
        self._id_to_path[entry.id] = target_path
        return target_path

    def get_entry(self, entry_id: str) -> MemoryEntry:
        """Return a single entry by ID or raise KeyError if missing."""
        for entry in self.get_entries():
            if entry.id == entry_id:
                return entry
        msg = f"Entry {entry_id!r} not found"
        raise KeyError(msg)

    def delete(self, entry_id: str) -> None:
        """Remove an entry file from disk by ID or raise KeyError if missing."""
        target = self._id_to_path.get(entry_id)
        if target is None:
            self.get_entries()
            target = self._id_to_path.get(entry_id)
        if target is None:
            msg = f"Entry {entry_id!r} not found"
            raise KeyError(msg)
        target.unlink()
        self._id_to_path.pop(entry_id, None)

    def _load_file(self, file_path: Path) -> MemoryEntry | None:
        raw = file_path.read_text(encoding="utf-8-sig")
        parts = raw.split("---", 2)
        if len(parts) < _FRONTMATTER_PARTS:
            _LOGGER.warning("Skipping malformed memory file without frontmatter: %s", file_path)
            return None
        _, frontmatter_raw, body = parts
        try:
            data = yaml.safe_load(frontmatter_raw) or {}
        except yaml.YAMLError as exc:
            _LOGGER.warning("Skipping malformed memory YAML in %s: %s", file_path, exc)
            return None
        if not isinstance(data, dict):
            _LOGGER.warning("Skipping memory file with non-object frontmatter: %s", file_path)
            return None
        data["content"] = body.strip()
        try:
            return MemoryEntry(**data)
        except ValidationError as exc:
            _LOGGER.warning("Skipping invalid memory entry in %s: %s", file_path, exc)
            return None
