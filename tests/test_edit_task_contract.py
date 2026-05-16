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

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import SingleTaskResponse, ValidationError

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


class TestFromAC_BodyClearSemantics:
    """AC2: Three-state body semantics — omit, set, clear."""

    def test_body_empty_string_clears_existing_body(self, tmp_path: Path) -> None:
        """body="" on a task with non-empty body must clear it to an empty string.

        FAIL path (RED): AgentView.edit_task treats body="" as falsy (bool("") is False)
        and does not forward it to the engine, so the body remains unchanged.
        The call also raises ERR_NO_OP because no kwargs are built.
        """
        engine = _make_engine(tmp_path)
        task = engine.create_task("T", body="original content", status="todo", priority="needed")
        task_id = task.id

        result = engine.agent_view().edit_task(task_id, body="")

        assert isinstance(result, SingleTaskResponse)
        assert result.body == "", f"Expected body to be cleared to '', got {result.body!r}"

    def test_body_empty_string_does_not_raise_noop_when_body_nonempty(self, tmp_path: Path) -> None:
        """body="" on a non-empty body must NOT raise ERR_NO_OP — it is a real mutation.

        FAIL path (RED): body_set = bool("") is False → kwargs is empty →
        ERR_NO_OP raised before any engine call.
        """
        engine = _make_engine(tmp_path)
        task = engine.create_task("T", body="has content", status="todo", priority="needed")
        task_id = task.id

        # Must not raise — body="" is a clear operation, not a no-op
        try:
            engine.agent_view().edit_task(task_id, body="")
        except ValidationError as exc:
            pytest.fail(
                f"edit_task(body='') raised ValidationError({exc.code!r}) "
                "but should have cleared the body without error"
            )

    def test_body_clear_then_noop_on_second_clear(self, tmp_path: Path) -> None:
        """First body="" succeeds; second body="" on already-empty body raises ERR_NO_OP.

        FAIL path (RED): First call raises ERR_NO_OP (wrong reason: no kwargs built).
        The test never reaches the second call.
        """
        engine = _make_engine(tmp_path)
        task = engine.create_task("T", body="initial text", status="todo", priority="needed")
        task_id = task.id

        # Step 1: clear the body (AC2 — must succeed)
        result = engine.agent_view().edit_task(task_id, body="")
        assert result.body == "", "First clear must succeed and set body to ''"

        # Step 2: clear again — now body is already empty → ERR_NO_OP (AC6)
        with pytest.raises(ValidationError) as exc_info:
            engine.agent_view().edit_task(task_id, body="")
        assert exc_info.value.code == "ERR_NO_OP", "Second body-clear on already-empty body must raise ERR_NO_OP"

    @pytest.mark.asyncio
    async def test_mcp_edit_task_empty_body_clears_task_body(self, tmp_path: Path) -> None:
        """MCP edit_task with body="" must result in the task body being cleared.

        FAIL path (RED): MCP handler does `if body:` which is falsy for body="",
        so body is not forwarded to AgentView → ERR_NO_OP → ToolError raised.
        """
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("T", body="original", status="todo", priority="needed")
        task_id = task.id
        app_ctx = AppContext(engine=engine, kanban_dir=board)
        ctx = _make_mcp_ctx(app_ctx)

        result = await edit_task(ctx, id=str(task_id), body="")

        assert result.body == "", f"MCP edit_task(body='') must clear body; got {result.body!r}"


# ---------------------------------------------------------------------------
# TestFromAC_ParentClearSemantics
# AC3: parent can be set to a positive task ID; parent can be cleared via
#      an explicit unambiguous contract.
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


class TestFromAC_TitleEditOrExclusion:
    """AC4: Title editing exposed with non-empty validation.

    These tests assert the 'title exposed' branch of AC4. If the builder
    decides to exclude title instead, they must record an explicit decision
    (DR/AR) and the AC will be revised in the next cycle.
    """

    def test_title_edit_updates_task_title(self, tmp_path: Path) -> None:
        """AgentView.edit_task with title= must update the task title.

        FAIL path (RED): AgentView.edit_task signature has no 'title' parameter;
        calling with title= raises TypeError: unexpected keyword argument 'title'.
        """
        engine = _make_engine(tmp_path)
        task = engine.create_task("Original Title", status="todo", priority="needed")
        task_id = task.id

        result = engine.agent_view().edit_task(task_id, title="Updated Title")

        assert isinstance(result, SingleTaskResponse)
        assert result.title == "Updated Title", f"Expected title 'Updated Title'; got {result.title!r}"

    def test_title_edit_rejects_empty_title(self, tmp_path: Path) -> None:
        """AgentView.edit_task with title="" must raise a ValidationError (non-empty required).

        FAIL path (RED): No 'title' parameter → TypeError raised instead of ValidationError.
        """
        engine = _make_engine(tmp_path)
        task = engine.create_task("My Task", status="todo", priority="needed")
        task_id = task.id

        with pytest.raises(ValidationError):
            engine.agent_view().edit_task(task_id, title="")

    def test_title_edit_rejects_whitespace_only_title(self, tmp_path: Path) -> None:
        """AgentView.edit_task with title='   ' must raise a ValidationError.

        FAIL path (RED): No 'title' parameter → TypeError raised instead of ValidationError.
        """
        engine = _make_engine(tmp_path)
        task = engine.create_task("My Task", status="todo", priority="needed")
        task_id = task.id

        with pytest.raises(ValidationError):
            engine.agent_view().edit_task(task_id, title="   ")

    @pytest.mark.asyncio
    async def test_mcp_title_edit_updates_title(self, tmp_path: Path) -> None:
        """MCP edit_task with title= must update the task title.

        FAIL path (RED): MCP tool signature has no 'title' parameter; fastMCP
        rejects the extra argument or the call raises ToolError/TypeError.
        """
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("Original", status="todo", priority="needed")
        task_id = task.id
        app_ctx = AppContext(engine=engine, kanban_dir=board)
        ctx = _make_mcp_ctx(app_ctx)

        # This call currently fails: 'title' is not a parameter of the MCP edit_task tool
        result = await edit_task(ctx, id=str(task_id), title="New Title")  # type: ignore[call-arg]

        assert result.title == "New Title", f"MCP edit_task(title='New Title') must update title; got {result.title!r}"

    @pytest.mark.asyncio
    async def test_mcp_title_edit_rejects_empty_title(self, tmp_path: Path) -> None:
        """MCP edit_task(title='') must raise ToolError (empty title rejected).

        FAIL path (RED): 'title' parameter does not exist in MCP tool; the call
        raises ToolError/TypeError before validation logic is reached.
        """
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("My Task", status="todo", priority="needed")
        task_id = task.id
        app_ctx = AppContext(engine=engine, kanban_dir=board)
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await edit_task(ctx, id=str(task_id), title="")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TestFromAC_InvalidCombinationValidation
# AC7: body="" (clear) + append_body="text" must raise ERR_BODY_EXCLUSIVE.
#      After the fix body="" is a real write signal — combining with append_body
#      is ambiguous and must be rejected.
# ---------------------------------------------------------------------------


class TestFromAC_InvalidCombinationValidation:
    """AC7: Clear and append on the same body field must raise ERR_BODY_EXCLUSIVE."""

    def test_body_clear_and_append_body_conflict_raises_exclusive_error(self, tmp_path: Path) -> None:
        """body="" (clear) + append_body="text" must raise ERR_BODY_EXCLUSIVE.

        FAIL path (RED): Currently body="" is falsy (body_set=False), so the
        mutual-exclusion check `if body_set and append_set:` evaluates to False.
        The call proceeds with only append_body, silently ignoring the clear intent.
        """
        engine = _make_engine(tmp_path)
        task = engine.create_task("T", body="existing", status="todo", priority="needed")
        task_id = task.id

        with pytest.raises(ValidationError) as exc_info:
            engine.agent_view().edit_task(task_id, body="", append_body="more text")

        assert exc_info.value.code == "ERR_BODY_EXCLUSIVE", f"Expected ERR_BODY_EXCLUSIVE; got {exc_info.value.code!r}"

    @pytest.mark.asyncio
    async def test_mcp_body_clear_and_append_body_conflict_raises_tool_error(self, tmp_path: Path) -> None:
        """MCP edit_task(body="", append_body="text") must raise ToolError.

        FAIL path (RED): MCP handler skips body="" (falsy), forwards only
        append_body → no conflict detected → appends successfully instead of raising.
        """
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("T", body="existing", status="todo", priority="needed")
        task_id = task.id
        app_ctx = AppContext(engine=engine, kanban_dir=board)
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await edit_task(ctx, id=str(task_id), body="", append_body="more text")
