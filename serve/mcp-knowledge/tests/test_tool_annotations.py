"""Tests for task #501: Complete ToolAnnotations on mcp-knowledge server (TDD RED).

AC coverage:
  - AC1: search_knowledge: readOnlyHint=True, idempotentHint=True
  - AC2: list_sources: idempotentHint=True (readOnlyHint already present)
  - AC3: list_entities: idempotentHint=True (readOnlyHint already present)
  - AC4: get_stats: idempotentHint=True (readOnlyHint already present)
  - AC5: ingest_document unchanged — covered by TestFromAC_ToolReadOnlyHints in
         test_ingest_graph_tools.py; no new tests needed (guard tests would pass).
  - AC6: outputSchema auto-generated — verified by ->str return annotations that already
         exist on all 5 functions; no new tests needed (would pass).

Tests FAIL in RED phase because:
  - search_knowledge: bare @mcp.tool() with no annotations object (_get_tool_annotations
    returns None), so readOnlyHint=True and idempotentHint=True assertions fail.
  - list_sources, list_entities, get_stats: ToolAnnotations(readOnlyHint=True) set but
    idempotentHint defaults to None; assert idempotentHint is True fails.
"""

from __future__ import annotations

from owlbear_mcp_knowledge.server import mcp


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named mcp-knowledge tool, or None."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ---------------------------------------------------------------------------
# TestFromAC_KnowledgeToolAnnotations
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeToolAnnotations:
    """Contract tests: ToolAnnotations must be fully specified on all mcp-knowledge tools."""

    # -- AC1: search_knowledge ------------------------------------------------

    def test_search_knowledge_read_only_hint_true(self) -> None:
        """search_knowledge is read-only: readOnlyHint must be True."""
        ann = _get_tool_annotations("search_knowledge")
        assert ann is not None, (
            "search_knowledge has no ToolAnnotations; "
            "add annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True) "
            "to its @mcp.tool() decorator"
        )
        assert ann.readOnlyHint is True, (  # type: ignore[union-attr]
            f"Expected readOnlyHint=True for search_knowledge, got: {ann.readOnlyHint!r}"
        )

    def test_search_knowledge_idempotent_hint_true(self) -> None:
        """search_knowledge is idempotent: same query always returns same results."""
        ann = _get_tool_annotations("search_knowledge")
        assert ann is not None, (
            "search_knowledge has no ToolAnnotations; "
            "add annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True) "
            "to its @mcp.tool() decorator"
        )
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for search_knowledge, got: {ann.idempotentHint!r}"
        )

    # -- AC2: list_sources ----------------------------------------------------

    def test_list_sources_idempotent_hint_true(self) -> None:
        """list_sources is idempotent: listing the same scope twice returns the same result."""
        ann = _get_tool_annotations("list_sources")
        assert ann is not None, (
            "list_sources has no ToolAnnotations; readOnlyHint=True already present but "
            "idempotentHint=True must also be added"
        )
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for list_sources, got: {ann.idempotentHint!r}"
        )

    # -- AC4: get_stats -------------------------------------------------------

    def test_get_stats_idempotent_hint_true(self) -> None:
        """get_stats is idempotent: reading counts does not change KB state."""
        ann = _get_tool_annotations("get_stats")
        assert ann is not None, (
            "get_stats has no ToolAnnotations; readOnlyHint=True already present but "
            "idempotentHint=True must also be added"
        )
        assert ann.idempotentHint is True, (  # type: ignore[union-attr]
            f"Expected idempotentHint=True for get_stats, got: {ann.idempotentHint!r}"
        )
