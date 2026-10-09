"""Memory engine with state transitions, OCC, and stat-signature caching."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, TypedDict
from uuid import uuid4

from owlbear_memory import storage
from owlbear_memory.errors import (
    ConcurrencyError,
    DuplicateEntryError,
    LifecycleRecoveryError,
    LifecycleRollbackFailure,
    NotFoundError,
    TransitionError,
    ValidationError,
)
from owlbear_memory.models import (
    AssessmentReceipt,
    AssessmentResult,
    ChallengeRecord,
    MemoryCategory,
    MemoryEntry,
    MemoryHealth,
    MemoryState,
    PurgePreview,
    PurgeResult,
)
from owlbear_memory.writer_lock import writer_lock

if TYPE_CHECKING:
    from collections.abc import Iterator

_LOGGER = logging.getLogger(__name__)

OUTSTANDING_BOOST = 0.1
UNREMARKABLE_PENALTY = 0.01
STALE_THRESHOLD = 50
_ASSESSMENT_TASK_ID_MAX_LENGTH = 128
_ASSESSMENT_RECEIPT_WINDOW = 20
_DUPLICATE_COPY_THRESHOLD = 2


@dataclass(slots=True)
class _DuplicateRepairContext:
    memory_dir: Path
    candidates: list[tuple[Path, MemoryEntry]]
    used_candidate_paths: set[Path]
    existing_ids: set[str]


def _read_entries_by_id(memory_dir: Path) -> tuple[int, dict[str, list[tuple[Path, MemoryEntry]]]]:
    parse_errors = 0
    entries_by_id: dict[str, list[tuple[Path, MemoryEntry]]] = {}
    for file_path in sorted(memory_dir.glob("*.md")):
        entry = storage.read_entry(file_path)
        if entry is None:
            parse_errors += 1
            continue
        entries_by_id.setdefault(entry.id, []).append((file_path, entry))
    return parse_errors, entries_by_id


def _select_canonical_copy(
    memory_dir: Path,
    entry_id: str,
    copies: list[tuple[Path, MemoryEntry]],
) -> tuple[Path, MemoryEntry]:
    latest_updated_at = max(datetime.fromisoformat(entry.updated_at) for _, entry in copies)
    newest_copies = [
        (path, entry) for path, entry in copies if datetime.fromisoformat(entry.updated_at) == latest_updated_at
    ]
    canonical_path = f"{entry_id}.md"
    named_copy = next(
        (copy for copy in newest_copies if copy[0].relative_to(memory_dir).as_posix() == canonical_path),
        None,
    )
    if named_copy is not None:
        return named_copy
    return min(newest_copies, key=lambda copy: copy[0].relative_to(memory_dir).as_posix())


def _relative_paths(memory_dir: Path, paths: list[Path]) -> tuple[str, ...]:
    return tuple(sorted(path.relative_to(memory_dir).as_posix() for path in paths))


def _matches_repair_copy(candidate: MemoryEntry, source: MemoryEntry, marked_title: str) -> bool:
    return (
        candidate.state == MemoryState.PENDING
        and candidate.approved_at is None
        and not candidate.challenges
        and not candidate.assessment_receipts
        and candidate.outstanding_count == 0
        and candidate.unremarkable_count == 0
        and candidate.didnt_use_count == 0
        and candidate.score == candidate.confidence
        and candidate.title == marked_title
        and candidate.content == source.content
        and candidate.categories == source.categories
        and candidate.confidence == source.confidence
        and candidate.source_agent == source.source_agent
        and candidate.scope_agents == source.scope_agents
        and candidate.created_at == source.created_at
    )


def _find_reusable_repair_copy(
    entry_id: str,
    source: MemoryEntry,
    marked_title: str,
    candidates: list[tuple[Path, MemoryEntry]],
    used_paths: set[Path],
) -> tuple[Path, MemoryEntry] | None:
    return next(
        (
            (path, entry)
            for path, entry in candidates
            if path not in used_paths and entry.id != entry_id and _matches_repair_copy(entry, source, marked_title)
        ),
        None,
    )


def _next_updated_at(previous_updated_at: str) -> str:
    now = datetime.now(UTC)
    previous = datetime.fromisoformat(previous_updated_at)
    if now <= previous:
        now = previous + timedelta(microseconds=1)
    return now.isoformat()


def _write_repair_copy(
    memory_dir: Path,
    source: MemoryEntry,
    marked_title: str,
    existing_ids: set[str],
) -> tuple[Path, MemoryEntry]:
    while True:
        new_id = str(uuid4())
        new_path = memory_dir / f"{new_id}.md"
        if new_id not in existing_ids and not new_path.exists():
            break

    repaired = source.model_copy(
        update={
            "id": new_id,
            "title": marked_title,
            "state": MemoryState.PENDING,
            "approved_at": None,
            "challenges": [],
            "assessment_receipts": [],
            "outstanding_count": 0,
            "unremarkable_count": 0,
            "didnt_use_count": 0,
            "score": source.confidence,
            "scope_agents": list(source.scope_agents),
            "updated_at": _next_updated_at(source.updated_at),
        }
    )
    storage.write_entry(new_path, repaired, memory_dir=memory_dir)
    existing_ids.add(new_id)
    return new_path, repaired


def _prepare_duplicate_group(
    entry_id: str,
    copies: list[tuple[Path, MemoryEntry]],
    canonical: tuple[Path, MemoryEntry],
    repair_context: _DuplicateRepairContext,
) -> tuple[str, tuple[str, ...], list[Path]]:
    canonical_path, canonical_entry = canonical
    duplicate_paths = [path for path, _ in copies if path != canonical_path]
    error_paths = _relative_paths(repair_context.memory_dir, [path for path, _ in copies])
    try:
        for old_path, old_entry in copies:
            if old_path == canonical_path or old_entry == canonical_entry:
                continue

            marked_title = f"[Recovered duplicate ID {entry_id}] {old_entry.title}"
            repair_copy = _find_reusable_repair_copy(
                entry_id,
                old_entry,
                marked_title,
                repair_context.candidates,
                repair_context.used_candidate_paths,
            )
            if repair_copy is None:
                repair_copy = _write_repair_copy(
                    repair_context.memory_dir,
                    old_entry,
                    marked_title,
                    repair_context.existing_ids,
                )
                repair_context.candidates.append(repair_copy)

            repair_context.used_candidate_paths.add(repair_copy[0])
            _LOGGER.warning(
                "Repaired duplicate UUID %s from %s as %s",
                entry_id,
                old_path.relative_to(repair_context.memory_dir).as_posix(),
                repair_copy[1].id,
            )
    except Exception as error:
        raise DuplicateEntryError(entry_id, error_paths) from error
    return entry_id, error_paths, duplicate_paths


def _prepare_duplicate_repairs(
    memory_dir: Path,
    entries_by_id: dict[str, list[tuple[Path, MemoryEntry]]],
) -> list[tuple[str, tuple[str, ...], list[Path]]]:
    canonical_copies = {
        entry_id: _select_canonical_copy(memory_dir, entry_id, copies) for entry_id, copies in entries_by_id.items()
    }
    scheduled_deletions = {
        path
        for entry_id, copies in entries_by_id.items()
        for path, _ in copies
        if path != canonical_copies[entry_id][0]
    }
    repair_context = _DuplicateRepairContext(
        memory_dir=memory_dir,
        candidates=[
            (path, entry)
            for copies in entries_by_id.values()
            for path, entry in copies
            if entry.state == MemoryState.PENDING and path not in scheduled_deletions
        ],
        used_candidate_paths=set(),
        existing_ids=set(entries_by_id),
    )
    plans: list[tuple[str, tuple[str, ...], list[Path]]] = []
    for entry_id, copies in entries_by_id.items():
        if len(copies) < _DUPLICATE_COPY_THRESHOLD:
            continue
        plans.append(
            _prepare_duplicate_group(
                entry_id,
                copies,
                canonical_copies[entry_id],
                repair_context,
            )
        )
    return plans


def _delete_duplicate_sources(
    memory_dir: Path,
    plans: list[tuple[str, tuple[str, ...], list[Path]]],
) -> None:
    for entry_id, error_paths, duplicate_paths in plans:
        for path in duplicate_paths:
            try:
                storage.delete_entry(path, memory_dir=memory_dir)
            except Exception as error:
                raise DuplicateEntryError(entry_id, error_paths) from error


def repair_duplicate_ids(memory_dir: Path | str) -> None:
    """Repair duplicate IDs; callers must hold writer_lock for ``memory_dir``."""
    directory = Path(memory_dir)
    _, entries_by_id = _read_entries_by_id(directory)
    if not any(len(copies) >= _DUPLICATE_COPY_THRESHOLD for copies in entries_by_id.values()):
        return
    plans = _prepare_duplicate_repairs(directory, entries_by_id)
    _delete_duplicate_sources(directory, plans)


def compute_score(confidence: float, outstanding_count: int, unremarkable_count: int) -> float:
    """Compute score from assessment counters."""
    return confidence + (outstanding_count * OUTSTANDING_BOOST) - (unremarkable_count * UNREMARKABLE_PENALTY)


def check_slot_efficiency(entry: MemoryEntry) -> bool:
    """Return True when didnt_use dominates outstanding+unremarkable slots."""
    denominator = max(entry.outstanding_count + entry.unremarkable_count, 1)
    return entry.didnt_use_count > (STALE_THRESHOLD * denominator)


class EditPayload(TypedDict, total=False):
    """Editable entry fields for MemoryEngine.edit()."""

    title: str
    content: str
    categories: list[MemoryCategory]
    confidence: float
    scope_agents: list[str]


class AgentRenameResult(TypedDict):
    """Counts from rewriting one agent identity."""

    entries_updated: int
    sources_updated: int
    scopes_updated: int


class AgentDeleteResult(TypedDict):
    """Counts from deleting one agent's memory references."""

    entries_deleted: int
    scopes_updated: int


class _StatSignatureCache:
    """Track entry-file metadata so unchanged stores skip unnecessary reparsing."""

    def __init__(self, memory_dir: Path) -> None:
        self._memory_dir = memory_dir
        self._last_signature: tuple[tuple[str, int, int, int], ...] | None = None

    def has_changed(self) -> bool:
        """Return True on first call or when an entry-file signature changes."""
        current = self._current_signature()
        if current == self._last_signature:
            return False
        self._last_signature = current
        return True

    def invalidate(self) -> None:
        """Force the next change check to request a reload."""
        self._last_signature = None

    def _current_signature(self) -> tuple[tuple[str, int, int, int], ...]:
        signature: list[tuple[str, int, int, int]] = []
        with os.scandir(self._memory_dir) as entries:
            for entry in entries:
                if not entry.name.endswith(".md"):
                    continue
                try:
                    metadata = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                signature.append((entry.name, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns))
        return tuple(sorted(signature))


class MemoryEngine:
    """Orchestrate markdown storage with state machine and OCC enforcement."""

    def __init__(
        self,
        memory_dir: Path | str = ".owlbear/memory",
        *,
        writer_lock_timeout: float = 30.0,
    ) -> None:
        self._memory_dir = Path(memory_dir)
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._cache = _StatSignatureCache(self._memory_dir)
        self._entries: list[MemoryEntry] = []
        self._id_to_path: dict[str, Path] = {}
        self._lock = RLock()
        self._writer_lock_timeout = writer_lock_timeout
        self.parse_errors = 0

    @contextmanager
    def _writer(self) -> Iterator[None]:
        with writer_lock(self._memory_dir, timeout=self._writer_lock_timeout), self._lock:
            try:
                repair_duplicate_ids(self._memory_dir)
                self._load_from_disk()
            except Exception:
                self._cache.invalidate()
                raise
            yield

    def load(self) -> list[MemoryEntry]:
        """Parse memory files from disk, skipping malformed files leniently."""
        with self._lock:
            try:
                return self._load()
            except Exception:
                self._cache.invalidate()
                raise

    def _load(self) -> list[MemoryEntry]:
        return self._load_from_disk()

    def _load_from_disk(self) -> list[MemoryEntry]:
        self.parse_errors, entries_by_id = _read_entries_by_id(self._memory_dir)
        by_id: dict[str, MemoryEntry] = {}
        id_to_path: dict[str, Path] = {}

        for entry_id, copies in entries_by_id.items():
            canonical_path, canonical_entry = _select_canonical_copy(self._memory_dir, entry_id, copies)
            by_id[entry_id] = canonical_entry
            id_to_path[entry_id] = canonical_path
            if len(copies) > 1:
                for path, _ in copies:
                    if path != canonical_path:
                        _LOGGER.warning("Duplicate UUID %s found in %s", entry_id, path)

        self._entries = list(by_id.values())
        self._id_to_path = id_to_path
        return list(self._entries)

    def get_entries(self) -> list[MemoryEntry]:
        """Return cached entries, reparsing only when an entry-file signature changes."""
        with self._lock:
            if self._cache.has_changed():
                try:
                    self._load()
                except Exception:
                    self._cache.invalidate()
                    raise
            return list(self._entries)

    def preview_purge(self, min_age_days: int = 30) -> PurgePreview:
        """Classify deleted entries without changing the filesystem."""
        with self._lock:
            eligible, too_recent = self._eligible_deleted(min_age_days)
            return PurgePreview(
                deleted_total=len(eligible) + len(too_recent),
                eligible=len(eligible),
                too_recent=len(too_recent),
            )

    def purge(self, min_age_days: int = 30) -> PurgeResult:
        """Best-effort remove age-eligible deleted entries."""
        with self._writer():
            eligible, too_recent = self._eligible_deleted(min_age_days)
            purged = 0
            failed = 0
            for entry in eligible:
                path = self._id_to_path.get(entry.id)
                if path is None:
                    failed += 1
                    continue
                try:
                    storage.delete_entry(path, memory_dir=self._memory_dir)
                except NotFoundError:
                    self._remove_from_cache(entry.id)
                    purged += 1
                except Exception:
                    failed += 1
                    _LOGGER.exception("Failed to purge deleted memory %s", entry.id)
                else:
                    self._remove_from_cache(entry.id)
                    purged += 1
            return PurgeResult(purged=purged, skipped=len(too_recent), failed=failed)

    def health(self) -> MemoryHealth:
        """Inspect memory files without changing loader state or files on disk."""
        with self._lock:
            paths_by_id: dict[str, list[str]] = {}
            unreadable_paths: list[str] = []

            for file_path in sorted(self._memory_dir.glob("*.md")):
                entry = storage.read_entry(file_path)
                relative_path = str(file_path.relative_to(self._memory_dir))
                if entry is None:
                    unreadable_paths.append(relative_path)
                    continue
                paths_by_id.setdefault(entry.id, []).append(relative_path)

            duplicate_paths = {entry_id: paths for entry_id, paths in paths_by_id.items() if len(paths) > 1}
            return MemoryHealth(unreadable_paths=unreadable_paths, duplicate_paths=duplicate_paths)

    def get_entry(self, entry_id: str) -> MemoryEntry:
        """Return one entry by ID or raise NotFoundError."""
        for entry in self.get_entries():
            if entry.id == entry_id:
                return entry
        msg = f"Entry not found: {entry_id}"
        raise NotFoundError(msg)

    def approve(
        self,
        entry_id: str,
        expected_updated_at: str | None = None,
        *,
        expected_revision: str | None = None,
    ) -> MemoryEntry:
        """Transition curated entry to approved after OCC check."""
        with self._writer():
            entry = self.get_entry(entry_id)
            self._validate_revision(
                entry,
                expected_updated_at=expected_updated_at,
                expected_revision=expected_revision,
            )

            if entry.state != MemoryState.CURATED:
                msg = f"approve() not allowed from state {entry.state}"
                raise TransitionError(msg)

            now = self._now_iso(entry.updated_at)
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
        with self._writer():
            entry = self.get_entry(entry_id)
            self._validate_occ(entry, expected_updated_at)

            if entry.state not in {MemoryState.CONTESTED, MemoryState.DISPUTED, MemoryState.STALE}:
                msg = f"resolve() not allowed from state {entry.state}"
                raise TransitionError(msg)

            now = self._now_iso(entry.updated_at)
            updated = entry.model_copy(
                update={
                    "state": MemoryState.APPROVED,
                    "approved_at": now,
                    "updated_at": now,
                    "challenges": [],
                    "didnt_use_count": 0 if entry.state == MemoryState.STALE else entry.didnt_use_count,
                }
            )
            return self._write_updated_entry(updated)

    def try_stale_transition(self, entry: MemoryEntry) -> MemoryEntry:
        """Transition eligible entries to stale when slot-efficiency predicate fires."""
        expected_updated_at = entry.updated_at
        with self._writer():
            entry = self.get_entry(entry.id)
            self._validate_occ(entry, expected_updated_at)
            if not check_slot_efficiency(entry):
                return entry

            if entry.state not in {MemoryState.APPROVED, MemoryState.CURATED, MemoryState.CONTESTED}:
                return entry

            updated = entry.model_copy(
                update={"state": MemoryState.STALE, "updated_at": self._now_iso(entry.updated_at)}
            )
            _LOGGER.info("Auto-transitioned entry %s to stale via slot-efficiency", entry.id)
            return self._write_updated_entry(updated)

    def edit(
        self,
        entry_id: str,
        fields: EditPayload,
        expected_updated_at: str | None = None,
        *,
        expected_revision: str | None = None,
    ) -> MemoryEntry:
        """Apply field updates with state-machine and OCC constraints."""
        with self._writer():
            entry = self.get_entry(entry_id)
            self._validate_revision(
                entry,
                expected_updated_at=expected_updated_at,
                expected_revision=expected_revision,
            )

            if entry.state == MemoryState.DELETED:
                msg = "edit() not allowed from state deleted"
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
            data["updated_at"] = self._now_iso(entry.updated_at)
            if "confidence" in fields:
                data["score"] = compute_score(
                    fields["confidence"],
                    entry.outstanding_count,
                    entry.unremarkable_count,
                )

            updated = MemoryEntry.model_validate(data)
            return self._write_updated_entry(updated)

    def delete(
        self,
        entry_id: str,
        expected_updated_at: str | None = None,
        *,
        expected_revision: str | None = None,
    ) -> MemoryEntry:
        """Hard-delete pending entries; soft-delete curated/approved entries."""
        with self._writer():
            entry = self.get_entry(entry_id)
            self._validate_revision(
                entry,
                expected_updated_at=expected_updated_at,
                expected_revision=expected_revision,
            )

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

            updated = entry.model_copy(
                update={"state": MemoryState.DELETED, "updated_at": self._now_iso(entry.updated_at)}
            )
            return self._write_updated_entry(updated)

    def rename_agent(self, old_name: str, new_name: str) -> AgentRenameResult:
        """Rewrite an agent identity in provenance and relevance scopes."""
        if not old_name.strip() or not new_name.strip() or old_name == new_name:
            msg = "old_name and new_name must be distinct non-empty agent names"
            raise ValidationError(msg)

        with self._writer():
            originals = self.get_entries()
            updated_entries: list[MemoryEntry] = []
            sources_updated = 0
            scopes_updated = 0
            for entry in originals:
                source_agent = new_name if entry.source_agent == old_name else entry.source_agent
                scope_agents = list(
                    dict.fromkeys(new_name if name == old_name else name for name in entry.scope_agents)
                )
                if source_agent == entry.source_agent and scope_agents == entry.scope_agents:
                    continue
                sources_updated += source_agent != entry.source_agent
                scopes_updated += scope_agents != entry.scope_agents
                updated_entries.append(
                    MemoryEntry.model_validate(
                        {
                            **entry.model_dump(),
                            "source_agent": source_agent,
                            "scope_agents": scope_agents,
                            "updated_at": self._now_iso(entry.updated_at),
                        }
                    )
                )

            self._write_agent_lifecycle_changes(originals, updated_entries, [])
            return AgentRenameResult(
                entries_updated=len(updated_entries),
                sources_updated=sources_updated,
                scopes_updated=scopes_updated,
            )

    def delete_agent(self, agent: str) -> AgentDeleteResult:
        """Remove an agent from scopes, preserving reviewed orphans as tombstones."""
        if not agent.strip():
            msg = "agent must not be empty"
            raise ValidationError(msg)

        with self._writer():
            originals = self.get_entries()
            updated_entries: list[MemoryEntry] = []
            deleted_entries: list[MemoryEntry] = []
            soft_deleted = 0
            scopes_updated = 0
            for entry in originals:
                if agent not in entry.scope_agents:
                    continue
                scope_agents = [name for name in entry.scope_agents if name != agent]
                if not scope_agents:
                    if entry.state == MemoryState.PENDING:
                        deleted_entries.append(entry)
                        continue

                    if entry.state == MemoryState.DELETED:
                        scopes_updated += 1
                    else:
                        soft_deleted += 1
                    updated_entries.append(
                        MemoryEntry.model_validate(
                            {
                                **entry.model_dump(),
                                "state": MemoryState.DELETED,
                                "scope_agents": scope_agents,
                                "updated_at": self._now_iso(entry.updated_at),
                            }
                        )
                    )
                    continue
                updated_entries.append(
                    MemoryEntry.model_validate(
                        {
                            **entry.model_dump(),
                            "scope_agents": scope_agents,
                            "updated_at": self._now_iso(entry.updated_at),
                        }
                    )
                )
                scopes_updated += 1

            self._write_agent_lifecycle_changes(originals, updated_entries, deleted_entries)
            return AgentDeleteResult(
                entries_deleted=len(deleted_entries) + soft_deleted,
                scopes_updated=scopes_updated,
            )

    def record_factually_wrong(
        self,
        entry_id: str,
        task_id: str,
        *,
        expected_revision: str,
    ) -> AssessmentResult:
        """Record a factually-wrong assessment via contested/disputed confirmation cycle."""
        with self._writer():
            entry = self.get_entry(entry_id)
            previous = self._existing_assessment_result(
                entry,
                task_id=task_id,
                expected_revision=expected_revision,
            )
            if previous is not None:
                return previous
            self._validate_assessment_task_id(task_id)

            if any(challenge.task_id == task_id for challenge in entry.challenges):
                return AssessmentResult(
                    entry=entry,
                    already_applied=True,
                    recorded_bucket="factually_wrong",
                )

            if entry.state in {MemoryState.APPROVED, MemoryState.CURATED}:
                next_state = MemoryState.CONTESTED
                initial_confirmation = True
            elif entry.state == MemoryState.CONTESTED:
                if not entry.challenges:
                    next_state = MemoryState.CONTESTED
                elif len(entry.challenges) == 1:
                    next_state = MemoryState.DISPUTED
                else:
                    msg = "record_factually_wrong() cannot add a third challenge"
                    raise TransitionError(msg)
                initial_confirmation = False
            else:
                msg = f"record_factually_wrong() not allowed from state {entry.state}"
                raise TransitionError(msg)

            write_timestamp = self._now_iso(entry.updated_at)
            challenge = ChallengeRecord(
                task_id=task_id,
                revision=expected_revision,
                recorded_at=write_timestamp,
            )
            challenges = [challenge] if initial_confirmation else [*entry.challenges, challenge]
            updates: dict[str, object] = {"state": next_state, "challenges": challenges}
            if initial_confirmation:
                updates["approved_at"] = None
            updated = entry.model_copy(update=updates)

            return self._write_assessment(
                entry,
                updated,
                AssessmentReceipt(task_id=task_id, revision=expected_revision, bucket="factually_wrong"),
                write_timestamp=write_timestamp,
            )

    def record_assessment(
        self,
        entry_id: str,
        bucket: str,
        *,
        task_id: str,
        expected_revision: str,
    ) -> AssessmentResult:
        """Record counter-based assessments and recompute score."""
        with self._writer():
            entry = self.get_entry(entry_id)
            previous = self._existing_assessment_result(
                entry,
                task_id=task_id,
                expected_revision=expected_revision,
            )
            if previous is not None:
                return previous
            self._validate_assessment_task_id(task_id)

            if entry.state not in {MemoryState.APPROVED, MemoryState.CURATED, MemoryState.CONTESTED}:
                msg = f"record_assessment() not allowed from state {entry.state}"
                raise TransitionError(msg)

            outstanding_count = entry.outstanding_count
            unremarkable_count = entry.unremarkable_count
            didnt_use_count = entry.didnt_use_count

            if bucket == "outstanding":
                outstanding_count += 1
            elif bucket == "unremarkable":
                unremarkable_count += 1
            elif bucket == "didnt_use":
                didnt_use_count += 1
            else:
                msg = "bucket must be one of: outstanding, unremarkable, didnt_use"
                raise ValidationError(msg)

            updated = entry.model_copy(
                update={
                    "outstanding_count": outstanding_count,
                    "unremarkable_count": unremarkable_count,
                    "didnt_use_count": didnt_use_count,
                    "score": compute_score(entry.confidence, outstanding_count, unremarkable_count),
                }
            )
            if check_slot_efficiency(updated):
                updated = updated.model_copy(update={"state": MemoryState.STALE})
                _LOGGER.info("Auto-transitioned entry %s to stale via slot-efficiency", entry.id)

            return self._write_assessment(
                entry,
                updated,
                AssessmentReceipt(task_id=task_id, revision=expected_revision, bucket=bucket),
            )

    @staticmethod
    def _validate_assessment_task_id(task_id: str) -> None:
        if (
            not isinstance(task_id, str)
            or not 1 <= len(task_id) <= _ASSESSMENT_TASK_ID_MAX_LENGTH
            or any(not "!" <= character <= "~" for character in task_id)
        ):
            msg = "task_id must be 1-128 printable ASCII characters without whitespace"
            raise ValidationError(msg)

    @staticmethod
    def _existing_assessment_result(
        entry: MemoryEntry,
        *,
        task_id: str,
        expected_revision: str,
    ) -> AssessmentResult | None:
        current_revision = entry.revision
        if current_revision != expected_revision:
            msg = (
                f"Entry {entry.id} changed since recall: expected revision {expected_revision!r}, "
                f"current revision {current_revision!r}; feedback was not applied"
            )
            raise ConcurrencyError(msg)

        for receipt in entry.assessment_receipts:
            if receipt.task_id == task_id and receipt.revision == expected_revision:
                return AssessmentResult(
                    entry=entry,
                    already_applied=True,
                    recorded_bucket=receipt.bucket,
                )
        return None

    def _write_assessment(
        self,
        original: MemoryEntry,
        updated: MemoryEntry,
        receipt: AssessmentReceipt,
        *,
        write_timestamp: str | None = None,
    ) -> AssessmentResult:
        updated = updated.model_copy(
            update={
                "assessment_receipts": [*original.assessment_receipts, receipt],
                "updated_at": write_timestamp if write_timestamp is not None else self._now_iso(original.updated_at),
            }
        )
        persisted = self._write_updated_entry(updated)
        return AssessmentResult(entry=persisted, already_applied=False, recorded_bucket=receipt.bucket)

    def save(  # noqa: PLR0913
        self,
        *,
        title: str,
        content: str,
        categories: list[MemoryCategory],
        confidence: float,
        source_agent: str,
        scope_agents: list[str],
    ) -> MemoryEntry:
        """Create, persist, and return a new pending memory entry."""
        with self._writer():
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

    def _validate_revision(
        self,
        entry: MemoryEntry,
        *,
        expected_updated_at: str | None,
        expected_revision: str | None,
    ) -> None:
        """Validate exactly one optimistic concurrency token before mutation."""
        if (expected_updated_at is None) == (expected_revision is None):
            msg = "exactly one of expected_updated_at or expected_revision must be provided"
            raise ValidationError(msg)

        if expected_revision is not None:
            current_revision = entry.revision
            if current_revision != expected_revision:
                msg = (
                    f"Revision check failed for entry {entry.id}: expected revision "
                    f"{expected_revision!r}, current revision {current_revision!r}"
                )
                raise ConcurrencyError(msg)
        elif expected_updated_at is not None:
            self._validate_occ(entry, expected_updated_at)

    def _validate_occ(self, entry: MemoryEntry, expected_updated_at: str) -> None:
        if entry.updated_at != expected_updated_at:
            msg = (
                "OCC check failed for entry "
                f"{entry.id}: expected updated_at {expected_updated_at!r}, got {entry.updated_at!r}"
            )
            raise ConcurrencyError(msg)

    def _eligible_deleted(self, min_age_days: int) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
        if not isinstance(min_age_days, int) or isinstance(min_age_days, bool) or min_age_days < 0:
            msg = "min_age_days must be a non-negative integer"
            raise ValidationError(msg)

        cutoff = datetime.now(UTC) - timedelta(days=min_age_days)
        eligible: list[MemoryEntry] = []
        too_recent: list[MemoryEntry] = []
        for entry in self.get_entries():
            if entry.state != MemoryState.DELETED:
                continue
            if self._parse_iso_datetime(entry.updated_at) <= cutoff:
                eligible.append(entry)
            else:
                too_recent.append(entry)
        return eligible, too_recent

    def _remove_from_cache(self, entry_id: str) -> None:
        self._id_to_path.pop(entry_id, None)
        self._entries = [entry for entry in self._entries if entry.id != entry_id]

    @staticmethod
    def _prepare_entry_for_write(entry: MemoryEntry) -> MemoryEntry:
        receipts = [receipt for receipt in entry.assessment_receipts if receipt.revision == entry.revision]
        receipts = receipts[-_ASSESSMENT_RECEIPT_WINDOW:]
        while receipts:
            prepared = entry.model_copy(update={"assessment_receipts": receipts})
            if storage.serialized_entry_size(prepared) <= storage.MAX_ENTRY_FILE_SIZE_BYTES:
                return prepared
            if len(receipts) == 1:
                msg = f"newest assessment receipt cannot fit within {storage.MAX_ENTRY_FILE_SIZE_BYTES} bytes"
                raise ValidationError(msg)
            receipts = receipts[1:]
        if entry.assessment_receipts:
            return entry.model_copy(update={"assessment_receipts": []})
        return entry

    def _write_updated_entry(self, entry: MemoryEntry) -> MemoryEntry:
        entry = self._prepare_entry_for_write(entry)
        path = self._id_to_path.get(entry.id, self._memory_dir / f"{entry.id}.md")
        storage.write_entry(path, entry, memory_dir=self._memory_dir)
        self._id_to_path[entry.id] = path
        self._upsert_cache(entry)
        return entry

    def _write_agent_lifecycle_changes(
        self,
        originals: list[MemoryEntry],
        updated_entries: list[MemoryEntry],
        deleted_entries: list[MemoryEntry],
    ) -> None:
        """Apply a multi-entry lifecycle change and report incomplete recovery."""
        original_paths = {entry.id: self._id_to_path[entry.id] for entry in originals}
        affected_ids = {entry.id for entry in (*updated_entries, *deleted_entries)}
        affected_entries = [entry for entry in originals if entry.id in affected_ids]
        prepared_entries = [self._prepare_entry_for_write(entry) for entry in updated_entries]
        try:
            for entry in prepared_entries:
                storage.write_entry(original_paths[entry.id], entry, memory_dir=self._memory_dir)
            for entry in deleted_entries:
                storage.delete_entry(original_paths[entry.id], memory_dir=self._memory_dir)
        except Exception as operation_error:
            rollback_errors: list[LifecycleRollbackFailure] = []
            for entry in affected_entries:
                try:
                    storage.write_entry(original_paths[entry.id], entry, memory_dir=self._memory_dir)
                except Exception as rollback_error:  # noqa: BLE001 - preserve every recovery failure.
                    rollback_errors.append(
                        LifecycleRollbackFailure(
                            entry_id=entry.id,
                            path=original_paths[entry.id],
                            error=rollback_error,
                        )
                    )

            cache_error: Exception | None = None
            recovery_status = "uncertain"
            try:
                reloaded_entries = self._load()
                recovery_status = self._lifecycle_recovery_status(
                    affected_entries,
                    reloaded_entries,
                    original_paths,
                )
            except Exception as reload_error:  # noqa: BLE001 - cache state is part of recovery diagnostics.
                cache_error = reload_error
                self._entries = []
                self._id_to_path = {}
                self._cache.invalidate()

            if rollback_errors or cache_error is not None or recovery_status != "complete":
                raise LifecycleRecoveryError(
                    operation_error,
                    tuple(rollback_errors),
                    cache_error,
                    recovery_status,
                ) from operation_error
            raise LifecycleRecoveryError(
                operation_error,
                (),
                None,
                recovery_status,
            ) from operation_error
        try:
            self._entries = self._load()
        except Exception:
            self._cache.invalidate()
            raise

    @staticmethod
    def _lifecycle_recovery_status(
        originals: list[MemoryEntry],
        reloaded_entries: list[MemoryEntry],
        original_paths: dict[str, Path],
    ) -> str:
        """Classify recovery from the reloaded entries and strict path verification."""
        try:
            reloaded_by_id = {entry.id: entry for entry in reloaded_entries}
            statuses = [
                MemoryEngine._lifecycle_recovery_entry_status(
                    original,
                    reloaded_by_id.get(original.id),
                    original_paths[original.id],
                )
                for original in originals
            ]
            if "uncertain" in statuses:
                return "uncertain"
            if "partial" in statuses:
                return "partial"
        except Exception:  # noqa: BLE001 - failed verification cannot establish disk state.
            return "uncertain"
        return "complete"

    @staticmethod
    def _lifecycle_recovery_entry_status(
        original: MemoryEntry,
        reloaded: MemoryEntry | None,
        path: Path,
    ) -> str:
        """Verify one affected entry and classify its recovered disk state."""
        try:
            verified = storage.read_entry_strict(path)
        except Exception:  # noqa: BLE001 - failed verification cannot establish disk state.
            try:
                if path.is_symlink():
                    return "uncertain"
                path.stat()
            except FileNotFoundError:
                return "partial"
            except OSError:
                return "uncertain"
            return "uncertain"

        if reloaded is None or reloaded != original or verified != original:
            return "partial"
        return "complete"

    def _upsert_cache(self, entry: MemoryEntry) -> None:
        for index, current in enumerate(self._entries):
            if current.id == entry.id:
                self._entries[index] = entry
                return
        self._entries.append(entry)

    def _now_iso(self, previous_updated_at: str | None = None) -> str:
        now = datetime.now(UTC)
        if previous_updated_at is not None:
            previous = datetime.fromisoformat(previous_updated_at)
            if now <= previous:
                now = previous + timedelta(microseconds=1)
        return now.isoformat()

    def _parse_iso_datetime(self, value: str) -> datetime:
        return datetime.fromisoformat(value)
