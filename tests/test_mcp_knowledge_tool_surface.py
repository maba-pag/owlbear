"""Tests for task #1334: Tool surface validation (active tools, inactive removed, stubs registered).

AC coverage:
    - AC1: exactly 10 tools in mcp._tool_manager.list_tools() at import time
    - AC2: active tool set contains all 10 expected names
         (search_knowledge, list_sources, get_stats, ingest_document, refresh_source,
            remove_source, get_next_batch, get_consolidation_candidates, store_enrichment,
          retry_failed_enrichment)
  - AC3: removed tools absent from tool list
         (list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge)

All tests FAIL in RED phase because current server has 16 registered tools:
  - get_consolidation_candidates is a bare function (not registered) → AC2 fails
  - list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge
    are registered → AC3 fails
  - Total count is 16, not 8 → AC1 fails

Tests pass GREEN after #1335:
  - Removes 5 tool decorators (list_entities, bookmark_source, list_bookmarks,
    update_bookmark_tags, consolidate_knowledge)
  - Registers get_consolidation_candidates via mcp.tool() decorator or post-def pattern

Run with: uv run pytest tests/test_mcp_knowledge_tool_surface_1334.py
"""

from __future__ import annotations

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
# Expected tool surface
# ---------------------------------------------------------------------------

_ACTIVE_TOOLS = frozenset(
    {
        "search_knowledge",
        "list_sources",
        "get_stats",
        "ingest_document",
        "refresh_source",
        "remove_source",
        "get_next_batch",
        "retry_failed_enrichment",
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

# ---------------------------------------------------------------------------
# TestFromAC_ToolSurfaceValidation
# ---------------------------------------------------------------------------


class TestFromAC_ToolSurfaceValidation:
    """Contract tests for the mcp-knowledge tool surface after phase-4 cleanup (#1334)."""

    # -- AC1: Exactly 10 tools registered -----------------------------------

    def test_exactly_eight_tools_registered(self) -> None:
        """AC1: mcp._tool_manager.list_tools() must return exactly 10 tools at import time.

        FAILS in RED: current server has 16 registered tools.
        PASSES in GREEN after #1335 removes 5 deprecated tools and 4 scope-stub decorators,
        and registers get_consolidation_candidates.
        """
        tool_names = _registered_tool_names()
        assert len(tool_names) == 10, (
            f"Expected exactly 10 registered tools, got {len(tool_names)}: {sorted(tool_names)!r}. "
            "After #1335: remove @mcp.tool() from list_entities, bookmark_source, list_bookmarks, "
            "update_bookmark_tags, consolidate_knowledge; and register get_consolidation_candidates."
        )

    # -- AC2: All 10 active tools present -----------------------------------

    def test_all_active_tools_present(self) -> None:
        """AC2: tool list must contain all 10 active tool names.

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
