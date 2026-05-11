"""KanbanEngine — native read/write engine for the owlbear kanban board.

Provides KanbanEngine, a filesystem-backed implementation for listing,
reading, and writing kanban task files without invoking the kanban-md CLI.

Architecture:
  - Constructor loads BoardConfig via config_loader.load_config().
  - list_tasks() scans tasks_dir (or archive dir), applies filters,
    sorts by config-ranked field, and returns list[TaskSummary].
  - show_task() finds a single task file by ID and returns its Task.
    - create_task() allocates the next ID via scan-based allocate_next_id
        (scans active and archive filename prefixes; no config.next_id mutation),
        then writes the new task file inside the same lock scope.
  - edit_task() modifies task fields in-place; slug/filename never changes.
  - move_task() changes status; "archived" moves file to archive/.
  - claim_task() marks a task as claimed by this engine's agent_name; rejects
    blocked tasks and rival claims within the configured timeout window.
    - release_task() clears claimed_at unconditionally;
        appends a timestamped note to the body when ``note`` is provided.
  - board_config() returns a defensive copy of the current BoardConfig.
  - refresh_config() reloads config from disk, updating all derived state.
  - valid_transitions(status) returns the set of all statuses except the given one.
  - revision is a per-instance counter incremented on every write operation.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import random
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from owlbear_kanban import storage
from owlbear_kanban._duration import _parse_duration
from owlbear_kanban._locking import _exclusive_file_lock  # noqa: F401
from owlbear_kanban.activity_store import compact_activity_log, list_activity_events
from owlbear_kanban.agent_names import ADJECTIVES, NOUNS
from owlbear_kanban.body_parser import parse_body
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.corruption import (
    ERR_CORRUPT_DUPLICATE_ID,
    CorruptionError,
    detect_corruption,
)
from owlbear_kanban.dispatch import PRIORITY_RANK, STATUS_RANK
from owlbear_kanban.models import (
    ActivityCompactionResult,
    ActivityEvent,
    BoardConfig,
    CleanupResult,
    ConcurrencyError,
    ConfigError,
    KanbanError,
    MigrationRequiredError,
    SessionRecord,
    Task,
    TaskSummary,
    ValidationError,
)
from owlbear_kanban.storage import (
    make_task_filename,
    read_task,
    validate_path_containment,
    write_task,
)

_BLOCK_REASON_UNSET = object()
_PARENT_UNSET = object()
_MAX_CLAIM_STALE_RETRIES = 4
_MAX_BODY_BYTES = 500 * 1024
LOGGER = logging.getLogger(__name__)


if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_kanban.agent_view import AgentView


@dataclass
class WorkSession:
    """One claim cycle derived from the activity log."""

    task_id: int
    state: str
    agent: str
    started_at: str
    duration: float | None
    outcome: str | None


def _classify_end_work_state(detail: str) -> str:
    """Map an end_work detail string to canonical SessionRecord state values."""
    if detail.startswith("success:"):
        return "completed"
    if detail.startswith("reject:"):
        return "rejected"
    if detail.startswith("release"):
        return "released"
    # blocked:* and outcome=fail both map to the canonical blocked state.
    return "blocked"


def _classify_end_work_outcome(detail: str) -> str:
    """Map an end_work detail string to canonical SessionRecord outcome values."""
    if detail.startswith("success:"):
        return "success"
    if detail.startswith("reject:"):
        return "reject"
    if detail.startswith("release"):
        return "released"
    if detail.startswith("outcome=fail"):
        return "fail"
    return "block"


_CLOSE_ACTIONS: frozenset[str] = frozenset({"end_work", "release", "sweep-release"})


def _storage_module() -> object:
    """Return the live storage module, even if tests force a re-import."""
    return sys.modules.get("owlbear_kanban.storage", storage)


def _compute_duration(claim_ts: str, close_ts: str) -> float:
    """Return (close_dt - claim_dt).total_seconds(), normalising tz-naive timestamps to UTC."""
    claim_dt = datetime.fromisoformat(claim_ts)
    close_dt = datetime.fromisoformat(close_ts)
    if claim_dt.tzinfo is None:
        claim_dt = claim_dt.replace(tzinfo=UTC)
    if close_dt.tzinfo is None:
        close_dt = close_dt.replace(tzinfo=UTC)
    return (close_dt - claim_dt).total_seconds()


def _task_body_as_text(body: object) -> str:
    """Return a string body for task mutation operations."""
    return body if isinstance(body, str) else ""


def _validate_dispatch_rank_coverage(config: BoardConfig) -> None:
    """Ensure dispatch rank maps cover every configured priority and status."""
    unranked_priorities = [
        value for value in config.priorities if value not in PRIORITY_RANK
    ]
    if unranked_priorities:
        names = ", ".join(unranked_priorities)
        raise ConfigError(
            code="ERR_DISPATCH_PRIORITY_MISMATCH",
            user_message=(
                f"dispatch priority ranks missing configured values: {names}"
            ),
        )

    unranked_statuses = [value for value in config.statuses if value not in STATUS_RANK]
    if unranked_statuses:
        names = ", ".join(unranked_statuses)
        raise ConfigError(
            code="ERR_DISPATCH_STATUS_MISMATCH",
            user_message=(f"dispatch status ranks missing configured values: {names}"),
        )


def _restore_snapshot_if_unchanged(
    original: Task,
    expected_updated: str,
    kanban_dir: Path,
) -> None:
    """Best-effort rollback that never overwrites a newer concurrent update."""
    try:
        _storage_module().write_task_if_unchanged(original, expected_updated, kanban_dir)
    except ConcurrencyError as exc:
        if exc.code != "ERR_STALE":
            raise


def _state_from_age(ref_ts: str, timeout: timedelta, now: datetime) -> str:
    """Return 'running' or 'stuck' based on whether *ref_ts* is within *timeout* of *now*."""
    ref_dt = datetime.fromisoformat(ref_ts)
    if ref_dt.tzinfo is None:
        ref_dt = ref_dt.replace(tzinfo=UTC)
    return "running" if (now - ref_dt) < timeout else "stuck"


def _collect_task_sessions(
    task_id: int,
    events: list[dict],
    timeout: timedelta,
    now: datetime,
    sessions: list[SessionRecord],
) -> None:
    """Append SessionRecord entries for one task's event list into *sessions*."""
    open_claim_ts: str | None = None
    open_claim_task_status: str | None = None
    open_claim_agent: str | None = None
    last_activity_ts: str | None = None

    for event in events:
        action = str(event["action"])
        detail = str(event["detail"])
        ts = str(event["timestamp"])

        if action in {"claim", "start_work"}:
            if open_claim_ts is not None:
                # A new claim arrived without a close event (crash/restart scenario).
                # Apply the same age-based logic as the unclosed-session path: only
                # classify as "stuck" when last activity exceeds claim_timeout.
                ref_ts = last_activity_ts or open_claim_ts
                sessions.append(
                    SessionRecord(
                        task_id=task_id,
                        task_status_at_start=open_claim_task_status,
                        agent=open_claim_agent,
                        state=_state_from_age(ref_ts, timeout, now),
                        started_at=open_claim_ts,
                        ended_at=None,
                        outcome=None,
                        duration=None,
                        duration_s=None,
                    )
                )
            open_claim_ts = ts
            open_claim_task_status = event.get("task_status_at_start")
            open_claim_agent = detail
            last_activity_ts = ts
        elif action in _CLOSE_ACTIONS:
            if open_claim_ts is None:
                continue
            if action == "release":
                state = "released"
                outcome = "release"
            elif action == "sweep-release":
                state = "expired"
                outcome = "expired"
            else:
                state = _classify_end_work_state(detail)
                outcome = _classify_end_work_outcome(detail)
            duration = _compute_duration(open_claim_ts, ts)
            sessions.append(
                SessionRecord(
                    task_id=task_id,
                    task_status_at_start=open_claim_task_status,
                    agent=open_claim_agent,
                    state=state,
                    started_at=open_claim_ts,
                    ended_at=ts,
                    outcome=outcome,
                    duration=duration,
                    duration_s=duration,
                )
            )
            open_claim_ts = None
            open_claim_task_status = None
            open_claim_agent = None
            last_activity_ts = None
        elif open_claim_ts is not None:
            last_activity_ts = ts

    if open_claim_ts is not None:
        ref_ts = last_activity_ts or open_claim_ts
        sessions.append(
            SessionRecord(
                task_id=task_id,
                task_status_at_start=open_claim_task_status,
                agent=open_claim_agent,
                state=_state_from_age(ref_ts, timeout, now),
                started_at=open_claim_ts,
                ended_at=None,
                outcome=None,
                duration=None,
                duration_s=None,
            )
        )


_SESSION_FILTER_STATES: dict[str, frozenset[str]] = {
    "active": frozenset({"running", "stuck"}),
    "blocked-or-rejected": frozenset({"blocked", "rejected"}),
    # Compatibility alias for pre-Brief-C consumers.
    "failed-or-rejected": frozenset({"blocked", "rejected"}),
    "released": frozenset({"released"}),
}


def _validate_session_filter(session_filter: str) -> None:
    """Validate the list_sessions filter name."""
    if session_filter == "all" or session_filter in _SESSION_FILTER_STATES:
        return
    msg = f"Unsupported session filter: {session_filter}"
    raise ValueError(msg)


def _apply_session_filter(
    sessions: list[SessionRecord], session_filter: str
) -> list[SessionRecord]:
    """Return *sessions* filtered by *filter* name."""
    if session_filter == "all":
        return sessions
    allowed = _SESSION_FILTER_STATES[session_filter]
    return [s for s in sessions if s.state in allowed]


def _move_file(src: Path, dest: Path, *, no_overwrite: bool = False) -> None:
    """Move *src* to *dest*, preferring ``git mv`` when inside a git repo.

    Falls back to :meth:`Path.replace` when ``git`` is unavailable, the file
    is not tracked, the repo check fails, or ``git mv`` times out.

    ``stdin`` is explicitly closed (``DEVNULL``) to prevent the child process
    from inheriting the MCP stdin pipe — if ``git`` ever prompted for input it
    would steal bytes from the protocol stream and deadlock both sides.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "mv", str(src), str(dest)],  # noqa: S607
            capture_output=True,
            check=False,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            return
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # git not installed, or timed out (e.g. waiting for index.lock)
        pass

    if no_overwrite:
        # os.link() is atomic for destination creation and fails if dest exists,
        # avoiding overwrite when a collision appears after a pre-check.
        os.link(src, dest)
        src.unlink()
        return

    src.replace(dest)


class KanbanEngine:
    """Native kanban engine backed by filesystem task files.

    All mutating operations (create, edit, move, claim, release) optionally
    append an entry to ``{kanban_dir}/activity.jsonl``.

    Args:
        kanban_dir:    Root directory of the kanban board.
        activity_log:  When ``True``, append entries to ``activity.jsonl`` on
                       every mutation.  When ``None`` (default), logging is
                       enabled.
    """

    def __init__(  # noqa: C901
        self,
        kanban_dir: Path,
        *,
        activity_log: bool | None = None,
    ) -> None:
        self._kanban_dir = kanban_dir
        self._config: BoardConfig = load_config(kanban_dir)
        _validate_dispatch_rank_coverage(self._config)
        self._tasks_dir = kanban_dir / self._config.paths.tasks_dir
        self._archive_dir = kanban_dir / self._config.paths.archive_dir
        validate_path_containment(self._kanban_dir, self._tasks_dir)
        validate_path_containment(self._kanban_dir, self._archive_dir)
        self._agent_name: str = (
            f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"  # noqa: S311
        )
        effective_activity_log = activity_log if activity_log is not None else True
        self._activity_log_path: Path | None = (
            kanban_dir / "activity.jsonl" if effective_activity_log else None
        )
        self._revision: int = 0
        self._task_cache: dict[str, tuple[int, Task]] = {}
        self._archive_cache: dict[str, tuple[int, Task]] = {}
        self._id_to_filename: dict[int, str] = {}
        from owlbear_kanban.agent_view import AgentView  # noqa: PLC0415

        self._agent_view = AgentView(self)

        # AC-C47: migration gate — new-schema boards only (no 'version' field)
        # Legacy boards used claimed_by; new-schema boards must not have it.
        is_legacy_schema = bool(
            getattr(self._config, "version", None)
            or (self._config.model_extra or {}).get("version")
        )
        if not is_legacy_schema and self._tasks_dir.exists():
            for p in self._tasks_dir.glob("*.md"):
                try:
                    content = p.read_text(encoding="utf-8")
                except OSError:
                    continue
                # Fast check: look for claimed_by in frontmatter
                if "claimed_by:" not in content:
                    continue
                # Verify it's in the frontmatter (not body)
                lines = content.splitlines()
                if not lines or lines[0].strip() != "---":
                    continue
                closing = None
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        closing = i
                        break
                if closing is None:
                    continue
                frontmatter_text = "\n".join(lines[1:closing])
                try:
                    frontmatter = YAML(typ="safe").load(frontmatter_text) or {}
                except YAMLError:
                    continue

                if not isinstance(frontmatter, dict) or "claimed_by" not in frontmatter:
                    continue

                claimed_by = frontmatter["claimed_by"]
                is_cleared = claimed_by is None or (
                    isinstance(claimed_by, str) and not claimed_by.strip()
                )
                if is_cleared:
                    continue

                raise MigrationRequiredError(
                    code="ERR_MIGRATION_REQUIRED",
                    user_message="board has legacy claimed_by fields — run: uv run kanban-migrate",
                )

    @property
    def agent_name(self) -> str:
        """Session-stable agent name generated once per engine instance."""
        return self._agent_name

    @property
    def revision(self) -> int:
        """Per-instance write counter; incremented on every mutating operation."""
        return self._revision

    @property
    def tasks_dir(self) -> Path:
        """Configured tasks directory for the active board."""
        return self._tasks_dir

    @property
    def kanban_dir(self) -> Path:
        """Root kanban directory for the active board."""
        return self._kanban_dir

    # ------------------------------------------------------------------
    # Config-derived rank maps
    # ------------------------------------------------------------------

    def _priority_rank(self) -> dict[str, int]:
        return {p: i for i, p in enumerate(self._config.pipeline.priorities)}

    def _status_rank(self) -> dict[str, int]:
        statuses = self._config.pipeline.statuses
        return {s: i for i, s in enumerate(statuses)}

    # ------------------------------------------------------------------
    # Config management
    # ------------------------------------------------------------------

    def board_config(self) -> BoardConfig:
        """Return a defensive copy of the current cached :class:`BoardConfig`.

        The returned object is a deep ``model_copy(deep=True)`` — mutating it
        (including nested lists and dicts) does not affect engine state.
        """
        return self._config.model_copy(deep=True)

    def agent_view(self) -> AgentView:
        """Return the cached agent-facing view facade."""
        return self._agent_view

    def refresh_config(self) -> None:
        """Reload config from disk and update all derived state.

        After calling this method, ``_status_rank()`` and ``_priority_rank()``
        use the newly loaded config values. Also updates ``_tasks_dir`` and
        ``_archive_dir`` to reflect any tasks_dir change in config. All three
        caches — ``_task_cache``, ``_archive_cache``, and ``_id_to_filename``
        — are cleared so the next ``list_tasks()`` call performs a full cold
        scan and rebuilds the id→filename index.
        """
        refreshed_config = load_config(self._kanban_dir)
        _validate_dispatch_rank_coverage(refreshed_config)

        self._config = refreshed_config
        self._tasks_dir = self._kanban_dir / refreshed_config.paths.tasks_dir
        self._archive_dir = self._kanban_dir / refreshed_config.paths.archive_dir
        validate_path_containment(self._kanban_dir, self._tasks_dir)
        validate_path_containment(self._kanban_dir, self._archive_dir)
        self._task_cache = {}
        self._archive_cache = {}
        self._id_to_filename = {}

    def valid_transitions(self, status: str) -> set[str]:
        """Return the set of all configured statuses except *status*.

        Args:
            status: The current status to exclude from the result.

        Returns:
            Set of valid target status names.

        Raises:
            ValueError: *status* is not a configured status.
        """
        valid_statuses = set(self._config.pipeline.statuses)
        if status not in valid_statuses:
            msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
            raise ValueError(msg)
        return valid_statuses - {status}

    @staticmethod
    def _dep_effect_from_archival_reason(reason: str | None) -> str:
        """Map archival reason to dependency effect category.

        Returns ``ok``, ``redirect``, or ``blocked``.
        """
        if reason in {"dropped", "wontfix"}:
            return "blocked"
        if reason in {"deprecated", "duplicate"}:
            return "redirect"
        return "ok"

    def _compute_dep_status(
        self,
        task: Task,
        *,
        active_ids: set[int],
        archived_reasons: dict[int, str | None],
    ) -> str | None:
        """Compute dep_status from dependency IDs and archive metadata.

        Precedence follows Brief B: blocked > redirect > ok.
        """
        deps = task.depends_on or []
        if not deps:
            return None

        status = "ok"
        for dep_id in deps:
            if dep_id in active_ids:
                continue
            if dep_id not in archived_reasons:
                return "blocked"

            dep_effect = self._dep_effect_from_archival_reason(archived_reasons[dep_id])
            if dep_effect == "blocked":
                return "blocked"
            if dep_effect == "redirect":
                status = "redirect"

        return status

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def list_tasks(  # noqa: PLR0912, PLR0913, PLR0915, C901
        self,
        *,
        status: str = "",
        tag: str = "",
        priority: str = "",
        parent: int | None = None,
        search: str = "",
        sort: str = "",
        unclaimed: bool = False,
        archived: bool = False,
        limit: int = 0,
        reverse: bool = False,
        blocked: bool | None = None,
    ) -> list[TaskSummary]:
        """Return tasks matching the given filters.

        Args:
            status:    Only return tasks with this status.  Empty = no filter.
            tag:       Only return tasks that include this tag.  Empty = no filter.
            priority:  Only return tasks with this priority.  Empty = no filter.
            parent:    Only return tasks whose parent exactly equals this task ID.
            search:    Case-insensitive substring match on title and body.
            sort:      Field to sort by: id, title, status, priority, created, updated.
            unclaimed: When True, only tasks with no claimed_at value (not claimed).
            archived:  When True, read from archive/ instead of tasks_dir.
            limit:     Cap on results (0 = unlimited).
            reverse:   When True, reverse the sort order.
            blocked:   True = only blocked; False = only unblocked; None = all.

        Returns:
            Filtered, sorted list of :class:`TaskSummary` objects.
        """
        cache = self._archive_cache if archived else self._task_cache
        source_dir = self._archive_dir if archived else self._tasks_dir
        tasks: list[Task] = []
        archive_ids: set[int] = set()
        archived_reasons: dict[int, str | None] = {}
        if not archived and self._archive_dir.exists():
            for archive_path in self._archive_dir.glob("*.md"):
                archive_stem = archive_path.stem
                archive_head = archive_stem.split("-", 1)[0]
                if archive_head.isdigit():
                    archive_id = int(archive_head)
                    archive_ids.add(archive_id)
                    try:
                        archive_task = read_task(archive_path, config=self._config)
                    except (FileNotFoundError, ValueError, KeyError):
                        archived_reasons[archive_id] = None
                    except CorruptionError:
                        archived_reasons[archive_id] = None
                    else:
                        archived_reasons[archive_id] = archive_task.archival_reason
        seen: set[str] = set()
        try:
            scan_iter = os.scandir(source_dir)
        except FileNotFoundError:
            cache.clear()
            return []
        with scan_iter:
            for entry in scan_iter:
                if not entry.name.endswith(".md"):
                    continue
                seen.add(entry.name)
                mtime_ns: int = entry.stat().st_mtime_ns
                if entry.name in cache and cache[entry.name][0] == mtime_ns:
                    tasks.append(cache[entry.name][1])
                else:
                    path = source_dir / entry.name
                    if not archived:
                        corruption = detect_corruption(path, self._config)
                        if corruption is not None and not (
                            corruption.code == "ERR_CORRUPT_MISSING_FIELD"
                            and corruption.detail
                            == "forbidden field claimed_by present"
                        ):
                            cache.pop(entry.name, None)
                            continue
                    try:
                        task = read_task(path, config=self._config)
                    except FileNotFoundError:
                        cache.pop(entry.name, None)
                        continue
                    except (ValueError, KeyError):
                        continue
                    except CorruptionError:
                        continue
                    cache[entry.name] = (mtime_ns, task)
                    if not archived and task.id in archive_ids:
                        # AC-C19 mode 7: if an archive copy exists, skip tasks/ copy.
                        cache.pop(entry.name, None)
                        continue
                    # AC-C19: skip mode 8 (invalid status) silently
                    _valid_statuses = set(self._config.pipeline.statuses)
                    if task.status not in _valid_statuses | {"archived"}:
                        continue
                    tasks.append(task)
        for name in list(cache):
            if name not in seen:
                del cache[name]

        # AC-C20: detect duplicate IDs (mode 2) — raise immediately
        if not archived:
            id_seen: dict[int, str] = {}
            for task in tasks:
                if task.id in id_seen:
                    raise CorruptionError(
                        code=ERR_CORRUPT_DUPLICATE_ID,
                        detail=f"task id={task.id} appears in multiple files",
                    )
                id_seen[task.id] = task.title

        if not archived:
            self._id_to_filename = dict(
                sorted(
                    (cached_task.id, filename)
                    for filename, (_, cached_task) in self._task_cache.items()
                )
            )

        all_active_ids = {task.id for task in tasks}

        # --- Filters ---
        if status:
            tasks = [t for t in tasks if t.status == status]
        if tag:
            tasks = [t for t in tasks if tag in t.tags]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if parent is not None:
            tasks = [t for t in tasks if t.parent == parent]
        if blocked is not None:
            tasks = [t for t in tasks if t.blocked is blocked]
        if unclaimed:
            tasks = [t for t in tasks if t.claimed_at is None]
        if search:
            needle = search.lower()
            tasks = [
                t
                for t in tasks
                if needle in t.title.lower() or needle in t.body.lower()
            ]

        # --- Sort ---
        if sort:
            if sort == "priority":
                rank = self._priority_rank()
                tasks.sort(key=lambda t: rank.get(t.priority, 999))
            elif sort == "status":
                rank = self._status_rank()
                tasks.sort(key=lambda t: rank.get(t.status, 999))
            elif sort == "id":
                tasks.sort(key=lambda t: t.id)
            elif sort == "title":
                tasks.sort(key=lambda t: t.title)
            elif sort == "created":
                tasks.sort(key=lambda t: (datetime.fromisoformat(t.created), t.id))
            elif sort == "updated":
                tasks.sort(key=lambda t: (datetime.fromisoformat(t.updated), t.id))

        if reverse:
            tasks.reverse()

        if limit > 0:
            tasks = tasks[:limit]

        if archived:
            return [TaskSummary.model_validate(t.model_dump()) for t in tasks]

        summaries: list[TaskSummary] = []
        for task in tasks:
            projected = task.model_dump()
            projected["dep_status"] = self._compute_dep_status(
                task,
                active_ids=all_active_ids,
                archived_reasons=archived_reasons,
            )
            summaries.append(TaskSummary.model_validate(projected))
        return summaries

    def show_task(self, task_id: str) -> Task:
        """Return the :class:`Task` for a single task by its string ID.

        When a matching file exists in both the ``archive/`` and ``tasks/``
        directories, the archived copy takes precedence.  The internal filename
        index is evicted on any archive-wins resolution so subsequent calls
        return a fresh lookup.

        Args:
            task_id: The numeric task ID as a string (e.g. ``"42"``).

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md`` in tasks_dir or
            archive_dir.
        """
        try:
            int_id = int(task_id)
        except ValueError:
            int_id = None

        if int_id is not None and int_id in self._id_to_filename:
            filename = self._id_to_filename[int_id]
            path = self._tasks_dir / filename
            try:
                mtime_ns = path.stat().st_mtime_ns
            except FileNotFoundError:
                self._task_cache.pop(filename, None)
                del self._id_to_filename[int_id]
                archive_path = self._archive_dir / filename
                if archive_path.exists():
                    archived_task = read_task(archive_path, config=self._config)
                    self._task_cache[filename] = (
                        archive_path.stat().st_mtime_ns,
                        archived_task,
                    )
                    return archived_task

            archive_path = self._archive_dir / filename
            if archive_path.exists():
                self._task_cache.pop(filename, None)
                del self._id_to_filename[int_id]
                return read_task(archive_path, config=self._config)

            if (
                filename in self._task_cache
                and self._task_cache[filename][0] == mtime_ns
            ):
                return self._task_cache[filename][1]
            task = read_task(path, config=self._config)
            self._task_cache[filename] = (mtime_ns, task)
            return task

        archive_matches = list(self._archive_dir.glob(f"{task_id}-*.md"))
        if archive_matches:
            return read_task(archive_matches[0], config=self._config)

        matches = list(self._tasks_dir.glob(f"{task_id}-*.md"))
        if matches:
            return read_task(matches[0], config=self._config)

        msg = f"Task {task_id!r} not found in {self._tasks_dir} or {self._archive_dir}"
        raise FileNotFoundError(msg)

    @staticmethod
    def _required_sections_passes(body: str, sections: list[str]) -> bool:
        if not sections:
            return True
        present = {
            part.heading.strip().casefold()
            for part in parse_body(body)
            if part.heading is not None and part.heading.strip()
        }
        required = {
            section.strip().lstrip("#").strip().casefold()
            for section in sections
            if section.strip()
        }
        return required.issubset(present)

    def task_exists(self, task_id: int) -> bool:
        """Return True when a task exists in active or archived storage."""
        try:
            self.show_task(str(task_id))
        except FileNotFoundError:
            return False
        return True

    def _has_archival_cycle(self, root_task_id: int, refs: list[int]) -> bool:
        """Return True when new archival refs would introduce a cycle."""

        def visits_root(task_id: int, seen: set[int]) -> bool:
            if task_id in seen:
                return False
            seen.add(task_id)
            try:
                task = self.show_task(str(task_id))
            except FileNotFoundError:
                return False
            for dep_id in task.archival_refs:
                if dep_id == root_task_id:
                    return True
                if visits_root(dep_id, seen):
                    return True
            return False

        return any(visits_root(ref_id, set()) for ref_id in refs)

    def validate_body_size(self, body: str) -> None:
        """Validate the 500 KB task body hard limit."""
        if len(body.encode("utf-8")) > _MAX_BODY_BYTES:
            raise ValidationError(
                code="ERR_BODY_TOO_LARGE",
                user_message="Task body exceeds 500 KB",
            )

    def validate_archival(
        self,
        *,
        task_id: int,
        archival_reason: str | None,
        archival_refs: list[int],
        can_mark_completed: bool,
        config: BoardConfig,
    ) -> None:
        """Validate archival reason/ref matrix and reference integrity."""
        if not archival_reason:
            raise ValidationError(
                code="ERR_ARCHIVAL_REASON_REQUIRED",
                user_message="archival_reason is required when status='archived'",
            )
        if archival_reason not in config.policy.archival_reasons:
            raise ValidationError(
                code="ERR_ARCHIVAL_REASON_INVALID",
                user_message=(
                    "archival_reason must be one of "
                    f"{sorted(config.policy.archival_reasons)}"
                ),
            )
        if archival_reason in {"deprecated", "duplicate"} and not archival_refs:
            raise ValidationError(
                code="ERR_ARCHIVAL_REFS_REQUIRED",
                user_message=(
                    f"archival_refs required for archival_reason='{archival_reason}'"
                ),
            )
        if archival_reason in {"completed", "dropped", "wontfix"} and archival_refs:
            raise ValidationError(
                code="ERR_ARCHIVAL_REFS_FORBIDDEN",
                user_message=(
                    f"archival_refs forbidden for archival_reason='{archival_reason}'"
                ),
            )
        if archival_reason == "completed" and not can_mark_completed:
            raise ValidationError(
                code="ERR_COMPLETED_REQUIRES_DONE",
                user_message="archival_reason='completed' requires terminal status",
            )
        for ref_id in archival_refs:
            if ref_id == task_id:
                raise ValidationError(
                    code="ERR_ARCHIVAL_REF_SELF",
                    user_message="archival_refs cannot include the task itself",
                )
            if not self.task_exists(ref_id):
                raise ValidationError(
                    code="ERR_ARCHIVAL_REF_MISSING",
                    user_message=f"archival reference task '{ref_id}' not found",
                )
        if self._has_archival_cycle(task_id, archival_refs):
            raise ValidationError(
                code="ERR_ARCHIVAL_REF_CYCLE",
                user_message="archival_refs would introduce a cycle",
            )

    def validate_status_predicate(
        self,
        *,
        target_status: str,
        body: str,
        config: BoardConfig,
    ) -> None:
        """Validate status predicate rules for a target status."""
        if target_status == "archived":
            return

        predicate_spec = config.policy.status_predicates.get(target_status)
        if not isinstance(predicate_spec, dict):
            return
        if predicate_spec.get("type") != "required_sections":
            return

        sections = predicate_spec.get("sections")
        required = (
            [str(section) for section in sections] if isinstance(sections, list) else []
        )
        if not self._required_sections_passes(body, required):
            raise ValidationError(
                code="ERR_PREDICATE_FAILED",
                user_message=(
                    f"Task body does not satisfy predicate for status '{target_status}'"
                ),
            )

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create_task(  # noqa: PLR0913, PLR0915
        self,
        title: str,
        *,
        body: str = "",
        tags: list[str] | None = None,
        priority: str = "",
        status: str = "",
        parent: int | None = None,
        depends_on: list[int] | None = None,
    ) -> Task:
        """Allocate a new task ID from board files, then write a new task file.

        ID allocation is delegated to ``storage.allocate_next_id()`` in callback
        mode so allocation scan and task write happen in one lock scope. This
        path does not read or write ``config.next_id``.

        Args:
            title:      Task title (used to generate the filename slug).
            body:       Initial markdown body.
            tags:       List of tag strings.
            priority:   Task priority; defaults to config defaults.priority.
            status:     Task status; defaults to config defaults.status.
            parent:     Optional parent task ID.
            depends_on: Optional list of dependency task IDs.

        Returns:
            The newly created :class:`Task`.

        Raises:
            ValueError: ``status`` or ``priority`` is not a valid configured value.
            PermissionError: A post-write config reload yields a ``tasks_dir`` or
                ``archive_dir`` path that escapes the board root (symlink escape).
                The cached engine state is not mutated when this is raised.
        """
        config: BoardConfig = load_config(self._kanban_dir)

        if status:
            valid_statuses = set(config.pipeline.statuses)
            if status not in valid_statuses:
                msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
                raise ValueError(msg)
        if priority and priority not in config.pipeline.priorities:
            msg = f"Invalid priority {priority!r}. Valid options: {config.pipeline.priorities}"
            raise ValueError(msg)

        self.validate_body_size(body)

        if parent is not None and not self.task_exists(parent):
            raise ValidationError(
                code="ERR_PARENT_NOT_FOUND",
                user_message=f"Parent task '{parent}' not found",
            )

        dep_ids = depends_on or []
        missing_dep = next(
            (dep_id for dep_id in dep_ids if not self.task_exists(dep_id)),
            None,
        )
        if missing_dep is not None:
            raise ValidationError(
                code="ERR_DEP_NOT_FOUND",
                user_message=f"Dependency task '{missing_dep}' not found",
            )

        entry_status = status or config.pipeline.entry_status
        self.validate_status_predicate(
            target_status=entry_status,
            body=body,
            config=config,
        )

        record: Task | None = None
        created_task_path: Path | None = None

        def _write_new_task(task_id: int) -> None:
            nonlocal record, created_task_path
            now = datetime.now(tz=UTC).isoformat()
            created_task = Task(
                id=task_id,
                title=title,
                status=entry_status,
                priority=priority or config.pipeline.default_priority,
                created=now,
                updated=now,
                body=body,
                tags=list(tags) if tags else [],
                parent=parent,
                depends_on=list(depends_on) if depends_on else [],
            )
            filename = make_task_filename(task_id, title)
            task_path = self._tasks_dir / filename
            validate_path_containment(self._tasks_dir, task_path)
            write_task(created_task, self._kanban_dir)
            record = created_task
            created_task_path = task_path

        _storage_module().allocate_next_id(self._kanban_dir, write_task_fn=_write_new_task)
        if record is None:
            msg = "create_task failed to construct task record"
            raise RuntimeError(msg)

        created_record = record
        reloaded_config = load_config(self._kanban_dir)
        reloaded_tasks_dir = self._kanban_dir / reloaded_config.paths.tasks_dir
        reloaded_archive_dir = self._kanban_dir / reloaded_config.paths.archive_dir
        validate_path_containment(self._kanban_dir, reloaded_tasks_dir)
        validate_path_containment(self._kanban_dir, reloaded_archive_dir)

        self._config = reloaded_config
        self._tasks_dir = reloaded_tasks_dir
        self._archive_dir = reloaded_archive_dir

        try:
            self._emit_event(
                action="create_task",
                task_id=created_record.id,
                detail=created_record.title,
                task_status_at_start=created_record.status,
            )
        except OSError:
            with contextlib.suppress(Exception):
                if created_task_path is not None and created_task_path.exists():
                    created_task_path.unlink()
                self._task_cache.pop(created_task_path.name, None)
                self._id_to_filename.pop(created_record.id, None)
            raise

        self._revision += 1
        return created_record

    def edit_task(  # noqa: PLR0912, PLR0913, PLR0915, C901
        self,
        task_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        parent: int | None | object = _PARENT_UNSET,
        add_tags: list[str] | None = None,
        remove_tags: list[str] | None = None,
        add_deps: list[int] | None = None,
        remove_deps: list[int] | None = None,
        blocked: bool | None = None,
        block_reason: str | None = None,
        append_body: str | None = None,
        timestamp: bool = False,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
        expected_updated: str | None = None,
        source: str = "engine",
    ) -> Task:
        """Modify fields on a task in-place; filename (slug) is never changed.

        Args:
            task_id:     Numeric task ID as a string.
            title:       Replace task title.
            body:        Replace task body; ``None`` means no change, ``""`` clears the
                         body, non-empty text replaces it.
            priority:    Replace priority.
            status:      Replace status.
            parent:      Replace parent ID.
            add_tags:    Tags to add (merged with existing).
            remove_tags: Tags to remove.
            add_deps:    Dependency IDs to add.
            remove_deps: Dependency IDs to remove.
            blocked:     Set blocked flag.
            block_reason: Set block reason (cleared when blocked=False).
            append_body: Text appended to existing body.
            timestamp:   When True, prepend ``[[YYYY-MM-DD]]`` to append_body.
            archival_reason: Replace archival reason when provided.
            archival_refs:   Replace archival reference IDs when provided.
            expected_updated: Optional OCC token for compare-and-swap writes.
            source:      Activity event source label (agent, cockpit, engine).

        Returns:
            Updated :class:`Task`.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
            ValueError: ``status`` or ``priority`` is not a valid configured value.
        """
        if status is not None:
            valid_statuses = set(self._config.pipeline.statuses)
            if status not in valid_statuses:
                msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
                raise ValueError(msg)
        if priority is not None and priority not in self._config.pipeline.priorities:
            msg = f"Invalid priority {priority!r}. Valid options: {self._config.pipeline.priorities}"
            raise ValueError(msg)

        if body is not None:
            self.validate_body_size(body)

        if parent is not _PARENT_UNSET and parent is not None and not self.task_exists(parent):
            raise ValidationError(
                code="ERR_PARENT_NOT_FOUND",
                user_message=f"Parent task '{parent}' not found",
            )

        for dep_id in add_deps or []:
            if not self.task_exists(dep_id):
                raise ValidationError(
                    code="ERR_DEP_NOT_FOUND",
                    user_message=f"Dependency task '{dep_id}' not found",
                )

        task_path = self._find_task_path(
            task_id, self._tasks_dir, include_archive_fallback=True
        )
        target_dir = task_path.parent
        record = read_task(task_path, config=self._config)
        original = record.model_copy(deep=True)

        if title is not None:
            record.title = title
        if body is not None:
            record.body = body
        if priority is not None:
            record.priority = priority
        if status is not None:
            record.status = status
        if parent is not _PARENT_UNSET:
            record.parent = parent

        if add_tags:
            for t in add_tags:
                if t not in record.tags:
                    record.tags.append(t)
        if remove_tags:
            record.tags = [t for t in record.tags if t not in remove_tags]

        if add_deps:
            for d in add_deps:
                if d not in record.depends_on:
                    record.depends_on.append(d)
        if remove_deps:
            record.depends_on = [d for d in record.depends_on if d not in remove_deps]

        if blocked is not None:
            record.blocked = blocked
            if not blocked:
                record.block_reason = None
        if block_reason is not None:
            record.block_reason = block_reason

        if append_body is not None:
            prefix = ""
            if timestamp:
                date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
                prefix = f"[[{date_str}]]\n"
            record.body = record.body + "\n" + prefix + append_body
            self.validate_body_size(record.body)

        if archival_reason is not None:
            record.archival_reason = archival_reason
        if archival_refs is not None:
            record.archival_refs = list(archival_refs)

        record.updated = datetime.now(tz=UTC).isoformat()

        if expected_updated is not None:
            storage.write_task_if_unchanged(
                record,
                expected_updated,
                self._kanban_dir,
            )
        else:
            write_task(record, self._kanban_dir, target_dir=target_dir)

        try:
            self._emit_event("edit", record.id, "task edited", source=source)
        except OSError:
            with contextlib.suppress(Exception):
                _restore_snapshot_if_unchanged(
                    original,
                    record.updated,
                    self._kanban_dir,
                )
            raise
        self._revision += 1
        return record

    def move_task(  # noqa: PLR0913, PLR0915
        self,
        task_id: str,
        status: str,
        *,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
        expected_updated: str | None = None,
        source: str = "engine",
    ) -> Task:
        """Change the status of a task; "archived" moves the file to archive/.

        Args:
            task_id: Numeric task ID as a string.
            status:  Target status name, or ``"archived"`` to archive the task.
            archival_reason: Optional archive reason persisted when archiving.
            archival_refs: Optional archive reference IDs persisted when archiving.
            expected_updated: Optional OCC token for compare-and-swap writes.
            source: Activity event source label (agent, cockpit, engine).

        Returns:
            Updated :class:`Task`.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
            ValueError:        ``status`` is not valid and is not ``"archived"``.
        """
        valid_statuses = set(self._config.pipeline.statuses)
        if status != "archived" and status not in valid_statuses:
            msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
            raise ValueError(msg)

        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path, config=self._config)
        original = record.model_copy(deep=True)
        old_status = record.status
        archived = False
        dest = self._archive_dir / task_path.name

        if status == "archived":
            self.validate_archival(
                task_id=record.id,
                archival_reason=archival_reason,
                archival_refs=archival_refs or [],
                can_mark_completed=record.status
                == self._config.pipeline.terminal_status,
                config=self._config,
            )
        elif archival_reason is not None or archival_refs is not None:
            raise ValidationError(
                code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
                user_message="archival fields are only allowed on archived tasks",
            )

        body = record.body if isinstance(record.body, str) else ""
        self.validate_status_predicate(
            target_status=status,
            body=body,
            config=self._config,
        )

        if status == "archived":
            self._archive_dir.mkdir(parents=True, exist_ok=True)
            record.status = "archived"
            record.claimed_at = None
            record.archival_reason = archival_reason
            record.archival_refs = (
                list(archival_refs) if archival_refs is not None else []
            )
            record.updated = datetime.now(tz=UTC).isoformat()
            if expected_updated is not None:
                storage.write_task_if_unchanged(
                    record,
                    expected_updated,
                    self._kanban_dir,
                )
            else:
                write_task(record, self._kanban_dir)
            try:
                _move_file(task_path, dest)
            except OSError:
                with contextlib.suppress(Exception):
                    _restore_snapshot_if_unchanged(
                        original,
                        record.updated,
                        self._kanban_dir,
                    )
                raise
            self._task_cache.pop(task_path.name, None)
            self._id_to_filename.pop(record.id, None)
            archived = True
        else:
            record.status = status
            record.updated = datetime.now(tz=UTC).isoformat()
            if expected_updated is not None:
                storage.write_task_if_unchanged(
                    record,
                    expected_updated,
                    self._kanban_dir,
                )
            else:
                write_task(record, self._kanban_dir)

        try:
            self._emit_event(
                "move",
                record.id,
                f"{old_status} -> {record.status}",
                source=source,
            )
        except OSError:
            with contextlib.suppress(Exception):
                if archived and dest.exists():
                    _move_file(dest, task_path)
                _restore_snapshot_if_unchanged(
                    original,
                    record.updated,
                    self._kanban_dir,
                )
            raise
        self._revision += 1
        return record

    def claim_task(self, task_id: str, *, now: datetime | None = None) -> Task:
        """Claim a task for this engine's agent.

        Args:
            task_id: Numeric task ID as a string.
            now:     Reference time for expiry calculation (injectable for tests).
                     Defaults to ``datetime.now(UTC)``.

        Returns:
            Updated :class:`Task` with ``claimed_at`` set.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
            ValueError: Task is blocked, or already claimed by a different agent
                        whose claim has not expired.
        """
        task_path = self._find_task_path(task_id, self._tasks_dir)
        stale_retries = 0

        while True:
            # Keep injected `now` deterministic in tests, but refresh runtime time
            # after each ERR_STALE retry so successful retries cannot regress D14.
            effective_now = now if now is not None else datetime.now(tz=UTC)
            record = read_task(task_path, config=self._config)
            original = record.model_copy(deep=True)
            expected_for_claim = original.updated

            if record.blocked:
                msg = f"Task {task_id!r} is blocked and cannot be claimed"
                raise ValueError(msg)

            if record.claimed_at is not None:
                # Reject unless the existing claim has expired.
                timeout = self._parse_claim_timeout()
                claimed_at_dt = datetime.fromisoformat(record.claimed_at)  # type: ignore[arg-type]
                if effective_now < claimed_at_dt + timeout:
                    msg = (
                        f"Task {task_id!r} is already claimed "
                        f"(claimed_at={record.claimed_at})"
                    )
                    raise ValueError(msg)

                # Expired rival claim: clear it first via CAS before claiming.
                cleared = record.model_copy(deep=True)
                cleared.claimed_at = None
                cleared.updated = effective_now.isoformat()
                try:
                    _storage_module().write_task_if_unchanged(
                        cleared,
                        original.updated,
                        self._kanban_dir,
                    )
                except ConcurrencyError as exc:
                    if (
                        exc.code == "ERR_STALE"
                        and stale_retries < _MAX_CLAIM_STALE_RETRIES
                    ):
                        stale_retries += 1
                        continue
                    raise
                expected_for_claim = cleared.updated
                record = cleared

            record.claimed_at = effective_now.isoformat()
            record.updated = effective_now.isoformat()

            try:
                _storage_module().write_task_if_unchanged(
                    record,
                    expected_for_claim,
                    self._kanban_dir,
                )
            except ConcurrencyError as exc:
                if exc.code == "ERR_STALE" and stale_retries < _MAX_CLAIM_STALE_RETRIES:
                    stale_retries += 1
                    continue
                raise

            try:
                self._emit_event(
                    "claim",
                    record.id,
                    self._agent_name,
                    task_status_at_start=record.status,
                    timestamp=effective_now,
                    source="agent",
                )
            except OSError:
                with contextlib.suppress(Exception):
                    write_task(original, self._kanban_dir)
                raise
            self._revision += 1
            return record

    def _append_timestamped_note(
        self,
        record: Task,
        note: str | None,
        now: datetime,
    ) -> None:
        """Append an ISO timestamp line and note line to ``record.body`` when provided."""
        if note is None:
            return
        body = _task_body_as_text(record.body)
        stamp = now.replace(microsecond=0).isoformat()
        record.body = body + "\n" + stamp + "\n" + note

    def release_task(
        self,
        task_id: str,
        *,
        expected_updated: str | None = None,
        source: str = "engine",
        note: str | None = None,
    ) -> Task:
        """Release the claim on a task, clearing ``claimed_at``.

        When the task is not currently claimed:

        - If ``expected_updated`` is ``None``, this is a silent no-op and the
          unchanged record is returned.
        - If ``expected_updated`` is provided, the token is verified against
          ``record.updated``; a stale token raises :class:`ConcurrencyError`
          (``ERR_STALE``); a matching token returns the unchanged record.

        Args:
            task_id: Numeric task ID as a string.
            expected_updated: Optional OCC token for compare-and-swap release.
            source:  Activity event source label (agent, cockpit, engine).
            note:    Optional note text appended with an ISO-8601 timestamp.

        Returns:
            :class:`Task` with claim fields cleared when the task was claimed,
            or the unchanged record when the task was already unclaimed.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
            ConcurrencyError: ``expected_updated`` was provided but does not
                match the stored ``updated`` timestamp (code ``ERR_STALE``).
        """
        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path, config=self._config)
        original = record.model_copy(deep=True)
        now = datetime.now(tz=UTC)

        if record.claimed_at is None:
            if expected_updated is not None and record.updated != expected_updated:
                raise ConcurrencyError(
                    code="ERR_STALE",
                    user_message=f"task {record.id} changed since read; reload and retry",
                )
            return record

        self._append_timestamped_note(record, note, now)

        record.claimed_at = None
        record.updated = now.isoformat()
        if expected_updated is not None:
            storage.write_task_if_unchanged(
                record,
                expected_updated,
                self._kanban_dir,
            )
        else:
            write_task(record, self._kanban_dir)
        try:
            self._emit_event(
                "release",
                record.id,
                f"released by {source}",
                source=source,
            )
        except OSError:
            with contextlib.suppress(Exception):
                _restore_snapshot_if_unchanged(
                    original,
                    record.updated,
                    self._kanban_dir,
                )
            raise
        self._revision += 1
        return record

    def start_work(self, task_id: str, *, now: datetime | None = None) -> Task:
        """Claim a task and return its full record (compound start-of-work operation).

        Delegates to :meth:`claim_task`, inheriting its blocked guard and rival-claim
        logic.

        Args:
            task_id: Numeric task ID as a string.
            now:     Reference time for claim expiry (injectable for tests).

        Returns:
            Updated :class:`Task` with claim fields set.

        Raises:
            FileNotFoundError: No task matching ``task_id``.
            ValueError: Task is blocked or already claimed by a live rival.
        """
        return self.claim_task(task_id, now=now)

    def _apply_outcome(  # noqa: PLR0913
        self,
        record: Task,
        outcome: str,
        block_reason: str,
        move_to: str | None,
        archival_reason: str | None,
        archival_refs: list[int],
    ) -> bool:
        """Apply outcome-specific mutations to *record* in-place.

        Returns ``True`` when the task should be moved to the archive directory.
        """
        if outcome == "success":
            statuses = list(self._config.pipeline.statuses)
            current_idx = (
                statuses.index(record.status) if record.status in statuses else -1
            )
            if move_to is not None:
                record.status = move_to
            elif current_idx == len(statuses) - 1:
                record.status = "archived"
                record.archival_reason = "completed"
                record.archival_refs = []
                return True
            else:
                record.status = statuses[current_idx + 1]
        elif outcome == "block":
            record.blocked = True
            record.block_reason = block_reason
            # Agent-owned blocking should clear any prior user-owned block tag.
            record.tags = [tag for tag in record.tags if tag != "block:user"]
            if move_to:
                record.status = move_to
        elif outcome == "reject":
            if move_to == "archived":
                record.status = "archived"
                record.archival_reason = archival_reason
                record.archival_refs = archival_refs
                return True
            if move_to is not None:
                record.status = move_to
        # outcome == "fail": no status change
        return False

    def end_work(  # noqa: PLR0913
        self,
        task_id: str,
        *,
        note: str,
        outcome: str = "success",
        block_reason: str = "",
        move_to: str | None = None,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
        expected_updated: str | None = None,
        source: str = "engine",
    ) -> Task:
        """Finalise a work session: append note, update task state, release claim.

        All mutations are applied in a single read→mutate→write cycle to avoid
        partial-state failures from multiple independent I/O operations.

        Args:
            task_id:      Numeric task ID as a string.
            note:         Text to append (prefixed with ISO-8601 datetime timestamp).
            outcome:      One of ``"success"``, ``"fail"``, ``"block"``, ``"reject"``.
            block_reason: Required when *outcome* is ``"block"``; stored on the task.
            move_to:      Optional target status when *outcome* is ``"reject"``.
            archival_reason: Archival reason used when ``reject`` moves to ``"archived"``.
            archival_refs: Archival references used when ``reject`` moves to ``"archived"``.
            expected_updated: Optional OCC token for compare-and-swap writes.
            source:       Activity source label for emitted ``end_work`` event.

        Returns:
            Updated :class:`Task` reflecting the new state.

        Raises:
            ValueError:        *outcome* is ``"block"`` but *block_reason* is empty,
                               or *outcome*/*move_to* is invalid.
            FileNotFoundError: No task matching ``task_id``.

        Note:
            The ``"success"`` outcome advances the task to the next status in the
            configured sequence.  This linear progression is an **agent-specific
            convention** used in OwlBear pipeline workflows — it is not enforced
            by the underlying state machine.  For the full set of reachable
            statuses from a given state, see :meth:`valid_transitions`.
        """
        valid_outcomes = {"success", "fail", "block", "reject"}
        if outcome not in valid_outcomes:
            msg = f"Unknown outcome: {outcome!r}"
            raise ValueError(msg)

        if outcome == "reject" and move_to is not None:
            valid_statuses = set(self._config.pipeline.statuses)
            valid_statuses.add("archived")
            if move_to not in valid_statuses:
                msg = f"Invalid move_to status {move_to!r}. Valid options: {sorted(valid_statuses)}"
                raise ValueError(msg)

        # --- Single read ---
        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path, config=self._config)
        original = record.model_copy(deep=True)
        old_status = record.status

        # --- Append timestamped note ---
        now = datetime.now(tz=UTC)
        self._append_timestamped_note(record, note, now)

        # --- Release claim ---
        record.claimed_at = None

        # --- Apply outcome-specific mutations ---
        needs_archive = self._apply_outcome(
            record,
            outcome,
            block_reason,
            move_to,
            archival_reason,
            list(archival_refs or []),
        )

        record.updated = now.isoformat()

        # --- Single write ---
        if expected_updated is not None:
            storage.write_task_if_unchanged(
                record,
                expected_updated,
                self._kanban_dir,
            )
        else:
            write_task(record, self._kanban_dir)

        # --- Archive move (only after successful write) ---
        dest = self._archive_dir / task_path.name
        if needs_archive:
            self._archive_dir.mkdir(parents=True, exist_ok=True)
            try:
                _move_file(task_path, dest)
            except OSError:
                with contextlib.suppress(Exception):
                    write_task(original, self._kanban_dir)
                raise

        # --- Activity logging ---
        _end_work_details = {
            "success": f"success: {old_status} -> {record.status}",
            "fail": "outcome=fail",
            "block": f"blocked: {block_reason}",
            "reject": f"reject: {old_status} -> {move_to}",
            "release": "release",
        }
        try:
            self._emit_event(
                "end_work", record.id, _end_work_details[outcome], source=source
            )
        except OSError:
            with contextlib.suppress(Exception):
                if needs_archive and dest.exists():
                    _move_file(dest, task_path)
                write_task(original, self._kanban_dir)
            raise

        self._revision += 1
        return record

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def sweep(self) -> list[int]:  # noqa: C901
        """Release expired claims and return list of released task IDs.

        Only handles ``claimed_at``-based timeouts (Brief C §1.5, AC-C23).
        Does NOT move archived tasks or touch corrupt files.

        Claim releases use compare-and-swap writes (``write_task_if_unchanged``);
        tasks modified concurrently (``ERR_STALE``) are silently skipped and not
        included in the returned list.

        Returns:
            List of integer task IDs whose expired claims were released.
        """
        released: list[int] = []
        timeout = self._parse_claim_timeout()
        now = datetime.now(tz=UTC)
        for path in sorted(self._tasks_dir.glob("*.md")):
            try:
                record = read_task(path, config=self._config)
            except (FileNotFoundError, ValueError, KeyError, CorruptionError):
                continue  # silently skip corrupt files (AC-C27)

            # AC-C27: do not mutate parseable-but-corrupt files.
            if detect_corruption(path, self._config) is not None:
                continue

            # Only handle claimed_at (Brief C — claimed_by is legacy)
            if record.claimed_at:
                try:
                    claimed_dt = datetime.fromisoformat(record.claimed_at)
                except ValueError:
                    continue
                if claimed_dt.tzinfo is None:
                    claimed_dt = claimed_dt.replace(tzinfo=UTC)
                if now >= claimed_dt + timeout:
                    original = record.model_copy(deep=True)
                    # Clear claimed_at and update timestamp
                    record.claimed_at = None
                    record.updated = datetime.now(tz=UTC).isoformat()
                    try:
                        storage.write_task_if_unchanged(
                            record,
                            original.updated,
                            self._kanban_dir,
                        )
                    except ConcurrencyError as exc:
                        if exc.code == "ERR_STALE":
                            continue
                        raise
                    try:
                        self._emit_event(
                            "sweep-release", record.id, "expired claim released"
                        )
                    except OSError:
                        with contextlib.suppress(Exception):
                            _restore_snapshot_if_unchanged(
                                original,
                                record.updated,
                                self._kanban_dir,
                            )
                        continue
                    released.append(record.id)

        return released

    def cleanup(self) -> CleanupResult:  # noqa: C901, PLR0912, PLR0915
        """Run maintenance cleanup and return aggregate results.

        Cleanup includes three categories in one call:
        - release expired claims (same semantics as :meth:`sweep`)
        - move drift-archived task files from tasks/ to archive/
        - report skipped task files with path+reason when they cannot be processed
        """
        released_claim_ids: list[int] = []
        archived_task_ids: list[int] = []
        skipped_items: list[dict[str, str]] = []
        timeout = self._parse_claim_timeout()
        now = datetime.now(tz=UTC)

        for path in sorted(self._tasks_dir.glob("*.md")):
            try:
                record = read_task(path, config=self._config)
            except (FileNotFoundError, ValueError, KeyError, CorruptionError) as exc:
                skipped_items.append({"path": str(path), "reason": str(exc)})
                continue

            issue = detect_corruption(path, self._config)
            if issue is not None:
                skipped_items.append(
                    {
                        "path": str(path),
                        "reason": getattr(issue, "user_message", str(issue)),
                    }
                )
                continue

            # Release expired claims via compare-and-swap, mirroring sweep() behavior.
            if record.claimed_at:
                try:
                    claimed_dt = datetime.fromisoformat(record.claimed_at)
                except ValueError:
                    skipped_items.append(
                        {
                            "path": str(path),
                            "reason": "invalid claimed_at timestamp",
                        }
                    )
                    continue
                if claimed_dt.tzinfo is None:
                    claimed_dt = claimed_dt.replace(tzinfo=UTC)
                if now >= claimed_dt + timeout:
                    original = record.model_copy(deep=True)
                    record.claimed_at = None
                    record.updated = datetime.now(tz=UTC).isoformat()
                    try:
                        storage.write_task_if_unchanged(
                            record,
                            original.updated,
                            self._kanban_dir,
                        )
                    except ConcurrencyError as exc:
                        if exc.code == "ERR_STALE":
                            skipped_items.append(
                                {
                                    "path": str(path),
                                    "reason": "concurrent update while releasing claim",
                                }
                            )
                            continue
                        raise
                    released_claim_ids.append(record.id)

            # Move drift-archived files from tasks/ to archive/ when valid.
            if record.status != "archived":
                continue
            if record.archival_reason is None:
                skipped_items.append(
                    {
                        "path": str(path),
                        "reason": "missing archival_reason for archived task",
                    }
                )
                continue

            dest = self._archive_dir / path.name
            if dest.exists():
                skipped_items.append(
                    {
                        "path": str(path),
                        "reason": "archive destination already exists",
                    }
                )
                continue

            self._archive_dir.mkdir(parents=True, exist_ok=True)
            try:
                _move_file(path, dest, no_overwrite=True)
            except FileExistsError:
                skipped_items.append(
                    {
                        "path": str(path),
                        "reason": "archive destination already exists",
                    }
                )
                continue
            except OSError as exc:
                skipped_items.append({"path": str(path), "reason": str(exc)})
                continue
            self._task_cache.pop(path.name, None)
            self._id_to_filename.pop(record.id, None)
            archived_task_ids.append(record.id)

        if released_claim_ids or archived_task_ids:
            self._revision += 1

        return CleanupResult(
            released_claim_ids=released_claim_ids,
            archived_task_ids=archived_task_ids,
            skipped_items=skipped_items,
        )

    def repair_storage(self) -> list:
        """Quarantine corrupt task files and create action-required tasks (AC-C24, AC-C25, AC-C30).

        Two-phase repair:
        1. Phase 1 (file ops): ``scan_and_fix`` quarantines corrupt files.
        2. Phase 2 (AR creation): for each quarantined file, create an AR task
           with ``type:user-action`` tag. If AR creation fails, outcome.action
           is updated to 'failed'.

        Returns:
            List of :class:`RepairOutcome` objects with action 'quarantined', 'failed', or 'fixed'.
        """
        from pathlib import Path as _Path  # noqa: PLC0415

        from owlbear_kanban.corruption import scan_and_fix  # noqa: PLC0415

        # Phase 1: file operations only
        outcomes = scan_and_fix(self._kanban_dir, self._config)

        # Phase 2: create AR tasks for each quarantined file
        final_outcomes = []
        for outcome in outcomes:
            if outcome.action == "quarantined":
                quarantine_path = (
                    self._kanban_dir / "quarantine" / _Path(outcome.file_path).name
                )
                body = (
                    "## Quarantined file\n\n"
                    f"- code: {outcome.code}\n"
                    f"- path: {quarantine_path}\n"
                    f"- detail: {outcome.detail or ''}\n"
                )
                try:
                    # Use unbound call so patched create_task spy receives self as first arg
                    type(self).create_task(
                        self,
                        f"Storage repair: {_Path(outcome.file_path).name}",
                        body=body,
                        tags=["type:user-action"],
                    )
                    final_outcomes.append(outcome)
                except (ValueError, KanbanError, OSError) as _exc:
                    from owlbear_kanban.corruption import RepairOutcome  # noqa: PLC0415

                    final_outcomes.append(
                        RepairOutcome(
                            task_id=outcome.task_id,
                            file_path=outcome.file_path,
                            code=outcome.code,
                            action="failed",
                            detail=f"AR creation failed: {_exc}",
                        )
                    )
            else:
                final_outcomes.append(outcome)

        return final_outcomes

    def _emit_event(  # noqa: PLR0913
        self,
        action: str,
        task_id: int | None = None,
        detail: str | None = None,
        task_status_at_start: str | None = None,
        timestamp: datetime | None = None,
        source: str = "engine",
    ) -> None:
        """Append one :class:`ActivityEvent` to ``activity.jsonl`` if logging is enabled."""
        if self._activity_log_path is None:
            return
        from owlbear_kanban.activity_store import append_activity_event  # noqa: PLC0415
        from owlbear_kanban.models import ActivityEvent  # noqa: PLC0415

        event_time = timestamp if timestamp is not None else datetime.now(tz=UTC)
        evt = ActivityEvent(
            timestamp=event_time.isoformat(),
            task_id=task_id,
            action=action,
            source=source,
            detail=detail or "",
            task_status_at_start=task_status_at_start,
        )
        append_activity_event(evt, self._kanban_dir)

    def list_activity(  # noqa: PLR0913
        self,
        *,
        task_id: int | None = None,
        action: str | None = None,
        source: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int | None = None,
    ) -> list[ActivityEvent]:
        """Return activity log entries filtered by task/action/source/time window."""
        return list_activity_events(
            self._kanban_dir,
            task_id=task_id,
            action=action,
            source=source,
            since=since,
            until=until,
            limit=limit,
        )

    def scan_corruption(self) -> list:
        """Read-only corruption scan for tasks and archive directories."""
        errors = []
        for directory in (self._tasks_dir, self._archive_dir):
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.md")):
                issue = detect_corruption(path, self._config)
                if issue is not None:
                    errors.append(issue)
        return errors

    def compact_activity(self) -> ActivityCompactionResult:
        """Compact activity.jsonl using retention rules in activity_store."""
        return compact_activity_log(self._kanban_dir)

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def list_sessions(self, *, filter: str = "active") -> list[SessionRecord]:  # noqa: A002
        """Derive logical SessionRecord values from activity.jsonl.

        Each claim-close event pair becomes one :class:`SessionRecord`.
        Open claims are classified as ``'running'`` or ``'stuck'``.

        Args:
            filter: One of ``"active"`` (default), ``"all"``,
                    ``"blocked-or-rejected"`` (or legacy alias
                    ``"failed-or-rejected"``), or ``"released"``.

        Returns:
            List of :class:`SessionRecord` objects matching the filter.
        """
        _validate_session_filter(filter)
        if self._activity_log_path is None or not self._activity_log_path.exists():
            return []
        return _apply_session_filter(self._derive_sessions(), filter)

    def _read_log_entries(self) -> list[dict]:
        """Parse activity.jsonl; skip malformed and incomplete lines."""
        assert self._activity_log_path is not None  # caller must check
        try:
            text = self._activity_log_path.read_text(encoding="utf-8")
        except OSError:
            return []
        entries: list[dict] = []
        for line in text.splitlines():
            line = line.strip()  # noqa: PLW2901
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if all(k in entry for k in ("action", "task_id", "detail", "timestamp")):
                try:
                    datetime.fromisoformat(str(entry["timestamp"]))
                except ValueError:
                    continue
                entries.append(entry)
        return entries

    def _derive_sessions(self) -> list[SessionRecord]:
        """Build SessionRecord list from parsed log entries."""
        by_task: dict[int, list[dict]] = defaultdict(list)
        for entry in self._read_log_entries():
            try:
                task_id = int(entry["task_id"])
            except (ValueError, TypeError):
                continue
            by_task[task_id].append(entry)

        timeout = self._parse_claim_timeout()
        now = datetime.now(tz=UTC)
        sessions: list[SessionRecord] = []
        for task_id, events in by_task.items():
            _collect_task_sessions(task_id, events, timeout, now, sessions)
        return sessions

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_claim_timeout(self) -> timedelta:
        """Parse the ``claim_timeout`` string from config into a :class:`timedelta`."""
        return _parse_duration(self._config.pipeline.claim_timeout)

    def _find_task_path(
        self,
        task_id: str,
        search_dir: Path,
        *,
        include_archive_fallback: bool = False,
    ) -> Path:
        """Return the path of ``{task_id}-*.md`` in *search_dir*.

        Raises:
            FileNotFoundError: No matching file found.
        """
        if search_dir == self._tasks_dir and self._id_to_filename:
            try:
                int_id = int(task_id)
            except ValueError:
                int_id = None
            if int_id is not None and int_id in self._id_to_filename:
                filename = self._id_to_filename[int_id]
                candidate = self._tasks_dir / filename
                if candidate.exists():
                    return candidate
                self._task_cache.pop(filename, None)
                del self._id_to_filename[int_id]

        matches = list(search_dir.glob(f"{task_id}-*.md"))
        if matches:
            return matches[0]

        if include_archive_fallback and search_dir == self._tasks_dir:
            archive_matches = list(self._archive_dir.glob(f"{task_id}-*.md"))
            if archive_matches:
                return archive_matches[0]

        msg = f"Task {task_id!r} not found in {search_dir}"
        raise FileNotFoundError(msg)


def __getattr__(name: str) -> object:
    """Provide backward-compatible lazy access to ``AgentView``."""
    if name == "AgentView":
        from owlbear_kanban.agent_view import AgentView  # noqa: PLC0415

        return AgentView
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
