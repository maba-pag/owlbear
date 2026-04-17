"""Failing tests for task #729: MCP server migration — replace _run_kanban with KanbanEngine.

Tests verify that the migrated MCP server delegates all operations to KanbanEngine
instead of subprocess _run_kanban calls.

All tests FAIL against the current subprocess-based server (RED phase).
Primary failure mode: AppContext(engine=..., kanban_dir=...) raises TypeError because
the current dataclass requires kanban_bin and does not accept engine.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import Task
from owlbear_mcp_kanban.models import KanbanTask
from owlbear_mcp_kanban.server import (
    AppContext,
    app_lifespan,
    create_task,
    edit_task,
    end_work,
    list_tasks,
    move_task,
    pick_tasks,
    show_task,
    start_work,
)

# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: MigrationTestBoard
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
    class: standard
claim_timeout: 1h
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 1
"""

_MINIMAL_TASK_RECORD = Task(
    id=1,
    title="Migration Task",
    status="todo",
    priority="important",
    created="2026-01-01T00:00:00+00:00",
    updated="2026-01-01T00:00:00+00:00",
    body="## AC\n- [ ] Something",
)

_CLAIMED_TASK_RECORD = Task(
    id=2,
    title="Claimed Task",
    status="in-progress",
    priority="needed",
    created="2026-01-01T00:00:00+00:00",
    updated="2026-01-01T00:00:00+00:00",
    body="## Test-Writer Notes\n- some notes\n## AC\n- [ ] Do something",
    claimed_by="brave-owl",
    claimed_at="2026-01-01T00:00:00+00:00",
)

_BLOCKED_TASK_RECORD = Task(
    id=3,
    title="Blocked Task",
    status="todo",
    priority="important",
    created="2026-01-01T00:00:00+00:00",
    updated="2026-01-01T00:00:00+00:00",
    blocked=True,
    block_reason="waiting on deps",
)


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban board directory with config.yml and empty tasks/."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


def _make_mock_engine(**attr_overrides: object) -> MagicMock:
    """Return a MagicMock with KanbanEngine spec."""
    mock = MagicMock(spec=KanbanEngine)
    for name, value in attr_overrides.items():
        getattr(mock, name).return_value = value
    return mock


def _make_engine_app_ctx(
    kanban_dir: Path = Path("/fake/kanban"),
    **engine_return_values: object,
) -> AppContext:
    """Build new-style AppContext with engine field — FAILS RED against current server.

    Current AppContext requires kanban_bin and has no engine field.
    This raises TypeError until the builder modifies AppContext.
    """
    mock_engine = _make_mock_engine(**engine_return_values)
    return AppContext(engine=mock_engine, kanban_dir=kanban_dir)  # type: ignore[call-arg]


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    """Return a MagicMock mimicking an MCP Context with lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ===========================================================================
# TestFromAC_AppContext
# ===========================================================================


class TestFromAC_AppContext:
    """The updated AppContext uses engine: KanbanEngine instead of kanban_bin: Path."""

    def test_engine_field_accepted(self, kanban_dir: Path) -> None:
        """AppContext can be constructed with engine= and kanban_dir= (no kanban_bin)."""
        engine = KanbanEngine(kanban_dir)
        ctx = AppContext(engine=engine, kanban_dir=kanban_dir)  # type: ignore[call-arg]
        assert ctx.engine is engine  # type: ignore[attr-defined]

    def test_kanban_bin_field_removed(self, kanban_dir: Path) -> None:
        """Updated AppContext does not expose a kanban_bin attribute."""
        engine = KanbanEngine(kanban_dir)
        ctx = AppContext(engine=engine, kanban_dir=kanban_dir)  # type: ignore[call-arg]
        assert not hasattr(ctx, "kanban_bin")

    def test_kanban_dir_field_retained(self, kanban_dir: Path) -> None:
        """Updated AppContext still exposes kanban_dir as a Path."""
        engine = KanbanEngine(kanban_dir)
        ctx = AppContext(engine=engine, kanban_dir=kanban_dir)  # type: ignore[call-arg]
        assert ctx.kanban_dir == kanban_dir
        assert isinstance(ctx.kanban_dir, Path)


# ===========================================================================
# TestFromAC_Lifespan
# ===========================================================================


class TestFromAC_Lifespan:
    """Updated lifespan: instantiates KanbanEngine, no binary check, yields AppContext.engine."""

    @pytest.mark.asyncio
    async def test_lifespan_no_binary_check(self) -> None:
        """New lifespan does NOT raise FileNotFoundError when binary is absent."""
        mock_server = MagicMock()
        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_engine_cls:
            mock_engine_cls.return_value = MagicMock(spec=KanbanEngine)
            # Current lifespan raises FileNotFoundError here — RED failure
            async with app_lifespan(mock_server) as ctx:
                assert isinstance(ctx, AppContext)

    @pytest.mark.asyncio
    async def test_lifespan_yields_context_with_engine(self) -> None:
        """Lifespan yields AppContext with engine attribute set to a KanbanEngine instance."""
        mock_server = MagicMock()
        fake_engine = MagicMock(spec=KanbanEngine)
        with patch("owlbear_mcp_kanban.server.KanbanEngine", return_value=fake_engine):
            async with app_lifespan(mock_server) as ctx:
                assert ctx.engine is fake_engine  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_lifespan_instantiates_engine_with_kanban_dir(self) -> None:
        """Lifespan passes kanban_dir to KanbanEngine constructor."""
        mock_server = MagicMock()
        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_engine_cls:
            mock_engine_cls.return_value = MagicMock(spec=KanbanEngine)
            async with app_lifespan(mock_server) as _ctx:
                pass
        mock_engine_cls.assert_called_once()
        call_args = mock_engine_cls.call_args
        kanban_dir_arg = call_args[0][0] if call_args[0] else call_args[1].get("kanban_dir")
        assert kanban_dir_arg is not None


# ===========================================================================
# TestFromAC_ListTasks
# ===========================================================================


class TestFromAC_ListTasks:
    """list_tasks delegates to engine.list_tasks and returns list[TaskSummary]."""

    @pytest.mark.asyncio
    async def test_list_tasks_calls_engine_list_tasks(self) -> None:
        """list_tasks calls engine.list_tasks() instead of _run_kanban."""
        app_ctx = _make_engine_app_ctx(list_tasks=[_MINIMAL_TASK_RECORD])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(mcp_ctx)
        app_ctx.engine.list_tasks.assert_called_once()  # type: ignore[attr-defined]
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_tasks_strips_body_and_timestamp_fields(self) -> None:
        """list_tasks strips body, file, claimed_by, claimed_at from output."""
        task = Task(
            id=1,
            title="Strip Test",
            status="todo",
            priority="important",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-02T00:00:00+00:00",
            body="## Body content",
            claimed_by="agent-name",
            claimed_at="2026-01-01T00:00:00+00:00",
        )
        app_ctx = _make_engine_app_ctx(list_tasks=[task])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(mcp_ctx)
        assert len(result) == 1
        row = result[0]
        for stripped_field in ("body", "file", "claimed_by", "claimed_at"):
            assert not hasattr(row, stripped_field), f"Field {stripped_field!r} should be stripped from list output"

    @pytest.mark.asyncio
    async def test_list_tasks_claimed_bool_derived_from_claimed_by(self) -> None:
        """list_tasks output includes claimed: True when task is claimed, False when unclaimed."""
        unclaimed = Task(
            id=1,
            title="Free",
            status="todo",
            priority="important",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
            claimed_by=None,
        )
        claimed = Task(
            id=2,
            title="Taken",
            status="in-progress",
            priority="needed",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
            claimed_by="brave-owl",
        )
        app_ctx = _make_engine_app_ctx(list_tasks=[unclaimed, claimed])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(mcp_ctx)
        assert result[0].claimed is False
        assert result[1].claimed is True

    @pytest.mark.asyncio
    async def test_list_tasks_passes_status_filter_to_engine(self) -> None:
        """list_tasks passes status= kwarg to engine.list_tasks."""
        app_ctx = _make_engine_app_ctx(list_tasks=[])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(mcp_ctx, status="todo")
        call_kwargs = app_ctx.engine.list_tasks.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("status") == "todo"

    @pytest.mark.asyncio
    async def test_list_tasks_returns_empty_list_when_no_tasks(self) -> None:
        """list_tasks returns [] when engine returns no tasks."""
        app_ctx = _make_engine_app_ctx(list_tasks=[])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(mcp_ctx)
        assert result == []

    def test_list_tasks_output_schema_items_match_tasksummary_schema(self) -> None:
        """outputSchema items must equal TaskSummary.model_json_schema() (AC5 regression guard).

        Catches hardcoded dicts that silently diverge from the model when fields change.
        """
        from owlbear_kanban.models import TaskSummary
        from owlbear_mcp_kanban.server import mcp

        tool = next(
            t
            for t in mcp._tool_manager._tools.values()  # noqa: SLF001
            if t.name == "list_tasks"
        )
        items_schema = tool.fn_metadata.output_schema["properties"]["result"]["items"]
        assert items_schema == TaskSummary.model_json_schema(), (
            "outputSchema items must equal TaskSummary.model_json_schema() — "
            "hardcoded dict diverges from model definition"
        )


# ===========================================================================
# TestFromAC_ShowTask
# ===========================================================================


class TestFromAC_ShowTask:
    """show_task delegates to engine.show_task and returns KanbanTask."""

    @pytest.mark.asyncio
    async def test_show_task_returns_kanban_task(self) -> None:
        """show_task returns a KanbanTask instance."""
        app_ctx = _make_engine_app_ctx(show_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await show_task(mcp_ctx, task_id="1")
        assert isinstance(result, KanbanTask)

    @pytest.mark.asyncio
    async def test_show_task_delegates_to_engine_show_task(self) -> None:
        """show_task calls engine.show_task(task_id)."""
        app_ctx = _make_engine_app_ctx(show_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await show_task(mcp_ctx, task_id="42")
        app_ctx.engine.show_task.assert_called_once_with("42")  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_show_task_not_found_raises_tool_error(self) -> None:
        """show_task raises ToolError when engine raises FileNotFoundError."""
        from mcp.server.fastmcp.exceptions import ToolError

        mock_engine = _make_mock_engine()
        mock_engine.show_task.side_effect = FileNotFoundError("Task not found")
        app_ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake"))  # type: ignore[call-arg]
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await show_task(mcp_ctx, task_id="99")


# ===========================================================================
# TestFromAC_CreateTask
# ===========================================================================


class TestFromAC_CreateTask:
    """create_task delegates to engine.create_task and returns KanbanTask."""

    @pytest.mark.asyncio
    async def test_create_task_returns_kanban_task(self) -> None:
        """create_task returns a KanbanTask instance."""
        app_ctx = _make_engine_app_ctx(create_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await create_task(mcp_ctx, title="New Task")
        assert isinstance(result, KanbanTask)

    @pytest.mark.asyncio
    async def test_create_task_delegates_to_engine_with_title(self) -> None:
        """create_task calls engine.create_task with the provided title."""
        app_ctx = _make_engine_app_ctx(create_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await create_task(mcp_ctx, title="My Task Title")
        call_args = app_ctx.engine.create_task.call_args  # type: ignore[attr-defined]
        assert "My Task Title" in call_args[0] or call_args[1].get("title") == "My Task Title"

    @pytest.mark.asyncio
    async def test_create_task_passes_optional_params_to_engine(self) -> None:
        """create_task forwards priority, tags, body, status to engine.create_task."""
        app_ctx = _make_engine_app_ctx(create_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await create_task(
            mcp_ctx, title="Parameterised", priority="critical",
            tags="phase-3,kanban", body="some body", status="todo",
        )
        call_kwargs = app_ctx.engine.create_task.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("priority") == "critical"
        assert call_kwargs.get("status") == "todo"
        assert call_kwargs.get("body") == "some body"


# ===========================================================================
# TestFromAC_EditTask
# ===========================================================================


class TestFromAC_EditTask:
    """edit_task: param-mapped delegation to engine.edit_task, no auto-retry logic."""

    @pytest.mark.asyncio
    async def test_edit_task_block_param_maps_to_blocked_true_and_block_reason(self) -> None:
        """block='reason text' maps to engine.edit_task(blocked=True, block_reason='reason text')."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await edit_task(mcp_ctx, task_id="1", block="waiting on dep")
        call_kwargs = app_ctx.engine.edit_task.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("blocked") is True
        assert call_kwargs.get("block_reason") == "waiting on dep"

    @pytest.mark.asyncio
    async def test_edit_task_unblock_param_maps_to_blocked_false(self) -> None:
        """unblock=True maps to engine.edit_task(blocked=False)."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await edit_task(mcp_ctx, task_id="1", unblock=True)
        call_kwargs = app_ctx.engine.edit_task.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("blocked") is False

    @pytest.mark.asyncio
    async def test_edit_task_add_tag_maps_to_add_tags_list(self) -> None:
        """add_tag='phase-3' maps to engine.edit_task(add_tags=['phase-3'])."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await edit_task(mcp_ctx, task_id="1", add_tag="phase-3")
        call_kwargs = app_ctx.engine.edit_task.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("add_tags") == ["phase-3"]

    @pytest.mark.asyncio
    async def test_edit_task_remove_tag_maps_to_remove_tags_list(self) -> None:
        """remove_tag='phase-2' maps to engine.edit_task(remove_tags=['phase-2'])."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await edit_task(mcp_ctx, task_id="1", remove_tag="phase-2")
        call_kwargs = app_ctx.engine.edit_task.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("remove_tags") == ["phase-2"]

    @pytest.mark.asyncio
    async def test_edit_task_add_dep_maps_to_add_deps_as_int_list(self) -> None:
        """add_dep='42' maps to engine.edit_task(add_deps=[42]) — string to int list conversion."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await edit_task(mcp_ctx, task_id="1", add_dep="42")
        call_kwargs = app_ctx.engine.edit_task.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("add_deps") == [42]

    @pytest.mark.asyncio
    async def test_edit_task_remove_dep_maps_to_remove_deps_as_int_list(self) -> None:
        """remove_dep='7' maps to engine.edit_task(remove_deps=[7]) — string to int list conversion."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await edit_task(mcp_ctx, task_id="1", remove_dep="7")
        call_kwargs = app_ctx.engine.edit_task.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("remove_deps") == [7]

    @pytest.mark.asyncio
    async def test_edit_task_no_auto_retry_claimed_task_succeeds_directly(self) -> None:
        """edit_task on a claimed task succeeds without auto-retry subprocess calls."""
        mock_engine = _make_mock_engine()
        mock_engine.edit_task.return_value = _CLAIMED_TASK_RECORD
        app_ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake"))  # type: ignore[call-arg]
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await edit_task(mcp_ctx, task_id="2", append_body="done note", timestamp=True)
        # Should succeed on first call — no retry logic
        assert isinstance(result, KanbanTask)
        mock_engine.edit_task.assert_called_once()


# ===========================================================================
# TestFromAC_MoveTask
# ===========================================================================


class TestFromAC_MoveTask:
    """move_task delegates to engine.move_task and returns KanbanTask."""

    @pytest.mark.asyncio
    async def test_move_task_returns_kanban_task(self) -> None:
        """move_task returns a KanbanTask instance."""
        moved = Task(
            id=1,
            title="Moved Task",
            status="in-progress",
            priority="important",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
        )
        app_ctx = _make_engine_app_ctx(move_task=moved)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await move_task(mcp_ctx, task_id="1", status="in-progress")
        assert isinstance(result, KanbanTask)

    @pytest.mark.asyncio
    async def test_move_task_delegates_to_engine_move_task(self) -> None:
        """move_task calls engine.move_task(task_id, status)."""
        app_ctx = _make_engine_app_ctx(move_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await move_task(mcp_ctx, task_id="5", status="review")
        app_ctx.engine.move_task.assert_called_once_with("5", "review")  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_move_task_archived_delegates_to_engine_with_archived(self) -> None:
        """move_task with status='archived' calls engine.move_task(task_id, 'archived')."""
        archived = Task(
            id=1,
            title="Done Task",
            status="archived",
            priority="important",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
        )
        app_ctx = _make_engine_app_ctx(move_task=archived)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await move_task(mcp_ctx, task_id="1", status="archived")
        app_ctx.engine.move_task.assert_called_once_with("1", "archived")  # type: ignore[attr-defined]
        assert isinstance(result, KanbanTask)


# ===========================================================================
# TestFromAC_StartWork
# ===========================================================================


class TestFromAC_StartWork:
    """start_work delegates to engine.start_work and returns KanbanTask."""

    @pytest.mark.asyncio
    async def test_start_work_returns_kanban_task(self) -> None:
        """start_work returns a KanbanTask instance."""
        app_ctx = _make_engine_app_ctx(start_work=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await start_work(mcp_ctx, task_id="1")
        assert isinstance(result, KanbanTask)

    @pytest.mark.asyncio
    async def test_start_work_delegates_to_engine_start_work(self) -> None:
        """start_work calls engine.start_work(task_id)."""
        app_ctx = _make_engine_app_ctx(start_work=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await start_work(mcp_ctx, task_id="7")
        app_ctx.engine.start_work.assert_called_once_with("7")  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_start_work_blocked_task_raises_tool_error(self) -> None:
        """start_work raises ToolError when engine raises ValueError (blocked task)."""
        from mcp.server.fastmcp.exceptions import ToolError

        mock_engine = _make_mock_engine()
        mock_engine.start_work.side_effect = ValueError("Task '3' is blocked and cannot be claimed")
        app_ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake"))  # type: ignore[call-arg]
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await start_work(mcp_ctx, task_id="3")


# ===========================================================================
# TestFromAC_EndWork
# ===========================================================================


class TestFromAC_EndWork:
    """end_work delegates to engine.end_work and returns KanbanTask."""

    @pytest.mark.asyncio
    async def test_end_work_delegates_to_engine_end_work(self) -> None:
        """end_work calls engine.end_work(task_id, note, outcome, block_reason, move_to)."""
        app_ctx = _make_engine_app_ctx(end_work=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await end_work(mcp_ctx, task_id="1", note="all done", outcome="success")
        app_ctx.engine.end_work.assert_called_once()  # type: ignore[attr-defined]
        assert isinstance(result, KanbanTask)

    @pytest.mark.asyncio
    async def test_end_work_block_raises_tool_error_without_block_reason(self) -> None:
        """end_work raises ToolError when outcome='block' and block_reason is empty."""
        from mcp.server.fastmcp.exceptions import ToolError

        app_ctx = _make_engine_app_ctx(end_work=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match="block_reason"):
            await end_work(mcp_ctx, task_id="1", note="blocking", outcome="block")

    @pytest.mark.asyncio
    async def test_end_work_success_passes_outcome_to_engine(self) -> None:
        """end_work passes outcome='success' to engine.end_work."""
        advanced = Task(
            id=1,
            title="Advanced Task",
            status="in-progress",
            priority="important",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
        )
        app_ctx = _make_engine_app_ctx(end_work=advanced)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await end_work(mcp_ctx, task_id="1", note="done note", outcome="success")
        call_kwargs = app_ctx.engine.end_work.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("outcome") == "success"
        assert call_kwargs.get("note") == "done note"

    @pytest.mark.asyncio
    async def test_end_work_fail_passes_outcome_to_engine(self) -> None:
        """end_work passes outcome='fail' to engine.end_work."""
        app_ctx = _make_engine_app_ctx(end_work=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await end_work(mcp_ctx, task_id="1", note="failed", outcome="fail")
        call_kwargs = app_ctx.engine.end_work.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("outcome") == "fail"

    @pytest.mark.asyncio
    async def test_end_work_reject_passes_move_to_to_engine(self) -> None:
        """end_work passes move_to kwarg when outcome='reject'."""
        app_ctx = _make_engine_app_ctx(end_work=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await end_work(mcp_ctx, task_id="1", note="reject note", outcome="reject", move_to="backlog")
        call_kwargs = app_ctx.engine.end_work.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("move_to") == "backlog"
        assert call_kwargs.get("outcome") == "reject"


# ===========================================================================
# TestFromAC_PickTasks
# ===========================================================================


class TestFromAC_PickTasks:
    """pick_tasks: engine.list_tasks(blocked=False, unclaimed=True) + _check_pick_gates."""

    @pytest.mark.asyncio
    async def test_pick_tasks_calls_engine_list_tasks_with_blocked_false_unclaimed(self) -> None:
        """pick_tasks delegates to pick_dispatchable with the AppContext engine."""
        app_ctx = _make_engine_app_ctx(list_tasks=[])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            await pick_tasks(mcp_ctx)
            mock_pd.assert_called_once()
            args, _ = mock_pd.call_args
            assert args[0] is app_ctx.engine

    @pytest.mark.asyncio
    async def test_pick_tasks_returns_dispatch_dict(self) -> None:
        """pick_tasks returns a dict with 'dispatch' key containing task_id/status pairs."""
        task = Task(
            id=10,
            title="Ready Task",
            status="todo",
            priority="critical",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
            body="## AC\n- [ ] Something important",
        )
        app_ctx = _make_engine_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = [task]
            result = await pick_tasks(mcp_ctx)
        assert isinstance(result, dict)
        assert "dispatch" in result
        dispatch = result["dispatch"]
        assert isinstance(dispatch, list)
        if dispatch:
            assert "task_id" in dispatch[0]
            assert "status" in dispatch[0]

    @pytest.mark.asyncio
    async def test_pick_tasks_applies_gates_filter_no_ac(self) -> None:
        """pick_tasks gates filter removes todo tasks without AC patterns in body."""
        app_ctx = _make_engine_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            result = await pick_tasks(mcp_ctx)
        # pick_dispatchable returns [] when all tasks fail gates
        assert result["dispatch"] == []

    @pytest.mark.asyncio
    async def test_pick_tasks_tag_filter_passed_to_engine(self) -> None:
        """pick_tasks passes tag= kwarg to pick_dispatchable when set."""
        app_ctx = _make_engine_app_ctx(list_tasks=[])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            await pick_tasks(mcp_ctx, tag="phase-3")
            call_kwargs = mock_pd.call_args[1]
            assert call_kwargs.get("tag") == "phase-3"


# ===========================================================================
# TestFromAC_TaskConversion
# ===========================================================================


class TestFromAC_TaskConversion:
    """Tool functions convert Task→KanbanTask correctly (claimed_by→claimed bool)."""

    @pytest.mark.asyncio
    async def test_show_task_converts_claimed_by_str_to_claimed_true(self) -> None:
        """show_task returns KanbanTask with claimed=True when engine returns Task(claimed_by=str)."""
        app_ctx = _make_engine_app_ctx(show_task=_CLAIMED_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await show_task(mcp_ctx, task_id="2")
        assert isinstance(result, KanbanTask)
        assert result.claimed is True

    @pytest.mark.asyncio
    async def test_show_task_converts_claimed_by_none_to_claimed_false(self) -> None:
        """show_task returns KanbanTask with claimed=False when engine returns Task(claimed_by=None)."""
        app_ctx = _make_engine_app_ctx(show_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await show_task(mcp_ctx, task_id="1")
        assert isinstance(result, KanbanTask)
        assert result.claimed is False

    @pytest.mark.asyncio
    async def test_show_task_preserves_all_required_fields_in_kanban_task(self) -> None:
        """show_task output preserves id, title, status, priority, blocked, tags from Task."""
        rich_record = Task(
            id=42,
            title="Preservation Test",
            status="review",
            priority="needed",
            created="2026-03-15T10:00:00+00:00",
            updated="2026-03-16T12:00:00+00:00",
            body="body content",
            tags=["kanban", "phase-3"],
            blocked=True,
            block_reason="waiting for review",
        )
        app_ctx = _make_engine_app_ctx(show_task=rich_record)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        result = await show_task(mcp_ctx, task_id="42")
        assert isinstance(result, KanbanTask)
        assert result.id == 42
        assert result.title == "Preservation Test"
        assert result.status == "review"
        assert result.priority == "needed"
        assert result.blocked is True
        assert result.block_reason == "waiting for review"
        assert "kanban" in result.tags


# ===========================================================================
# TestBuilderDiscovered
# ===========================================================================


class TestBuilderDiscovered:
    """Builder-discovered edge cases to reach ≥90% coverage on server.py."""

    # edit_task guards
    @pytest.mark.asyncio
    async def test_edit_task_depends_on_guard_raises_tool_error(self) -> None:
        """edit_task raises ToolError when depends_on= is passed (guard present)."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match="depends_on"):
            await edit_task(mcp_ctx, task_id="1", depends_on="42")

    @pytest.mark.asyncio
    async def test_edit_task_tags_guard_raises_tool_error(self) -> None:
        """edit_task raises ToolError when tags= is passed (guard present)."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError, match="tags"):
            await edit_task(mcp_ctx, task_id="1", tags="phase-3")

    # edit_task optional param branches
    @pytest.mark.asyncio
    async def test_edit_task_optional_str_params_forwarded_to_engine(self) -> None:
        """edit_task forwards body, title, priority, status, parent to engine.edit_task."""
        app_ctx = _make_engine_app_ctx(edit_task=_MINIMAL_TASK_RECORD)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        await edit_task(
            mcp_ctx,
            task_id="1",
            body="new body",
            title="New Title",
            priority="critical",
            status="todo",
            parent=5,
        )
        call_kwargs = app_ctx.engine.edit_task.call_args[1]  # type: ignore[attr-defined]
        assert call_kwargs.get("body") == "new body"
        assert call_kwargs.get("title") == "New Title"
        assert call_kwargs.get("priority") == "critical"
        assert call_kwargs.get("status") == "todo"
        assert call_kwargs.get("parent") == 5

    @pytest.mark.asyncio
    async def test_edit_task_file_not_found_raises_tool_error(self) -> None:
        """edit_task raises ToolError when engine.edit_task raises FileNotFoundError."""
        mock_engine = _make_mock_engine()
        mock_engine.edit_task.side_effect = FileNotFoundError("Task not found")
        app_ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake"))  # type: ignore[call-arg]
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await edit_task(mcp_ctx, task_id="99", append_body="note")

    # move_task error path
    @pytest.mark.asyncio
    async def test_move_task_engine_error_raises_tool_error(self) -> None:
        """move_task raises ToolError when engine raises ValueError."""
        mock_engine = _make_mock_engine()
        mock_engine.move_task.side_effect = ValueError("Invalid status")
        app_ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake"))  # type: ignore[call-arg]
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await move_task(mcp_ctx, task_id="1", status="invalid-status")

    # start_work FileNotFoundError path
    @pytest.mark.asyncio
    async def test_start_work_file_not_found_raises_tool_error(self) -> None:
        """start_work raises ToolError when engine.start_work raises FileNotFoundError."""
        mock_engine = _make_mock_engine()
        mock_engine.start_work.side_effect = FileNotFoundError("Task not found")
        app_ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake"))  # type: ignore[call-arg]
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await start_work(mcp_ctx, task_id="99")

    # end_work FileNotFoundError path
    @pytest.mark.asyncio
    async def test_end_work_engine_error_raises_tool_error(self) -> None:
        """end_work raises ToolError when engine.end_work raises FileNotFoundError."""
        mock_engine = _make_mock_engine()
        mock_engine.end_work.side_effect = FileNotFoundError("Task not found")
        app_ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake"))  # type: ignore[call-arg]
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await end_work(mcp_ctx, task_id="99", note="done")

    # AppContext.__contains__
    def test_app_context_contains_always_returns_false(self) -> None:
        """AppContext.__contains__ returns False for any membership test."""
        mock_engine = MagicMock(spec=KanbanEngine)
        ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake"))  # type: ignore[call-arg]
        assert "engine" not in ctx
        assert "anything" not in ctx

    # pick_tasks TDD gate via pick_dispatchable delegation
    @pytest.mark.asyncio
    async def test_pick_tasks_filters_in_progress_without_writer_notes(self) -> None:
        """pick_tasks filters in-progress tasks without Test-Writer Notes (TDD gate)."""
        app_ctx = _make_engine_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            result = await pick_tasks(mcp_ctx)
        assert result["dispatch"] == []
