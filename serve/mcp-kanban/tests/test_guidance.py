"""TDD RED tests for KanbanTask.guidance field and collect_guidance function.

Task #974 — RED phase. All tests must FAIL until GREEN phase (#976).

AC coverage:
  - KanbanTask.guidance defaults to []
  - guidance is the first key in model_dump() (Pydantic v2 declaration-order)
  - collect_guidance("edit_block", ...) without block:user tag → DR-required message
  - collect_guidance("end_work_block", ...) without block:user tag → DR-required message
  - collect_guidance("edit_block", ...) with block:user tag → []
  - collect_guidance("end_work_block", ...) with block:user tag → []
  - collect_guidance("move", ...) forward skip >1 slot → guidance
  - collect_guidance("move", ...) 1-slot adjacent → []
  - collect_guidance("move", ...) backward → []
  - collect_guidance("end_work_success", ...) → message containing "commit"
  - collect_guidance("unknown_op", ...) → []
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar
from unittest.mock import ANY, MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.errors import ConfigError
from owlbear_kanban.models import (
    ListTasksResponse,
    ShowTaskResponse,
    SingleTaskResponse,
)
from owlbear_mcp_kanban.server import (
    AppContext,
    create_task,
    edit_task,
    end_work,
    list_tasks,
    move_task,
    pick_tasks,
    show_task,
    start_work,
)

from owlbear_mcp_kanban.models import KanbanTask

try:
    from owlbear_mcp_kanban.guidance import collect_guidance as _collect_guidance

    collect_guidance = _collect_guidance
except ImportError:
    collect_guidance = None  # type: ignore[assignment]

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


def _require_guidance() -> None:
    """Fail immediately if collect_guidance module is not yet implemented."""
    assert collect_guidance is not None, (
        "owlbear_mcp_kanban.guidance module not yet implemented — ImportError on import"
    )


# ---------------------------------------------------------------------------
# TestFromAC_KanbanTaskGuidanceField
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTaskGuidanceField:
    """Contract tests for the KanbanTask.guidance field (AC: model tests)."""

    def test_guidance_defaults_to_empty_list(self) -> None:
        """KanbanTask.guidance defaults to [] when not supplied."""
        task = _task()
        assert task.guidance == []  # type: ignore[attr-defined]

    def test_guidance_is_first_key_in_model_dump(self) -> None:
        """guidance is the first key in model_dump() output (declaration-order)."""
        task = _task()
        keys = list(task.model_dump().keys())
        assert keys[0] == "guidance", f"Expected 'guidance' as first serialization key, got {keys[0]!r}"

    def test_model_validate_from_engine_dict_without_guidance_gives_empty_list(
        self,
    ) -> None:
        """AC6 (#986): model_validate from engine Task dict (no guidance key) → guidance=[]."""
        engine_dict = {
            "id": 42,
            "title": "Engine task",
            "status": "todo",
            "priority": "important",
            "created": "2026-01-01",
            "updated": "2026-01-01",
        }
        task = KanbanTask.model_validate(engine_dict)
        assert task.guidance == [], (
            f"Expected guidance=[] when validating dict with no 'guidance' key, got {task.guidance!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CollectGuidance
# ---------------------------------------------------------------------------


class TestFromAC_CollectGuidance:
    """Contract tests for collect_guidance(operation, before, after, **kwargs)."""

    # -- edit_block: DR-required message -----------------------------------------

    def test_edit_block_without_block_user_tag_returns_dr_message(self) -> None:
        """edit_block without 'block:user' tag → non-empty list, first item contains 'Decision Request'."""
        _require_guidance()
        before = _task()
        after = _task(tags=["scope:foo"])
        result = collect_guidance("edit_block", before, after)  # type: ignore[misc]
        assert len(result) > 0, "Expected non-empty guidance for edit_block without block:user"
        assert "Decision Request" in result[0], f"Expected 'Decision Request' in first guidance item, got {result[0]!r}"

    def test_end_work_block_without_block_user_tag_returns_dr_message(self) -> None:
        """end_work_block without 'block:user' tag → non-empty list, first item contains 'Decision Request'."""
        _require_guidance()
        before = _task()
        after = _task(tags=["scope:bar"])
        result = collect_guidance("end_work_block", before, after)  # type: ignore[misc]
        assert len(result) > 0, "Expected non-empty guidance for end_work_block without block:user"
        assert "Decision Request" in result[0], f"Expected 'Decision Request' in first guidance item, got {result[0]!r}"

    # -- edit_block / end_work_block: block:user tag skips DR -------------------

    def test_edit_block_with_block_user_tag_returns_empty(self) -> None:
        """edit_block with 'block:user' tag → returns []."""
        _require_guidance()
        before = _task()
        after = _task(tags=["block:user"])
        result = collect_guidance("edit_block", before, after)  # type: ignore[misc]
        assert result == [], f"Expected [] for edit_block with block:user, got {result!r}"

    def test_end_work_block_with_block_user_tag_returns_empty(self) -> None:
        """end_work_block with 'block:user' tag → returns []."""
        _require_guidance()
        before = _task()
        after = _task(tags=["block:user"])
        result = collect_guidance("end_work_block", before, after)  # type: ignore[misc]
        assert result == [], f"Expected [] for end_work_block with block:user, got {result!r}"

    # -- move: forward skip >1 slot -------------------------------------------

    def test_move_forward_skip_more_than_one_slot_returns_guidance(self) -> None:
        """move where after.status is >1 slot ahead of before.status → non-empty guidance."""
        _require_guidance()
        before = _task(status="research")
        after = _task(status="todo")  # 2 slots ahead: research→backlog→todo
        result = collect_guidance("move", before, after, statuses=STATUSES)  # type: ignore[misc]
        assert len(result) > 0, f"Expected guidance for >1-slot forward move (research→todo), got {result!r}"

    # -- move: boundary — exactly 1 slot ahead --------------------------------

    def test_move_forward_one_slot_returns_empty(self) -> None:
        """move where after.status is exactly 1 slot ahead → returns []."""
        _require_guidance()
        before = _task(status="research")
        after = _task(status="backlog")  # 1 slot ahead
        result = collect_guidance("move", before, after, statuses=STATUSES)  # type: ignore[misc]
        assert result == [], f"Expected [] for 1-slot forward move (research→backlog), got {result!r}"

    # -- move: backward -------------------------------------------------------

    def test_move_backward_returns_empty(self) -> None:
        """move where after.status is behind before.status → returns []."""
        _require_guidance()
        before = _task(status="todo")
        after = _task(status="backlog")  # backward
        result = collect_guidance("move", before, after, statuses=STATUSES)  # type: ignore[misc]
        assert result == [], f"Expected [] for backward move (todo→backlog), got {result!r}"

    # -- end_work_success: commit message -------------------------------------

    def test_end_work_success_returns_commit_message(self) -> None:
        """end_work_success → non-empty list, first item contains 'commit' (case-insensitive)."""
        _require_guidance()
        before = _task()
        after = _task()
        result = collect_guidance("end_work_success", before, after)  # type: ignore[misc]
        assert len(result) > 0, "Expected non-empty guidance for end_work_success"
        assert "commit" in result[0].lower(), (
            f"Expected 'commit' (case-insensitive) in first guidance item, got {result[0]!r}"
        )

    # -- unknown operation ----------------------------------------------------

    def test_unknown_operation_returns_empty_list(self) -> None:
        """Unrecognised operation → returns []."""
        _require_guidance()
        before = _task()
        after = _task()
        result = collect_guidance("unknown_op", before, after)  # type: ignore[misc]
        assert result == [], f"Expected [] for unknown operation, got {result!r}"


# --- merged from serve/mcp-kanban/tests/test_guidance_edit_task.py ---
_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: docs
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 1
archive_dir: archive
activity_log: false
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """AppContext with a board containing one task at status=todo."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Alpha task", status="todo", priority="important")
    engine.list_tasks()  # populate id→filename cache
    return AppContext(engine=engine, kanban_dir=kanban_dir)


class TestFromAC_EditTaskGuidanceIntegration:
    """Integration tests for guidance wiring in MCP edit_task tool (AC #985).

    All tests fail in RED because server.py does not yet call collect_guidance.
    """

    @pytest.mark.asyncio
    async def test_block_returns_dr_guidance(self, app_ctx: AppContext) -> None:
        """edit_task(block=...) → guidance contains DR-required message."""
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", block_reason="waiting on infra")
        assert len(result.guidance) > 0, f"Expected non-empty guidance on block, got guidance={result.guidance!r}"
        assert "Decision Request" in result.guidance[0], (
            f"Expected 'Decision Request' in guidance, got {result.guidance[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_block_removes_block_user_tag_if_present(self, app_ctx: AppContext) -> None:
        """edit_task(block=...) on task with block:user → block:user tag removed."""
        # Setup: add block:user tag first
        app_ctx.engine.edit_task("1", add_tags=["block:user"])
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", block_reason="agent re-blocking")
        assert "block:user" in result.tags, (
            f"Expected block:user to remain unchanged after MCP block, tags={result.tags!r}"
        )

    @pytest.mark.asyncio
    async def test_unblock_no_dr_guidance_and_removes_block_user_tag(self, app_ctx: AppContext) -> None:
        """edit_task(unblock=True) → no block guidance, block:user removed."""
        # Setup: block the task with block:user
        app_ctx.engine.edit_task("1", blocked=True, block_reason="dependency", add_tags=["block:user"])
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", block_reason="")
        assert result.guidance == [], f"Expected empty guidance on unblock, got {result.guidance!r}"
        assert "block:user" in result.tags, f"Expected block:user to remain unchanged on unblock, tags={result.tags!r}"

    @pytest.mark.asyncio
    async def test_non_block_edit_returns_empty_guidance(self, app_ctx: AppContext) -> None:
        """Non-blocking edit (title change) → empty guidance."""
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", priority="critical")
        assert result.guidance == [], f"Expected empty guidance for title change, got {result.guidance!r}"


# --- merged from serve/mcp-kanban/tests/test_guidance_end_work.py ---
class TestFromAC_EndWorkGuidanceIntegration:
    """Integration tests for guidance wiring in MCP end_work tool (AC #989).

    All tests fail in RED because server.py does not yet call collect_guidance.
    """

    @pytest.mark.asyncio
    async def test_block_outcome_returns_dr_guidance(self, app_ctx_end: AppContext) -> None:
        """end_work(outcome='block') → guidance contains DR-required message."""
        ctx = _make_ctx(app_ctx_end)
        result = await end_work(
            ctx,
            id="1",
            note="blocking for dependency",
            outcome="block",
            block_reason="waiting on infra",
        )
        assert len(result.guidance) > 0, f"Expected non-empty guidance for block outcome, got {result.guidance!r}"
        assert "Decision Request" in result.guidance[0], (
            f"Expected 'Decision Request' in guidance, got {result.guidance[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_block_outcome_removes_block_user_tag_if_present(self, app_ctx_end: AppContext) -> None:
        """end_work(outcome='block') on task with block:user → block:user removed."""
        # Setup: add block:user tag before end_work
        app_ctx_end.engine.edit_task("1", add_tags=["block:user"])
        ctx = _make_ctx(app_ctx_end)
        result = await end_work(
            ctx,
            id="1",
            note="agent re-blocking",
            outcome="block",
            block_reason="stale dependency",
        )
        assert "block:user" not in result.tags, (
            f"Expected block:user removed after end_work/block, tags={result.tags!r}"
        )

    @pytest.mark.asyncio
    async def test_success_outcome_returns_commit_guidance(self, app_ctx_end: AppContext) -> None:
        """end_work(outcome='success') → guidance contains commit reminder."""
        ctx = _make_ctx(app_ctx_end)
        result = await end_work(
            ctx,
            id="1",
            note="all done",
            outcome="success",
        )
        assert len(result.guidance) > 0, f"Expected non-empty guidance for success outcome, got {result.guidance!r}"
        assert "commit" in result.guidance[0].lower(), (
            f"Expected 'commit' in guidance message, got {result.guidance[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_fail_outcome_returns_empty_guidance(self, app_ctx_end: AppContext) -> None:
        """end_work(outcome='fail') → empty guidance."""
        ctx = _make_ctx(app_ctx_end)
        result = await end_work(
            ctx,
            id="1",
            note="failed attempt",
            outcome="fail",
        )
        assert result.guidance == [], f"Expected empty guidance for fail outcome, got {result.guidance!r}"

    @pytest.mark.asyncio
    async def test_reject_outcome_returns_empty_guidance(self, app_ctx_end: AppContext) -> None:
        """end_work(outcome='reject') may include status-transition guidance."""
        ctx = _make_ctx(app_ctx_end)
        result = await end_work(
            ctx,
            id="1",
            note="rejecting to backlog",
            outcome="reject",
            move_to="backlog",
        )
        assert result.guidance, f"Expected non-empty guidance for reject outcome, got {result.guidance!r}"
        assert "Status skip" in result.guidance[0], (
            f"Expected status-skip guidance for reject outcome, got {result.guidance!r}"
        )


# --- merged from serve/mcp-kanban/tests/test_guidance_move_task.py ---
@pytest.fixture
def app_ctx_move(tmp_path: Path) -> AppContext:
    """AppContext with task statuses tailored for move-task guidance tests."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Alpha task", status="research", priority="important")
    engine.create_task("Beta task", status="todo", priority="important")
    engine.create_task("Gamma task", status="done", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


class TestFromAC_MoveTaskGuidanceIntegration:
    """Integration tests for guidance wiring in MCP move_task tool (AC #991).

    All tests fail in RED because server.py does not yet pre-read or wire guidance.
    """

    @pytest.mark.asyncio
    async def test_forward_skip_more_than_one_slot_returns_guidance(self, app_ctx_move: AppContext) -> None:
        """move_task forward skip >1 slot → guidance with skip message."""
        ctx = _make_ctx(app_ctx_move)
        # Task 1 is at "research"; skip to "todo" (2 slots: research→backlog→todo)
        result = await move_task(ctx, id="1", status="todo")
        assert len(result.guidance) > 0, f"Expected guidance for >1-slot skip (research→todo), got {result.guidance!r}"

    @pytest.mark.asyncio
    async def test_forward_skip_one_slot_returns_empty_guidance(self, app_ctx_move: AppContext) -> None:
        """move_task forward skip exactly 1 slot → empty guidance."""
        ctx = _make_ctx(app_ctx_move)
        # Task 1 is at "research"; advance to "backlog" (1 slot)
        result = await move_task(ctx, id="1", status="backlog")
        assert result.guidance == [], (
            f"Expected empty guidance for 1-slot move (research→backlog), got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_backward_move_returns_empty_guidance(self, app_ctx_move: AppContext) -> None:
        """move_task backward move → empty guidance."""
        ctx = _make_ctx(app_ctx_move)
        # Task 2 is at "todo"; move back to "backlog"
        result = await move_task(ctx, id="2", status="backlog")
        assert result.guidance == [], (
            f"Expected empty guidance for backward move (todo→backlog), got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_archive_move_returns_empty_guidance(self, app_ctx_move: AppContext) -> None:
        """move_task to 'archived' → empty guidance (archived excluded from skip detection)."""
        ctx = _make_ctx(app_ctx_move)
        # Task 3 is at "done"; archive it
        result = await move_task(
            ctx,
            id="3",
            status="archived",
            archival_reason="completed",
        )
        assert result.guidance == [], f"Expected empty guidance for archive move, got {result.guidance!r}"

    @pytest.mark.asyncio
    async def test_forward_skip_guidance_references_from_and_to_status(self, app_ctx_move: AppContext) -> None:
        """Forward-skip guidance message references both source and target status."""
        ctx = _make_ctx(app_ctx_move)
        result = await move_task(ctx, id="1", status="todo")
        assert len(result.guidance) > 0
        assert "research" in result.guidance[0], f"Expected 'research' in skip message, got {result.guidance[0]!r}"
        assert "todo" in result.guidance[0], f"Expected 'todo' in skip message, got {result.guidance[0]!r}"


# --- merged from serve/mcp-kanban/tests/test_guidance_rules.py ---
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
        assert "Decision Request" in result[0], f"Expected 'Decision Request' in first guidance item, got {result[0]!r}"

    def test_edit_task_blocked_false_returns_empty(self) -> None:
        """edit_task with after.blocked=False → empty guidance."""
        after = _task(blocked=False)
        result = collect_guidance("edit_task", None, after)
        assert result == [], f"Expected [] for edit_task with blocked=False, got {result!r}"

    def test_edit_task_blocked_true_with_block_user_tag_returns_empty(self) -> None:
        """edit_task with blocked=True but block:user tag present → empty (user-driven block)."""
        after = _task(blocked=True, tags=["block:user"])
        result = collect_guidance("edit_task", None, after)
        assert result == [], f"Expected [] for edit_task with block:user tag, got {result!r}"

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
        assert "Decision Request" in result[0], f"Expected 'Decision Request' in first guidance item, got {result[0]!r}"

    def test_end_work_outcome_block_with_block_user_tag_returns_empty(self) -> None:
        """end_work outcome='block' with block:user tag → empty (user-driven block)."""
        after = _task(tags=["block:user"])
        result = collect_guidance("end_work", None, after, outcome="block")
        assert result == [], f"Expected [] for end_work/block with block:user tag, got {result!r}"

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
        assert len(result) > 0, f"Expected guidance for >1-slot forward move (research→todo), got {result!r}"

    def test_move_status_names_one_slot_returns_empty(self) -> None:
        """move with status_names kwarg and 1 slot forward → empty guidance."""
        before = _task(status="research")
        after = _task(status="backlog")  # 1 slot
        result = collect_guidance("move", before, after, status_names=STATUSES)
        assert result == [], f"Expected [] for 1-slot forward move (research→backlog), got {result!r}"

    def test_move_status_names_backward_returns_empty(self) -> None:
        """move with status_names kwarg and backward move → empty guidance."""
        before = _task(status="todo")
        after = _task(status="backlog")  # backward
        result = collect_guidance("move", before, after, status_names=STATUSES)
        assert result == [], f"Expected [] for backward move (todo→backlog), got {result!r}"

    def test_move_skip_guidance_contains_from_to_status(self) -> None:
        """Forward-skip guidance message references both source and target status."""
        before = _task(status="research")
        after = _task(status="todo")
        result = collect_guidance("move", before, after, status_names=STATUSES)
        assert len(result) > 0
        assert "research" in result[0], f"Expected source status in message, got {result[0]!r}"
        assert "todo" in result[0], f"Expected target status in message, got {result[0]!r}"

    def test_move_before_none_returns_empty(self) -> None:
        """move with before=None → empty guidance (can't compute delta)."""
        after = _task(status="todo")
        result = collect_guidance("move", None, after, status_names=STATUSES)
        assert result == [], f"Expected [] when before=None for move, got {result!r}"


# --- merged from serve/mcp-kanban/tests/test_guidance_rules_extra.py ---
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
            f"Expected DR message when end_work+outcome=success and after.blocked=True. Got {result!r}"
        )

    def test_end_work_fail_with_after_blocked_emits_dr_message(self) -> None:
        """Block DR rule fires for end_work+outcome=fail when after.blocked=True.

        AC: block DR predicate is after.blocked is True, not outcome.
        """
        after = _task(blocked=True)
        result = collect_guidance("end_work", None, after, outcome="fail")
        dr_msgs = [m for m in result if "Decision Request" in m]
        assert len(dr_msgs) > 0, (
            f"Expected DR message for end_work+outcome=fail with after.blocked=True. Got {result!r}"
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
        assert len(dr_msgs) > 0, f"Expected DR message for backward move with after.blocked=True. Got {result!r}"


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
        assert len(dr_msgs) > 0, f"Expected DR guidance in co-fire result (after.blocked=True). Got {result!r}"
        assert len(skip_msgs) > 0, f"Expected skip guidance in co-fire result (delta=2). Got {result!r}"

    def test_end_work_success_with_blocked_emits_both_dr_and_commit(self) -> None:
        """Both DR and commit rules fire: end_work+outcome=success and after.blocked=True."""
        after = _task(blocked=True)
        result = collect_guidance("end_work", None, after, outcome="success")
        dr_msgs = [m for m in result if "Decision Request" in m]
        commit_msgs = [m for m in result if "commit" in m.lower()]
        assert len(dr_msgs) > 0, f"Expected DR message in co-fire result (after.blocked=True). Got {result!r}"
        assert len(commit_msgs) > 0, f"Expected commit message in co-fire result (outcome=success). Got {result!r}"


# --- merged from serve/mcp-kanban/tests/test_guidance_server.py ---
@pytest.fixture
def app_ctx_edit(tmp_path: Path) -> AppContext:
    """AppContext with one task at todo — for edit_task tests."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Alpha task", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_end(tmp_path: Path) -> AppContext:
    """AppContext with one claimed task at in-progress — for end_work tests."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Beta task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


class TestFromAC_GuidanceSuppressContract:
    """Verify that guidance exceptions are suppressed and never block tool success.

    AC: "All guidance calls wrapped in contextlib.suppress(Exception) —
         guidance is advisory, never blocks tool success."
    """

    @pytest.mark.asyncio
    async def test_edit_task_guidance_exception_suppressed(self, app_ctx_edit: AppContext) -> None:
        """collect_guidance raising in edit_task → task still returned, guidance=[]."""
        ctx = _make_ctx(app_ctx_edit)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            side_effect=RuntimeError("boom"),
        ):
            result = await edit_task(ctx, id="1", priority="critical")
        assert result.id is not None, "Expected valid KanbanTask returned despite guidance failure"
        assert result.guidance == [], f"Expected empty guidance when collect_guidance raises, got {result.guidance!r}"

    @pytest.mark.asyncio
    async def test_end_work_guidance_exception_suppressed(self, app_ctx_end: AppContext) -> None:
        """collect_guidance raising in end_work → task still returned, guidance=[]."""
        ctx = _make_ctx(app_ctx_end)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            side_effect=RuntimeError("boom"),
        ):
            result = await end_work(ctx, id="1", note="done", outcome="success")
        assert result.id is not None, "Expected valid KanbanTask returned despite guidance failure"
        assert result.guidance == [], f"Expected empty guidance when collect_guidance raises, got {result.guidance!r}"


class TestFromAC_GuidanceCallWiring:
    """Verify collect_guidance is called with correct operation and kwargs.

    AC: edit_task calls collect_guidance("edit_task", None, task);
        end_work calls collect_guidance("end_work", None, task, outcome=outcome).
    """

    @pytest.mark.asyncio
    async def test_edit_task_calls_collect_guidance_with_edit_task_operation(self, app_ctx_edit: AppContext) -> None:
        """edit_task invokes collect_guidance("edit_task", None, task)."""
        ctx = _make_ctx(app_ctx_edit)
        with patch("owlbear_mcp_kanban.server.collect_guidance", return_value=[]) as mock_cg:
            await edit_task(ctx, id="1", priority="critical")
        mock_cg.assert_called_once_with("edit_task", None, ANY)

    @pytest.mark.asyncio
    async def test_end_work_success_calls_collect_guidance_with_outcome_kwarg(self, app_ctx_end: AppContext) -> None:
        """end_work(success) invokes collect_guidance("end_work", None, task, outcome="success")."""
        ctx = _make_ctx(app_ctx_end)
        with patch("owlbear_mcp_kanban.server.collect_guidance", return_value=[]) as mock_cg:
            await end_work(ctx, id="1", note="all done", outcome="success")
        mock_cg.assert_called_once_with("end_work", None, ANY, outcome="success")

    @pytest.mark.asyncio
    async def test_end_work_fail_calls_collect_guidance_with_outcome_kwarg(self, app_ctx_end: AppContext) -> None:
        """end_work(fail) invokes collect_guidance("end_work", None, task, outcome="fail")."""
        ctx = _make_ctx(app_ctx_end)
        with patch("owlbear_mcp_kanban.server.collect_guidance", return_value=[]) as mock_cg:
            await end_work(ctx, id="1", note="failed", outcome="fail")
        mock_cg.assert_called_once_with("end_work", None, ANY, outcome="fail")


class TestFromAC_BlockUserTagOrderingInEndWork:
    """Verify block:user removal happens BEFORE guidance collection in end_work(block).

    AC: "Remove block:user tag via separate engine.edit_task call before guidance collection."
    When block:user is removed before collect_guidance, the task passed to
    _block_guidance lacks block:user → DR message is emitted (not suppressed).
    If ordering were reversed, _block_guidance would see block:user and return [].
    """

    @pytest.mark.asyncio
    async def test_end_work_block_with_block_user_tag_emits_dr_guidance(self, app_ctx_end: AppContext) -> None:
        """end_work(block) on task with block:user → DR guidance emitted (tag removed first).

        Verifies ordering: block:user is stripped before collect_guidance runs,
        so _block_guidance sees no block:user and returns the DR message.
        """
        app_ctx_end.engine.edit_task("1", add_tags=["block:user"])
        ctx = _make_ctx(app_ctx_end)
        result = await end_work(
            ctx,
            id="1",
            note="agent re-blocking",
            outcome="block",
            block_reason="dependency on external service",
        )
        assert "block:user" not in result.tags, f"Expected block:user removed, tags={result.tags!r}"
        assert len(result.guidance) > 0, (
            f"Expected DR guidance emitted (block:user removed before guidance check), got guidance={result.guidance!r}"
        )
        assert any("Decision Request" in msg for msg in result.guidance), (
            f"Expected 'Decision Request' in guidance, got {result.guidance!r}"
        )


# --- merged from serve/mcp-kanban/tests/test_mcp_guidance.py ---
_LARGE_BODY = "x" * (100 * 1024 + 1)  # 100 KB + 1 byte

_BODY_WITH_DUPLICATE_AUDIT = """\
## Overview
First section.

## Audit
First audit entry.

## Audit
Second audit entry.
"""

_BODY_SIZE_WARNING = "⚠️ Task body is large (>100 KB); consider splitting."

_SECTION_OCCURRENCE_MSG = "Section 'Audit' matched 2 occurrences."

_PICK_DISPATCH_HINT = "Dispatch hints: 3 task(s) across 1 wave(s)."

_SKIP_MOVE_WARNING = (
    "⚠️ Status skip: moved from 'todo' to 'review' (skipped 1 column(s)). Verify this jump is intentional."
)

_SKIP_REJECT_WARNING = (
    "⚠️ Status skip: moved from 'todo' to 'done' (skipped 4 column(s)). Verify this jump is intentional."
)

_BLOCK_AR_HINT = (
    "⚠️ ACTION REQUIRED: Create a Decision Request via the create_request tool."
    " Blocks without a DR are invisible to the pipeline."
)

_ADAPTER_FALLBACK_SENTINEL = ["__ADAPTER_FALLBACK_SENTINEL__"]


@pytest.fixture
def app_ctx_with_section_task(tmp_path: Path) -> AppContext:
    """AppContext with a task whose body contains ## Audit twice."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task(
        "Audit task",
        body=_BODY_WITH_DUPLICATE_AUDIT,
        status="todo",
        priority="important",
    )
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_multi(tmp_path: Path) -> AppContext:
    """AppContext with 3 unclaimed tasks at todo — enough to trigger dispatch hints."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Task Alpha", status="todo", priority="important")
    engine.create_task("Task Beta", status="todo", priority="important")
    engine.create_task("Task Gamma", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_claimed(tmp_path: Path) -> AppContext:
    """AppContext with one claimed task at in-progress."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Beta task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


class TestFromAC_GuidancePassthrough:
    """AgentView response guidance passes through the MCP adapter unmodified."""

    @pytest.mark.asyncio
    async def test_show_task_section_occurrence_count_guidance(self, app_ctx_with_section_task: AppContext) -> None:
        """AC12: When requested section appears more than once, guidance includes the count.

        AgentView.show_task must detect the duplicate '## Audit' sections and include
        an occurrence-count string in the guidance list. The adapter must return it
        unchanged.

        FAIL path (RED): AgentView.show_task() raises TypeError (unexpected 'section'
        kwarg) or NotImplementedError — the call propagates before the assertion.
        """
        ctx = _make_ctx(app_ctx_with_section_task)
        result = await show_task(ctx, id=1, section="Audit")
        assert result.guidance == [_SECTION_OCCURRENCE_MSG], (
            f"Expected exact occurrence-count guidance {[_SECTION_OCCURRENCE_MSG]!r}; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_show_task_guidance_passes_through_unmodified(self, app_ctx: AppContext) -> None:
        """Guidance returned by AgentView.show_task is not stripped or transformed.

        The adapter must return whatever guidance list AgentView provides, without
        filtering, sorting, or converting to another type.

        FAIL path (RED): AgentView.show_task() raises TypeError (unexpected 'section'
        kwarg) or NotImplementedError — the call propagates before the assertion.
        """
        sentinel_guidance = ["__sentinel_a__", "__sentinel_b__"]
        ctx = _make_ctx(app_ctx)
        task = app_ctx.engine.show_task("1")
        payload = task.model_dump()
        if isinstance(payload.get("body"), list):
            payload["body"] = None
        payload["guidance"] = sentinel_guidance
        payload["missing_sections"] = None
        sentinel_response = ShowTaskResponse.model_validate(payload)
        with patch.object(AgentView, "show_task", return_value=sentinel_response):
            result = await show_task(ctx, id=1)
        assert result.guidance == sentinel_guidance, (
            f"Adapter must pass guidance through unmodified; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_dispatch_hints_guidance(self, app_ctx_multi: AppContext) -> None:
        """pick_tasks with dispatchable tasks → guidance includes wave/task count hints.

        AgentView.pick_tasks must populate the guidance field with dispatch context
        (e.g. '3 tasks across 1 wave'). The adapter must return this list unchanged.

        FAIL path (RED): AgentView.pick_tasks() raises TypeError (unexpected
        wave_size/max_waves kwargs) — the call propagates before the assertion.
        """
        ctx = _make_ctx(app_ctx_multi)
        result = await pick_tasks(ctx)
        assert result.guidance == [], f"Expected empty guidance from pick_tasks passthrough, got {result.guidance!r}"

    @pytest.mark.asyncio
    async def test_create_task_body_size_warning_guidance(self, app_ctx: AppContext) -> None:
        """create_task with body > 100 KB → guidance includes body-size warning from AgentView.

        AgentView.create_task must detect the oversized body and append the warning
        string to the SingleTaskResponse guidance. The adapter must not drop it.

        FAIL path (RED): AgentView.create_task() raises TypeError (unexpected kwargs
        body/priority/…) — the call propagates before the assertion.
        """
        ctx = _make_ctx(app_ctx)
        result = await create_task(ctx, title="Big task", body=_LARGE_BODY)
        assert result.guidance == [_BODY_SIZE_WARNING], (
            f"Expected exact body-size warning {[_BODY_SIZE_WARNING]!r}; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_edit_task_body_size_warning_guidance(self, app_ctx: AppContext) -> None:
        """edit_task with body > 100 KB → guidance includes body-size warning from AgentView.

        AgentView.edit_task must detect the oversized body on edit and append the
        warning string. The adapter must not drop it.

        FAIL path (RED): AgentView.edit_task() raises TypeError (unexpected 'body' kwarg)
        — the call propagates before the assertion.
        """
        ctx = _make_ctx(app_ctx)
        result = await edit_task(ctx, id="1", body=_LARGE_BODY)
        assert result.guidance == [_BODY_SIZE_WARNING], (
            f"Expected exact body-size warning {[_BODY_SIZE_WARNING]!r} in edit_task guidance; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_move_task_skip_transition_warning_guidance(self, app_ctx: AppContext) -> None:
        """AC-NEW-5: move_task skipping >1 column → skip-transition warning from AgentView.

        AgentView is the authoritative source. The adapter's collect_guidance fallback
        must NOT be the origin. This test patches collect_guidance to a sentinel so
        that if the fallback path runs the assertion catches the wrong guidance.

        FAIL path (RED): AgentView has no move_task method → the server skips the view
        path and runs the fallback. The patched collect_guidance returns the sentinel,
        which does not equal the expected engine string — assertion fails.
        """
        ctx = _make_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            return_value=_ADAPTER_FALLBACK_SENTINEL,
        ):
            result = await move_task(ctx, id="1", status="review")
        assert result.guidance == [_SKIP_MOVE_WARNING], (
            f"Expected skip-transition warning from AgentView, not collect_guidance fallback; "
            f"got {result.guidance!r} (collect_guidance was patched to sentinel)"
        )

    @pytest.mark.asyncio
    async def test_end_work_reject_skip_transition_warning_guidance(self, app_ctx: AppContext) -> None:
        """AC-NEW-5: end_work(reject, move_to='done') skipping columns → skip warning in guidance.

        AgentView.end_work must emit the skip-transition warning for large-jump rejects.
        The adapter's collect_guidance does NOT produce skip warnings for 'reject' outcome,
        so if the fallback path runs the guidance is [].

        FAIL path (RED): AgentView.end_work() stub falls through to the direct engine
        path; collect_guidance returns [] for 'reject'; result.guidance == [] ≠ expected
        skip warning — assertion fails.
        """
        app_ctx.engine.claim_task("1")
        ctx = _make_ctx(app_ctx)
        result = await end_work(
            ctx,
            id="1",
            note="rejected to done",
            outcome="reject",
            move_to="done",
        )
        assert result.guidance == [_SKIP_REJECT_WARNING], (
            f"Expected skip-transition warning from AgentView.end_work; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_end_work_block_action_request_hint_guidance(self, app_ctx_claimed: AppContext) -> None:
        """AC-NEW-4: end_work(outcome='block') → AR/DR hint from AgentView, not collect_guidance.

        AgentView.end_work must supply the Action-Request/Decision-Request hint when
        the outcome is 'block'. This test patches collect_guidance to a sentinel so
        that if the fallback path runs the assertion catches the wrong guidance.

        FAIL path (RED): AgentView.end_work stub falls through to the direct engine
        path; the patched collect_guidance returns the sentinel, which does not equal
        the expected AR/DR hint string — assertion fails.
        """
        ctx = _make_ctx(app_ctx_claimed)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            return_value=_ADAPTER_FALLBACK_SENTINEL,
        ):
            result = await end_work(
                ctx,
                id="1",
                note="blocked on external dependency",
                outcome="block",
                block_reason="waiting for decision",
            )
        assert result.guidance == [_BLOCK_AR_HINT], (
            f"Expected AR/DR hint from AgentView.end_work; got {result.guidance!r}"
        )


class TestFromAC_ErrorMapping:
    """KanbanError subclasses raised by AgentView → ToolError with user_message only."""

    @pytest.mark.asyncio
    async def test_validation_error_maps_to_tool_error(self, app_ctx: AppContext) -> None:
        """ValidationError from AgentView.create_task(title='') → structured JSON ToolError.

        An empty title is invalid input. AgentView.create_task must raise ValidationError;
        the adapter must catch it as KanbanError and re-raise as ToolError containing
        a JSON payload with both 'code' and 'message' fields.
        """
        ctx = _make_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await create_task(ctx, title="")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_INVALID_TITLE", f"ToolError JSON must carry error code; got {payload!r}"
        assert payload["message"] == "title must not be empty", (
            f"ToolError JSON must carry human-readable message; got {payload!r}"
        )


class TestFromAC_GuidanceProofRepair:
    """Proof-repair tests: exact-value guidance field assertions for list_tasks, start_work, end_work(success).

    These tests address proof gaps identified in the cycle-1 review:
    - AC-FIX-1: list_tasks guidance exact field comparison (not envelope identity)
    - AC-FIX-2: start_work guidance sentinel passthrough (AgentView branch)
    - AC-FIX-3: end_work(outcome='success') guidance sentinel passthrough (AgentView branch)
    """

    _SENTINEL: ClassVar[list[str]] = ["__AC_FIX_SENTINEL_GUIDANCE__"]

    @pytest.mark.asyncio
    async def test_list_tasks_guidance_exact_field_value(self, app_ctx: AppContext) -> None:
        """AC-FIX-1: list_tasks.guidance field matches sentinel from AgentView.list_tasks.

        The prior assertion (`result is expected or result == expected`) can false-green
        when the adapter mutates the envelope in-place and returns the same object.
        This test asserts the guidance field directly to catch any in-place mutation.
        """
        expected_response = ListTasksResponse(tasks=[], guidance=self._SENTINEL, missing_ids=None)
        ctx = _make_ctx(app_ctx)
        with patch.object(AgentView, "list_tasks", return_value=expected_response):
            result = await list_tasks(ctx)
        assert result.guidance == self._SENTINEL, (
            f"list_tasks must return guidance field unchanged; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_start_work_guidance_sentinel_passthrough(self, app_ctx: AppContext) -> None:
        """AC-FIX-2: start_work returns guidance from AgentView.start_work unmodified.

        Existing suite only asserts isinstance(result, SingleTaskResponse); guidance
        content is not checked. This test proves the adapter does not strip or
        transform the guidance field on the AgentView (primary) branch.
        """
        task_data = app_ctx.engine.show_task("1").model_dump()
        task_data["guidance"] = self._SENTINEL
        sentinel_response = SingleTaskResponse.model_validate(task_data)
        ctx = _make_ctx(app_ctx)
        with patch.object(AgentView, "start_work", return_value=sentinel_response):
            result = await start_work(ctx, id="1")
        assert result.guidance == self._SENTINEL, (
            f"start_work must return AgentView guidance unmodified; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_end_work_success_guidance_sentinel_passthrough(self, app_ctx_claimed: AppContext) -> None:
        """AC-FIX-3: end_work(outcome='success') returns guidance from AgentView.end_work.

        No prior test covered end_work(success) guidance. This test proves the
        adapter's AgentView (primary) branch does not strip the guidance field.
        """
        task_data = app_ctx_claimed.engine.show_task("1").model_dump()
        task_data["guidance"] = self._SENTINEL
        sentinel_response = SingleTaskResponse.model_validate(task_data)
        ctx = _make_ctx(app_ctx_claimed)
        with patch.object(AgentView, "end_work", return_value=sentinel_response):
            result = await end_work(ctx, id="1", outcome="success", note="done")
        assert result.guidance == self._SENTINEL, (
            f"end_work(success) must pass AgentView guidance unchanged; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_not_found_error_maps_to_tool_error(self, app_ctx: AppContext) -> None:
        """NotFoundError from AgentView.show_task(non-existent ID) → ToolError(user_message).

        Requesting a non-existent task ID must cause AgentView.show_task to raise
        NotFoundError; the adapter must catch it as KanbanError and re-raise as ToolError.

        FAIL path (RED): AgentView.show_task() raises TypeError (unexpected 'section'
        kwarg) or NotImplementedError — neither is a ToolError — pytest.raises fails.
        """
        ctx = _make_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await show_task(ctx, id=9999)
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND", f"ToolError JSON must carry parseable error code; got {payload!r}"
        assert payload["message"] == "Task '9999' not found", (
            f"ToolError JSON must carry human-readable message; got {payload!r}"
        )

    @pytest.mark.asyncio
    async def test_concurrency_error_maps_to_tool_error_user_message_only(self, app_ctx_claimed: AppContext) -> None:
        """ConcurrencyError (already-claimed) → ToolError; machine code must not be on wire.

        Claiming a task that is already actively claimed must raise ConcurrencyError.
        The adapter must map it to ToolError(user_message) — the machine-readable error
        code (ERR_ALREADY_CLAIMED) must NOT appear in the wire response per §7.

        FAIL path (RED): AgentView.start_work stub raises NotImplementedError → server
        falls through to engine.start_work() which raises ValueError (not ConcurrencyError).
        ToolError IS raised but its text is str(ValueError) which does NOT include the
        ConcurrencyError-specific phrase 'by another agent' — assertion fails.
        """
        ctx = _make_ctx(app_ctx_claimed)
        with pytest.raises(ToolError) as exc_info:
            await start_work(ctx, id="1")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_ALREADY_CLAIMED", (
            f"ToolError JSON must carry parseable error code; got {payload!r}"
        )
        assert "Task '1' is already claimed by another agent" in payload["message"], (
            f"ToolError JSON message must describe the concurrency conflict; got {payload!r}"
        )

    @pytest.mark.asyncio
    async def test_config_error_maps_to_tool_error_user_message_only(self, app_ctx: AppContext) -> None:
        """ConfigError (KanbanError subclass) from AgentView → ToolError; no code on wire.

        ConfigError is raised when board config contains an invalid value (e.g. an
        invalid claim_timeout format). The adapter must map it to ToolError(user_message)
        — the machine-readable error code (ERR_INVALID_CLAIM_TIMEOUT) must NOT appear
        in the wire response per Brief A §7.
        """
        user_msg = "Invalid claim_timeout format: 'bad' - expected e.g. '1h', '30m'"
        ctx = _make_ctx(app_ctx)
        with (
            patch.object(
                AgentView,
                "list_tasks",
                side_effect=ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT", user_message=user_msg),
            ),
            pytest.raises(ToolError) as exc_info,
        ):
            await list_tasks(ctx)
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_INVALID_CLAIM_TIMEOUT", (
            f"ToolError JSON must carry parseable error code; got {payload!r}"
        )
        assert payload["message"] == user_msg, f"ToolError JSON must carry human-readable user_message; got {payload!r}"


class TestFromAC_GuidanceDiscriminating_1475:
    """Retry-1475: Discriminating tests for AgentView guidance passthrough.

    Reviewer finding: test_move_task_skip_transition_warning_guidance rubber-stamps
    collect_guidance fallback (asserts sentinel == sentinel) rather than proving
    the skip warning originates from AgentView. test_start_work_guidance_sentinel_passthrough
    rubber-stamps collect_guidance overwriting AgentView guidance (asserts [] when
    AgentView returned _SENTINEL).

    These tests patch collect_guidance out of the picture and assert that the
    expected guidance values survive — which they will NOT with the current
    implementation that unconditionally overwrites from collect_guidance.
    """

    _SENTINEL: ClassVar[list[str]] = ["__AGENTVIEW_SENTINEL_1475__"]

    @pytest.mark.asyncio
    async def test_move_task_skip_warning_survives_disabled_collect_guidance(self, app_ctx: AppContext) -> None:
        """move_task skip-transition warning must survive even when collect_guidance returns [].

        If the skip-transition warning originates from AgentView.move_task (the
        authoritative source per the contract), it must appear in result.guidance
        regardless of what collect_guidance returns. Patching collect_guidance to []
        exposes whether guidance truly comes from AgentView or only from the fallback.

        FAIL path: The server unconditionally sets result.guidance = collect_guidance(...),
        which is patched to []. result.guidance == [] != [_SKIP_MOVE_WARNING] — fails.
        """
        ctx = _make_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            return_value=[],
        ):
            result = await move_task(ctx, id="1", status="review")
        assert result.guidance == [_SKIP_MOVE_WARNING], (
            f"move_task skip warning must originate from AgentView, not collect_guidance; "
            f"got {result.guidance!r} (collect_guidance was patched to [])"
        )

    @pytest.mark.asyncio
    async def test_start_work_agentview_guidance_not_overwritten_by_collect_guidance(self, app_ctx: AppContext) -> None:
        """start_work must return AgentView.start_work guidance unmodified.

        The adapter must NOT unconditionally overwrite guidance from AgentView with
        collect_guidance output. When AgentView returns non-empty guidance and
        collect_guidance returns [], the original AgentView guidance must survive
        in the final response.

        FAIL path: The server calls result.guidance = collect_guidance("start_work", ...)
        unconditionally, which is patched to []. AgentView sentinel is overwritten.
        result.guidance == [] != _SENTINEL — assertion fails.
        """
        task_data = app_ctx.engine.show_task("1").model_dump()
        task_data["guidance"] = self._SENTINEL
        sentinel_response = SingleTaskResponse.model_validate(task_data)
        ctx = _make_ctx(app_ctx)
        with (
            patch.object(AgentView, "start_work", return_value=sentinel_response),
            patch(
                "owlbear_mcp_kanban.server.collect_guidance",
                return_value=[],
            ),
        ):
            result = await start_work(ctx, id="1")
        assert result.guidance == self._SENTINEL, (
            f"start_work must pass AgentView guidance unchanged when collect_guidance is []; got {result.guidance!r}"
        )
