"""Tests for task #525: Implement memory-mcp tools — cross-cutting requirements.

Covers AC items NOT exercised by test_memory_tools_556.py (the test task that
verified tool-contract behaviour). This file focuses on structural / operational
requirements that the architect added to #525's AC after #556 was written:

  - AC-CC1: sqlite3.connect() uses check_same_thread=False in server.py
  - AC-CC2: All SQLite calls wrapped in asyncio.to_thread in tools.py
  - AC-CC3: _apply_tool_exclusions called at module level after tool registration
  - AC-CC4: __all__ in server.py includes all 4 tool functions + _apply_tool_exclusions
  - AC-ERR1: confidence < 0.7 error includes ", got {value}" suffix
  - AC-ERR2: invalid category error uses "Valid:" prefix and lists 5 categories in AC order

AC coverage table:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| check_same_thread=False | test_server_sqlite_connect_uses_check_same_thread_false | error |
| asyncio.to_thread | test_tools_wraps_sqlite_calls_in_asyncio_to_thread | error |
| _apply_tool_exclusions called at module level | test_apply_tool_exclusions_called_at_module_level | error |
| __all__ in server.py | test_server_all_exports_tool_functions | error |
| error: confidence ... got {value} | test_confidence_error_includes_got_value, test_confidence_error_value_matches_input | boundary |
| error: invalid category ... Valid: | test_invalid_category_error_uses_valid_prefix, test_invalid_category_error_lists_categories_in_ac_order | error |

All tests FAIL in RED phase — the current implementation (built in task #556) is
missing check_same_thread=False, asyncio.to_thread wrapping, module-level
_apply_tool_exclusions call, server.py __all__ updates, and the "got {value}"
/ "Valid:" error message detail.
"""

from __future__ import annotations

import ast
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_mcp_memory.server import AppContext
from owlbear_mcp_memory.tools import record_learning

_REPO_ROOT = Path(__file__).parent.parent
_SRC = _REPO_ROOT / "serve" / "mcp-memory" / "src" / "owlbear_mcp_memory"

_DDL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL,
    scope_agent TEXT,
    scope_project TEXT,
    approval_state TEXT NOT NULL DEFAULT 'pending',
    deleted_at TEXT
)
"""


def _make_conn() -> sqlite3.Connection:
    """In-memory SQLite connection with the memory_entries schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(_DDL)
    conn.commit()
    return conn


def _make_ctx(
    conn: sqlite3.Connection,
    project_name: str | None = None,
) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(conn=conn, project_name=project_name)
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_CrossCutting_525 — static analysis of server.py and tools.py
# ---------------------------------------------------------------------------


class TestFromAC_CrossCutting_525:
    """AST-level verification of structural requirements absent from test_556.

    These tests parse server.py and tools.py rather than exercising runtime
    behaviour so they can catch missing boilerplate before any code runs.
    """

    def _server_source(self) -> str:
        path = _SRC / "server.py"
        assert path.is_file(), f"server.py not found at {path}"
        return path.read_text(encoding="utf-8")

    def _tools_source(self) -> str:
        path = _SRC / "tools.py"
        assert path.is_file(), f"tools.py not found at {path}"
        return path.read_text(encoding="utf-8")

    # AC-CC1: sqlite3.connect() must pass check_same_thread=False
    def test_server_sqlite_connect_uses_check_same_thread_false(self) -> None:
        """AC-CC1: sqlite3.connect() in server.py must include check_same_thread=False.

        asyncio.to_thread dispatches the blocking SQLite call to a worker thread
        that is different from the thread that opened the connection. SQLite's
        default check_same_thread=True will raise ProgrammingError in that case.
        """
        tree = ast.parse(self._server_source())
        found = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "connect"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "sqlite3"
            ):
                for kw in node.keywords:
                    if kw.arg == "check_same_thread" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                        found = True
        assert found, (
            "server.py sqlite3.connect() is missing check_same_thread=False. "
            "Add it: sqlite3.connect(str(db_path), check_same_thread=False). "
            "Without it asyncio.to_thread will raise ProgrammingError."
        )

    # AC-CC2: SQLite calls must be dispatched via asyncio.to_thread
    def test_tools_wraps_sqlite_calls_in_asyncio_to_thread(self) -> None:
        """AC-CC2: tools.py must call await asyncio.to_thread(fn) for SQLite operations.

        Direct conn.execute() in an async function blocks the event loop.
        Per mcp-knowledge pattern, all blocking IO must be wrapped via
        asyncio.to_thread so the event loop remains responsive.
        """
        tree = ast.parse(self._tools_source())
        found = False
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Await)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "to_thread"
                and isinstance(node.value.func.value, ast.Name)
                and node.value.func.value.id == "asyncio"
            ):
                found = True
        assert found, (
            "tools.py contains no 'await asyncio.to_thread(...)' call. "
            "Wrap blocking SQLite operations per the mcp-knowledge pattern: "
            "await asyncio.to_thread(conn.execute, sql, params)."
        )

    # AC-CC3: _apply_tool_exclusions must be invoked at module level
    def test_apply_tool_exclusions_called_at_module_level(self) -> None:
        """AC-CC3: _apply_tool_exclusions(mcp) must appear as a top-level statement
        in tools.py (or server.py) after all @mcp.tool decorators have run.

        During import, @mcp.tool decorators register every tool. A module-level
        call then prunes them according to MEMORY_TOOLS_EXCLUDE before the server
        starts. Omitting this call means the env var has no effect.
        """

        def _has_module_level_exclusion_call(tree: ast.Module) -> bool:
            for node in tree.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    call = node.value
                    if isinstance(call.func, ast.Name) and call.func.id == "_apply_tool_exclusions":
                        return True
            return False

        server_tree = ast.parse(self._server_source())
        tools_tree = ast.parse(self._tools_source())

        assert _has_module_level_exclusion_call(server_tree) or _has_module_level_exclusion_call(tools_tree), (
            "_apply_tool_exclusions(mcp) is never called at module level. "
            "Add a top-level call at the end of tools.py (or server.py) after all "
            "@mcp.tool decorators so MEMORY_TOOLS_EXCLUDE takes effect on import."
        )

    # AC-CC4: server.py __all__ must export all 4 tool functions + _apply_tool_exclusions
    def test_server_all_exports_tool_functions(self) -> None:
        """AC-CC4: server.py __all__ must list all 4 tool functions (and _apply_tool_exclusions)
        so they are importable from a single authoritative module.

        The mcp-kanban reference server exports every tool alongside AppContext and
        app_lifespan. mcp-memory must follow the same pattern.
        """
        tree = ast.parse(self._server_source())
        exported: set[str] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
                and isinstance(node.value, ast.List)
            ):
                for elt in node.value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        exported.add(elt.value)

        required = {
            "get_knowledge",
            "record_learning",
            "list_entries",
            "mark_for_deletion",
            "_apply_tool_exclusions",
        }
        missing = required - exported
        assert not missing, (
            f"server.py __all__ is missing: {sorted(missing)}. "
            "Import the tool functions from tools.py and add them to __all__ "
            "to match the mcp-kanban reference pattern."
        )


# ---------------------------------------------------------------------------
# TestFromAC_ErrorMessages_525 — exact error string format from AC
# ---------------------------------------------------------------------------


class TestFromAC_ErrorMessages_525:
    """Verify that error message strings exactly match the AC specification.

    test_memory_tools_556.py only checks result.startswith('error:'); these tests
    verify the full format required by the AC.
    """

    # AC-ERR1: confidence error must include "got {value}" with the actual value
    @pytest.mark.asyncio
    async def test_confidence_error_includes_got_value(self) -> None:
        """AC-ERR1: confidence < 0.7 error format is "error: confidence must be >= 0.7, got {value}".

        Current implementation omits the ", got {value}" portion; the AC requires it
        so callers can see which value was rejected without re-reading the request.
        """
        conn = _make_conn()
        ctx = _make_ctx(conn, project_name="proj")

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test content",
            category="knowledge",
            confidence=0.42,
        )

        assert isinstance(result, str), f"Expected str, got {type(result).__name__}"
        assert result.startswith("error:"), f"Expected a soft-error string, got {result!r}"
        assert "got 0.42" in result, (
            f"AC specifies format 'error: confidence must be >= 0.7, got {{value}}' "
            f"but 'got 0.42' is absent from {result!r}"
        )

    # AC-ERR1: boundary — the reported value matches the caller's exact input
    @pytest.mark.asyncio
    async def test_confidence_error_value_reflects_caller_input(self) -> None:
        """AC-ERR1: the value in 'got {value}' must equal the confidence passed by the caller."""
        conn = _make_conn()
        ctx = _make_ctx(conn, project_name="proj")

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test content",
            category="knowledge",
            confidence=0.0,
        )

        assert isinstance(result, str)
        assert "got 0.0" in result, f"Error for confidence=0.0 must say 'got 0.0', got {result!r}"

    # AC-ERR2: invalid category error uses "Valid:" not "Valid categories:"
    @pytest.mark.asyncio
    async def test_invalid_category_error_uses_valid_prefix(self) -> None:
        """AC-ERR2: invalid category error must use '. Valid:' per AC specification.

        Current implementation says '. Valid categories:'; the AC shortens it to
        '. Valid:'.  Callers parsing the error string will fail to match if the
        prefix differs.
        """
        conn = _make_conn()
        ctx = _make_ctx(conn, project_name="proj")

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test content",
            category="not_a_real_category",
            confidence=0.8,
        )

        assert isinstance(result, str), f"Expected str, got {type(result).__name__}"
        assert result.startswith("error:"), f"Expected a soft-error string, got {result!r}"
        assert ". Valid:" in result, (
            f"AC specifies '. Valid:' prefix for the category list (not '. Valid categories:') — got {result!r}"
        )

    # AC-ERR2: category list must follow the AC-specified order
    @pytest.mark.asyncio
    async def test_invalid_category_error_lists_categories_in_ac_order(self) -> None:
        """AC-ERR2: categories listed as 'preference, knowledge, context, behavior, goal'.

        The AC gives a specific order. Current implementation sorts alphabetically
        ('behavior, context, goal, knowledge, preference'), which breaks any caller
        that compares the error string against the AC-specified format.
        """
        conn = _make_conn()
        ctx = _make_ctx(conn, project_name="proj")

        result = await record_learning(
            ctx,
            agent_id="agent1",
            content="test content",
            category="not_a_real_category",
            confidence=0.8,
        )

        assert isinstance(result, str)
        expected_list = "preference, knowledge, context, behavior, goal"
        assert expected_list in result, f"Category list must be '{expected_list}' per AC — got {result!r}"
