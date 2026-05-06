"""RED phase tests — MCP create_dr tool adapter (#1182)."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import NotFoundError
from owlbear_mcp_kanban.server import AppContext, mcp


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
agent_map:
  research: researcher
  backlog: architect
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    (kanban_dir / "decisions" / "pending").mkdir(parents=True, exist_ok=True)
    return kanban_dir


def _make_mcp_ctx(app_ctx: object) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Task 1", status="todo", priority="needed")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


class TestFromAC_CreateDrTool:
    def test_create_dr_tool_is_registered_via_mcp_decorator(self) -> None:
        import owlbear_mcp_kanban.server as server_mod

        tool = next(  # noqa: SLF001
            (t for t in mcp._tool_manager._tools.values() if t.name == "create_dr"),
            None,
        )
        assert tool is not None, (
            "create_dr must be registered via @mcp.tool(); "
            f"registered tools: {[t.name for t in mcp._tool_manager._tools.values()]}"
        )
        fn_ref = getattr(tool, "fn", None)
        assert (
            fn_ref is server_mod.create_dr
            or getattr(fn_ref, "__wrapped__", None) is server_mod.create_dr
        ), (
            "create_dr tool must be backed by the module-level create_dr callable; "
            "decorator identity check failed"
        )

    def test_create_dr_tool_accepts_four_required_params(self) -> None:
        import owlbear_mcp_kanban.server as server_mod

        fn = getattr(server_mod, "create_dr", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_dr must exist"

        params = inspect.signature(fn).parameters
        assert len(params) == 5, (
            f"create_dr must accept exactly 5 params (ctx + 4 business), got {len(params)}: {list(params)}"
        )
        for required in ("task_id", "agent", "request_type", "body"):
            assert required in params, f"create_dr missing required param: {required}"
            assert params[required].default is inspect.Parameter.empty, (
                f"create_dr param '{required}' must be required (no default), "
                f"got default={params[required].default!r}"
            )

    @pytest.mark.asyncio
    async def test_create_dr_success_returns_created_true_and_relative_path(
        self, app_ctx: AppContext
    ) -> None:
        import owlbear_mcp_kanban.server as server_mod

        fn = getattr(server_mod, "create_dr", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_dr must exist"

        ctx = _make_mcp_ctx(app_ctx)
        absolute_path = app_ctx.kanban_dir / "decisions" / "pending" / "1-decision.md"

        with patch(
            "owlbear_mcp_kanban.server.decisions.create_dr", return_value=absolute_path
        ) as mock_create_dr:
            result = await fn(
                ctx,
                task_id="1",
                agent="builder",
                request_type="decision",
                body="## Question\nShould we proceed?",
            )

        mock_create_dr.assert_called_once()
        _args, _kwargs = mock_create_dr.call_args
        assert _kwargs.get("task_id") == 1 or (len(_args) > 0 and _args[0] == 1), (
            "create_dr did not forward task_id to decisions.create_dr"
        )
        assert _kwargs.get("agent") == "builder" or (
            len(_args) > 1 and _args[1] == "builder"
        ), "create_dr did not forward agent to decisions.create_dr"
        assert _kwargs.get("request_type") == "decision" or (
            len(_args) > 2 and _args[2] == "decision"
        ), "create_dr did not forward request_type to decisions.create_dr"
        assert _kwargs.get("body") == "## Question\nShould we proceed?" or (
            len(_args) > 3 and _args[3] == "## Question\nShould we proceed?"
        ), "create_dr did not forward body to decisions.create_dr"
        assert result["created"] is True
        assert result["path"] == "decisions/pending/1-decision.md", (
            "create_dr must return a workspace-relative path"
        )
        assert not Path(result["path"]).is_absolute(), (
            "create_dr response path must be relative, not absolute"
        )

    @pytest.mark.asyncio
    async def test_create_dr_task_not_found_maps_to_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        import owlbear_mcp_kanban.server as server_mod

        fn = getattr(server_mod, "create_dr", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_dr must exist"

        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch(
                "owlbear_mcp_kanban.server.decisions.create_dr",
                side_effect=NotFoundError(
                    code="ERR_NOT_FOUND", user_message="task 999 not found"
                ),
            ),
            pytest.raises(ToolError, match="task 999 not found"),
        ):
            await fn(
                ctx,
                task_id="999",
                agent="builder",
                request_type="decision",
                body="## Q",
            )

    @pytest.mark.asyncio
    async def test_create_dr_collision_path_passthrough(
        self, app_ctx: AppContext
    ) -> None:
        import owlbear_mcp_kanban.server as server_mod

        fn = getattr(server_mod, "create_dr", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_dr must exist"

        ctx = _make_mcp_ctx(app_ctx)
        collision_path = (
            app_ctx.kanban_dir / "decisions" / "pending" / "1-decision-2.md"
        )

        with patch(
            "owlbear_mcp_kanban.server.decisions.create_dr", return_value=collision_path
        ):
            result = await fn(
                ctx,
                task_id="1",
                agent="builder",
                request_type="decision",
                body="## Q",
            )

        assert result == {
            "created": True,
            "path": "decisions/pending/1-decision-2.md",
        }, (
            "create_dr must preserve collision suffix path returned by decisions.create_dr"
        )

    @pytest.mark.asyncio
    async def test_create_dr_accepts_action_request_type(
        self, app_ctx: AppContext
    ) -> None:
        import owlbear_mcp_kanban.server as server_mod

        fn = getattr(server_mod, "create_dr", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_dr must exist"

        ctx = _make_mcp_ctx(app_ctx)
        action_path = app_ctx.kanban_dir / "decisions" / "pending" / "1-action.md"

        with patch(
            "owlbear_mcp_kanban.server.decisions.create_dr", return_value=action_path
        ) as mock_create_dr:
            result = await fn(
                ctx,
                task_id="1",
                agent="builder",
                request_type="action",
                body="## Action Request",
            )

        mock_create_dr.assert_called_once()
        assert result["created"] is True, (
            "create_dr must accept request_type='action' (got non-success result)"
        )
        assert result["path"] == "decisions/pending/1-action.md"

    @pytest.mark.asyncio
    async def test_create_dr_rejects_invalid_request_type(
        self, app_ctx: AppContext
    ) -> None:
        import owlbear_mcp_kanban.server as server_mod

        fn = getattr(server_mod, "create_dr", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_dr must exist"

        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr") as mock_create_dr,
            pytest.raises(ToolError, match=r"decision|action"),
        ):
            await fn(
                ctx,
                task_id="1",
                agent="builder",
                request_type="approach-selection",
                body="## Q",
            )

        mock_create_dr.assert_not_called()
