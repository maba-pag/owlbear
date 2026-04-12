"""KanbanEngine — native read/write engine for the owlbear kanban board.

Provides KanbanEngine, a filesystem-backed implementation for listing,
reading, and writing kanban task files without invoking the kanban-md CLI.

Architecture:
  - Constructor loads BoardConfig via config_loader.load_config().
  - list_tasks() scans tasks_dir (or archive dir), applies filters,
    sorts by config-ranked field, and returns list[TaskSummary].
  - show_task() finds a single task file by ID and returns its Task.
  - create_task() allocates next_id, writes a new task file, increments config.
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
import random
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from owlbear_kanban.activity_log import log_activity
from owlbear_kanban.agent_names import ADJECTIVES, NOUNS
from owlbear_kanban.config_loader import load_config, save_config
from owlbear_kanban.models import BoardConfig, Task, TaskSummary
from owlbear_kanban.task_io import make_task_filename, read_task, validate_path_containment, write_task

if TYPE_CHECKING:
    from pathlib import Path

_ARCHIVE_DIR_NAME = "archive"


class KanbanEngine:
    """Native kanban engine backed by filesystem task files.

    All mutating operations (create, edit, move, claim, release) append an
    entry to ``{kanban_dir}/activity.jsonl``, creating the file on first write.

    Args:
        kanban_dir:  Root directory of the kanban board.
        agent_name:  Fixed agent identity for this instance.  Generated as
                     ``{adjective}-{noun}`` from the ``agent_names`` pool if
                     omitted; stable across all calls on the same instance.
    """

    def __init__(self, kanban_dir: Path, *, agent_name: str | None = None) -> None:
        self._kanban_dir = kanban_dir
        self._config: BoardConfig = load_config(kanban_dir)
        self._tasks_dir = kanban_dir / self._config.tasks_dir
        self._archive_dir = kanban_dir / _ARCHIVE_DIR_NAME
        self._agent_name: str = (
            agent_name
            if agent_name is not None
            else f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"  # noqa: S311
        )
        self._activity_log_path = kanban_dir / "activity.jsonl"
        self._revision: int = 0

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
        return {s["name"]: i for i, s in enumerate(self._config.statuses)}

    # ------------------------------------------------------------------
    # Config management
    # ------------------------------------------------------------------

    def board_config(self) -> BoardConfig:
        """Return a defensive copy of the current cached :class:`BoardConfig`.

        The returned object is a deep ``model_copy(deep=True)`` — mutating it
        (including nested lists and dicts) does not affect engine state.
        """
        return self._config.model_copy(deep=True)

    def refresh_config(self) -> None:
        """Reload config from disk and update all derived state.

        After calling this method, ``_status_rank()`` and ``_priority_rank()``
        use the newly loaded config values. Also updates ``_tasks_dir`` and
        ``_archive_dir`` to reflect any tasks_dir change in config.
        """
        self._config = load_config(self._kanban_dir)
        self._tasks_dir = self._kanban_dir / self._config.tasks_dir
        self._archive_dir = self._kanban_dir / _ARCHIVE_DIR_NAME

    def valid_transitions(self, status: str) -> set[str]:
        """Return the set of all configured statuses except *status*.

        Args:
            status: The current status to exclude from the result.

        Returns:
            Set of valid target status names.

        Raises:
            ValueError: *status* is not a configured status.
        """
        valid_statuses = {s["name"] for s in self._config.statuses}
        if status not in valid_statuses:
            msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
            raise ValueError(msg)
        return valid_statuses - {status}

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def list_tasks(  # noqa: PLR0912, PLR0913, C901
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
            unclaimed: When True, only tasks with no claimed_by value.
            archived:  When True, read from archive/ instead of tasks_dir.
            limit:     Cap on results (0 = unlimited).
            reverse:   When True, reverse the sort order.
            blocked:   True = only blocked; False = only unblocked; None = all.

        Returns:
            Filtered, sorted list of :class:`TaskSummary` objects.
        """
        source_dir = self._archive_dir if archived else self._tasks_dir
        tasks: list[Task] = []
        for path in source_dir.glob("*.md"):
            with contextlib.suppress(ValueError, KeyError):
                tasks.append(read_task(path))

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
            tasks = [t for t in tasks if t.claimed_by is None]
        if search:
            needle = search.lower()
            tasks = [
                t for t in tasks
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

        return [TaskSummary.model_validate(t.model_dump()) for t in tasks]

    def show_task(self, task_id: str) -> Task:
        """Return the :class:`Task` for a single task by its string ID.

        Args:
            task_id: The numeric task ID as a string (e.g. ``"42"``).

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md`` in tasks_dir.
        """
        matches = list(self._tasks_dir.glob(f"{task_id}-*.md"))
        if not matches:
            msg = f"Task {task_id!r} not found in {self._tasks_dir}"
            raise FileNotFoundError(msg)
        return read_task(matches[0])

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
        """Allocate next_id, write a new task file, and increment config next_id.

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
            valid_statuses = {s["name"] for s in config.statuses}
            if status not in valid_statuses:
                msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
                raise ValueError(msg)
        if priority and priority not in config.priorities:
            msg = f"Invalid priority {priority!r}. Valid options: {config.priorities}"
            raise ValueError(msg)

        task_id = config.next_id
        now = datetime.now(tz=UTC).isoformat()

        record = Task(
            id=task_id,
            title=title,
            status=status or config.defaults.status,
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
        write_task(task_path, record)

        config.next_id = task_id + 1
        save_config(self._kanban_dir, config)
        self._config = config
        self._tasks_dir = self._kanban_dir / self._config.tasks_dir
        self._archive_dir = self._kanban_dir / _ARCHIVE_DIR_NAME

        log_activity(self._activity_log_path, "create", record.id, record.title, actor=self._agent_name)
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

        Returns:
            Updated :class:`Task`.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
            ValueError: ``status`` or ``priority`` is not a valid configured value.
        """
        if status is not None:
            valid_statuses = {s["name"] for s in self._config.statuses}
            if status not in valid_statuses:
                msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
                raise ValueError(msg)
        if priority is not None and priority not in self._config.priorities:
            msg = f"Invalid priority {priority!r}. Valid options: {self._config.priorities}"
            raise ValueError(msg)

        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path)
        old_blocked = record.blocked

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

        record.updated = datetime.now(tz=UTC).isoformat()

        write_task(task_path, record)

        if blocked is not None and old_blocked != record.blocked:
            if record.blocked:
                log_activity(self._activity_log_path, "block", record.id, block_reason or "", actor=self._agent_name)
            else:
                log_activity(self._activity_log_path, "unblock", record.id, "", actor=self._agent_name)
        else:
            changed = [name for name, val in [
                ("title", title), ("body", body), ("priority", priority),
                ("status", status), ("parent", parent), ("add_tags", add_tags),
                ("remove_tags", remove_tags), ("add_deps", add_deps),
                ("remove_deps", remove_deps), ("blocked", blocked),
                ("block_reason", block_reason), ("append_body", append_body),
            ] if val is not None]
            log_activity(
                self._activity_log_path, "edit", record.id,
                ", ".join(changed) or "updated", actor=self._agent_name,
            )

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
        valid_statuses = {s["name"] for s in self._config.statuses}
        if status != "archived" and status not in valid_statuses:
            msg = f"Invalid status {status!r}. Valid options: {sorted(valid_statuses)}"
            raise ValueError(msg)

        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path)
        old_status = record.status

        if status == "archived":
            self._archive_dir.mkdir(parents=True, exist_ok=True)
            dest = self._archive_dir / task_path.name
            task_path.replace(dest)
            record.status = "archived"
        else:
            record.status = status
            record.updated = datetime.now(tz=UTC).isoformat()
            write_task(task_path, record)

        log_activity(
            self._activity_log_path, "move", record.id,
            f"{old_status} -> {record.status}", actor=self._agent_name,
        )
        self._revision += 1
        return record

    def claim_task(self, task_id: str, *, now: datetime | None = None) -> Task:
        """Claim a task for this engine's agent.

        Args:
            task_id: Numeric task ID as a string.
            now:     Reference time for expiry calculation (injectable for tests).
                     Defaults to ``datetime.now(UTC)``.

        Returns:
            Updated :class:`Task` with ``claimed_by`` and ``claimed_at`` set.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
            ValueError: Task is blocked, or already claimed by a different agent
                        whose claim has not expired.
        """
        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path)

        if record.blocked:
            msg = f"Task {task_id!r} is blocked and cannot be claimed"
            raise ValueError(msg)

        effective_now = now if now is not None else datetime.now(tz=UTC)

        if record.claimed_by is not None and record.claimed_by != self._agent_name:
            # Reject unless the existing claim has expired.
            timeout = self._parse_claim_timeout()
            claimed_at_dt = datetime.fromisoformat(record.claimed_at)  # type: ignore[arg-type]
            if effective_now < claimed_at_dt + timeout:
                msg = f"Task {task_id!r} is already claimed by {record.claimed_by!r}"
                raise ValueError(msg)

        record.claimed_by = self._agent_name
        record.claimed_at = effective_now.isoformat()
        record.updated = effective_now.isoformat()
        write_task(task_path, record)
        log_activity(self._activity_log_path, "claim", record.id, self._agent_name, actor=self._agent_name)
        self._revision += 1
        return record

    def release_task(self, task_id: str) -> Task:
        """Release the claim on a task, clearing ``claimed_by`` and ``claimed_at``.

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

        record.claimed_by = None
        record.claimed_at = None
        record.updated = datetime.now(tz=UTC).isoformat()
        write_task(task_path, record)
        log_activity(self._activity_log_path, "release", record.id, self._agent_name, actor=self._agent_name)
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

        Args:
            task_id:      Numeric task ID as a string.
            note:         Text to append (prefixed with ``[[YYYY-MM-DD]]`` timestamp).
            outcome:      One of ``"success"``, ``"fail"``, ``"block"``, ``"reject"``.
            block_reason: Required when *outcome* is ``"block"``; stored on the task.
            move_to:      Target status when *outcome* is ``"reject"`` (default ``"research"``).

        Returns:
            Updated :class:`Task` reflecting the new state.

        Raises:
            ValueError:        *outcome* is ``"block"`` but *block_reason* is empty.
            FileNotFoundError: No task matching ``task_id``.

        Note:
            The ``"success"`` outcome advances the task to the next status in the
            configured sequence.  This linear progression is an **agent-specific
            convention** used in OwlBear pipeline workflows — it is not enforced
            by the underlying state machine.  For the full set of reachable
            statuses from a given state, see :meth:`valid_transitions`.
        """
        if outcome == "block" and not block_reason:
            msg = "block_reason is required when outcome='block'"
            raise ValueError(msg)

        # Append timestamped note first (before any status/claim mutation).
        self.edit_task(task_id, append_body=note, timestamp=True)

        if outcome == "success":
            statuses = [s["name"] for s in self._config.statuses]
            record = self.show_task(task_id)
            current_idx = statuses.index(record.status) if record.status in statuses else -1
            is_last = current_idx == len(statuses) - 1

            if is_last:
                self.release_task(task_id)
                return self.move_task(task_id, "archived")

            next_status = statuses[current_idx + 1]
            self.release_task(task_id)
            return self.move_task(task_id, next_status)

        if outcome == "fail":
            return self.release_task(task_id)

        if outcome == "block":
            self.edit_task(task_id, blocked=True, block_reason=block_reason)
            return self.release_task(task_id)

        if outcome == "reject":
            self.release_task(task_id)
            return self.move_task(task_id, move_to)

        msg = f"Unknown outcome: {outcome!r}"
        raise ValueError(msg)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_claim_timeout(self) -> timedelta:
        """Parse the ``claim_timeout`` string from config into a :class:`timedelta`.

        Supported suffixes: ``h`` (hours), ``m`` (minutes).

        Raises:
            ValueError: Unrecognised timeout format.
        """
        raw = self._config.claim_timeout
        if raw.endswith("h"):
            return timedelta(hours=int(raw[:-1]))
        if raw.endswith("m"):
            return timedelta(minutes=int(raw[:-1]))
        msg = f"Unsupported claim_timeout format: {raw!r}"
        raise ValueError(msg)

    def _find_task_path(self, task_id: str, search_dir: Path) -> Path:
        """Return the path of ``{task_id}-*.md`` in *search_dir*.

        Raises:
            FileNotFoundError: No matching file found.
        """
        matches = list(search_dir.glob(f"{task_id}-*.md"))
        if not matches:
            msg = f"Task {task_id!r} not found in {search_dir}"
            raise FileNotFoundError(msg)
        return matches[0]
