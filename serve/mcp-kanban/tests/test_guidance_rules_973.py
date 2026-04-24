"""TDD tests for collect_guidance() NEW API (task #987).

These tests cover the approved NEW API from subtask #987's architecture review:
- operation="edit_task" with after.blocked=True for block DR rule
- operation="end_work" with outcome kwarg for block/success rules
- operation="move" with status_names= kwarg
- before=None is allowed for non-move operations

RED phase — all tests fail until guidance.py supports the new API.
"""

from __future__ import annotations

from owlbear_mcp_kanban.guidance import collect_guidance
from owlbear_mcp_kanban.models import KanbanTask

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATUSES = ["research", "backlog", "todo", "in-progress", "review", "docs", "done"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task(
    *,
    status: str = "todo",
    tags: list[str] | None = None,
    blocked: bool = False,
) -> KanbanTask:
    return KanbanTask(
        id=1,
        title="Test Task",
        status=status,
        priority="needed",
        created="2026-01-01",
        updated="2026-01-01",
        tags=tags or [],
        blocked=blocked,
    )


# ---------------------------------------------------------------------------
# TestFromAC_CollectGuidanceNewAPI
# ---------------------------------------------------------------------------


class TestFromAC_CollectGuidanceNewAPI:
    """Contract tests for collect_guidance() using the NEW approved API.

    AC coverage (subtask #987):
    - Block DR rule: edit_task with after.blocked=True → DR message
    - Block DR rule: end_work with outcome="block" → DR message
    - block:user exemption: after task with block:user tag → no DR message
    - Success/commit rule: end_work with outcome="success" → commit message
    - Fail/reject: end_work with outcome=fail/reject → empty guidance
    - Forward-skip rule: move with status_names kwarg and >1 slot jump → guidance
    - 1-slot move → empty guidance
    - Backward move → empty guidance
    - before=None allowed for non-move operations
    """

    # -- Block DR rule: edit_task -----------------------------------------

    def test_edit_task_blocked_true_returns_dr_message(self) -> None:
        """edit_task with after.blocked=True → DR-required message."""
        after = _task(blocked=True)
        result = collect_guidance("edit_task", None, after)
        assert len(result) > 0, "Expected guidance for edit_task with blocked=True"
        assert "Decision Request" in result[0], (
            f"Expected 'Decision Request' in first guidance item, got {result[0]!r}"
        )

    def test_edit_task_blocked_false_returns_empty(self) -> None:
        """edit_task with after.blocked=False → empty guidance."""
        after = _task(blocked=False)
        result = collect_guidance("edit_task", None, after)
        assert result == [], (
            f"Expected [] for edit_task with blocked=False, got {result!r}"
        )

    def test_edit_task_blocked_true_with_block_user_tag_returns_empty(self) -> None:
        """edit_task with blocked=True but block:user tag present → empty (user-driven block)."""
        after = _task(blocked=True, tags=["block:user"])
        result = collect_guidance("edit_task", None, after)
        assert result == [], (
            f"Expected [] for edit_task with block:user tag, got {result!r}"
        )

    def test_edit_task_before_none_works(self) -> None:
        """collect_guidance accepts before=None without error for edit_task."""
        after = _task(blocked=True)
        # Should not raise
        result = collect_guidance("edit_task", None, after)
        assert isinstance(result, list)

    # -- Block DR rule: end_work outcome="block" ---------------------------

    def test_end_work_outcome_block_returns_dr_message(self) -> None:
        """end_work with outcome='block' → DR-required message."""
        after = _task()
        result = collect_guidance("end_work", None, after, outcome="block")
        assert len(result) > 0, "Expected guidance for end_work with outcome=block"
        assert "Decision Request" in result[0], (
            f"Expected 'Decision Request' in first guidance item, got {result[0]!r}"
        )

    def test_end_work_outcome_block_with_block_user_tag_returns_empty(self) -> None:
        """end_work outcome='block' with block:user tag → empty (user-driven block)."""
        after = _task(tags=["block:user"])
        result = collect_guidance("end_work", None, after, outcome="block")
        assert result == [], (
            f"Expected [] for end_work/block with block:user tag, got {result!r}"
        )

    def test_end_work_outcome_fail_returns_empty(self) -> None:
        """end_work with outcome='fail' → empty guidance."""
        after = _task()
        result = collect_guidance("end_work", None, after, outcome="fail")
        assert result == [], f"Expected [] for end_work/fail, got {result!r}"

    def test_end_work_outcome_reject_returns_empty(self) -> None:
        """end_work with outcome='reject' → empty guidance."""
        after = _task()
        result = collect_guidance("end_work", None, after, outcome="reject")
        assert result == [], f"Expected [] for end_work/reject, got {result!r}"

    def test_end_work_no_outcome_returns_empty(self) -> None:
        """end_work with no outcome kwarg → empty guidance."""
        after = _task()
        result = collect_guidance("end_work", None, after)
        assert result == [], f"Expected [] for end_work with no outcome, got {result!r}"

    # -- Success/commit rule: end_work outcome="success" ------------------

    def test_end_work_outcome_success_returns_commit_message(self) -> None:
        """end_work with outcome='success' → commit reminder."""
        after = _task()
        result = collect_guidance("end_work", None, after, outcome="success")
        assert len(result) > 0, "Expected guidance for end_work with outcome=success"
        assert "commit" in result[0].lower(), (
            f"Expected 'commit' (case-insensitive) in first guidance item, got {result[0]!r}"
        )

    # -- Forward-skip rule: move with status_names kwarg ------------------

    def test_move_status_names_forward_skip_more_than_one_slot(self) -> None:
        """move with status_names kwarg and >1 slot forward skip → guidance."""
        before = _task(status="research")
        after = _task(status="todo")  # 2 slots: research→backlog→todo
        result = collect_guidance("move", before, after, status_names=STATUSES)
        assert len(result) > 0, (
            f"Expected guidance for >1-slot forward move (research→todo), got {result!r}"
        )

    def test_move_status_names_one_slot_returns_empty(self) -> None:
        """move with status_names kwarg and 1 slot forward → empty guidance."""
        before = _task(status="research")
        after = _task(status="backlog")  # 1 slot
        result = collect_guidance("move", before, after, status_names=STATUSES)
        assert result == [], (
            f"Expected [] for 1-slot forward move (research→backlog), got {result!r}"
        )

    def test_move_status_names_backward_returns_empty(self) -> None:
        """move with status_names kwarg and backward move → empty guidance."""
        before = _task(status="todo")
        after = _task(status="backlog")  # backward
        result = collect_guidance("move", before, after, status_names=STATUSES)
        assert result == [], (
            f"Expected [] for backward move (todo→backlog), got {result!r}"
        )

    def test_move_skip_guidance_contains_from_to_status(self) -> None:
        """Forward-skip guidance message references both source and target status."""
        before = _task(status="research")
        after = _task(status="todo")
        result = collect_guidance("move", before, after, status_names=STATUSES)
        assert len(result) > 0
        assert "research" in result[0], (
            f"Expected source status in message, got {result[0]!r}"
        )
        assert "todo" in result[0], (
            f"Expected target status in message, got {result[0]!r}"
        )

    def test_move_before_none_returns_empty(self) -> None:
        """move with before=None → empty guidance (can't compute delta)."""
        after = _task(status="todo")
        result = collect_guidance("move", None, after, status_names=STATUSES)
        assert result == [], f"Expected [] when before=None for move, got {result!r}"
