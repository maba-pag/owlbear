"""KanbanEngine — native read/write engine for the owlbear kanban board.

Provides KanbanEngine, a filesystem-backed implementation for listing,
reading, and writing kanban task files without invoking the kanban-md CLI.

Architecture:
  - Constructor loads BoardConfig via config_loader.load_config().
  - list_tasks() scans tasks_dir (or archive dir), applies filters,
    sorts by config-ranked field, and returns list[TaskSummary].
  - show_task() finds a single task file by ID and returns its Task.
    - create_task() allocates next_id via allocate_next_id
        (persists config.next_id before write), then writes a new task file.
  - edit_task() modifies task fields in-place; slug/filename never changes.
  - move_task() changes status; "archived" moves file to archive/.
  - claim_task() marks a task as claimed by this engine's agent_name; rejects
    blocked tasks and rival claims within the configured timeout window.
  - release_task() clears claimed_by and claimed_at fields unconditionally.
  - board_config() returns a defensive copy of the current BoardConfig.
  - refresh_config() reloads config from disk, updating all derived state.
  - valid_transitions(status) returns the set of all statuses except the given one.
  - revision is a per-instance counter incremented on every write operation.
"""

from __future__ import annotations

import contextlib
import json
import os
import random
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from owlbear_kanban import storage
from owlbear_kanban.agent_names import ADJECTIVES, NOUNS
from owlbear_kanban.body_parser import parse_body
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.models import (
    BoardConfig,
    ConcurrencyError,
    ConfigError,
    DispatchEntry,
    ListTasksResponse,
    MigrationRequiredError,
    NotFoundError,
    PickTasksResponse,
    SessionRecord,
    ShowTaskResponse,
    SingleTaskResponse,
    Task,
    TaskSummary,
    ValidationError,
    Wave,
)
from owlbear_kanban.storage import (
    make_task_filename,
    read_task,
    validate_path_containment,
    write_task,
)

# ---------------------------------------------------------------------------
# Module-level duration parser (AC-C49)
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")
_BLOCK_REASON_UNSET = object()


def _parse_duration(s: str) -> timedelta:
    """Parse a duration string like ``'1h'``, ``'30m'``, ``'2h30m'``, ``'30s'``, ``'2d'``.

    Args:
        s: Duration string.

    Returns:
        :class:`timedelta` representation.

    Raises:
        ConfigError: code='ERR_INVALID_CLAIM_TIMEOUT' when format is invalid.
    """
    m = _DURATION_RE.match(s.strip())
    if not m or not any(m.groups()):
        raise ConfigError(
            code="ERR_INVALID_CLAIM_TIMEOUT",
            user_message=(
                f"Invalid claim_timeout format: {s!r} — expected e.g. "
                "'1h', '30m', '2h30m', '30s', '2d'"
            ),
        )
    days = int(m.group(1) or 0)
    hours = int(m.group(2) or 0)
    minutes = int(m.group(3) or 0)
    seconds = int(m.group(4) or 0)
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


def _validate_engine_config(config: BoardConfig) -> None:  # noqa: C901
    """Validate engine-specific config invariants required at engine init."""
    statuses = config.statuses
    priorities = config.priorities

    if not statuses:
        raise ConfigError(
            code="ERR_INVALID_STATUS",
            user_message="config.statuses must contain at least one status",
        )
    if not priorities:
        raise ConfigError(
            code="ERR_INVALID_PRIORITY",
            user_message="config.priorities must contain at least one priority",
        )

    if config.entry_status not in statuses:
        raise ConfigError(
            code="ERR_ENTRY_STATUS_INVALID",
            user_message=(
                f"entry_status {config.entry_status!r} must be one of statuses: {statuses}"
            ),
        )

    terminal_status = config.terminal_status
    if terminal_status not in statuses or terminal_status != statuses[-1]:
        raise ConfigError(
            code="ERR_TERMINAL_STATUS_INVALID",
            user_message=(
                f"terminal_status {terminal_status!r} must equal statuses[-1] ({statuses[-1]!r})"
            ),
        )

    missing_statuses = [status for status in statuses if status not in config.agent_map]
    if missing_statuses:
        raise ConfigError(
            code="ERR_INVALID_STATUS",
            user_message=f"agent_map missing status entries: {missing_statuses}",
        )

    # Validate timeout format eagerly at engine init.
    _parse_duration(config.claim_timeout)

    compatibility_sets: dict[str, set[str]] = {}
    for agent, peers in config.agent_compatibility.items():
        if not isinstance(peers, list):
            raise ConfigError(
                code="ERR_INVALID_STATUS",
                user_message=f"agent_compatibility[{agent!r}] must be a list[str]",
            )
        compatibility_sets[agent] = {str(peer) for peer in peers}

    for agent, peers in compatibility_sets.items():
        for peer in peers:
            reverse = compatibility_sets.get(peer)
            if reverse is None or agent not in reverse:
                raise ConfigError(
                    code="ERR_INVALID_STATUS",
                    user_message=(
                        "agent_compatibility must be symmetric: "
                        f"{agent!r} -> {peer!r} requires {peer!r} -> {agent!r}"
                    ),
                )


if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


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
    # blocked:* and outcome=fail both map to the canonical blocked state.
    return "blocked"


def _classify_end_work_outcome(detail: str) -> str:
    """Map an end_work detail string to canonical SessionRecord outcome values."""
    if detail.startswith("success:"):
        return "success"
    if detail.startswith("reject:"):
        return "reject"
    if detail.startswith("outcome=fail"):
        return "fail"
    return "block"


_CLOSE_ACTIONS: frozenset[str] = frozenset({"end_work", "release", "sweep-release"})


def _compute_duration(claim_ts: str, close_ts: str) -> float:
    """Return (close_dt - claim_dt).total_seconds(), normalising tz-naive timestamps to UTC."""
    claim_dt = datetime.fromisoformat(claim_ts)
    close_dt = datetime.fromisoformat(close_ts)
    if claim_dt.tzinfo is None:
        claim_dt = claim_dt.replace(tzinfo=UTC)
    if close_dt.tzinfo is None:
        close_dt = close_dt.replace(tzinfo=UTC)
    return (close_dt - claim_dt).total_seconds()


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

        if action == "claim":
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
                outcome = "released"
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


def _move_file(src: Path, dest: Path) -> None:
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
    src.replace(dest)


@contextlib.contextmanager
def _exclusive_file_lock(lock_path: Path) -> Generator[None, None, None]:
    """Acquire an exclusive cross-process file lock on *lock_path*.

    Uses ``msvcrt.locking`` on Windows and ``fcntl.flock`` on Unix.
    The lock is always released, including on exception paths.
    """
    with lock_path.open("a+b") as fh:
        if sys.platform == "win32":  # pragma: no cover
            import msvcrt  # noqa: PLC0415

            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl  # noqa: PLC0415

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


class KanbanEngine:
    """Native kanban engine backed by filesystem task files.

    All mutating operations (create, edit, move, claim, release) optionally
    append an entry to ``{kanban_dir}/activity.jsonl``.

    Args:
        kanban_dir:    Root directory of the kanban board.
        activity_log:  When ``True``, append entries to ``activity.jsonl`` on
                       every mutation.  When ``None`` (default), reads from
                       ``config.yml`` ``activity_log`` field.
    """

    def __init__(  # noqa: C901
        self,
        kanban_dir: Path,
        *,
        activity_log: bool | None = None,
    ) -> None:
        self._kanban_dir = kanban_dir
        self._config: BoardConfig = load_config(kanban_dir)
        _validate_engine_config(self._config)
        self._tasks_dir = kanban_dir / self._config.tasks_dir
        self._archive_dir = kanban_dir / self._config.archive_dir
        self._agent_name: str = f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"  # noqa: S311
        effective_activity_log = (
            activity_log if activity_log is not None else self._config.activity_log
        )
        self._activity_log_path: Path | None = (
            kanban_dir / "activity.jsonl" if effective_activity_log else None
        )
        self._revision: int = 0
        self._task_cache: dict[str, tuple[int, Task]] = {}
        self._archive_cache: dict[str, tuple[int, Task]] = {}
        self._id_to_filename: dict[int, str] = {}
        self._agent_view = AgentView(self)
        self._cockpit_view = CockpitView(self)

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

    # ------------------------------------------------------------------
    # Config-derived rank maps
    # ------------------------------------------------------------------

    def _priority_rank(self) -> dict[str, int]:
        return {p: i for i, p in enumerate(self._config.priorities)}

    def _status_rank(self) -> dict[str, int]:
        statuses = self._config.statuses
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

    def cockpit_view(self) -> CockpitView:
        """Return the cached cockpit-facing view facade."""
        return self._cockpit_view

    def refresh_config(self) -> None:
        """Reload config from disk and update all derived state.

        After calling this method, ``_status_rank()`` and ``_priority_rank()``
        use the newly loaded config values. Also updates ``_tasks_dir`` and
        ``_archive_dir`` to reflect any tasks_dir change in config. All three
        caches — ``_task_cache``, ``_archive_cache``, and ``_id_to_filename``
        — are cleared so the next ``list_tasks()`` call performs a full cold
        scan and rebuilds the id→filename index.
        """
        self._config = load_config(self._kanban_dir)
        self._tasks_dir = self._kanban_dir / self._config.tasks_dir
        self._archive_dir = self._kanban_dir / self._config.archive_dir
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
        valid_statuses = set(self._config.statuses)
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
        from owlbear_kanban.storage import detect_corruption as _detect_corruption  # noqa: PLC0415

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
                        archive_task = read_task(archive_path)
                    except (FileNotFoundError, ValueError, KeyError):
                        archived_reasons[archive_id] = None
                    except Exception:  # noqa: BLE001
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
                        corruption = _detect_corruption(path, self._config)
                        if corruption is not None and not (
                            corruption.code == "ERR_CORRUPT_MISSING_FIELD"
                            and corruption.detail
                            == "forbidden field claimed_by present"
                        ):
                            cache.pop(entry.name, None)
                            continue
                    try:
                        task = read_task(path)
                    except FileNotFoundError:
                        cache.pop(entry.name, None)
                        continue
                    except (ValueError, KeyError):
                        continue
                    except Exception as _exc:  # noqa: BLE001
                        # Silently skip other parse errors (CorruptionError modes 1, 3-9)
                        from owlbear_kanban.corruption import CorruptionError as _CorruptionError  # noqa: PLC0415

                        if isinstance(_exc, _CorruptionError):
                            continue
                        continue
                    cache[entry.name] = (mtime_ns, task)
                    if not archived and task.id in archive_ids:
                        # AC-C19 mode 7: if an archive copy exists, skip tasks/ copy.
                        cache.pop(entry.name, None)
                        continue
                    # AC-C19: skip mode 8 (invalid status) silently
                    _valid_statuses = set(self._config.statuses)
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
                    from owlbear_kanban.corruption import ERR_CORRUPT_DUPLICATE_ID  # noqa: PLC0415
                    from owlbear_kanban.corruption import CorruptionError as _CorruptionError  # noqa: PLC0415

                    raise _CorruptionError(
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
                tasks.sort(key=lambda t: datetime.fromisoformat(t.created))
            elif sort == "updated":
                tasks.sort(key=lambda t: datetime.fromisoformat(t.updated))

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

        Args:
            task_id: The numeric task ID as a string (e.g. ``"42"``).

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md`` in tasks_dir.
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
                    archived_task = read_task(archive_path)
                    self._task_cache[filename] = (
                        archive_path.stat().st_mtime_ns,
                        archived_task,
                    )
                    return archived_task
            if (
                filename in self._task_cache
                and self._task_cache[filename][0] == mtime_ns
            ):
                return self._task_cache[filename][1]
            task = read_task(path)
            self._task_cache[filename] = (mtime_ns, task)
            return task

        matches = list(self._tasks_dir.glob(f"{task_id}-*.md"))
        if matches:
            return read_task(matches[0])

        archive_matches = list(self._archive_dir.glob(f"{task_id}-*.md"))
        if archive_matches:
            return read_task(archive_matches[0])

        msg = f"Task {task_id!r} not found in {self._tasks_dir} or {self._archive_dir}"
        raise FileNotFoundError(msg)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create_task(  # noqa: PLR0913
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
        """Allocate next_id, then write a new task file.

        ID allocation is delegated to ``storage.allocate_next_id()``, which
        advances and persists ``config.next_id`` under the shared file lock.
        If writing the task file fails after allocation, the allocated ID is
        intentionally burned to preserve crash safety.

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
        """
        config: BoardConfig = load_config(self._kanban_dir)

        if status:
            valid_statuses = set(config.statuses)
            if status not in valid_statuses:
                msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
                raise ValueError(msg)
        if priority and priority not in config.priorities:
            msg = f"Invalid priority {priority!r}. Valid options: {config.priorities}"
            raise ValueError(msg)

        task_id = storage.allocate_next_id(self._kanban_dir)
        now = datetime.now(tz=UTC).isoformat()

        record = Task(
            id=task_id,
            title=title,
            status=status or config.entry_status,
            priority=priority or config.defaults.priority,
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
        write_task(record, self._kanban_dir)
        self._config = load_config(self._kanban_dir)

        self._tasks_dir = self._kanban_dir / self._config.tasks_dir
        self._archive_dir = self._kanban_dir / self._config.archive_dir

        self._revision += 1
        return record

    def edit_task(  # noqa: PLR0912, PLR0913, PLR0915, C901
        self,
        task_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        parent: int | None = None,
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
    ) -> Task:
        """Modify fields on a task in-place; filename (slug) is never changed.

        Args:
            task_id:     Numeric task ID as a string.
            title:       Replace task title.
            body:        Replace task body.
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

        Returns:
            Updated :class:`Task`.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
            ValueError: ``status`` or ``priority`` is not a valid configured value.
        """
        if status is not None:
            valid_statuses = set(self._config.statuses)
            if status not in valid_statuses:
                msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
                raise ValueError(msg)
        if priority is not None and priority not in self._config.priorities:
            msg = f"Invalid priority {priority!r}. Valid options: {self._config.priorities}"
            raise ValueError(msg)

        task_path = self._find_task_path(task_id, self._tasks_dir, include_archive_fallback=True)
        target_dir = task_path.parent
        record = read_task(task_path)
        original = record.model_copy(deep=True)

        if title is not None:
            record.title = title
        if body is not None:
            record.body = body
        if priority is not None:
            record.priority = priority
        if status is not None:
            record.status = status
        if parent is not None:
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

        if archival_reason is not None:
            record.archival_reason = archival_reason
        if archival_refs is not None:
            record.archival_refs = list(archival_refs)

        record.updated = datetime.now(tz=UTC).isoformat()

        write_task(record, self._kanban_dir, target_dir=target_dir)

        try:
            self._emit_event("edit", record.id, "task edited")
        except OSError:
            with contextlib.suppress(Exception):
                write_task(original, self._kanban_dir, target_dir=target_dir)
            raise
        self._revision += 1
        return record

    def move_task(self, task_id: str, status: str) -> Task:
        """Change the status of a task; "archived" moves the file to archive/.

        Args:
            task_id: Numeric task ID as a string.
            status:  Target status name, or ``"archived"`` to archive the task.

        Returns:
            Updated :class:`Task`.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
            ValueError:        ``status`` is not valid and is not ``"archived"``.
        """
        valid_statuses = set(self._config.statuses)
        if status != "archived" and status not in valid_statuses:
            msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
            raise ValueError(msg)

        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path)
        original = record.model_copy(deep=True)
        old_status = record.status
        archived = False
        dest = self._archive_dir / task_path.name

        if status == "archived":
            self._archive_dir.mkdir(parents=True, exist_ok=True)
            record.status = "archived"
            record.updated = datetime.now(tz=UTC).isoformat()
            write_task(record, self._kanban_dir)
            _move_file(task_path, dest)
            self._task_cache.pop(task_path.name, None)
            self._id_to_filename.pop(record.id, None)
            archived = True
        else:
            record.status = status
            record.updated = datetime.now(tz=UTC).isoformat()
            write_task(record, self._kanban_dir)

        try:
            self._emit_event("move", record.id, f"{old_status} -> {record.status}")
        except OSError:
            with contextlib.suppress(Exception):
                if archived and dest.exists():
                    _move_file(dest, task_path)
                write_task(original, self._kanban_dir)
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
        record = read_task(task_path)
        original = record.model_copy(deep=True)

        if record.blocked:
            msg = f"Task {task_id!r} is blocked and cannot be claimed"
            raise ValueError(msg)

        effective_now = now if now is not None else datetime.now(tz=UTC)

        if record.claimed_at is not None:
            # Reject unless the existing claim has expired.
            timeout = self._parse_claim_timeout()
            claimed_at_dt = datetime.fromisoformat(record.claimed_at)  # type: ignore[arg-type]
            if effective_now < claimed_at_dt + timeout:
                msg = f"Task {task_id!r} is already claimed"
                raise ValueError(msg)

        record.claimed_at = effective_now.isoformat()
        record.claimed_by = self._agent_name
        record.updated = effective_now.isoformat()
        write_task(record, self._kanban_dir)
        try:
            self._emit_event(
                "claim",
                record.id,
                self._agent_name,
                task_status_at_start=record.status,
                timestamp=effective_now,
            )
        except OSError:
            with contextlib.suppress(Exception):
                write_task(original, self._kanban_dir)
            raise
        self._revision += 1
        return record

    def release_task(self, task_id: str) -> Task:
        """Release the claim on a task, clearing ``claimed_at``.

        This operation is a no-op if the task is not currently claimed.

        Args:
            task_id: Numeric task ID as a string.

        Returns:
            Updated :class:`Task` with claim fields cleared.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
        """
        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path)
        original = record.model_copy(deep=True)

        record.claimed_at = None
        record.claimed_by = None
        record.updated = datetime.now(tz=UTC).isoformat()
        write_task(record, self._kanban_dir)
        try:
            self._emit_event("release", record.id, f"released by {self._agent_name}")
        except OSError:
            with contextlib.suppress(Exception):
                write_task(original, self._kanban_dir)
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

    def _apply_outcome(
        self,
        record: Task,
        outcome: str,
        block_reason: str,
        move_to: str,
    ) -> bool:
        """Apply outcome-specific mutations to *record* in-place.

        Returns ``True`` when the task should be moved to the archive directory.
        """
        if outcome == "success":
            statuses = list(self._config.statuses)
            current_idx = (
                statuses.index(record.status) if record.status in statuses else -1
            )
            if current_idx == len(statuses) - 1:
                record.status = "archived"
                return True
            record.status = statuses[current_idx + 1]
        elif outcome == "block":
            record.blocked = True
            record.block_reason = block_reason
        elif outcome == "reject":
            record.status = move_to
        # outcome == "fail": no status change
        return False

    def end_work(
        self,
        task_id: str,
        *,
        note: str,
        outcome: str = "success",
        block_reason: str = "",
        move_to: str = "research",
    ) -> Task:
        """Finalise a work session: append note, update task state, release claim.

        All mutations are applied in a single read→mutate→write cycle to avoid
        partial-state failures from multiple independent I/O operations.

        Args:
            task_id:      Numeric task ID as a string.
            note:         Text to append (prefixed with ``[[YYYY-MM-DD]]`` timestamp).
            outcome:      One of ``"success"``, ``"fail"``, ``"block"``, ``"reject"``.
            block_reason: Required when *outcome* is ``"block"``; stored on the task.
            move_to:      Target status when *outcome* is ``"reject"`` (default ``"research"``).

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

        if outcome == "reject":
            valid_statuses = set(self._config.statuses)
            if move_to not in valid_statuses:
                msg = f"Invalid move_to status {move_to!r}. Valid options: {sorted(valid_statuses)}"
                raise ValueError(msg)

        # --- Single read ---
        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path)
        original = record.model_copy(deep=True)
        old_status = record.status

        # --- Append timestamped note ---
        date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        record.body = record.body + "\n" + f"[[{date_str}]]\n" + note

        # --- Release claim ---
        record.claimed_at = None

        # --- Apply outcome-specific mutations ---
        needs_archive = self._apply_outcome(record, outcome, block_reason, move_to)

        record.updated = datetime.now(tz=UTC).isoformat()

        # --- Single write ---
        write_task(record, self._kanban_dir)

        # --- Archive move (only after successful write) ---
        dest = self._archive_dir / task_path.name
        if needs_archive:
            self._archive_dir.mkdir(parents=True, exist_ok=True)
            _move_file(task_path, dest)

        # --- Activity logging ---
        _end_work_details = {
            "success": f"success: {old_status} -> {record.status}",
            "fail": "outcome=fail",
            "block": f"blocked: {block_reason}",
            "reject": f"reject: {old_status} -> {move_to}",
        }
        try:
            self._emit_event("end_work", record.id, _end_work_details[outcome])
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

    def sweep(self) -> list[int]:
        """Release expired claims and return list of released task IDs.

        Only handles ``claimed_at``-based timeouts (Brief C §1.5, AC-C23).
        Does NOT move archived tasks or touch corrupt files.

        Returns:
            List of integer task IDs whose expired claims were released.
        """
        released: list[int] = []
        timeout = self._parse_claim_timeout()
        now = datetime.now(tz=UTC)
        from owlbear_kanban.storage import detect_corruption as _detect_corruption  # noqa: PLC0415

        for path in sorted(self._tasks_dir.glob("*.md")):
            try:
                record = read_task(path)
            except Exception:  # noqa: BLE001, S112
                continue  # silently skip corrupt files (AC-C27)

            # AC-C27: do not mutate parseable-but-corrupt files.
            if _detect_corruption(path, self._config) is not None:
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
                    write_task(record, self._kanban_dir)
                    try:
                        self._emit_event(
                            "sweep-release", record.id, "expired claim released"
                        )
                    except OSError:
                        with contextlib.suppress(Exception):
                            write_task(original, self._kanban_dir)
                        continue
                    released.append(record.id)

        return released

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
                except Exception as _exc:  # noqa: BLE001
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

    def _emit_event(
        self,
        action: str,
        task_id: int | None = None,
        detail: str | None = None,
        task_status_at_start: str | None = None,
        timestamp: datetime | None = None,
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
            source="engine",
            detail=detail or "",
            task_status_at_start=task_status_at_start,
        )
        append_activity_event(evt, self._kanban_dir)

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
        return _parse_duration(self._config.claim_timeout)

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


class AgentView:
    """Minimal role-scoped wrapper for agent-facing engine use."""

    _MAX_BODY_BYTES = 500 * 1024
    _BODY_SIZE_WARNING = "\u26a0\ufe0f Task body is large (>100 KB); consider splitting."
    _BLOCK_AR_HINT = (
        "\u26a0\ufe0f ACTION REQUIRED: Create a Decision Request for this block via the"
        " scribe agent (see w-decision-routing)."
        " Blocks without a DR are invisible to the pipeline."
    )

    def __init__(self, engine: KanbanEngine) -> None:
        self.engine = engine

    @staticmethod
    def _to_single_response(task: Task, guidance: list[str] | None = None) -> SingleTaskResponse:
        payload = task.model_dump()
        if isinstance(payload.get("body"), list):
            payload["body"] = None
        payload["guidance"] = guidance or []
        return SingleTaskResponse.model_validate(payload)

    @staticmethod
    def _skip_transition_guidance(
        *,
        before_status: str,
        after_status: str,
        status_names: list[str],
        include_target_column: bool = False,
    ) -> list[str]:
        try:
            from_idx = status_names.index(before_status)
            to_idx = status_names.index(after_status)
        except ValueError:
            return []
        delta = to_idx - from_idx
        if delta <= 1:
            return []
        skipped = delta if include_target_column else delta - 1
        return [
            "\u26a0\ufe0f Status skip: moved from "
            f"'{before_status}' to '{after_status}' (skipped {skipped} column(s))."
            " Verify this jump is intentional."
        ]

    def _wrap_not_found(self, task_id: int) -> NotFoundError:
        return NotFoundError(
            code="ERR_NOT_FOUND",
            user_message=f"Task '{task_id}' not found",
        )

    def _task_exists(self, task_id: int) -> bool:
        try:
            self.engine.show_task(str(task_id))
        except FileNotFoundError:
            return False
        return True

    @staticmethod
    def _required_sections_passes(body: str, sections: list[str]) -> bool:
        if not sections:
            return True
        present = {
            part.heading.strip().casefold()
            for part in parse_body(body)
            if part.heading is not None and part.heading.strip()
        }
        return all(section.strip().casefold() in present for section in sections)

    @classmethod
    def _validate_body_size(cls, body: str) -> None:
        if len(body.encode("utf-8")) > cls._MAX_BODY_BYTES:
            raise ValidationError(
                code="ERR_BODY_TOO_LARGE",
                user_message="Task body exceeds 500 KB",
            )

    def _has_archival_cycle(self, root_task_id: int, refs: list[int]) -> bool:
        def visits_root(task_id: int, seen: set[int]) -> bool:
            if task_id in seen:
                return False
            seen.add(task_id)
            try:
                task = self.engine.show_task(str(task_id))
            except FileNotFoundError:
                return False
            for dep_id in task.archival_refs:
                if dep_id == root_task_id:
                    return True
                if visits_root(dep_id, seen):
                    return True
            return False

        return any(visits_root(ref_id, set()) for ref_id in refs)

    def list_tasks(  # noqa: PLR0913
        self,
        *,
        status: str = "",
        tag: str = "",
        priority: str = "",
        archival_reason: str = "",
        ids: list[int] | None = None,
        search: str = "",
        sort: str = "",
        unclaimed: bool = False,
        archived: bool = False,
        limit: int = 0,
        reverse: bool = False,
        blocked: bool | None = None,
    ) -> ListTasksResponse:
        config = self.engine.board_config()

        if status and status != "archived" and status not in config.statuses:
            raise ValidationError(
                code="ERR_INVALID_STATUS",
                user_message=f"status must be one of {[*config.statuses, 'archived']}",
            )
        if priority and priority not in config.priorities:
            raise ValidationError(
                code="ERR_INVALID_PRIORITY",
                user_message=f"priority must be one of {config.priorities}",
            )
        if archival_reason and archival_reason not in config.archival_reasons:
            raise ValidationError(
                code="ERR_ARCHIVAL_REASON_INVALID",
                user_message=(
                    f"archival_reason must be one of {sorted(config.archival_reasons)}"
                ),
            )

        if ids and (
            status
            or tag
            or priority
            or search
            or unclaimed
            or blocked is not None
            or archival_reason
        ):
            raise ValidationError(
                code="ERR_IDS_EXCLUSIVE",
                user_message="ids cannot be combined with other filters",
            )

        missing_ids: list[int] | None = None
        if ids:
            active_tasks = self.engine.list_tasks(archived=False)
            archived_tasks = self.engine.list_tasks(archived=True)
            found_by_id = {task.id: task for task in [*active_tasks, *archived_tasks]}
            wanted = set(ids)
            tasks = [task for task_id, task in found_by_id.items() if task_id in wanted]
            found = {task.id for task in tasks}
            missing = sorted(wanted - found)
            missing_ids = missing or None
        else:
            read_archived = archived or status == "archived"
            tasks = self.engine.list_tasks(
                status=status,
                tag=tag,
                priority=priority,
                search=search,
                sort=sort,
                unclaimed=unclaimed,
                archived=read_archived,
                limit=limit,
                reverse=reverse,
                blocked=blocked,
            )
            if archival_reason:
                tasks = [task for task in tasks if task.archival_reason == archival_reason]

        return ListTasksResponse(tasks=tasks, guidance=[], missing_ids=missing_ids)

    def show_task(self, task_id: int, section: str | None = None) -> ShowTaskResponse:
        try:
            task = self.engine.show_task(str(task_id))
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc

        payload = task.model_dump()
        if isinstance(payload.get("body"), list):
            payload["body"] = None

        guidance: list[str] = []
        missing_sections: list[str] | None = None

        if section is not None:
            section_name = section.strip()
            if not section_name:
                raise ValidationError(
                    code="ERR_SECTION_EMPTY",
                    user_message="section must not be an empty string",
                )

            body_text = payload.get("body") if isinstance(payload.get("body"), str) else ""
            matches = [
                part
                for part in parse_body(body_text)
                if part.heading is not None
                and part.heading.strip().casefold() == section_name.casefold()
            ]
            if not matches:
                payload["body"] = None
                missing_sections = [section_name]
            else:
                payload["body"] = "\n".join(match.content for match in matches)
                if len(matches) > 1:
                    guidance.append(
                        f"Section '{section_name}' matched {len(matches)} occurrences."
                    )

        payload["guidance"] = guidance
        payload["missing_sections"] = missing_sections
        return ShowTaskResponse.model_validate(payload)

    def pick_tasks(self, wave_size: int | None = None, max_waves: int = 3) -> PickTasksResponse:
        if max_waves < 1:
            raise ValidationError(
                code="ERR_INVALID_WAVE_PARAM",
                user_message="max_waves must be >= 1",
            )
        if wave_size is not None and wave_size < 1:
            raise ValidationError(
                code="ERR_INVALID_WAVE_PARAM",
                user_message="wave_size must be >= 1",
            )

        active = self.engine.list_tasks(archived=False, blocked=False, unclaimed=True)
        dispatchable = [task for task in active if task.status == "todo"]
        if not dispatchable:
            return PickTasksResponse(waves=[], guidance=[])

        effective_wave = wave_size if wave_size is not None else self.engine.board_config().wave_size
        max_items = effective_wave * max_waves
        selected = dispatchable[:max_items]

        status_agents = self.engine.board_config().agent_map
        default_agent = ""
        waves: list[Wave] = []
        for wave_index, start in enumerate(range(0, len(selected), effective_wave)):
            chunk = selected[start : start + effective_wave]
            entries = [
                DispatchEntry(
                    id=task.id,
                    status=task.status,
                    priority=task.priority,
                    title=task.title,
                    tags=list(task.tags),
                    agent=(status_agents.get(task.status) or [default_agent])[0],
                )
                for task in chunk
            ]
            waves.append(Wave(index=wave_index, tasks=entries))

        guidance = [f"Dispatch hints: {len(selected)} task(s) across {len(waves)} wave(s)."]
        return PickTasksResponse(waves=waves, guidance=guidance)

    def create_task(  # noqa: PLR0913
        self,
        *,
        title: str,
        body: str = "",
        priority: str = "",
        tags: list[str] | None = None,
        parent: int | None = None,
        depends_on: list[int] | None = None,
    ) -> SingleTaskResponse:
        if not title.strip():
            raise ValidationError(
                code="ERR_INVALID_STATUS",
                user_message="title must not be empty",
            )
        self._validate_body_size(body)

        if parent is not None and not self._task_exists(parent):
            raise ValidationError(
                code="ERR_PARENT_NOT_FOUND",
                user_message=f"Parent task '{parent}' not found",
            )

        dep_ids = depends_on or []
        missing_dep = next(
            (dep_id for dep_id in dep_ids if not self._task_exists(dep_id)),
            None,
        )
        if missing_dep is not None:
            raise ValidationError(
                code="ERR_DEP_NOT_FOUND",
                user_message=f"Dependency task '{missing_dep}' not found",
            )

        config = self.engine.board_config()
        entry_status = config.entry_status
        predicate_spec = config.status_predicates.get(entry_status)
        if (
            isinstance(predicate_spec, dict)
            and predicate_spec.get("type") == "required_sections"
        ):
            sections = predicate_spec.get("sections")
            required = [str(section) for section in sections] if isinstance(sections, list) else []
            if not self._required_sections_passes(body, required):
                raise ValidationError(
                    code="ERR_PREDICATE_FAILED",
                    user_message=f"Task body does not satisfy predicate for status '{entry_status}'",
                )

        try:
            task = self.engine.create_task(
                title=title,
                body=body,
                status=entry_status,
                priority=priority,
                tags=tags,
                parent=parent,
                depends_on=depends_on,
            )
        except ValueError as exc:
            raise ValidationError(code="ERR_INVALID_STATUS", user_message=str(exc)) from exc

        guidance: list[str] = []
        if len(body.encode("utf-8")) > 100 * 1024:
            guidance.append(self._BODY_SIZE_WARNING)
        return self._to_single_response(task, guidance)

    def edit_task(  # noqa: C901, PLR0912, PLR0913, PLR0915
        self,
        task_id: int,
        *,
        body: str = "",
        append_body: str = "",
        timestamp: bool = False,
        priority: str = "",
        parent: int = 0,
        add_dep: list[int] | None = None,
        remove_dep: list[int] | None = None,
        add_tag: list[str] | None = None,
        remove_tag: list[str] | None = None,
        block_reason: str | None | object = _BLOCK_REASON_UNSET,
        archival_reason: str = "",
        archival_refs: list[int] | None = None,
    ) -> SingleTaskResponse:
        try:
            existing = self.engine.show_task(str(task_id))
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc

        config = self.engine.board_config()
        body_set = bool(body)
        append_set = bool(append_body)
        archival_reason_set = bool(archival_reason)
        archival_refs_set = archival_refs is not None
        block_reason_set = block_reason is not _BLOCK_REASON_UNSET
        append_payload = append_body
        append_resulting_body = ""

        if body_set and append_set:
            raise ValidationError(
                code="ERR_BODY_EXCLUSIVE",
                user_message="body and append_body cannot both be set",
            )

        if body_set:
            self._validate_body_size(body)

        if parent > 0 and not self._task_exists(parent):
            raise ValidationError(
                code="ERR_PARENT_NOT_FOUND",
                user_message=f"Parent task '{parent}' not found",
            )

        for dep_id in add_dep or []:
            if not self._task_exists(dep_id):
                raise ValidationError(
                    code="ERR_DEP_NOT_FOUND",
                    user_message=f"Dependency task '{dep_id}' not found",
                )

        if append_set:
            if timestamp:
                stamp = datetime.now(tz=UTC).replace(microsecond=0).isoformat()
                append_payload = f"{stamp}\n{append_body}"
            current_body = existing.body if isinstance(existing.body, str) else ""
            append_resulting_body = current_body + "\n" + append_payload
            self._validate_body_size(append_resulting_body)

        if archival_reason_set or archival_refs_set:
            if existing.status != "archived":
                raise ValidationError(
                    code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
                    user_message="archival fields are only allowed on archived tasks",
                )

            effective_reason = (
                archival_reason if archival_reason_set else (existing.archival_reason or "")
            )
            effective_refs = archival_refs if archival_refs_set else list(existing.archival_refs)

            if archival_reason_set and effective_reason not in config.archival_reasons:
                raise ValidationError(
                    code="ERR_ARCHIVAL_REASON_INVALID",
                    user_message=(
                        "archival_reason must be one of "
                        f"{sorted(config.archival_reasons)}"
                    ),
                )

            if effective_reason in {"deprecated", "duplicate"} and not effective_refs:
                raise ValidationError(
                    code="ERR_ARCHIVAL_REFS_REQUIRED",
                    user_message=f"archival_refs required for archival_reason='{effective_reason}'",
                )

            if effective_reason in {"completed", "dropped", "wontfix"} and effective_refs:
                raise ValidationError(
                    code="ERR_ARCHIVAL_REFS_FORBIDDEN",
                    user_message=f"archival_refs forbidden for archival_reason='{effective_reason}'",
                )

            if effective_reason == "completed" and existing.status != config.terminal_status:
                raise ValidationError(
                    code="ERR_COMPLETED_REQUIRES_DONE",
                    user_message="archival_reason='completed' requires terminal status",
                )

            for ref_id in effective_refs:
                if ref_id == task_id:
                    raise ValidationError(
                        code="ERR_ARCHIVAL_REF_SELF",
                        user_message="archival_refs cannot include the task itself",
                    )
                if not self._task_exists(ref_id):
                    raise ValidationError(
                        code="ERR_ARCHIVAL_REF_MISSING",
                        user_message=f"archival reference task '{ref_id}' not found",
                    )

            if self._has_archival_cycle(task_id, effective_refs):
                raise ValidationError(
                    code="ERR_ARCHIVAL_REF_CYCLE",
                    user_message="archival_refs would introduce a cycle",
                )

        kwargs: dict[str, object] = {}
        if body:
            kwargs["body"] = body
        if append_set:
            kwargs["append_body"] = append_payload
        if priority:
            kwargs["priority"] = priority
        if parent > 0:
            kwargs["parent"] = parent
        if add_dep is not None:
            kwargs["add_deps"] = add_dep
        if remove_dep is not None:
            kwargs["remove_deps"] = remove_dep
        if add_tag is not None:
            kwargs["add_tags"] = add_tag
        if remove_tag is not None:
            kwargs["remove_tags"] = remove_tag
        if block_reason_set:
            if block_reason:
                kwargs["blocked"] = True
                kwargs["block_reason"] = block_reason
            else:
                kwargs["blocked"] = False
                kwargs["block_reason"] = None
        if archival_reason_set:
            kwargs["archival_reason"] = archival_reason
        if archival_refs_set:
            kwargs["archival_refs"] = archival_refs

        if not kwargs and not archival_reason_set and not archival_refs_set:
            raise ValidationError(
                code="ERR_NO_OP",
                user_message="No changes requested",
            )

        changes_requested = False
        if body_set and body.rstrip("\n") != existing.body.rstrip("\n"):
            changes_requested = True
        if append_set:
            changes_requested = True
        if priority and priority != existing.priority:
            changes_requested = True
        if parent > 0 and parent != existing.parent:
            changes_requested = True
        if add_dep is not None and any(dep_id not in existing.depends_on for dep_id in add_dep):
            changes_requested = True
        if remove_dep is not None and any(dep_id in existing.depends_on for dep_id in remove_dep):
            changes_requested = True
        if add_tag is not None and any(tag not in existing.tags for tag in add_tag):
            changes_requested = True
        if remove_tag is not None and any(tag in existing.tags for tag in remove_tag):
            changes_requested = True
        if block_reason_set:
            if block_reason:
                changes_requested = changes_requested or (
                    existing.blocked is not True or existing.block_reason != block_reason
                )
            else:
                changes_requested = changes_requested or (
                    existing.blocked is not False or existing.block_reason is not None
                )
        if archival_reason_set:
            changes_requested = changes_requested or (
                (archival_reason or None) != (existing.archival_reason or None)
            )
        if archival_refs_set:
            changes_requested = changes_requested or (
                list(archival_refs or []) != list(existing.archival_refs)
            )

        if not changes_requested:
            raise ValidationError(
                code="ERR_NO_OP",
                user_message="No changes requested",
            )

        try:
            task = self.engine.edit_task(str(task_id), **kwargs)
        except ValueError as exc:
            raise ValidationError(code="ERR_INVALID_STATUS", user_message=str(exc)) from exc

        guidance: list[str] = []
        if body_set and len(body.encode("utf-8")) > 100 * 1024:
            guidance.append(self._BODY_SIZE_WARNING)
        if append_set and len(append_resulting_body.encode("utf-8")) > 100 * 1024:
            guidance.append(self._BODY_SIZE_WARNING)
        return self._to_single_response(task, guidance)

    def move_task(
        self,
        task_id: int,
        status: str,
        *,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
    ) -> SingleTaskResponse:
        _ = (archival_reason, archival_refs)
        try:
            before = self.engine.show_task(str(task_id))
            task = self.engine.move_task(str(task_id), status)
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc
        except ValueError as exc:
            raise ValidationError(code="ERR_INVALID_STATUS", user_message=str(exc)) from exc

        guidance = self._skip_transition_guidance(
            before_status=before.status,
            after_status=task.status,
            status_names=self.engine.board_config().statuses,
        )
        return self._to_single_response(task, guidance)

    def start_work(self, task_id: int) -> SingleTaskResponse:
        try:
            task = self.engine.start_work(str(task_id))
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc
        except ValueError as exc:
            msg = str(exc)
            if "already claimed" in msg:
                raise ConcurrencyError(
                    code="ERR_ALREADY_CLAIMED",
                    user_message=f"Task '{task_id}' is already claimed by another agent",
                ) from exc
            raise ValidationError(code="ERR_INVALID_STATUS", user_message=msg) from exc
        return self._to_single_response(task)

    def end_work(  # noqa: PLR0913
        self,
        task_id: int,
        *,
        outcome: str,
        note: str,
        move_to: str | None = None,
        block_reason: str | None = None,
        archival_reason: str | None = None,
        archival_refs: list[int] | None = None,
    ) -> SingleTaskResponse:
        _ = (archival_reason, archival_refs)
        try:
            before = self.engine.show_task(str(task_id))
            task = self.engine.end_work(
                str(task_id),
                note=note,
                outcome=outcome,
                block_reason=block_reason or "",
                move_to=move_to or "research",
            )
        except FileNotFoundError as exc:
            raise self._wrap_not_found(task_id) from exc
        except ValueError as exc:
            msg = str(exc)
            if "already claimed" in msg:
                raise ConcurrencyError(
                    code="ERR_ALREADY_CLAIMED",
                    user_message=f"Task '{task_id}' is already claimed by another agent",
                ) from exc
            raise ValidationError(code="ERR_INVALID_OUTCOME", user_message=msg) from exc

        guidance: list[str] = []
        if outcome == "reject":
            guidance = self._skip_transition_guidance(
                before_status=before.status,
                after_status=task.status,
                status_names=self.engine.board_config().statuses,
                include_target_column=True,
            )
        elif outcome == "block":
            guidance = [self._BLOCK_AR_HINT]
        return self._to_single_response(task, guidance)


class CockpitView:
    """Minimal role-scoped wrapper for cockpit-facing engine use."""

    def __init__(self, engine: KanbanEngine) -> None:
        self.engine = engine

    def list_tasks(self) -> None:
        raise NotImplementedError

    def show_task(self, task_id: int) -> None:
        _ = task_id
        raise NotImplementedError

    def edit_task(self, task_id: int) -> None:
        _ = task_id
        raise NotImplementedError

    def move_task(self, task_id: int, status: str) -> None:
        _ = (task_id, status)
        raise NotImplementedError

    def release_task(self, task_id: int) -> None:
        _ = task_id
        raise NotImplementedError

    def board_config(self) -> None:
        raise NotImplementedError
