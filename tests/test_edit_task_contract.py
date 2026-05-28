"""Failing tests for edit_task set/clear/omit semantics (#1348).

AC coverage:
- AC2: body="" clears body; body="text" replaces body; body=None/omitted → no change
- AC3: parent can be set to a positive ID; parent can be cleared via explicit contract
- AC4: title editing exposed with non-empty validation, OR explicit exclusion decision
- AC6: ERR_NO_OP when clearing an already-empty body; first clear succeeds
- AC7: body="" (clear) + append_body conflict raises ERR_BODY_EXCLUSIVE

All tests must FAIL against the current implementation (RED phase).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine

from owlbear_mcp_kanban.server import AppContext, edit_task

# ---------------------------------------------------------------------------
# Board fixtures — minimal grouped-schema kanban board
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_engine(base_dir: Path) -> KanbanEngine:
    board = _make_board(base_dir)
    return KanbanEngine(board, activity_log=False)


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_BodyClearSemantics
# AC2: body="" intentionally clears the body; body=None/omitted = no change;
#      body="text" replaces the body.
# ---------------------------------------------------------------------------


class TestFromAC_ParentClearSemantics:
    """AC3: Parent can be set and cleared through an explicit contract."""

    def test_parent_cleared_to_none_via_agent_view(self, tmp_path: Path) -> None:
        """After being set, parent must be clearable; cleared parent → result.parent is None.

        FAIL path (RED): parent=0 with no other changes raises ERR_NO_OP because
        `parent > 0` is False — parent is never forwarded and no effective change is detected.
        """
        engine = _make_engine(tmp_path)
        parent_task = engine.create_task("Parent", status="todo", priority="needed")
        child_task = engine.create_task("Child", status="todo", priority="needed")
        parent_id = parent_task.id
        child_id = child_task.id

        # Set parent first (current code supports this: parent > 0)
        set_result = engine.agent_view().edit_task(child_id, parent=parent_id)
        assert set_result.parent == parent_id, "Setup: parent must be set successfully"

        # Clear parent via the new contract (parent=0 as clear signal per AC3)
        clear_result = engine.agent_view().edit_task(child_id, parent=0)
        assert clear_result.parent is None, f"Cleared parent must be None; got {clear_result.parent!r}"

    @pytest.mark.asyncio
    async def test_mcp_parent_can_be_cleared(self, tmp_path: Path) -> None:
        """MCP edit_task must support clearing parent via the defined contract.

        FAIL path (RED): MCP handler does `if parent > 0:` — parent=0 is never
        forwarded to AgentView, so the parent remains set after the "clear" call.
        """
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        parent_task = engine.create_task("Parent", status="todo", priority="needed")
        child_task = engine.create_task("Child", status="todo", priority="needed")
        parent_id = parent_task.id
        child_id = child_task.id

        # Set parent through raw engine so setup is independent of AC3 (AgentView layer)
        engine.edit_task(str(child_id), parent=parent_id)

        app_ctx = AppContext(engine=engine, kanban_dir=board)
        ctx = _make_mcp_ctx(app_ctx)

        # Clear parent via MCP (parent=0 as clear signal per AC3)
        result = await edit_task(ctx, id=str(child_id), parent=0)

        assert result.parent is None, f"MCP edit_task(parent=0) must clear parent; got {result.parent!r}"


# ---------------------------------------------------------------------------
# TestFromAC_TitleEditOrExclusion
# AC4: MCP/AgentView must expose title editing with non-empty validation,
#      OR the task must record an explicit decision that title editing is excluded.
# ---------------------------------------------------------------------------
