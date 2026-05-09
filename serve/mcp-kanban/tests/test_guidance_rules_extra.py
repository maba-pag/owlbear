"""TDD failing tests for collect_guidance() — task #987 AC-direct.

AC source: "Block DR rule: when `after.blocked is True`, emit [message]."
No operation restriction is stated for the block DR rule — unlike forward-skip
("when `operation == 'move'`") and success/commit ("when `operation == 'end_work'`"),
which both explicitly name their triggering operation. The absence of an operation
constraint on the DR rule means it should fire for ANY operation.

Architecture review refinement #4: "Multiple rules can co-fire. The flat tuple
registry iterates ALL rules and collects all matching messages. No early return."

These tests fail against the current implementation (which restricts DR to
edit_task and end_work/outcome='block') and define the correct AC contract.
"""

from __future__ import annotations

from owlbear_mcp_kanban.guidance import collect_guidance
from owlbear_mcp_kanban.models import KanbanTask

STATUSES = ["research", "backlog", "todo", "in-progress", "review", "docs", "done"]


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


class TestFromAC_BlockDRRuleOperationIndependence:
    """Block DR rule fires for any operation when after.blocked is True.

    AC: "Block DR rule: when `after.blocked is True`, emit [message]."
    No operation is named, unlike the other two rules. The rule predicate is
    solely `after.blocked is True` (with block:user exemption).
    """

    def test_non_edit_operation_with_blocked_true_emits_dr_message(self) -> None:
        """Block DR rule fires for operations other than edit_task when after.blocked=True.

        AC: predicate is after.blocked is True — no operation restriction.
        """
        after = _task(blocked=True)
        result = collect_guidance("start_work", None, after)
        dr_msgs = [m for m in result if "Decision Request" in m]
        assert len(dr_msgs) > 0, (
            f"Expected DR message for start_work with after.blocked=True "
            f"(AC: DR rule has no operation restriction). Got {result!r}"
        )

    def test_end_work_success_with_after_blocked_emits_dr_message(self) -> None:
        """DR rule fires alongside commit rule when end_work+outcome=success and after.blocked=True.

        AC: block DR fires when after.blocked is True (any op).
            Success/commit fires when operation==end_work and outcome==success.
        Both conditions hold simultaneously here.
        """
        after = _task(blocked=True)
        result = collect_guidance("end_work", None, after, outcome="success")
        dr_msgs = [m for m in result if "Decision Request" in m]
        assert len(dr_msgs) > 0, (
            f"Expected DR message when end_work+outcome=success and after.blocked=True. "
            f"Got {result!r}"
        )

    def test_end_work_fail_with_after_blocked_emits_dr_message(self) -> None:
        """Block DR rule fires for end_work+outcome=fail when after.blocked=True.

        AC: block DR predicate is after.blocked is True, not outcome.
        """
        after = _task(blocked=True)
        result = collect_guidance("end_work", None, after, outcome="fail")
        dr_msgs = [m for m in result if "Decision Request" in m]
        assert len(dr_msgs) > 0, (
            f"Expected DR message for end_work+outcome=fail with after.blocked=True. "
            f"Got {result!r}"
        )

    def test_move_backward_with_after_blocked_emits_dr_message(self) -> None:
        """Block DR rule fires for backward move when after.blocked=True.

        AC: after.blocked is True triggers DR regardless of direction or operation.
        Forward-skip rule does NOT fire (backward), so result should contain
        exactly the DR message.
        """
        before = _task(status="todo")
        after = _task(status="backlog", blocked=True)  # backward: delta = -1
        result = collect_guidance("move", before, after, status_names=STATUSES)
        dr_msgs = [m for m in result if "Decision Request" in m]
        assert len(dr_msgs) > 0, (
            f"Expected DR message for backward move with after.blocked=True. "
            f"Got {result!r}"
        )


class TestFromAC_MultiRuleCofiring:
    """Arch review refinement #4: all matching rules fire; no early return.

    The block DR rule (after.blocked is True) and the forward-skip rule
    (operation==move, delta>1) can co-fire when both conditions hold.
    """

    def test_blocked_move_with_forward_skip_emits_dr_and_skip_guidance(self) -> None:
        """Both DR and forward-skip fire: move with after.blocked=True and delta>1."""
        before = _task(status="research")
        after = _task(status="todo", blocked=True)  # research→todo = delta 2 (>1)
        result = collect_guidance("move", before, after, status_names=STATUSES)
        dr_msgs = [m for m in result if "Decision Request" in m]
        skip_msgs = [m for m in result if "Status skip" in m]
        assert len(dr_msgs) > 0, (
            f"Expected DR guidance in co-fire result (after.blocked=True). Got {result!r}"
        )
        assert len(skip_msgs) > 0, (
            f"Expected skip guidance in co-fire result (delta=2). Got {result!r}"
        )

    def test_end_work_success_with_blocked_emits_both_dr_and_commit(self) -> None:
        """Both DR and commit rules fire: end_work+outcome=success and after.blocked=True."""
        after = _task(blocked=True)
        result = collect_guidance("end_work", None, after, outcome="success")
        dr_msgs = [m for m in result if "Decision Request" in m]
        commit_msgs = [m for m in result if "commit" in m.lower()]
        assert len(dr_msgs) > 0, (
            f"Expected DR message in co-fire result (after.blocked=True). Got {result!r}"
        )
        assert len(commit_msgs) > 0, (
            f"Expected commit message in co-fire result (outcome=success). Got {result!r}"
        )
