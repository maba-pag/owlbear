"""RED tests — guidance passthrough and KanbanError → ToolError mapping (#1089).

AC coverage:
- Guidance passthrough: engine (AgentView) response guidance passes through unmodified
- show_task section occurrence count guidance (AC12) passes through
- pick_tasks dispatch hints pass through
- create_task body size warning (>100 KB) passes through
- edit_task body size warning (>100 KB) passes through
- move_task skip-transition warning passes through (AC-NEW-5)
- end_work(reject) skip-transition warning passes through (AC-NEW-5)
- end_work(outcome="block") Action-Request/Decision-Request hint passes through (AC-NEW-4)
- ValidationError → ToolError (user_message only, no code on wire per §7)
- NotFoundError → ToolError
- ConcurrencyError → ToolError (e.g. already-claimed)

All tests must FAIL (RED phase).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import (
    ConcurrencyError,
    NotFoundError,
    PickTasksResponse,
    ShowTaskResponse,
    SingleTaskResponse,
    ValidationError,
)
from owlbear_mcp_kanban.server import (
    AppContext,
    create_task,
    edit_task,
    end_work,
    move_task,
    pick_tasks,
    show_task,
    start_work,
)

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

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

_NOW = "2026-01-01T00:00:00+00:00"


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


def _single_task_response(guidance: list[str]) -> SingleTaskResponse:
    """Minimal SingleTaskResponse carrying the given guidance."""
    return SingleTaskResponse(
        id=1,
        title="Test Task",
        status="todo",
        priority="important",
        created=_NOW,
        updated=_NOW,
        guidance=guidance,
    )


def _show_task_response(guidance: list[str]) -> ShowTaskResponse:
    """Minimal ShowTaskResponse carrying the given guidance."""
    return ShowTaskResponse(
        id=1,
        title="Test Task",
        status="todo",
        priority="important",
        created=_NOW,
        updated=_NOW,
        guidance=guidance,
    )


def _pick_tasks_response(guidance: list[str]) -> PickTasksResponse:
    """Minimal PickTasksResponse carrying the given guidance."""
    return PickTasksResponse(waves=[], guidance=guidance)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """AppContext with one unclaimed task at todo."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Test task", status="todo", priority="important")
    engine.list_tasks()  # populate id→filename cache
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


# ---------------------------------------------------------------------------
# TestFromAC_GuidancePassthrough
# ---------------------------------------------------------------------------


class TestFromAC_GuidancePassthrough:
    """Guidance strings from AgentView response envelopes pass through to MCP response."""

    @pytest.mark.asyncio
    async def test_show_task_section_occurrence_count_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """AC12: show_task section matching multiple times → guidance includes occurrence count.

        The engine (AgentView.show_task) returns guidance reporting the occurrence
        count; the adapter must include it in the returned KanbanTask.guidance.
        """
        ctx = _make_ctx(app_ctx)
        expected_guidance = ["Found 2 occurrences of '## Audit'"]
        mock_view = MagicMock()
        mock_view.show_task.return_value = _show_task_response(expected_guidance)
        with patch.object(app_ctx.engine, "agent_view", return_value=mock_view):
            result = await show_task(ctx, task_id="1")
        assert result.guidance == expected_guidance, (
            f"Expected occurrence-count guidance {expected_guidance!r} "
            f"from AgentView.show_task, got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_show_task_guidance_passes_through_unmodified(
        self, app_ctx: AppContext
    ) -> None:
        """Guidance strings from AgentView are not modified or stripped by the adapter."""
        ctx = _make_ctx(app_ctx)
        expected_guidance = ["Exact engine string — must not be mangled by adapter"]
        mock_view = MagicMock()
        mock_view.show_task.return_value = _show_task_response(expected_guidance)
        with patch.object(app_ctx.engine, "agent_view", return_value=mock_view):
            result = await show_task(ctx, task_id="1")
        assert result.guidance == expected_guidance, (
            f"Guidance must pass through unmodified; got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_dispatch_hints_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """pick_tasks response dict includes 'guidance' key with AgentView dispatch hints."""
        ctx = _make_ctx(app_ctx)
        expected_guidance = ["3 tasks ready across 2 waves"]
        mock_view = MagicMock()
        mock_view.pick_tasks.return_value = _pick_tasks_response(expected_guidance)
        with patch.object(app_ctx.engine, "agent_view", return_value=mock_view):
            result = await pick_tasks(ctx)
        assert isinstance(result, dict), "pick_tasks must return a dict"
        assert result.get("guidance") == expected_guidance, (
            f"Expected guidance {expected_guidance!r} in pick_tasks result, "
            f"got result={result!r}"
        )

    @pytest.mark.asyncio
    async def test_create_task_body_size_warning_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """create_task with body >100 KB → guidance includes body-size warning from engine."""
        ctx = _make_ctx(app_ctx)
        large_body = "x" * (100 * 1024 + 1)  # 100 KB + 1 byte
        expected_guidance = ["⚠️ Task body is large (>100 KB); consider splitting."]
        mock_view = MagicMock()
        mock_view.create_task.return_value = _single_task_response(expected_guidance)
        with patch.object(app_ctx.engine, "agent_view", return_value=mock_view):
            result = await create_task(ctx, title="Big task", body=large_body)
        assert result.guidance == expected_guidance, (
            f"Expected body-size warning guidance from engine, got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_edit_task_body_size_warning_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """edit_task with body >100 KB → guidance includes body-size warning from engine."""
        ctx = _make_ctx(app_ctx)
        large_body = "y" * (100 * 1024 + 1)
        expected_guidance = ["⚠️ Task body is large (>100 KB); consider splitting."]
        mock_view = MagicMock()
        mock_view.edit_task.return_value = _single_task_response(expected_guidance)
        with patch.object(app_ctx.engine, "agent_view", return_value=mock_view):
            result = await edit_task(ctx, task_id="1", body=large_body)
        assert result.guidance == expected_guidance, (
            f"Expected body-size warning guidance from engine on edit_task, "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_move_task_skip_transition_warning_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """AC-NEW-5: move_task skipping >1 column → skip-transition warning from engine passes through.

        The engine (AgentView.move_task) is the authoritative source of skip-transition
        guidance. The adapter must not compute its own guidance and must pass the engine's
        warning through.
        """
        ctx = _make_ctx(app_ctx)
        expected_guidance = [
            "⚠️ Status skip: moved from 'todo' to 'review' (skipped 1 column(s))."
            " Verify this jump is intentional."
        ]
        mock_view = MagicMock()
        mock_view.move_task.return_value = _single_task_response(expected_guidance)
        # Suppress adapter's own collect_guidance so test verifies engine is the source
        with patch.object(app_ctx.engine, "agent_view", return_value=mock_view), patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=[]
        ):
            result = await move_task(ctx, task_id="1", status="review")
        assert result.guidance == expected_guidance, (
            f"Expected skip-transition warning from AgentView.move_task, "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_end_work_reject_skip_transition_warning_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """AC-NEW-5: end_work(reject, move_to) skipping >1 column → skip warning from engine."""
        ctx = _make_ctx(app_ctx)
        expected_guidance = [
            "⚠️ Status skip: moved from 'todo' to 'done' (skipped 4 column(s))."
            " Verify this jump is intentional."
        ]
        mock_view = MagicMock()
        mock_view.end_work.return_value = _single_task_response(expected_guidance)
        with patch.object(app_ctx.engine, "agent_view", return_value=mock_view):
            result = await end_work(
                ctx,
                task_id="1",
                note="rejected to done",
                outcome="reject",
                move_to="done",
            )
        assert result.guidance == expected_guidance, (
            f"Expected skip-transition warning from AgentView.end_work, "
            f"got {result.guidance!r}"
        )

    @pytest.mark.asyncio
    async def test_end_work_block_action_request_hint_guidance(
        self, app_ctx_claimed: AppContext
    ) -> None:
        """AC-NEW-4: end_work(outcome='block') → AR/DR creation hint from engine passes through.

        The engine (AgentView.end_work) emits an Action-Request / Decision-Request
        creation suggestion when outcome='block'. The adapter must pass it through.
        This hint must NOT be computed by the adapter's own collect_guidance.
        """
        ctx = _make_ctx(app_ctx_claimed)
        expected_guidance = [
            "⚠️ ACTION REQUIRED: Create a Decision Request for this block via the"
            " scribe agent (see w-decision-routing)."
            " Blocks without a DR are invisible to the pipeline."
        ]
        mock_view = MagicMock()
        mock_view.end_work.return_value = _single_task_response(expected_guidance)
        # Suppress adapter's own collect_guidance to verify engine is the sole source
        with patch.object(app_ctx_claimed.engine, "agent_view", return_value=mock_view), patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=[]
        ):
            result = await end_work(
                ctx,
                task_id="1",
                note="blocked on external dependency",
                outcome="block",
                block_reason="waiting for decision",
            )
        assert result.guidance == expected_guidance, (
            f"Expected AR/DR hint from AgentView.end_work, got {result.guidance!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ErrorMapping
# ---------------------------------------------------------------------------


class TestFromAC_ErrorMapping:
    """KanbanError subclasses raised by engine → ToolError with user_message only."""

    @pytest.mark.asyncio
    async def test_validation_error_maps_to_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """ValidationError raised by engine → ToolError containing user_message.

        ValidationError inherits from KanbanError, not from ValueError.
        The adapter must catch it and re-raise as ToolError.
        """
        ctx = _make_ctx(app_ctx)
        user_msg = "Invalid status 'flying' — not a configured status"
        err = ValidationError(code="ERR_INVALID_STATUS", user_message=user_msg)
        with (
            patch.object(app_ctx.engine, "create_task", side_effect=err),
            pytest.raises(ToolError) as exc_info,
        ):
            await create_task(ctx, title="Test task", status="flying")
        assert user_msg in str(exc_info.value), (
            f"ToolError must contain user_message {user_msg!r}, "
            f"got {exc_info.value!r}"
        )

    @pytest.mark.asyncio
    async def test_not_found_error_maps_to_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """NotFoundError raised by engine → ToolError containing user_message.

        NotFoundError inherits from KanbanError, not from FileNotFoundError.
        The adapter must catch it and re-raise as ToolError.
        """
        ctx = _make_ctx(app_ctx)
        user_msg = "task '999' not found in tasks directory"
        err = NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)
        with (
            patch.object(app_ctx.engine, "show_task", side_effect=err),
            pytest.raises(ToolError) as exc_info,
        ):
            await show_task(ctx, task_id="999")
        assert user_msg in str(exc_info.value), (
            f"ToolError must contain user_message {user_msg!r}, "
            f"got {exc_info.value!r}"
        )

    @pytest.mark.asyncio
    async def test_concurrency_error_maps_to_tool_error_user_message_only(
        self, app_ctx: AppContext
    ) -> None:
        """ConcurrencyError (already-claimed) → ToolError; user_message only, no code on wire.

        ConcurrencyError inherits from KanbanError. The adapter must catch it and
        re-raise as ToolError with only the human-readable user_message.
        Machine-readable error codes (e.g. 'ERR_ALREADY_CLAIMED') must NOT appear
        in the wire error shape per §7.
        """
        ctx = _make_ctx(app_ctx)
        user_msg = "task '1' is already claimed"
        code = "ERR_ALREADY_CLAIMED"
        err = ConcurrencyError(code=code, user_message=user_msg)
        with (
            patch.object(app_ctx.engine, "start_work", side_effect=err),
            pytest.raises(ToolError) as exc_info,
        ):
            await start_work(ctx, task_id="1")
        error_text = str(exc_info.value)
        assert user_msg in error_text, (
            f"ToolError must contain user_message {user_msg!r}, got {error_text!r}"
        )
        assert code not in error_text, (
            f"ToolError must NOT expose machine code on wire; "
            f"found {code!r} in {error_text!r}"
        )
