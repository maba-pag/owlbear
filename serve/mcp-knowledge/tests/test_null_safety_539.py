"""Tests for task #539: null-safety guards and __all__ fix in mcp-knowledge server.

TDD RED phase — all tests FAIL before builder adds None checks and updates __all__.

AC coverage:
  - list_sources: source_store=None → "error: source store not available"
  - list_entities: graph_store=None → "error: graph store not available" (before entity_type validation)
  - get_stats: graph_store=None → "error: graph store not available"
  - ingest_document: ingest_pipeline=None → "error: ingest pipeline not available" (replaces old catch-all)
  - __all__: "get_stats" present in alphabetical order
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import owlbear_mcp_knowledge.server as _server_module
from owlbear_mcp_knowledge.server import (
    get_stats,
    ingest_document,
    list_entities,
    list_sources,
)


# ---------------------------------------------------------------------------
# Helpers — follow _make_ctx pattern from test_list_sources.py
# ---------------------------------------------------------------------------


def _make_ctx(
    *,
    source_store: object = None,
    graph_store: object = None,
    ingest_pipeline: object = None,
    query_service: object = None,
) -> MagicMock:
    """Return a FastMCP Context mock with fully-controlled lifespan_context fields."""
    mcp_ctx = MagicMock()
    app_ctx = MagicMock()
    app_ctx.source_store = source_store
    app_ctx.graph_store = graph_store
    app_ctx.ingest_pipeline = ingest_pipeline
    app_ctx.query_service = query_service
    mcp_ctx.request_context.lifespan_context = app_ctx
    return mcp_ctx


# ---------------------------------------------------------------------------
# TestFromAC_NullSafetyGuards
# ---------------------------------------------------------------------------


class TestFromAC_NullSafetyGuards:
    """Contract tests: each tool must early-return an error string when its
    required AppContext field is None.

    Tests are derived directly from AC lines — not from implementation details.
    """

    # -- list_sources: source_store=None --------------------------------------

    @pytest.mark.asyncio
    async def test_list_sources_returns_error_when_source_store_is_none(self) -> None:
        """list_sources must raise ToolError (no 'error: ' prefix) when source_store is None."""
        ctx = _make_ctx(source_store=None)

        with pytest.raises(ToolError) as exc_info:
            await list_sources(ctx)

        msg = str(exc_info.value)
        assert not msg.startswith("error:"), (
            f"ToolError message must not carry 'error:' prefix; got: {msg!r}"
        )
        assert "source store not available" in msg, (
            f"Expected 'source store not available' in message, got: {msg!r}"
        )

    # -- list_entities: graph_store=None --------------------------------------

    @pytest.mark.asyncio
    async def test_list_entities_returns_error_when_graph_store_is_none(self) -> None:
        """list_entities must return 'error: graph store not available' when graph_store is None."""
        ctx = _make_ctx(graph_store=None)

        result = await list_entities(ctx)

        assert result == "error: graph store not available", (
            f"Expected error string for None graph_store, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_list_entities_null_check_fires_before_entity_type_validation(
        self,
    ) -> None:
        """list_entities must check graph_store BEFORE validating entity_type.

        AC requires the None guard to precede entity_type validation so that an
        invalid entity_type with a None graph_store still returns the store error,
        not the entity_type error.
        """
        ctx = _make_ctx(graph_store=None)

        result = await list_entities(ctx, entity_type="invalid_type_xyz")

        assert result == "error: graph store not available", (
            f"Expected graph_store null error before entity_type validation, got: {result!r}"
        )

    # -- get_stats: graph_store=None ------------------------------------------

    @pytest.mark.asyncio
    async def test_get_stats_returns_error_when_graph_store_is_none(self) -> None:
        """get_stats must raise ToolError (no 'error: ' prefix) when graph_store is None."""
        ctx = _make_ctx(graph_store=None)

        with pytest.raises(ToolError) as exc_info:
            await get_stats(ctx)

        msg = str(exc_info.value)
        assert not msg.startswith("error:"), (
            f"ToolError message must not carry 'error:' prefix; got: {msg!r}"
        )
        assert "graph store not available" in msg, (
            f"Expected 'graph store not available' in message, got: {msg!r}"
        )

    # -- ingest_document: ingest_pipeline=None --------------------------------

    @pytest.mark.asyncio
    async def test_ingest_document_returns_error_when_ingest_pipeline_is_none(
        self,
    ) -> None:
        """ingest_document must return 'error: ingest pipeline not available' when ingest_pipeline is None."""
        ctx = _make_ctx(ingest_pipeline=None)

        result = await ingest_document(ctx, text="hello world")

        assert result == "error: ingest pipeline not available", (
            f"Expected explicit pipeline-unavailable error, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_pipeline_none_does_not_return_ingestion_failed(
        self,
    ) -> None:
        """ingest_document with None pipeline must NOT fall through to the generic try/except.

        AC changes the error message from the old catch-all 'error: ingestion failed: ...'
        (which masked the root cause) to an explicit 'error: ingest pipeline not available'.
        """
        ctx = _make_ctx(ingest_pipeline=None)

        result = await ingest_document(ctx, text="any text")

        assert not isinstance(result, str) or not result.startswith(
            "error: ingestion failed:"
        ), (
            "ingest_document with None pipeline must not fall through to the generic "
            f"try/except handler; got: {result!r}"
        )
        assert result == "error: ingest pipeline not available", (
            f"Must return exact error string 'error: ingest pipeline not available', got: {result!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_DunderAll
# ---------------------------------------------------------------------------


class TestFromAC_DunderAll:
    """Contract tests: __all__ must include get_stats in alphabetical order."""

    def test_get_stats_is_in_dunder_all(self) -> None:
        """'get_stats' must be exported in server.__all__."""
        assert "get_stats" in _server_module.__all__, (
            f"'get_stats' is missing from __all__; current __all__: {_server_module.__all__}"
        )

    def test_get_stats_is_before_ingest_document_in_dunder_all(self) -> None:
        """'get_stats' must appear before 'ingest_document' in __all__ (alphabetical order).

        Currently 'get_stats' is absent; after adding it, alphabetical order requires
        it precedes 'ingest_document' (g < i).
        """
        all_list = list(_server_module.__all__)
        assert "get_stats" in all_list, f"'get_stats' missing from __all__: {all_list}"
        assert "ingest_document" in all_list, (
            f"'ingest_document' missing from __all__: {all_list}"
        )
        idx_get = all_list.index("get_stats")
        idx_ingest = all_list.index("ingest_document")
        assert idx_get < idx_ingest, (
            f"'get_stats' (index {idx_get}) must appear before 'ingest_document' "
            f"(index {idx_ingest}) in __all__ for alphabetical order"
        )
