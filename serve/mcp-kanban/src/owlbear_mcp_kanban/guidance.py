"""Contextual guidance messages for kanban MCP operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_mcp_kanban.models import KanbanTask

# Legacy operation aliases (from task #974 RED phase — kept for backward compat)
_BLOCK_OP_ALIASES = frozenset(("edit_block", "end_work_block"))

_DR_REQUIRED_MSG = (
    "⚠️ ACTION REQUIRED: Create a Decision Request via the create_dr tool."
    " Blocks without a DR are invisible to the pipeline."
)
_COMMIT_REMINDER_MSG = "Reminder: verify your changes are committed before this task advances."


def collect_guidance(
    operation: str,
    before: KanbanTask | None,
    after: KanbanTask,
    **kwargs: object,
) -> list[str]:
    """Return contextual guidance messages for the given operation.

    Supports both the legacy API (edit_block, end_work_block, end_work_success)
    and the current approved API (edit_task, end_work with outcome kwarg, move
    with status_names kwarg).

    Args:
        operation: The operation being performed.
        before: Task state before the operation (may be None for non-move ops).
        after: Task state after the operation.
        **kwargs: Operation-specific keyword arguments. Recognised keys:
            - outcome: "block" | "success" | "fail" | "reject" (for end_work)
            - status_names: list[str] (current API, for move)
            - statuses: list[str] (legacy kwarg alias, for move)

    Returns:
        A list of guidance message strings, or ``[]`` when no guidance applies.
    """
    messages: list[str] = []

    if _is_block_operation(operation, after, kwargs):
        messages.extend(_block_guidance(after))

    if _is_success_operation(operation, kwargs):
        messages.append(_COMMIT_REMINDER_MSG)

    if operation == "move":
        messages.extend(_move_guidance(before, after, kwargs))

    return messages


def _is_block_operation(
    operation: str,
    after: KanbanTask,
    kwargs: dict[str, object],
) -> bool:
    # Legacy operation aliases (pre-AC)
    if operation in _BLOCK_OP_ALIASES:
        return True
    # AC: Block DR rule fires for ANY operation when after.blocked is True
    if after.blocked:
        return True
    # Legacy trigger: caller signals blocking via outcome kwarg before setting after.blocked
    return operation == "end_work" and kwargs.get("outcome") == "block"


def _is_success_operation(operation: str, kwargs: dict[str, object]) -> bool:
    if operation == "end_work_success":
        return True
    return operation == "end_work" and kwargs.get("outcome") == "success"


def _block_guidance(after: KanbanTask) -> list[str]:
    if "block:user" in after.tags:
        return []
    return [_DR_REQUIRED_MSG]


def _move_guidance(
    before: KanbanTask | None,
    after: KanbanTask,
    kwargs: dict[str, object],
) -> list[str]:
    if before is None:
        return []
    # Support both status_names (current API) and statuses (legacy alias)
    status_names: list[str] = list(
        kwargs.get("status_names") or kwargs.get("statuses") or []  # type: ignore[arg-type]
    )
    if not status_names:
        return []
    try:
        from_idx = status_names.index(before.status)
        to_idx = status_names.index(after.status)
    except ValueError:
        return []
    delta = to_idx - from_idx
    if delta > 1:
        n = delta - 1
        return [
            f"⚠️ Status skip: moved from '{before.status}' to '{after.status}'"
            f" (skipped {n} column(s)). Verify this jump is intentional."
        ]
    return []
