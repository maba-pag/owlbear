"""Integration tests for mcp-kanban against real kanban-md binary.

Tests exercise the full stack: MCP tool → subprocess → kanban-md binary → temp filesystem.
All tests require the kanban-md binary and are therefore marked @pytest.mark.integration.

Task #57: Add mcp-kanban integration tests with real kanban-md binary.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from owlbear_mcp_kanban.server import (
    AppContext,
    create_task,
    list_tasks,
    move_task,
    show_task,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# ---------------------------------------------------------------------------
# Minimal board config — only the fields kanban-md requires to run
# ---------------------------------------------------------------------------

_MINIMAL_CONFIG = """\
version: 10
board:
    name: test
tasks_dir: tasks
statuses:
    - name: ideation
    - name: backlog
    - name: todo
priorities:
    - important
defaults:
    status: ideation
    priority: important
    class: standard
tui:
    title_lines: 1
next_id: 1
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def real_kanban_bin() -> Path:
    """Resolve the kanban-md binary path.

    Resolution order:
    1. ``KANBAN_BIN`` environment variable
    2. ``kanban/kanban-md.exe`` relative to the repository root

    Calls ``pytest.skip`` if neither location yields a real file.
    """
    env_bin = os.environ.get("KANBAN_BIN")
    if env_bin:
        p = Path(env_bin)
        if p.exists():
            return p

    # Traverse from this file up to repo root: tests/ → mcp-kanban/ → serve/ → root
    repo_root = Path(__file__).resolve().parents[3]
    convention = repo_root / ".owlbear" / "kanban" / "kanban-md.exe"
    if convention.exists():
        return convention

    pytest.skip(
        "kanban-md binary not found — run kanban/setup.ps1 or set KANBAN_BIN env var"
    )


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Create a temp board directory with minimal config.yml and tasks/ subdirectory."""
    (tmp_path / "tasks").mkdir()
    (tmp_path / "config.yml").write_text(_MINIMAL_CONFIG, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Test server factory — creates a FastMCP with overridden lifespan
# ---------------------------------------------------------------------------


def _make_test_server(board: Path, binary: Path) -> FastMCP:
    """Create a FastMCP test server with a custom lifespan that injects temp board dir.

    The lifespan yields an AppContext pointing at the given temp directory and
    binary, overriding the production lifespan that uses the workspace 'kanban/'
    directory.  All four tools under test are registered via add_tool so that
    the MCP in-memory client can invoke them by name.
    """

    @asynccontextmanager
    async def _test_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext, None]:
        yield AppContext(kanban_bin=binary, kanban_dir=board)

    test_server = FastMCP("test-kanban", lifespan=_test_lifespan)
    test_server.add_tool(list_tasks)
    test_server.add_tool(create_task)
    test_server.add_tool(show_task)
    test_server.add_tool(move_task)
    return test_server


# ---------------------------------------------------------------------------
# TestFromAC_Integration
# ---------------------------------------------------------------------------


class TestFromAC_Integration:
    """Contract tests derived from task #57 acceptance criteria.

    Each test connects to a fresh FastMCP test server via the MCP SDK
    in-memory transport and exercises one end-to-end scenario against
    the real kanban-md binary with a temp board directory.
    """

    # AC: create task + list tasks roundtrip — created task appears in list output
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_list_roundtrip(
        self, board_dir: Path, real_kanban_bin: Path
    ) -> None:
        """create_task followed by list_tasks returns the newly created task title."""
        server = _make_test_server(board_dir, real_kanban_bin)
        async with create_connected_server_and_client_session(server) as client:
            await client.call_tool("create_task", {"title": "My Integration Task"})
            list_result = await client.call_tool("list_tasks", {})
        text = list_result.content[0].text
        assert "My Integration Task" in text

    # AC: create task + show by ID roundtrip — returned fields (title, status) match
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_show_roundtrip(
        self, board_dir: Path, real_kanban_bin: Path
    ) -> None:
        """show_task returns a result containing the created task's title and default status."""
        server = _make_test_server(board_dir, real_kanban_bin)
        async with create_connected_server_and_client_session(server) as client:
            await client.call_tool("create_task", {"title": "Show Roundtrip Task"})
            # Fresh board starts at next_id: 1 → first task always has ID 1
            show_result = await client.call_tool("show_task", {"task_id": "1"})
        text = show_result.content[0].text
        assert "Show Roundtrip Task" in text
        assert "ideation" in text  # default status per config.yml statuses

    # AC: create + move + show — status change persists after move
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_create_move_show(
        self, board_dir: Path, real_kanban_bin: Path
    ) -> None:
        """move_task changes the task status; subsequent show_task reflects the new status."""
        server = _make_test_server(board_dir, real_kanban_bin)
        async with create_connected_server_and_client_session(server) as client:
            await client.call_tool("create_task", {"title": "Move Me Task"})
            await client.call_tool("move_task", {"task_id": "1", "status": "backlog"})
            show_result = await client.call_tool("show_task", {"task_id": "1"})
        text = show_result.content[0].text
        assert "backlog" in text.lower()

    # AC: create 2 tasks with distinct tags + filtered list — only matching task returned
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_filtered_list_by_tag(
        self, board_dir: Path, real_kanban_bin: Path
    ) -> None:
        """list_tasks with tag filter returns only tasks whose tags match the filter."""
        server = _make_test_server(board_dir, real_kanban_bin)
        async with create_connected_server_and_client_session(server) as client:
            await client.call_tool("create_task", {"title": "Alpha Task", "tags": "alpha"})
            await client.call_tool("create_task", {"title": "Beta Task", "tags": "beta"})
            filter_result = await client.call_tool("list_tasks", {"tag": "alpha"})
        filtered_text = filter_result.content[0].text
        assert "Alpha Task" in filtered_text
        assert "Beta Task" not in filtered_text

    # AC: show nonexistent task ID returns error string in tool result, not exception
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_show_nonexistent_returns_error_not_exception(
        self, board_dir: Path, real_kanban_bin: Path
    ) -> None:
        """show_task with a missing ID returns an error string — never raises an exception."""
        server = _make_test_server(board_dir, real_kanban_bin)
        async with create_connected_server_and_client_session(server) as client:
            # Should NOT raise — tool must return an error string
            result = await client.call_tool("show_task", {"task_id": "99999"})
        assert result.content, "Tool result must have at least one content item"
        text = result.content[0].text
        assert "error" in text.lower(), (
            f"Expected error message in result, got: {text!r}"
        )

    # AC: show_task returns data containing the expected fields (title, status)
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_show_returns_output_with_title_and_status_fields(
        self, board_dir: Path, real_kanban_bin: Path
    ) -> None:
        """show_task output identifies the task by title and includes a status label."""
        server = _make_test_server(board_dir, real_kanban_bin)
        async with create_connected_server_and_client_session(server) as client:
            await client.call_tool("create_task", {"title": "Field Check Task"})
            result = await client.call_tool("show_task", {"task_id": "1"})
        text = result.content[0].text
        assert "Field Check Task" in text, f"title not found in: {text!r}"
        # The status field must appear in the output in recognisable form
        assert "Status:" in text or '"status"' in text, (
            f"No status field found in: {text!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_Configuration — non-binary AC items
# ---------------------------------------------------------------------------


class TestFromAC_Configuration:
    """Contract tests covering marker registration and CI requirements from #57 AC."""

    # AC: Tests marked @pytest.mark.integration; marker registered in root pyproject.toml
    def test_integration_marker_registered_in_pyproject(self) -> None:
        """The 'integration' marker must be declared in the root pyproject.toml markers list."""
        import tomllib

        repo_root = Path(__file__).resolve().parents[3]
        pyproject_path = repo_root / "pyproject.toml"
        assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"
        with pyproject_path.open("rb") as fh:
            config = tomllib.load(fh)
        markers: list[str] = (
            config.get("tool", {})
            .get("pytest", {})
            .get("ini_options", {})
            .get("markers", [])
        )
        integration_entries = [m for m in markers if m.startswith("integration:")]
        assert integration_entries, (
            "No 'integration:' marker found in [tool.pytest.ini_options].markers in pyproject.toml. "
            "Add: integration: marks tests that require the kanban-md binary (deselect with -m 'not integration')"
        )


# ---------------------------------------------------------------------------
# TestFromAC_StructuredContent — MCP protocol-level structuredContent verification
# ---------------------------------------------------------------------------


class TestFromAC_StructuredContent:
    """Contract tests derived from task #538 acceptance criteria.

    Verify that FastMCP populates ``CallToolResult.structuredContent`` when
    tools return a ``KanbanTask`` Pydantic model.  These tests exercise the
    end-to-end MCP protocol layer, complementing the unit-level outputSchema
    registration tests in ``test_mcp_kanban_kanbantask_model_495.py``.
    """

    # AC: show_task structuredContent — non-None dict with id, title, status, class keys
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_show_task_structured_content(
        self, board_dir: Path, real_kanban_bin: Path
    ) -> None:
        """show_task CallToolResult.structuredContent is a non-None dict with required keys."""
        server = _make_test_server(board_dir, real_kanban_bin)
        async with create_connected_server_and_client_session(server) as client:
            await client.call_tool("create_task", {"title": "StructuredContent Task"})
            result = await client.call_tool("show_task", {"task_id": "1"})
        sc = result.structuredContent
        assert sc is not None, "structuredContent must be populated for KanbanTask return type"
        assert isinstance(sc, dict), f"structuredContent must be a dict, got {type(sc)}"
        assert isinstance(sc.get("id"), int), f"'id' must be int, got: {sc.get('id')!r}"
        assert isinstance(sc.get("title"), str), f"'title' must be str, got: {sc.get('title')!r}"
        assert isinstance(sc.get("status"), str), f"'status' must be str, got: {sc.get('status')!r}"

    # AC: move_task structuredContent — non-None dict with status matching target
    @pytest.mark.integration
    @pytest.mark.asyncio(loop_scope="function")
    async def test_move_task_structured_content(
        self, board_dir: Path, real_kanban_bin: Path
    ) -> None:
        """move_task CallToolResult.structuredContent contains the updated status."""
        server = _make_test_server(board_dir, real_kanban_bin)
        async with create_connected_server_and_client_session(server) as client:
            await client.call_tool("create_task", {"title": "Move StructuredContent Task"})
            result = await client.call_tool("move_task", {"task_id": "1", "status": "backlog"})
        sc = result.structuredContent
        assert sc is not None, "structuredContent must be populated for KanbanTask return type"
        assert isinstance(sc, dict), f"structuredContent must be a dict, got {type(sc)}"
        assert sc.get("status") == "backlog", (
            f"structuredContent['status'] must equal 'backlog', got: {sc.get('status')!r}"
        )


