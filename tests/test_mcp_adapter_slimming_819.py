"""Regression tests — MCP adapter slimming boundary (task #819).

Verifies the target state reached by Phase 2 adapter slimming (#818):

AC1: serve/mcp-kanban src contains NO local engine files — all engine logic
     lives in the owlbear_kanban package.
AC2: All 8 MCP tools delegate to owlbear_kanban.KanbanEngine and return the
     correct result types.
AC3: server.py app_lifespan creates KanbanEngine from the owlbear_kanban package,
     not from a local engine module.

AC4 note: #818 completed slimming before these tests were written; tests pass
GREEN against the current state.  Each assertion carries a message documenting
the pre-slimming failure mode it guards against for future regressions.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine, Task, TaskSummary
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
# Module-level constants
# ---------------------------------------------------------------------------

_MCP_KANBAN_SRC: Path = (
    Path(__file__).parent.parent
    / "serve"
    / "mcp-kanban"
    / "src"
    / "owlbear_mcp_kanban"
)

# Engine files that must NOT exist inside mcp-kanban after slimming (#818)
_REMOVED_ENGINE_FILES: list[str] = [
    "engine.py",
    "engine_models.py",
    "task_io.py",
    "config_loader.py",
    "activity_log.py",
    "agent_names.py",
]

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

_MINIMAL_TASK = Task(
    id=1,
    title="Regression Task",
    status="todo",
    priority="important",
    created="2026-01-01T00:00:00+00:00",
    updated="2026-01-01T00:00:00+00:00",
    body="## AC\n- [ ] verify slimming boundary",
)


def _make_mock_engine() -> MagicMock:
    """Return a MagicMock with KanbanEngine spec, returning _MINIMAL_TASK for all ops."""
    mock = MagicMock(spec=KanbanEngine)
    mock.list_tasks.return_value = [_MINIMAL_TASK]
    mock.show_task.return_value = _MINIMAL_TASK
    mock.create_task.return_value = _MINIMAL_TASK
    mock.move_task.return_value = _MINIMAL_TASK
    mock.edit_task.return_value = _MINIMAL_TASK
    mock.start_work.return_value = _MINIMAL_TASK
    mock.end_work.return_value = _MINIMAL_TASK
    return mock


def _make_app_ctx(engine: MagicMock | None = None) -> AppContext:
    return AppContext(engine=engine or _make_mock_engine(), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ===========================================================================
# AC1 — Adapter import boundary: no local engine files remain
# ===========================================================================


class TestFromAC_AdapterImportBoundary:
    """AC1: serve/mcp-kanban src contains NO local engine files after slimming."""

    @pytest.mark.parametrize("filename", _REMOVED_ENGINE_FILES)
    def test_engine_file_absent(self, filename: str) -> None:
        """Each engine file must be absent from serve/mcp-kanban/src/owlbear_mcp_kanban/."""
        path = _MCP_KANBAN_SRC / filename
        assert not path.exists(), (
            f"{filename} still present in mcp-kanban — "
            f"should have been moved to owlbear_kanban during #818"
        )

    def test_server_imports_from_owlbear_kanban(self) -> None:
        """server.py AST check: at least one import comes from owlbear_kanban."""
        server_py = _MCP_KANBAN_SRC / "server.py"
        assert server_py.exists(), f"server.py not found at {server_py}"
        tree = ast.parse(server_py.read_text(encoding="utf-8"), filename=str(server_py))

        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(a.name.split(".")[0] == "owlbear_kanban" for a in node.names):
                    found = True
                    break
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.level == 0
                and node.module.split(".")[0] == "owlbear_kanban"
            ):
                found = True
                break

        assert found, (
            "server.py does not import from owlbear_kanban — "
            "pre-slimming failure: engine was a local module inside mcp-kanban"
        )

    def test_server_no_local_engine_module_import(self) -> None:
        """server.py AST check: NO import from owlbear_mcp_kanban.engine* paths."""
        server_py = _MCP_KANBAN_SRC / "server.py"
        assert server_py.exists(), f"server.py not found at {server_py}"
        tree = ast.parse(server_py.read_text(encoding="utf-8"), filename=str(server_py))

        violations: list[str] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.level == 0
                and node.module.startswith("owlbear_mcp_kanban.engine")
            ):
                violations.append(f"from {node.module} import ...")

        assert not violations, (
            "server.py imports from local engine paths — "
            "pre-slimming failure: engine was a local module: "
            + ", ".join(violations)
        )


# ===========================================================================
# AC2 — All 8 MCP tools delegate to owlbear_kanban.KanbanEngine
# ===========================================================================


class TestFromAC_AllToolsDelegateToEngine:
    """AC2: All 8 MCP tools call the owlbear_kanban engine and return correct types."""

    @pytest.mark.asyncio
    async def test_list_tasks_delegates_to_engine(self) -> None:
        """list_tasks calls engine.list_tasks() and returns list[TaskSummary]."""
        engine = _make_mock_engine()
        ctx = _make_mcp_ctx(_make_app_ctx(engine))

        result = await list_tasks(ctx)

        engine.list_tasks.assert_called_once()
        assert isinstance(result, list), (
            "list_tasks must return a list — "
            "pre-slimming failure: engine.list_tasks() was not callable on AppContext"
        )
        assert all(isinstance(item, TaskSummary) for item in result), (
            "list_tasks items must be TaskSummary — "
            "pre-slimming failure: engine not yet wired to AppContext"
        )

    @pytest.mark.asyncio
    async def test_show_task_delegates_to_engine(self) -> None:
        """show_task calls engine.show_task(task_id) and returns KanbanTask."""
        engine = _make_mock_engine()
        ctx = _make_mcp_ctx(_make_app_ctx(engine))

        result = await show_task(ctx, task_id="1")

        engine.show_task.assert_called_once_with("1")
        assert isinstance(result, KanbanTask), (
            "show_task must return KanbanTask — "
            "pre-slimming failure: engine.show_task() was not callable from server"
        )

    @pytest.mark.asyncio
    async def test_create_task_delegates_to_engine(self) -> None:
        """create_task calls engine.create_task() and returns KanbanTask."""
        engine = _make_mock_engine()
        ctx = _make_mcp_ctx(_make_app_ctx(engine))

        result = await create_task(ctx, title="New Regression Task")

        engine.create_task.assert_called_once()
        assert isinstance(result, KanbanTask), (
            "create_task must return KanbanTask — "
            "pre-slimming failure: engine.create_task() was not callable from server"
        )

    @pytest.mark.asyncio
    async def test_move_task_delegates_to_engine(self) -> None:
        """move_task calls engine.move_task(task_id, status) and returns KanbanTask."""
        engine = _make_mock_engine()
        ctx = _make_mcp_ctx(_make_app_ctx(engine))

        result = await move_task(ctx, task_id="1", status="in-progress")

        engine.move_task.assert_called_once()
        assert isinstance(result, KanbanTask), (
            "move_task must return KanbanTask — "
            "pre-slimming failure: engine.move_task() was not callable from server"
        )

    @pytest.mark.asyncio
    async def test_edit_task_delegates_to_engine(self) -> None:
        """edit_task calls engine.edit_task() and returns KanbanTask."""
        engine = _make_mock_engine()
        ctx = _make_mcp_ctx(_make_app_ctx(engine))

        result = await edit_task(ctx, task_id="1", title="Renamed Regression Task")

        engine.edit_task.assert_called_once()
        assert isinstance(result, KanbanTask), (
            "edit_task must return KanbanTask — "
            "pre-slimming failure: engine.edit_task() was not callable from server"
        )

    @pytest.mark.asyncio
    async def test_start_work_delegates_to_engine(self) -> None:
        """start_work calls engine.start_work(task_id) and returns KanbanTask."""
        engine = _make_mock_engine()
        ctx = _make_mcp_ctx(_make_app_ctx(engine))

        result = await start_work(ctx, task_id="1")

        engine.start_work.assert_called_once_with("1")
        assert isinstance(result, KanbanTask), (
            "start_work must return KanbanTask — "
            "pre-slimming failure: engine.start_work() was not callable from server"
        )

    @pytest.mark.asyncio
    async def test_end_work_delegates_to_engine(self) -> None:
        """end_work calls engine.end_work() and returns KanbanTask."""
        engine = _make_mock_engine()
        ctx = _make_mcp_ctx(_make_app_ctx(engine))

        result = await end_work(ctx, task_id="1", note="regression guard")

        engine.end_work.assert_called_once()
        assert isinstance(result, KanbanTask), (
            "end_work must return KanbanTask — "
            "pre-slimming failure: engine.end_work() was not callable from server"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_delegates_to_engine(self) -> None:
        """pick_tasks delegates to pick_dispatchable and returns dict with 'dispatch' key."""
        engine = _make_mock_engine()
        ctx = _make_mcp_ctx(_make_app_ctx(engine))

        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            result = await pick_tasks(ctx)
            mock_pd.assert_called_once()

        assert isinstance(result, dict), (
            "pick_tasks must return a dict — "
            "pre-slimming failure: pick_dispatchable not wired into server pick_tasks"
        )
        assert "dispatch" in result, (
            "pick_tasks result must have 'dispatch' key — "
            "pre-slimming failure: adapter not yet wired to pick_dispatchable"
        )


# ===========================================================================
# AC3 — server.py app_lifespan creates KanbanEngine from owlbear_kanban
# ===========================================================================


class TestFromAC_EngineCreation:
    """AC3: app_lifespan creates KanbanEngine imported from owlbear_kanban, not a local class."""

    def test_server_kanban_engine_resolves_to_owlbear_kanban(self) -> None:
        """server module's KanbanEngine name must resolve to owlbear_kanban.KanbanEngine."""
        import owlbear_mcp_kanban.server as server_module

        from owlbear_kanban import KanbanEngine as CanonicalEngine

        assert server_module.KanbanEngine is CanonicalEngine, (
            "server.KanbanEngine must be owlbear_kanban.KanbanEngine — "
            "pre-slimming failure: KanbanEngine was defined locally in "
            "owlbear_mcp_kanban.engine (which no longer exists)"
        )

    @pytest.mark.asyncio
    async def test_lifespan_creates_engine_instance(self) -> None:
        """app_lifespan must instantiate KanbanEngine and expose it on AppContext.engine."""
        mock_server = MagicMock()
        fake_engine = MagicMock(spec=KanbanEngine)

        with patch("owlbear_mcp_kanban.server.KanbanEngine", return_value=fake_engine) as mock_cls:
            async with app_lifespan(mock_server) as ctx:
                mock_cls.assert_called_once(), (
                    "app_lifespan must call KanbanEngine() — "
                    "pre-slimming failure: lifespan used subprocess calls instead"
                )
                assert ctx.engine is fake_engine, (
                    "AppContext.engine must be the KanbanEngine created in lifespan — "
                    "pre-slimming failure: engine field absent from AppContext"
                )

    @pytest.mark.asyncio
    async def test_lifespan_engine_receives_kanban_dir(self) -> None:
        """app_lifespan passes a Path (kanban_dir) to KanbanEngine constructor."""
        mock_server = MagicMock()

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            mock_cls.return_value = MagicMock(spec=KanbanEngine)
            async with app_lifespan(mock_server):
                args, _ = mock_cls.call_args
                assert args, (
                    "KanbanEngine must be called with a positional kanban_dir argument — "
                    "pre-slimming failure: lifespan did not pass kanban_dir to engine"
                )
                assert isinstance(args[0], Path), (
                    f"KanbanEngine first arg must be a Path, got {type(args[0]).__name__} — "
                    "pre-slimming failure: lifespan passed wrong type to engine constructor"
                )
