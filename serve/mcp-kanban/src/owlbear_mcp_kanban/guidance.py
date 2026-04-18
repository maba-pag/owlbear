"""Contextual guidance messages for kanban MCP operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_mcp_kanban.models import KanbanTask

_BLOCK_OPS = frozenset(("edit_block", "end_work_block"))


def collect_guidance(
    operation: str,
    before: KanbanTask,
    after: KanbanTask,
    **kwargs: object,
) -> list[str]:
    """Return contextual guidance messages for the given operation.

    Args:
        operation: One of ``edit_block``, ``end_work_block``, ``move``,
            ``end_work_success``, or any unknown string.
        before: Task state before the operation.
        after: Task state after the operation.
        **kwargs: Operation-specific keyword arguments (e.g. ``statuses`` for move).

    Returns:
        A list of guidance message strings, or ``[]`` when no guidance applies.
    """
    if operation in _BLOCK_OPS:
        return _block_guidance(after)
    if operation == "move":
        return _move_guidance(before, after, kwargs)
    if operation == "end_work_success":
        return ["Remember to commit and push your changes before advancing the task."]
    return []


def _block_guidance(after: KanbanTask) -> list[str]:
    if "block:user" in after.tags:
        return []
    return [
        "Decision Request: blocking a task without the 'block:user' tag"
        " requires a Decision Request (DR) in the task body."
    ]


def _move_guidance(
    before: KanbanTask,
    after: KanbanTask,
    kwargs: dict[str, object],
) -> list[str]:
    statuses: list[str] = list(kwargs.get("statuses", []))  # type: ignore[arg-type]
    if not statuses:
        return []
    try:
        delta = statuses.index(after.status) - statuses.index(before.status)
    except ValueError:
        return []
    if delta > 1:
        return [
            f"Forward skip of {delta} slots detected"
            f" ({before.status} → {after.status})."
            " Consider advancing step-by-step through the pipeline."
        ]
    return []
