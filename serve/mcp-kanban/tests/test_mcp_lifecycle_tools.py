"""RED phase tests — MCP lifecycle tool adapters (#1088).

Tests the 3 lifecycle tool adapters: move_task, start_work, end_work.
All tests mock AgentView. Tests verify:
  - Correct AgentView method called with correct args
  - SingleTaskResponse returned (not KanbanTask)
  - KanbanError subclasses mapped to ToolError with user_message
  - end_work forbidden-parameter matrix (paper-integration.md §1.8)

Module: serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, NonCallableMagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban.engine import AgentView  # noqa: F401 — documents the mocked interface
from owlbear_kanban.errors import (
    ConcurrencyError,
    MigrationRequiredError,
    NotFoundError,
    ValidationError,
)
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import end_work, move_task, start_work

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response() -> SingleTaskResponse:
    """Minimal valid SingleTaskResponse for mock return values."""
    return SingleTaskResponse(
        id=42,
        title="Test Task",
        status="in-progress",
        priority="needed",
        created="2026-01-01T00:00:00+00:00",
        updated="2026-01-01T01:00:00+00:00",
    )


def _make_task_dict() -> dict:
    """Task dict that KanbanTask.model_validate accepts — keeps current adapter path alive."""
    return {
        "id": 42,
        "title": "Test Task",
        "status": "in-progress",
        "priority": "needed",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T01:00:00+00:00",
        "claimed": False,
        "tags": [],
        "body": None,
        "blocked": False,
        "block_reason": None,
        "parent": None,
        "depends_on": [],
    }


def _make_engine_mock(agent_view: MagicMock) -> MagicMock:
    """Engine mock where engine.agent_view() returns mock_av and all methods return valid dicts.

    Allows the current adapter code to run without crashing,
    so tests reach the assertion point and fail for the right reason.
    """
    engine = MagicMock()
    engine.agent_view = MagicMock(return_value=agent_view)
    task_dict = _make_task_dict()
    for method_name in (
        "show_task",
        "move_task",
        "start_work",
        "end_work",
        "edit_task",
    ):
        getattr(engine, method_name).return_value.model_dump.return_value = task_dict
    engine.board_config.return_value.statuses = [
        "research",
        "backlog",
        "todo",
        "in-progress",
        "review",
        "docs",
        "done",
    ]
    return engine


def _make_ctx(agent_view: MagicMock) -> MagicMock:
    """MCP Context mock with agent_view injected via engine."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = _make_engine_mock(agent_view)
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_av() -> MagicMock:
    """Mock AgentView with SingleTaskResponse configured on lifecycle methods.

    No spec=AgentView: AgentView.move_task is not yet implemented (builder task),
    so spec would block attribute access on the mock.
    """
    av = NonCallableMagicMock()
    resp = _make_response()
    av.move_task.return_value = resp
    av.start_work.return_value = resp
    av.end_work.return_value = resp
    return av


@pytest.fixture
def ctx(mock_av: MagicMock) -> MagicMock:
    """MCP Context configured for mock_av."""
    return _make_ctx(mock_av)


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskAdapter
# AC: move_task forwards id, status, archival_reason, archival_refs to AgentView;
#     returns SingleTaskResponse; KanbanError → ToolError
# ---------------------------------------------------------------------------


class TestFromAC_MoveTaskAdapter:
    """move_task adapter delegates to AgentView and returns SingleTaskResponse."""

    @pytest.mark.asyncio
    async def test_move_task_forwards_id_and_status_to_agent_view(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """move_task calls AgentView.move_task(id, status, archival_reason=None, archival_refs=None)."""
        await move_task(ctx, id="42", status="in-progress")
        mock_av.move_task.assert_called_once_with(42, "in-progress", archival_reason=None, archival_refs=None)

    @pytest.mark.asyncio
    async def test_move_task_forwards_archival_reason_and_refs(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """move_task forwards archival_reason and archival_refs to AgentView."""
        await move_task(
            ctx,
            id="42",
            status="archived",
            archival_reason="completed",
            archival_refs=[],
        )
        mock_av.move_task.assert_called_once_with(42, "archived", archival_reason="completed", archival_refs=[])

    @pytest.mark.asyncio
    async def test_move_task_returns_single_task_response(self, ctx: MagicMock) -> None:
        """move_task returns SingleTaskResponse, not KanbanTask."""
        result = await move_task(ctx, id="42", status="in-progress")
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_move_task_archived_without_archival_reason_raises_tool_error(
        self, ctx: MagicMock, mock_av: MagicMock
    ) -> None:
        """status='archived' without archival_reason → AgentView raises ValidationError → ToolError."""
        mock_av.move_task.side_effect = ValidationError(
            code="ERR_ARCHIVAL_REASON_REQUIRED",
            user_message="archival_reason is required when status is archived",
        )
        with pytest.raises(ToolError, match="archival_reason is required when status is archived"):
            await move_task(
                ctx,
                id="42",
                status="archived",
                archival_reason=None,
                archival_refs=None,
            )

    @pytest.mark.asyncio
    async def test_move_task_not_found_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """Task not found → NotFoundError from AgentView → ToolError with user_message."""
        mock_av.move_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND",
            user_message="task 99 not found",
        )
        with pytest.raises(ToolError, match="task 99 not found"):
            await move_task(ctx, id="99", status="in-progress")


# ---------------------------------------------------------------------------
# TestFromAC_StartWorkAdapter
# AC: start_work forwards id; returns SingleTaskResponse;
#     already-claimed / archived / blocked → ToolError
# ---------------------------------------------------------------------------


class TestFromAC_StartWorkAdapter:
    """start_work adapter delegates to AgentView.start_work and maps KanbanError → ToolError."""

    @pytest.mark.asyncio
    async def test_start_work_forwards_id_to_agent_view(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """start_work calls AgentView.start_work(int(task_id))."""
        await start_work(ctx, id="42")
        mock_av.start_work.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_start_work_returns_single_task_response(self, ctx: MagicMock) -> None:
        """start_work returns SingleTaskResponse, not KanbanTask."""
        result = await start_work(ctx, id="42")
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_start_work_already_claimed_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """Already-claimed task → ConcurrencyError from AgentView → ToolError."""
        mock_av.start_work.side_effect = ConcurrencyError(
            code="ERR_ALREADY_CLAIMED",
            user_message="already claimed at 2026-01-01T00:00:00+00:00",
        )
        with pytest.raises(ToolError, match="already claimed at"):
            await start_work(ctx, id="42")

    @pytest.mark.asyncio
    async def test_start_work_archived_task_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """Archived task → ValidationError from AgentView → ToolError."""
        mock_av.start_work.side_effect = ValidationError(
            code="ERR_ARCHIVED_NOT_CLAIMABLE",
            user_message="archived task not claimable",
        )
        with pytest.raises(ToolError, match="archived task not claimable"):
            await start_work(ctx, id="42")

    @pytest.mark.asyncio
    async def test_start_work_blocked_task_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """Blocked task → ValidationError from AgentView → ToolError."""
        mock_av.start_work.side_effect = ValidationError(
            code="ERR_BLOCKED_NOT_CLAIMABLE",
            user_message="blocked task not claimable",
        )
        with pytest.raises(ToolError, match="blocked task not claimable"):
            await start_work(ctx, id="42")


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkAdapter
# AC: end_work forwards all 7 Brief A §5.8 params to AgentView;
#     outcome enum includes "release"; note is optional;
#     outcome="block" without block_reason → ToolError
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkAdapter:
    """end_work adapter delegates to AgentView; all 7 params forwarded per Brief A §5.8."""

    @pytest.mark.asyncio
    async def test_end_work_all_params_forwarded_to_agent_view(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """All 7 Brief A §5.8 params (id, outcome, move_to, note, block_reason, archival_reason, archival_refs) forwarded."""
        await end_work(
            ctx,
            id="42",
            outcome="reject",
            move_to="backlog",
            note="rejected: scope too large",
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )
        mock_av.end_work.assert_called_once_with(
            42,
            outcome="reject",
            move_to="backlog",
            note="rejected: scope too large",
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )

    @pytest.mark.asyncio
    async def test_end_work_returns_single_task_response(self, ctx: MagicMock) -> None:
        """end_work returns SingleTaskResponse."""
        result = await end_work(ctx, id="42", outcome="success", note=None)
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_end_work_success_auto_advance(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='success': AgentView.end_work called with outcome='success'; move_to not provided."""
        await end_work(ctx, id="42", outcome="success", note=None)
        mock_av.end_work.assert_called_once()
        call_kwargs = mock_av.end_work.call_args.kwargs
        assert call_kwargs.get("outcome") == "success"
        # success must not carry move_to (engine drives the transition per D52)
        assert call_kwargs.get("move_to") is None

    @pytest.mark.asyncio
    async def test_end_work_reject_with_move_to(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='reject': AgentView.end_work called with move_to."""
        await end_work(ctx, id="42", outcome="reject", move_to="research", note=None)
        mock_av.end_work.assert_called_once()
        assert mock_av.end_work.call_args.kwargs.get("move_to") == "research"

    @pytest.mark.asyncio
    async def test_end_work_release_idempotent(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='release': AgentView.end_work called with outcome='release' (idempotent no-op)."""
        await end_work(ctx, id="42", outcome="release", note=None)
        mock_av.end_work.assert_called_once()
        assert mock_av.end_work.call_args.kwargs.get("outcome") == "release"

    @pytest.mark.asyncio
    async def test_end_work_block_with_block_reason(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='block' + block_reason: AgentView.end_work called with block_reason forwarded."""
        await end_work(
            ctx,
            id="42",
            outcome="block",
            block_reason="waiting for design review",
            note=None,
        )
        mock_av.end_work.assert_called_once()
        assert mock_av.end_work.call_args.kwargs.get("block_reason") == "waiting for design review"

    @pytest.mark.asyncio
    async def test_end_work_block_without_block_reason_raises_tool_error(
        self, ctx: MagicMock, mock_av: MagicMock
    ) -> None:
        """outcome='block' without block_reason → ToolError; message from KanbanError.user_message."""
        # Configure AgentView to raise the engine-level error (no machine code in user_message per §7):
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_BLOCK_REASON_REQUIRED",
            user_message="block_reason is required when outcome=block",
        )
        with pytest.raises(ToolError) as exc_info:
            await end_work(ctx, id="42", outcome="block", block_reason=None, note=None)
        # ToolError message must carry the KanbanError.user_message verbatim (§7: no ERR_ codes on wire)
        assert "block_reason is required when outcome=block" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_end_work_forwards_non_null_archival_fields(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """Non-null archival_reason/archival_refs forwarded to AgentView verbatim."""
        await end_work(
            ctx,
            id="42",
            outcome="fail",
            note=None,
            block_reason=None,
            archival_reason="completed",
            archival_refs=[100],
        )
        mock_av.end_work.assert_called_once_with(
            42,
            outcome="fail",
            move_to=None,
            note=None,
            block_reason=None,
            archival_reason="completed",
            archival_refs=[100],
        )

    @pytest.mark.asyncio
    async def test_end_work_note_is_optional(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """note is optional per Brief A §5.8 — omitting note must not raise."""
        await end_work(ctx, id="42", outcome="success")
        mock_av.end_work.assert_called_once()


# ---------------------------------------------------------------------------
# TestFromAC_KanbanErrorMapping
# AC: all KanbanError subclasses mapped to MCP ToolError with user_message
# ---------------------------------------------------------------------------


class TestFromAC_KanbanErrorMapping:
    """All KanbanError subclasses raised by AgentView are mapped to ToolError."""

    @pytest.mark.asyncio
    async def test_validation_error_mapped_to_tool_error_with_user_message(
        self, ctx: MagicMock, mock_av: MagicMock
    ) -> None:
        """ValidationError from AgentView → ToolError that carries user_message."""
        user_msg = "invalid status value '__bad__'"
        mock_av.move_task.side_effect = ValidationError(code="ERR_INVALID_STATUS", user_message=user_msg)
        with pytest.raises(ToolError, match="invalid status value"):
            await move_task(ctx, id="1", status="__bad__")

    @pytest.mark.asyncio
    async def test_not_found_error_mapped_to_tool_error_with_user_message(
        self, ctx: MagicMock, mock_av: MagicMock
    ) -> None:
        """NotFoundError from AgentView → ToolError with JSON payload carrying code + message."""
        user_msg = "task 999 not found"
        mock_av.start_work.side_effect = NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)
        with pytest.raises(ToolError) as exc_info:
            await start_work(ctx, id="999")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"
        assert payload["message"] == user_msg

    @pytest.mark.asyncio
    async def test_concurrency_error_mapped_to_tool_error_with_user_message(
        self, ctx: MagicMock, mock_av: MagicMock
    ) -> None:
        """ConcurrencyError from AgentView → ToolError with JSON payload carrying code + message."""
        user_msg = "already claimed at 2026-01-01T00:00:00+00:00"
        mock_av.start_work.side_effect = ConcurrencyError(code="ERR_ALREADY_CLAIMED", user_message=user_msg)
        with pytest.raises(ToolError) as exc_info:
            await start_work(ctx, id="42")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_ALREADY_CLAIMED"
        assert payload["message"] == user_msg

    @pytest.mark.asyncio
    async def test_migration_error_mapped_to_tool_error_with_user_message(
        self, ctx: MagicMock, mock_av: MagicMock
    ) -> None:
        """MigrationRequiredError (KanbanError subclass) from AgentView → ToolError with JSON payload."""
        user_msg = "board requires migration before use"
        mock_av.end_work.side_effect = MigrationRequiredError(code="ERR_MIGRATION_REQUIRED", user_message=user_msg)
        with pytest.raises(ToolError) as exc_info:
            await end_work(ctx, id="42", outcome="success", note=None)
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_MIGRATION_REQUIRED"
        assert payload["message"] == user_msg


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkForbiddenMatrix
# AC: forbidden-parameter matrix — deterministic ToolError per paper-integration.md §1.8
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkForbiddenMatrix:
    """end_work forbidden-parameter matrix: deterministic ToolError for all forbidden combos."""

    @pytest.mark.asyncio
    async def test_success_with_invalid_move_to_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='success' + invalid move_to → ToolError (ERR_MOVE_TO_INVALID_STATUS)."""
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_MOVE_TO_INVALID_STATUS",
            user_message="move_to='nonexistent' is not a valid pipeline status",
        )
        with pytest.raises(ToolError, match="is not a valid pipeline status"):
            await end_work(ctx, id="42", outcome="success", move_to="nonexistent", note=None)

    @pytest.mark.asyncio
    async def test_release_with_move_to_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='release' + move_to → ToolError (ERR_MOVE_TO_FORBIDDEN_ON_RELEASE)."""
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_MOVE_TO_FORBIDDEN_ON_RELEASE",
            user_message="move_to is forbidden when outcome is release",
        )
        with pytest.raises(ToolError, match="move_to is forbidden when outcome is release"):
            await end_work(ctx, id="42", outcome="release", move_to="research", note=None)

    @pytest.mark.asyncio
    async def test_success_with_archival_reason_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='success' + archival_reason → ToolError (ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS)."""
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS",
            user_message="archival fields are forbidden when outcome is success",
        )
        with pytest.raises(ToolError, match="archival fields are forbidden"):
            await end_work(
                ctx,
                id="42",
                outcome="success",
                archival_reason="completed",
                note=None,
            )

    @pytest.mark.asyncio
    async def test_success_with_archival_refs_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='success' + archival_refs → ToolError (ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS)."""
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_ARCHIVAL_FIELDS_FORBIDDEN_ON_SUCCESS",
            user_message="archival fields are forbidden when outcome is success",
        )
        with pytest.raises(ToolError, match="archival fields are forbidden"):
            await end_work(
                ctx,
                id="42",
                outcome="success",
                archival_refs=[1, 2],
                note=None,
            )

    @pytest.mark.asyncio
    async def test_success_with_block_reason_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='success' + block_reason → ToolError (ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK)."""
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
            user_message="block_reason is forbidden when outcome is not block",
        )
        with pytest.raises(ToolError, match="block_reason is forbidden"):
            await end_work(ctx, id="42", outcome="success", block_reason="oops", note=None)

    @pytest.mark.asyncio
    async def test_reject_with_block_reason_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='reject' + block_reason → ToolError (ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK)."""
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
            user_message="block_reason is forbidden when outcome is not block",
        )
        with pytest.raises(ToolError, match="block_reason is forbidden"):
            await end_work(
                ctx,
                id="42",
                outcome="reject",
                move_to="research",
                block_reason="oops",
                note=None,
            )

    @pytest.mark.asyncio
    async def test_release_with_block_reason_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='release' + block_reason → ToolError (ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK)."""
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
            user_message="block_reason is forbidden when outcome is not block",
        )
        with pytest.raises(ToolError, match="block_reason is forbidden"):
            await end_work(ctx, id="42", outcome="release", block_reason="oops", note=None)

    @pytest.mark.asyncio
    async def test_fail_with_block_reason_raises_tool_error(self, ctx: MagicMock, mock_av: MagicMock) -> None:
        """outcome='fail' + block_reason → ToolError (ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK).

        'fail' is a valid non-block outcome (server.py L485) and must also reject block_reason.
        """
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK",
            user_message="block_reason is forbidden when outcome is not block",
        )
        with pytest.raises(ToolError, match="block_reason is forbidden"):
            await end_work(ctx, id="42", outcome="fail", block_reason="oops", note=None)
