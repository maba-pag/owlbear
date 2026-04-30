"""Failing tests for #1196: task_id input validation at MCP boundary for create_dr.

AC coverage:
  ac1-error      — empty string "" → ToolError before decisions.create_dr called
  ac1-error      — wildcard "*" → ToolError before decisions.create_dr called
  ac1-error      — path-traversal "../" → ToolError before decisions.create_dr called
  ac1-error      — non-numeric string "abc" → ToolError before decisions.create_dr called
  ac1-boundary   — mixed alphanumeric "42abc" → ToolError (purely-numeric check)
  ac2-error      — invalid task_id: decisions.create_dr never reached (wildcard)
  ac2-edge       — invalid task_id: decisions.create_dr never reached (empty)
  ac4-smoke      — numeric string "42" coerced to int 42 before forwarding

All tests FAIL (RED phase):
  - Tests 1-5 (ac1/ac3): current create_dr tool performs no task_id validation;
    ToolError is not raised for invalid inputs. pytest.raises(ToolError) fails
    with 'DID NOT RAISE'.
  - Tests 6-7 (ac2): same — no validation means decisions.create_dr IS called;
    mock_create_dr.assert_not_called() is never reached because 'DID NOT RAISE'
    fails first.
  - Test 8 (ac4): task_id='42' forwarded as str to decisions.create_dr; assertion
    isinstance(call_kwargs['task_id'], int) fails because type is str, not int.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext
from owlbear_mcp_kanban.server import create_dr as mcp_create_dr

# ---------------------------------------------------------------------------
# Board / context helpers
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
    return kanban_dir


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """Minimal AppContext — real KanbanEngine, decisions not needed (decisions.create_dr mocked)."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# TestFromAC_CreateDrTaskIdValidation
# ---------------------------------------------------------------------------


class TestFromAC_CreateDrTaskIdValidation:
    """Tests for task_id input validation at the MCP boundary in create_dr.

    All tests verify behavior of the create_dr MCP tool (server layer), not
    decisions.create_dr (engine layer). decisions.create_dr is mocked throughout.
    """

    # ------------------------------------------------------------------
    # AC1 + AC3 (td:2): Rejection — invalid task_id → ToolError
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_string_rejected_with_tool_error(self, app_ctx: AppContext) -> None:
        """AC1+AC3: empty string task_id → ToolError raised at MCP boundary.

        FAIL path (RED): current code performs no task_id validation; empty string
        is forwarded to decisions.create_dr. No ToolError raised. pytest.raises(ToolError)
        fails with 'DID NOT RAISE'.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await mcp_create_dr(ctx, task_id="", agent="builder", request_type="decision", body="b")

    @pytest.mark.asyncio
    async def test_wildcard_rejected_with_tool_error(self, app_ctx: AppContext) -> None:
        """AC1+AC3: wildcard '*' task_id → ToolError raised at MCP boundary.

        FAIL path (RED): current code passes '*' to decisions.create_dr, which
        constructs filename '*-decision.md' — a security hole. No ToolError raised.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await mcp_create_dr(ctx, task_id="*", agent="builder", request_type="decision", body="b")

    @pytest.mark.asyncio
    async def test_path_traversal_rejected_with_tool_error(self, app_ctx: AppContext) -> None:
        """AC1+AC3: path-traversal '../' task_id → ToolError raised at MCP boundary.

        FAIL path (RED): current code passes '../' to decisions.create_dr; this
        value ends up in the filename f'{task_id}-decision.md' enabling path traversal.
        No ToolError raised currently.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await mcp_create_dr(ctx, task_id="../", agent="builder", request_type="decision", body="b")

    @pytest.mark.asyncio
    async def test_non_numeric_string_rejected_with_tool_error(self, app_ctx: AppContext) -> None:
        """AC1+AC3: non-numeric string 'abc' → ToolError raised at MCP boundary.

        FAIL path (RED): no validation in current code; 'abc' is forwarded.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await mcp_create_dr(ctx, task_id="abc", agent="builder", request_type="decision", body="b")

    @pytest.mark.asyncio
    async def test_mixed_alphanumeric_rejected_with_tool_error(self, app_ctx: AppContext) -> None:
        """AC1 boundary: '42abc' (mixed numeric+alpha) → ToolError.

        Purely-numeric-only check must reject inputs that contain alphabetic
        characters even when they begin with digits.

        FAIL path (RED): current code does not validate; '42abc' is forwarded.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await mcp_create_dr(ctx, task_id="42abc", agent="builder", request_type="decision", body="b")

    # ------------------------------------------------------------------
    # AC2 (td:2): Invalid task_id must not reach decisions.create_dr
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_wildcard_does_not_reach_decisions_create_dr(self, app_ctx: AppContext) -> None:
        """AC2 error: wildcard task_id raises ToolError; decisions.create_dr never called.

        FAIL path (RED): current code calls decisions.create_dr with the wildcard value.
        pytest.raises(ToolError) fails with 'DID NOT RAISE' before assert_not_called()
        is even reached.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.decisions.create_dr") as mock_create_dr:
            with pytest.raises(ToolError):
                await mcp_create_dr(ctx, task_id="*", agent="builder", request_type="decision", body="b")
            mock_create_dr.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_string_does_not_reach_decisions_create_dr(self, app_ctx: AppContext) -> None:
        """AC2 edge: empty string task_id raises ToolError; decisions.create_dr never called.

        FAIL path (RED): current code calls decisions.create_dr with the empty string.
        """
        ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.decisions.create_dr") as mock_create_dr:
            with pytest.raises(ToolError):
                await mcp_create_dr(ctx, task_id="", agent="builder", request_type="decision", body="b")
            mock_create_dr.assert_not_called()

    # ------------------------------------------------------------------
    # AC4 (td:1): Valid numeric task_id coerced to int before forwarding
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_numeric_string_coerced_to_int_before_forwarding(self, app_ctx: AppContext) -> None:
        """AC4 smoke: string '42' is coerced to int 42 before calling decisions.create_dr.

        FAIL path (RED): current code forwards task_id='42' (str) unchanged.
        The assertion isinstance(call_kwargs['task_id'], int) fails because the
        actual kwarg is '42' (str) and str != int. '42' == 42 is also False in Python.
        """
        ctx = _make_mcp_ctx(app_ctx)
        mock_create_dr = MagicMock(return_value=MagicMock())
        with patch("owlbear_mcp_kanban.server.decisions.create_dr", mock_create_dr):
            await mcp_create_dr(ctx, task_id="42", agent="builder", request_type="decision", body="body text")

        call_kwargs = mock_create_dr.call_args.kwargs
        assert call_kwargs["task_id"] == 42, (
            f"task_id forwarded as {call_kwargs['task_id']!r}; expected int 42"
        )
        assert isinstance(call_kwargs["task_id"], int), (
            f"task_id must be int, got {type(call_kwargs['task_id']).__name__!r}"
        )
