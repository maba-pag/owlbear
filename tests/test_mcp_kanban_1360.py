"""RED phase tests — MCP dual-path dead code removal (#1360).

Verifies that after the refactor:
  - _canonical_agent_view_for, _invoke_view_move_task, _invoke_view_end_work,
    and _invoke_engine_end_work are removed from the server module.
  - move_task, start_work, and end_work call engine.agent_view() directly with
    no engine-level fallback path.
  - Server module line count reflects ~100-line net reduction.

All tests are expected to FAIL against the current (pre-refactor) code.

Module: tests/test_mcp_kanban_1360.py
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import owlbear_mcp_kanban.server as server_module
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import end_work, move_task, start_work

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TASK_DICT: dict = {
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


def _make_engine(mock_view: MagicMock) -> MagicMock:
    """Engine where engine.agent_view() is a *callable* returning mock_view.

    This is the post-refactor call convention: engine.agent_view() invoked
    as a method.  The engine's own move_task, start_work, end_work are also
    mocked with valid data so that, if the current code hits the legacy
    fallback path, it completes successfully — allowing the assertion failure
    (FAIL: DID NOT RAISE) to surface cleanly rather than a secondary error.
    """
    engine = MagicMock()
    engine.agent_view = MagicMock(return_value=mock_view)
    for method in ("show_task", "move_task", "start_work", "end_work"):
        getattr(engine, method).return_value = MagicMock(
            model_dump=MagicMock(return_value=_TASK_DICT)
        )
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


def _make_ctx(mock_view: MagicMock) -> MagicMock:
    """MCP Context mock backed by an engine wired to mock_view."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = _make_engine(mock_view)
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_DeadCodeRemoval
# AC1: _canonical_agent_view_for helper removed.
# AC2: _invoke_view_move_task, _invoke_view_start_work, _invoke_view_end_work
#      fallback branches removed (includes _invoke_engine_end_work).
# AC5: ~100 lines net reduction.
# ---------------------------------------------------------------------------


class TestFromAC_DeadCodeRemoval:
    """Dead helper symbols and the fallback boilerplate must be absent after refactor."""

    def test_canonical_agent_view_for_helper_removed(self) -> None:
        """_canonical_agent_view_for must not exist in the server module (AC1)."""
        assert not hasattr(server_module, "_canonical_agent_view_for"), (
            "_canonical_agent_view_for still present — dead helper not removed"
        )

    def test_invoke_view_move_task_removed(self) -> None:
        """_invoke_view_move_task must not exist in the server module (AC2)."""
        assert not hasattr(server_module, "_invoke_view_move_task"), (
            "_invoke_view_move_task still present — move_task fallback not removed"
        )

    def test_invoke_view_end_work_removed(self) -> None:
        """_invoke_view_end_work must not exist in the server module (AC2)."""
        assert not hasattr(server_module, "_invoke_view_end_work"), (
            "_invoke_view_end_work still present — end_work fallback not removed"
        )

    def test_invoke_engine_end_work_removed(self) -> None:
        """_invoke_engine_end_work must not exist — it wraps the engine fallback (AC2)."""
        assert not hasattr(server_module, "_invoke_engine_end_work"), (
            "_invoke_engine_end_work still present — engine fallback wrapper not removed"
        )

    def test_server_module_line_count_reduced(self) -> None:
        """Server module must be <720 lines after ~100-line dead code removal (AC5)."""
        import inspect

        source = inspect.getsource(server_module)
        line_count = len(source.splitlines())
        assert line_count < 720, (
            f"Expected <720 lines after ~100-line dead code removal, got {line_count}. "
            "Dead code (dual-path helpers + fallback branches) not yet removed."
        )


# ---------------------------------------------------------------------------
# TestFromAC_DirectAgentViewPath
# AC3: Direct AgentView calls replace the view-or-fallback pattern in
#      move_task, start_work, and end_work.
# ---------------------------------------------------------------------------


class TestFromAC_DirectAgentViewPath:
    """After refactor, all three tools call engine.agent_view() directly with no engine fallback."""

    # ---- move_task --------------------------------------------------------

    @pytest.mark.asyncio
    async def test_move_task_not_implemented_propagates_without_fallback(
        self,
    ) -> None:
        """move_task: NotImplementedError from view propagates; no silent engine.move_task fallback.

        Current code: _invoke_view_move_task catches NotImplementedError → returns None →
        engine.move_task fallback succeeds → no exception raised → test FAILS (DID NOT RAISE).
        After refactor: NotImplementedError propagates → test PASSES.
        """
        mock_view = MagicMock()
        mock_view.move_task.side_effect = NotImplementedError
        ctx = _make_ctx(mock_view)

        with pytest.raises(NotImplementedError):
            await move_task(ctx, id="42", status="in-progress")

    # ---- start_work -------------------------------------------------------

    @pytest.mark.asyncio
    async def test_start_work_not_implemented_propagates_without_fallback(
        self,
    ) -> None:
        """start_work: NotImplementedError from view propagates; no engine.start_work fallback.

        Current code: inline except NotImplementedError: pass → falls through to
        engine.start_work which succeeds → no exception raised → test FAILS (DID NOT RAISE).
        After refactor: NotImplementedError propagates → test PASSES.
        """
        mock_view = MagicMock()
        mock_view.start_work.side_effect = NotImplementedError
        ctx = _make_ctx(mock_view)

        with pytest.raises(NotImplementedError):
            await start_work(ctx, id="42")

    # ---- end_work ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_end_work_not_implemented_propagates_without_fallback(
        self,
    ) -> None:
        """end_work: NotImplementedError from view propagates; no _invoke_engine_end_work fallback.

        Current code: _invoke_view_end_work catches NotImplementedError → returns None →
        _invoke_engine_end_work(engine) called → succeeds → no exception → test FAILS (DID NOT RAISE).
        After refactor: NotImplementedError propagates → test PASSES.
        """
        mock_view = MagicMock()
        mock_view.end_work.side_effect = NotImplementedError
        ctx = _make_ctx(mock_view)

        with pytest.raises(NotImplementedError):
            await end_work(ctx, id="42", outcome="success")
