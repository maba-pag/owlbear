"""Memory engine with state transitions, OCC, and mtime-based caching."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from owlbear_memory import storage
from owlbear_memory.errors import ConcurrencyError, NotFoundError, TransitionError
from owlbear_memory.models import MemoryCategory, MemoryEntry, MemoryState

_LOGGER = logging.getLogger(__name__)

OUTSTANDING_BOOST = 0.1
UNREMARKABLE_PENALTY = 0.01
STALE_THRESHOLD = 50


def compute_score(confidence: float, outstanding_count: int, unremarkable_count: int) -> float:
    """Compute score from confidence and assessment counters."""
    return confidence + (outstanding_count * OUTSTANDING_BOOST) - (unremarkable_count * UNREMARKABLE_PENALTY)


class EditPayload(TypedDict, total=False):
    """Editable entry fields for MemoryEngine.edit()."""

    title: str
    content: str
    categories: list[MemoryCategory]
    confidence: float
    scope_agents: list[str]


class MtimeScanCache:
    """Track directory mtime so callers can skip unnecessary reparsing."""

    def __init__(self, memory_dir: Path) -> None:
        self._memory_dir = memory_dir
        self._last_mtime_ns: int | None = None

    def has_changed(self) -> bool:
        """Return True on first call and when directory mtime changes."""
        current = self._memory_dir.stat().st_mtime_ns
        if self._last_mtime_ns is None:
            self._last_mtime_ns = current
            return True
        if current != self._last_mtime_ns:
            self._last_mtime_ns = current
            return True
        return False


class MemoryEngine:
    """Orchestrate markdown storage with state machine and OCC enforcement."""

    def __init__(self, memory_dir: Path | str = ".owlbear/memory") -> None:
        self._memory_dir = Path(memory_dir)
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._cache = MtimeScanCache(self._memory_dir)
        self._entries: list[MemoryEntry] = []
        self._id_to_path: dict[str, Path] = {}
        self.parse_errors = 0

    def load(self) -> list[MemoryEntry]:
        """Parse memory files from disk, skipping malformed files leniently."""
        self.parse_errors = 0
        by_id: dict[str, MemoryEntry] = {}
        id_to_path: dict[str, Path] = {}

        for file_path in sorted(self._memory_dir.glob("*.md")):
            entry = storage.read_entry(file_path)
            if entry is None:
                self.parse_errors += 1
                continue

            current = by_id.get(entry.id)
            if current is None:
                by_id[entry.id] = entry
                id_to_path[entry.id] = file_path
                continue

            if self._parse_iso_datetime(entry.updated_at) > self._parse_iso_datetime(current.updated_at):
                _LOGGER.warning("Duplicate UUID %s found in %s; keeping later updated_at", entry.id, file_path)
                by_id[entry.id] = entry
                id_to_path[entry.id] = file_path
            else:
                _LOGGER.warning(
                    "Duplicate UUID %s found in %s; keeping existing later updated_at",
                    entry.id,
                    file_path,
                )

        self._entries = list(by_id.values())
        self._id_to_path = id_to_path
        return list(self._entries)

    def get_entries(self) -> list[MemoryEntry]:
        """Return cached entries, reparsing only when directory mtime changes."""
        if self._cache.has_changed():
            self.load()
        return list(self._entries)

    def get_entry(self, entry_id: str) -> MemoryEntry:
        """Return one entry by ID or raise NotFoundError."""
        for entry in self.get_entries():
            if entry.id == entry_id:
                return entry
        msg = f"Entry not found: {entry_id}"
        raise NotFoundError(msg)

    def approve(self, entry_id: str, expected_updated_at: str) -> MemoryEntry:
        """Transition curated entry to approved after OCC check."""
        entry = self.get_entry(entry_id)
        self._validate_occ(entry, expected_updated_at)

        if entry.state != MemoryState.CURATED:
            msg = f"approve() not allowed from state {entry.state}"
            raise TransitionError(msg)

        now = self._now_iso()
        updated = entry.model_copy(
            update={
                "state": MemoryState.APPROVED,
                "approved_at": now,
                "updated_at": now,
            }
        )
        return self._write_updated_entry(updated)

    def resolve(self, entry_id: str, expected_updated_at: str) -> MemoryEntry:
        """Transition contested/disputed/stale entry to approved after OCC check."""
        entry = self.get_entry(entry_id)
        self._validate_occ(entry, expected_updated_at)

        if entry.state not in {MemoryState.CONTESTED, MemoryState.DISPUTED, MemoryState.STALE}:
            msg = f"resolve() not allowed from state {entry.state}"
            raise TransitionError(msg)

        now = self._now_iso()
        updated = entry.model_copy(
            update={
                "state": MemoryState.APPROVED,
                "approved_at": now,
                "updated_at": now,
            }
        )
        return self._write_updated_entry(updated)

    def edit(self, entry_id: str, fields: EditPayload, expected_updated_at: str) -> MemoryEntry:
        """Apply field updates with state-machine and OCC constraints."""
        entry = self.get_entry(entry_id)
        self._validate_occ(entry, expected_updated_at)

        if entry.state == MemoryState.DELETED:
            msg = "edit() not allowed from state deleted"
            raise TransitionError(msg)
        if entry.state in {MemoryState.CONTESTED, MemoryState.DISPUTED, MemoryState.STALE}:
            msg = f"edit() not allowed from state {entry.state}; resolve first"
            raise TransitionError(msg)

        target_state = entry.state
        approved_at = entry.approved_at

        if entry.state == MemoryState.APPROVED:
            target_state = MemoryState.CURATED
            approved_at = None
        elif entry.state == MemoryState.PENDING and fields.get("scope_agents"):
            target_state = MemoryState.CURATED

        data = entry.model_dump()
        for key in ("title", "content", "categories", "confidence", "scope_agents"):
            if key in fields:
                data[key] = fields[key]  # type: ignore[literal-required]
        data["state"] = target_state
        data["approved_at"] = approved_at
        data["updated_at"] = self._now_iso()

        updated = MemoryEntry.model_validate(data)
        return self._write_updated_entry(updated)

    def delete(self, entry_id: str, expected_updated_at: str) -> MemoryEntry:
        """Hard-delete pending entries; soft-delete curated/approved entries."""
        entry = self.get_entry(entry_id)
        self._validate_occ(entry, expected_updated_at)

        if entry.state == MemoryState.DELETED:
            msg = "delete() not allowed from state deleted"
            raise TransitionError(msg)

        path = self._id_to_path.get(entry.id)
        if path is None:
            msg = f"Entry path missing for id: {entry.id}"
            raise NotFoundError(msg)

        if entry.state == MemoryState.PENDING:
            storage.delete_entry(path, memory_dir=self._memory_dir)
            self._id_to_path.pop(entry.id, None)
            self._entries = [current for current in self._entries if current.id != entry.id]
            return entry

        updated = entry.model_copy(update={"state": MemoryState.DELETED, "updated_at": self._now_iso()})
        return self._write_updated_entry(updated)

    def save(  # noqa: PLR0913
        self,
        title: str,
        content: str,
        categories: list[MemoryCategory],
        confidence: float,
        source_agent: str,
        scope_agents: list[str],
    ) -> MemoryEntry:
        """Create, persist, and return a new pending memory entry."""
        now = self._now_iso()
        entry = MemoryEntry(
            id=str(uuid4()),
            title=title,
            content=content,
            categories=categories,
            confidence=confidence,
            state=MemoryState.PENDING,
            outstanding_count=0,
            unremarkable_count=0,
            didnt_use_count=0,
            score=confidence,
            scope_agents=scope_agents,
            source_agent=source_agent,
            created_at=now,
            updated_at=now,
            approved_at=None,
        )
        return self._write_updated_entry(entry)

    def _validate_occ(self, entry: MemoryEntry, expected_updated_at: str) -> None:
        if entry.updated_at != expected_updated_at:
            msg = (
                "OCC check failed for entry "
                f"{entry.id}: expected updated_at {expected_updated_at!r}, got {entry.updated_at!r}"
            )
            raise ConcurrencyError(msg)

    def _write_updated_entry(self, entry: MemoryEntry) -> MemoryEntry:
        path = self._id_to_path.get(entry.id, self._memory_dir / f"{entry.id}.md")
        storage.write_entry(path, entry, memory_dir=self._memory_dir)
        self._id_to_path[entry.id] = path
        self._upsert_cache(entry)
        return entry

    def _upsert_cache(self, entry: MemoryEntry) -> None:
        for index, current in enumerate(self._entries):
            if current.id == entry.id:
                self._entries[index] = entry
                return
        self._entries.append(entry)

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    def _parse_iso_datetime(self, value: str) -> datetime:
        return datetime.fromisoformat(value)
