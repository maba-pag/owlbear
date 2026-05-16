"""Tests for task #1334: Tool surface validation (8 active, inactive removed, stubs registered).

AC coverage:
  - AC1: exactly 8 tools in mcp._tool_manager.list_tools() at import time
  - AC2: active tool set contains all 8 expected names
         (search_knowledge, list_sources, get_stats, ingest_document, refresh_source,
          get_next_batch, get_consolidation_candidates, store_enrichment)
  - AC3: removed tools absent from tool list
         (list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge)
  - AC4+AC5 (combined): scope stubs exist as callables in server module AND are NOT
         registered as MCP tools
         (import_scope, export_scope, sync_from_global, sync_to_global)

Notes on AC4 standalone viability:
  FastMCP's @mcp.tool decorator returns the original function unchanged (side-effect-only
  registration). So callable(server_mod.import_scope) is True both before and after #1335
  removes the decorator. A pure callable() test would pass in RED — it is therefore merged
  with AC5 into a single assertion: callable AND not in tool list.

All tests FAIL in RED phase because current server has 16 registered tools:
  - get_consolidation_candidates is a bare function (not registered) → AC2 fails
  - list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge
    are registered → AC3 fails
  - import_scope, export_scope, sync_from_global, sync_to_global are registered as tools
    → AC4+AC5 combined test fails
  - Total count is 16, not 8 → AC1 fails

Tests pass GREEN after #1335:
  - Removes 5 tool decorators (list_entities, bookmark_source, list_bookmarks,
    update_bookmark_tags, consolidate_knowledge)
  - Removes 4 scope-stub decorators (import_scope, export_scope, sync_from_global,
    sync_to_global) while keeping the functions
  - Registers get_consolidation_candidates via mcp.tool() decorator or post-def pattern

Run with: uv run pytest tests/test_mcp_knowledge_tool_surface_1334.py
"""

from __future__ import annotations

import owlbear_mcp_knowledge.server as server_mod
from owlbear_mcp_knowledge.server import mcp


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _registered_tool_names() -> frozenset[str]:
    """Return frozenset of names registered in the FastMCP tool manager at import time."""
    if hasattr(mcp, "_tool_manager"):
        return frozenset(
            getattr(t, "name", "")
            for t in mcp._tool_manager.list_tools()  # noqa: SLF001
        )
    return frozenset()


# ---------------------------------------------------------------------------
# Expected tool surface (post-#1335)
# ---------------------------------------------------------------------------

_ACTIVE_TOOLS = frozenset(
    {
        "search_knowledge",
        "list_sources",
        "get_stats",
        "ingest_document",
        "refresh_source",
        "get_next_batch",
        "get_consolidation_candidates",
        "store_enrichment",
    }
)

_REMOVED_TOOLS = frozenset(
    {
        "list_entities",
        "bookmark_source",
        "list_bookmarks",
        "update_bookmark_tags",
        "consolidate_knowledge",
    }
)

_SCOPE_STUBS = frozenset(
    {
        "import_scope",
        "export_scope",
        "sync_from_global",
        "sync_to_global",
    }
)


# ---------------------------------------------------------------------------
# TestFromAC_ToolSurfaceValidation
# ---------------------------------------------------------------------------


class TestFromAC_ToolSurfaceValidation:
    """Contract tests for the mcp-knowledge tool surface after phase-4 cleanup (#1334)."""

    # -- AC1: Exactly 8 tools registered ------------------------------------

    def test_exactly_eight_tools_registered(self) -> None:
        """AC1: mcp._tool_manager.list_tools() must return exactly 8 tools at import time.

        FAILS in RED: current server has 16 registered tools.
        PASSES in GREEN after #1335 removes 5 deprecated tools and 4 scope-stub decorators,
        and registers get_consolidation_candidates.
        """
        tool_names = _registered_tool_names()
        assert len(tool_names) == 8, (
            f"Expected exactly 8 registered tools, got {len(tool_names)}: {sorted(tool_names)!r}. "
            "After #1335: remove @mcp.tool() from list_entities, bookmark_source, list_bookmarks, "
            "update_bookmark_tags, consolidate_knowledge, import_scope, export_scope, "
            "sync_from_global, sync_to_global; and register get_consolidation_candidates."
        )

    # -- AC2: All 8 active tools present ------------------------------------

    def test_all_active_tools_present(self) -> None:
        """AC2: tool list must contain all 8 active tool names.

        FAILS in RED: get_consolidation_candidates is currently a bare function,
        not registered with @mcp.tool().
        PASSES in GREEN after #1335 registers it.
        """
        tool_names = _registered_tool_names()
        missing = _ACTIVE_TOOLS - tool_names
        assert not missing, (
            f"Active tools missing from registry: {sorted(missing)!r}. "
            "Ensure get_consolidation_candidates is registered via @mcp.tool() or post-def pattern "
            "like get_next_batch = mcp.tool(...)(get_consolidation_candidates)."
        )

    # -- AC3: Removed tools absent ------------------------------------------

    def test_removed_tools_not_registered(self) -> None:
        """AC3: deprecated tools must not appear in the tool list.

        Removed tools: list_entities, bookmark_source, list_bookmarks,
        update_bookmark_tags, consolidate_knowledge.

        FAILS in RED: all 5 are still registered with @mcp.tool() decorators.
        PASSES in GREEN after #1335 removes those decorators.
        """
        tool_names = _registered_tool_names()
        still_present = _REMOVED_TOOLS & tool_names
        assert not still_present, (
            f"Tools that must be removed are still registered: {sorted(still_present)!r}. "
            "Remove @mcp.tool() decorators from these functions."
        )

    # -- AC4+AC5: Scope stubs callable AND not registered as tools ----------

    def test_scope_stubs_are_callable_and_not_registered_as_tools(self) -> None:
        """AC4+AC5: scope stubs must exist as callable functions NOT in the MCP tool list.

        Scope stubs: import_scope, export_scope, sync_from_global, sync_to_global.
        They are intended as internal utilities reserved for future activation (D12, D16).

        FAILS in RED: all 4 currently have @mcp.tool() decorators → they appear in the
        tool list (AC5 assertion fails for each).
        PASSES in GREEN after #1335 removes their @mcp.tool() decorators while keeping
        the function definitions intact.

        Note: FastMCP's @mcp.tool() decorator is side-effect-only — it does NOT wrap the
        function, so callable() returns True both before and after removal. The failing
        assertion in RED is the "not in tool list" check (AC5).
        """
        tool_names = _registered_tool_names()
        failures: list[str] = []
        for name in sorted(_SCOPE_STUBS):
            fn = getattr(server_mod, name, None)
            if fn is None:
                failures.append(f"  {name!r}: not found in server module")
                continue
            if not callable(fn):
                failures.append(f"  {name!r}: found but not callable (AC4)")
            if name in tool_names:
                failures.append(f"  {name!r}: registered as MCP tool — remove @mcp.tool() decorator (AC5)")
        assert not failures, "Scope stub check failures:\n" + "\n".join(failures)
