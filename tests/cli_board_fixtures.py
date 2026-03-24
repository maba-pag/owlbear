"""Fixture helpers for board CLI tests.

These helpers mirror the JSON payload shapes returned by:

- ``kanban-md list --json`` for tasks
- ``kanban-md log --action move --json`` for move log entries
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
    """Build a task payload matching ``kanban-md list --json`` output."""
    task: dict[str, object] = {
        "id": task_id,
        "title": title,
        "status": status,
        "tags": list(tags) if tags is not None else [],
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
    """Build a move payload matching ``kanban-md log --action move --json`` output."""
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
    """Serialize paired list/log payloads to JSON strings."""
    return json.dumps(tasks), json.dumps(moves)
