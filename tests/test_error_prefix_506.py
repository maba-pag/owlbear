"""Failing tests for task #506: standardize error: prefix across mcp-knowledge and mcp-project.

Covers (TDD RED phase — all tests must FAIL before builder implements #506):
  - AC1: ingest_document exception returns 'error: ingestion failed: {exc}'
  - AC2: list_entities invalid type returns 'error: Invalid entity_type ...'
  - AC3: search_knowledge when service unavailable returns 'error: Knowledge service not available.'
  - AC4: project_info when config absent returns 'error: No owlbear-project.json ...'
  - AC5: project_readme when README absent returns 'error: No README.md ...'
  - AC6: owlbear_mcp_knowledge.server exports __all__

Tests fail with AssertionError (wrong error string without prefix) or AttributeError (__all__ missing)
against the current implementation.  The builder makes them green by adding the 'error: '
prefix and the __all__ export.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

import owlbear_mcp_knowledge.server as kn_server
from owlbear_mcp_knowledge.server import (
    ingest_document,
    list_entities,
    search_knowledge,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kn_ctx(
    *,
    query_service: Any = None,
    ingest_pipeline: Any = None,
    graph_store: Any = None,
) -> MagicMock:
    """Return a FastMCP Context mock whose lifespan_context has mcp-knowledge fields."""
    app_ctx = MagicMock()
    app_ctx.query_service = query_service
    app_ctx.ingest_pipeline = ingest_pipeline if ingest_pipeline is not None else MagicMock()
    app_ctx.graph_store = graph_store if graph_store is not None else MagicMock()
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_ErrorPrefixKnowledge
# ---------------------------------------------------------------------------


class TestFromAC_ErrorPrefixKnowledge:
    """Contract tests for AC1-AC3: error-prefix standardization in mcp-knowledge."""

    # -- AC3: search_knowledge — service unavailable --------------------------

    @pytest.mark.asyncio
    async def test_search_knowledge_no_service_returns_error_prefix(self) -> None:
        """search_knowledge returns string starting with 'error: ' when query_service is None."""
        ctx = _make_kn_ctx(query_service=None)
        result = await search_knowledge(ctx, query="anything")
        assert result.startswith("error: "), f"Expected 'error: ' prefix, got: {result!r}"

    @pytest.mark.asyncio
    async def test_search_knowledge_no_service_exact_error_string(self) -> None:
        """search_knowledge returns exact string 'error: Knowledge service not available.' when service is None."""
        ctx = _make_kn_ctx(query_service=None)
        result = await search_knowledge(ctx, query="test")
        assert result == "error: Knowledge service not available.", f"Expected exact string, got: {result!r}"

    # -- AC1: ingest_document — pipeline exception ----------------------------

    @pytest.mark.asyncio
    async def test_ingest_document_exception_returns_error_prefix(self) -> None:
        """ingest_document returns string starting with 'error: ' when pipeline raises."""
        pipeline = AsyncMock()
        pipeline.ingest_text.side_effect = RuntimeError("disk full")
        ctx = _make_kn_ctx(ingest_pipeline=pipeline)
        result = await ingest_document(ctx, text="hello")
        assert result.startswith("error: "), f"Expected 'error: ' prefix, got: {result!r}"

    @pytest.mark.asyncio
    async def test_ingest_document_error_starts_with_error_ingestion_failed(self) -> None:
        """ingest_document error string starts with 'error: ingestion failed:' (lowercase prefix)."""
        pipeline = AsyncMock()
        pipeline.ingest_text.side_effect = ValueError("bad input")
        ctx = _make_kn_ctx(ingest_pipeline=pipeline)
        result = await ingest_document(ctx, text="foo")
        assert result.startswith("error: ingestion failed:"), (
            f"Expected 'error: ingestion failed:' prefix, got: {result!r}"
        )

    @pytest.mark.asyncio
    async def test_ingest_document_error_has_no_capital_ingestion(self) -> None:
        """ingest_document error does NOT start with 'Ingestion failed:' (old uppercase form)."""
        pipeline = AsyncMock()
        pipeline.ingest_text.side_effect = RuntimeError("oops")
        ctx = _make_kn_ctx(ingest_pipeline=pipeline)
        result = await ingest_document(ctx, text="text")
        assert not result.startswith("Ingestion failed:"), f"Old uppercase prefix still present: {result!r}"

    # -- AC2: list_entities — invalid entity type -----------------------------

    @pytest.mark.asyncio
    async def test_list_entities_invalid_type_returns_error_prefix(self) -> None:
        """list_entities returns string starting with 'error: ' for an invalid entity_type."""
        ctx = _make_kn_ctx()
        result = await list_entities(ctx, entity_type="BOGUS_ENTITY_TYPE_XYZ")
        assert result.startswith("error: "), f"Expected 'error: ' prefix, got: {result!r}"


# ---------------------------------------------------------------------------
# TestFromAC_KnowledgeServerAll
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeServerAll:
    """Contract tests for AC6: __all__ export in owlbear_mcp_knowledge.server."""

    def test_server_has_dunder_all(self) -> None:
        """owlbear_mcp_knowledge.server defines __all__."""
        assert hasattr(kn_server, "__all__"), "owlbear_mcp_knowledge.server has no __all__ attribute"

    def test_server_all_is_sequence(self) -> None:
        """owlbear_mcp_knowledge.server.__all__ is a list or tuple."""
        all_attr = kn_server.__all__  # type: ignore[attr-defined]
        assert isinstance(all_attr, (list, tuple)), f"__all__ should be list or tuple, got {type(all_attr)}"

    def test_server_all_is_non_empty(self) -> None:
        """owlbear_mcp_knowledge.server.__all__ exports at least one name."""
        all_attr = kn_server.__all__  # type: ignore[attr-defined]
        assert len(all_attr) > 0, "__all__ must not be empty"

    def test_server_all_includes_mcp_instance(self) -> None:
        """owlbear_mcp_knowledge.server.__all__ includes 'mcp'."""
        all_attr = kn_server.__all__  # type: ignore[attr-defined]
        assert "mcp" in all_attr, f"'mcp' not in __all__: {all_attr}"

    def test_server_all_includes_public_tools(self) -> None:
        """owlbear_mcp_knowledge.server.__all__ includes the public tool function names."""
        expected_tools = {"search_knowledge", "ingest_document", "list_entities"}
        all_attr = set(kn_server.__all__)  # type: ignore[attr-defined]
        missing = expected_tools - all_attr
        assert not missing, f"Tool names missing from __all__: {missing}"
