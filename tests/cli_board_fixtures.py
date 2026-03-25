"""Board JSON fixtures for BearClaw CLI tests.

This module provides pure helpers to build synchronized task-list and move-log
payloads for tests patching ``subprocess.run`` in the board command.
"""

from __future__ import annotations

import json


def board_task(  # noqa: PLR0913
    task_id: int = 1,
    title: str = "A task",
    status: str = "in-progress",
    tags: list[str] | None = None,
    assignee: str | None = None,
    claimed_by: str | None = None,
    created: str = "2026-01-01T10:00:00+01:00",
) -> dict[str, object]:
    """Build a kanban task payload matching ``kanban-md list --json`` shape."""
    task: dict[str, object] = {
        "id": task_id,
        "title": title,
        "status": status,
        "tags": tags or [],
        "created": created,
    }
    if assignee is not None:
        task["assignee"] = assignee
    if claimed_by is not None:
        task["claimed_by"] = claimed_by
    return task


def board_move(
    task_id: int,
    from_status: str,
    to_status: str,
    timestamp: str = "2026-03-15T10:00:00+01:00",
) -> dict[str, object]:
    """Build a move-log payload matching ``kanban-md log --action move --json``."""
    return {
        "timestamp": timestamp,
        "action": "move",
        "task_id": task_id,
        "detail": f"{from_status} -> {to_status}",
    }


def board_payloads(
    tasks: list[dict[str, object]],
    moves: list[dict[str, object]],
) -> tuple[str, str]:
    """Serialize task and move fixtures into list/log JSON payload strings."""
    return json.dumps(tasks), json.dumps(moves)


__all__ = ["board_move", "board_payloads", "board_task"]
