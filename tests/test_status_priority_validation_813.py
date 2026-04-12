"""Failing tests for status/priority validation in create_task and edit_task (#813, RED phase).

AC coverage:
  AC1 - create_task raises ValueError for invalid status
  AC2 - create_task raises ValueError for invalid priority
  AC3 - edit_task raises ValueError for invalid status
  AC4 - edit_task raises ValueError for invalid priority
  AC5 - valid status/priority values accepted (from config)
  AC6 - MCP adapter maps ValueError to ToolError for create_task and edit_task

All tests must FAIL at this stage — GREEN phase is task #814.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, create_task, edit_task

# ---------------------------------------------------------------------------
# Shared config content — mirrors real .owlbear/kanban/config.yml
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
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
next_id: 100
"""


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine instance wired to the temp kanban_dir."""
    return KanbanEngine(kanban_dir)


@pytest.fixture()
def task_id(engine: KanbanEngine) -> str:
    """Create a minimal task and return its string ID."""
    record = engine.create_task("Fixture task")
    return str(record.id)


def _make_raising_engine(method: str, exc: Exception) -> MagicMock:
    """Return a MagicMock KanbanEngine where method raises exc when called."""
    mock = MagicMock(spec=KanbanEngine)
    getattr(mock, method).side_effect = exc
    return mock


def _make_mcp_ctx(mock_engine: MagicMock) -> MagicMock:
    """Return a MagicMock MCP Context with the given mock engine in AppContext."""
    app_ctx = AppContext(engine=mock_engine, kanban_dir=Path("/fake/kanban"))
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ===========================================================================
# TestFromAC_CreateTaskValidation — AC1, AC2, AC5
# ===========================================================================


class TestFromAC_CreateTaskValidation:
    """Tests for AC1/AC2/AC5: create_task raises ValueError for invalid status or priority."""

    # --- AC1: invalid status rejected ----------------------------------------

    def test_create_task_invalid_status_raises_value_error(
        self, engine: KanbanEngine
    ) -> None:
        """create_task with a status not in config.statuses raises ValueError."""
        with pytest.raises(ValueError, match=r"badstatus"):
            engine.create_task("Bad status task", status="badstatus")

    def test_create_task_invalid_status_near_valid_raises_value_error(
        self, engine: KanbanEngine
    ) -> None:
        """create_task with a near-miss status string ('tdo' vs 'todo') raises ValueError."""
        with pytest.raises(ValueError, match=r"tdo"):
            engine.create_task("Typo status", status="tdo")

    # --- AC2: invalid priority rejected --------------------------------------

    def test_create_task_invalid_priority_raises_value_error(
        self, engine: KanbanEngine
    ) -> None:
        """create_task with a priority not in config.priorities raises ValueError."""
        with pytest.raises(ValueError, match=r"extreme"):
            engine.create_task("Bad priority task", priority="extreme")

    def test_create_task_invalid_priority_near_valid_raises_value_error(
        self, engine: KanbanEngine
    ) -> None:
        """create_task with a capitalized priority ('Important' not 'important') raises ValueError."""
        with pytest.raises(ValueError, match=r"Important"):
            engine.create_task("Capitalized priority", priority="Important")

    # --- AC5: valid values accepted — boundary test (doubles as AC1 edge) ----

    def test_create_task_valid_status_in_progress_accepted_underscore_rejected(
        self, engine: KanbanEngine
    ) -> None:
        """'in-progress' (hyphen) is valid; 'in_progress' (underscore) is not.
        Fails RED: pytest.raises(ValueError) block not satisfied — engine does not yet validate."""
        with pytest.raises(ValueError, match=r"in_progress"):
            engine.create_task("Underscore bad", status="in_progress")
        # GREEN phase: the above raises correctly; verify the valid form is still accepted
        record = engine.create_task("Hyphen good", status="in-progress")
        assert record.status == "in-progress"

    def test_create_task_valid_priority_critical_accepted(self, engine: KanbanEngine) -> None:
        """create_task with a valid priority 'critical' stores it without raising.
        AC4 priority dimension: valid values must be accepted without change."""
        record = engine.create_task("Valid priority task", priority="critical")
        assert record.priority == "critical"


# ===========================================================================
# TestFromAC_EditTaskValidation — AC3, AC4, AC5
# ===========================================================================


class TestFromAC_EditTaskValidation:
    """Tests for AC3/AC4/AC5: edit_task raises ValueError for invalid status or priority."""

    # --- AC3: invalid status rejected ----------------------------------------

    def test_edit_task_invalid_status_raises_value_error(
        self, engine: KanbanEngine, task_id: str
    ) -> None:
        """edit_task with a status not in config.statuses raises ValueError."""
        with pytest.raises(ValueError, match=r"bogus"):
            engine.edit_task(task_id, status="bogus")

    def test_edit_task_invalid_status_near_valid_raises_value_error(
        self, engine: KanbanEngine, task_id: str
    ) -> None:
        """edit_task with near-miss status 'todos' (not 'todo') raises ValueError."""
        with pytest.raises(ValueError, match=r"todos"):
            engine.edit_task(task_id, status="todos")

    # --- AC4: invalid priority rejected --------------------------------------

    def test_edit_task_invalid_priority_raises_value_error(
        self, engine: KanbanEngine, task_id: str
    ) -> None:
        """edit_task with a priority not in config.priorities raises ValueError."""
        with pytest.raises(ValueError, match=r"super-high"):
            engine.edit_task(task_id, priority="super-high")

    def test_edit_task_invalid_priority_near_valid_raises_value_error(
        self, engine: KanbanEngine, task_id: str
    ) -> None:
        """edit_task with near-miss priority 'someday!' raises ValueError."""
        with pytest.raises(ValueError, match=r"someday!"):
            engine.edit_task(task_id, priority="someday!")

    # --- AC5: valid values accepted — boundary test (doubles as AC3 edge) ----

    def test_edit_task_valid_status_done_accepted_typo_rejected(
        self, engine: KanbanEngine, task_id: str
    ) -> None:
        """Valid status 'done' is accepted; typo 'donne' raises ValueError.
        Fails RED: pytest.raises(ValueError) block not satisfied — no validation exists."""
        with pytest.raises(ValueError, match=r"donne"):
            engine.edit_task(task_id, status="donne")
        # GREEN phase: typo raises; valid 'done' must also be accepted
        record = engine.edit_task(task_id, status="done")
        assert record.status == "done"

    def test_edit_task_valid_priority_someday_accepted(self, engine: KanbanEngine, task_id: str) -> None:
        """edit_task with a valid priority 'someday' stores it without raising.
        AC4 priority dimension: valid values must be accepted without change."""
        record = engine.edit_task(task_id, priority="someday")
        assert record.priority == "someday"


# ===========================================================================
# TestFromAC_MCPAdapterValidation — AC6
# ===========================================================================


class TestFromAC_MCPAdapterValidation:
    """Tests for AC6: MCP adapter maps ValueError to ToolError for create_task and edit_task."""

    # --- create_task adapter -------------------------------------------------

    @pytest.mark.asyncio
    async def test_mcp_create_task_invalid_status_raises_tool_error(self) -> None:
        """MCP create_task wraps engine ValueError (invalid status) as ToolError.
        Fails RED: adapter has no try/except for ValueError — raw ValueError propagates."""
        mock_engine = _make_raising_engine(
            "create_task", ValueError("Invalid status 'badstatus'")
        )
        mcp_ctx = _make_mcp_ctx(mock_engine)
        with pytest.raises(ToolError):
            await create_task(mcp_ctx, title="Bad status task", status="badstatus")

    @pytest.mark.asyncio
    async def test_mcp_create_task_invalid_priority_raises_tool_error(self) -> None:
        """MCP create_task wraps engine ValueError (invalid priority) as ToolError.
        Fails RED: adapter has no try/except for ValueError — raw ValueError propagates."""
        mock_engine = _make_raising_engine(
            "create_task", ValueError("Invalid priority 'extreme'")
        )
        mcp_ctx = _make_mcp_ctx(mock_engine)
        with pytest.raises(ToolError):
            await create_task(mcp_ctx, title="Bad priority task", priority="extreme")

    # --- edit_task adapter ---------------------------------------------------

    @pytest.mark.asyncio
    async def test_mcp_edit_task_invalid_status_raises_tool_error(self) -> None:
        """MCP edit_task wraps engine ValueError (invalid status) as ToolError.
        Fails RED: adapter catches only FileNotFoundError, not ValueError."""
        mock_engine = _make_raising_engine(
            "edit_task", ValueError("Invalid status 'bogus'")
        )
        mcp_ctx = _make_mcp_ctx(mock_engine)
        with pytest.raises(ToolError):
            await edit_task(mcp_ctx, task_id="1", status="bogus")

    @pytest.mark.asyncio
    async def test_mcp_edit_task_invalid_priority_raises_tool_error(self) -> None:
        """MCP edit_task wraps engine ValueError (invalid priority) as ToolError.
        Fails RED: adapter catches only FileNotFoundError, not ValueError."""
        mock_engine = _make_raising_engine(
            "edit_task", ValueError("Invalid priority 'super-high'")
        )
        mcp_ctx = _make_mcp_ctx(mock_engine)
        with pytest.raises(ToolError):
            await edit_task(mcp_ctx, task_id="1", priority="super-high")
