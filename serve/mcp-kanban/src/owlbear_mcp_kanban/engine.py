"""KanbanEngine — native read/write engine for the owlbear kanban board.

Provides KanbanEngine, a filesystem-backed implementation for listing,
reading, and writing kanban task files without invoking the kanban-md CLI.

Architecture:
  - Constructor loads BoardConfig via config_loader.load_config().
  - list_tasks() scans tasks_dir (or archive dir), applies filters,
    sorts by config-ranked field, and returns list[TaskRecord].
  - show_task() finds a single task file by ID and returns its TaskRecord.
  - create_task() allocates next_id, writes a new task file, increments config.
  - edit_task() modifies task fields in-place; slug/filename never changes.
  - move_task() changes status; "archived" moves file to v1-archive/.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_mcp_kanban.config_loader import load_config, save_config
from owlbear_mcp_kanban.engine_models import TaskRecord
from owlbear_mcp_kanban.task_io import make_task_filename, read_task, validate_path_containment, write_task

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_mcp_kanban.engine_models import BoardConfig

_ARCHIVE_DIR_NAME = "v1-archive"


class KanbanEngine:
    """Native kanban engine backed by filesystem task files."""

    def __init__(self, kanban_dir: Path) -> None:
        self._kanban_dir = kanban_dir
        self._config: BoardConfig = load_config(kanban_dir)
        self._tasks_dir = kanban_dir / self._config.tasks_dir
        self._archive_dir = kanban_dir / _ARCHIVE_DIR_NAME

    # ------------------------------------------------------------------
    # Config-derived rank maps
    # ------------------------------------------------------------------

    def _priority_rank(self) -> dict[str, int]:
        return {p: i for i, p in enumerate(self._config.priorities)}

    def _status_rank(self) -> dict[str, int]:
        return {s["name"]: i for i, s in enumerate(self._config.statuses)}

    # ------------------------------------------------------------------
    # Public API
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
    ) -> list[TaskRecord]:
        """Return filtered, sorted, and paginated list of :class:`TaskRecord`.

        Args:
            status:    Only return tasks with this status.  Empty = no filter.
            tag:       Only return tasks that include this tag.  Empty = no filter.
            priority:  Only return tasks with this priority.  Empty = no filter.
            search:    Case-insensitive substring match on title and body.
            sort:      Field to sort by: id, title, status, priority, created, updated.
            unclaimed: When True, only tasks with no claimed_by value.
            archived:  When True, read from v1-archive/ instead of tasks_dir.
            limit:     Cap on results (0 = unlimited).
            reverse:   When True, reverse the sort order.
            blocked:   True = only blocked; False = only unblocked; None = all.

        Returns:
            Filtered, sorted list of :class:`TaskRecord` objects.
        """
        source_dir = self._archive_dir if archived else self._tasks_dir
        tasks: list[TaskRecord] = []
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
                tasks.sort(key=lambda t: t.created)
            elif sort == "updated":
                tasks.sort(key=lambda t: t.updated)

        if reverse:
            tasks.reverse()

        if limit > 0:
            tasks = tasks[:limit]

        return tasks

    def show_task(self, task_id: str) -> TaskRecord:
        """Return the :class:`TaskRecord` for a single task by its string ID.

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
    ) -> TaskRecord:
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
            The newly created :class:`TaskRecord`.
        """
        config: BoardConfig = load_config(self._kanban_dir)
        task_id = config.next_id
        now = datetime.now(tz=UTC).isoformat()

        record = TaskRecord(
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

        return record

    def edit_task(  # noqa: PLR0912, PLR0913, C901
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
    ) -> TaskRecord:
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
            Updated :class:`TaskRecord`.

        Raises:
            FileNotFoundError: No task file matching ``{task_id}-*.md``.
        """
        task_path = self._find_task_path(task_id, self._tasks_dir)
        record = read_task(task_path)

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
        return record

    def move_task(self, task_id: str, status: str) -> TaskRecord:
        """Change the status of a task; "archived" moves the file to v1-archive/.

        Args:
            task_id: Numeric task ID as a string.
            status:  Target status name, or ``"archived"`` to archive the task.

        Returns:
            Updated :class:`TaskRecord`.

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

        if status == "archived":
            self._archive_dir.mkdir(parents=True, exist_ok=True)
            dest = self._archive_dir / task_path.name
            task_path.replace(dest)
            record.status = "archived"
        else:
            record.status = status
            record.updated = datetime.now(tz=UTC).isoformat()
            write_task(task_path, record)

        return record

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
