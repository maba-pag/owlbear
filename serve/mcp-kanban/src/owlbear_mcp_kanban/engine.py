"""KanbanEngine — native read/write engine for the owlbear kanban board.

Provides KanbanEngine, a filesystem-backed implementation for listing,
reading, and writing kanban task files without invoking the kanban-md CLI.

Architecture:
  - Constructor loads BoardConfig via config_loader.load_config().
  - list_tasks() scans tasks_dir (or archive dir), applies filters,
    sorts by config-ranked field, and returns list[TaskRecord].
  - show_task() finds a single task file by ID and returns its TaskRecord.
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from owlbear_mcp_kanban.config_loader import load_config
from owlbear_mcp_kanban.task_io import read_task

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_mcp_kanban.engine_models import BoardConfig, TaskRecord

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
