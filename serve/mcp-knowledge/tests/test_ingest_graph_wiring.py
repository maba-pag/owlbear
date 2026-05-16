"""Tests for MCP knowledge graph wiring — task #699.

Validates GraphAugmentedRetriever wiring (AC3a) and search_knowledge
entity_type response field (AC3b). LLMExtractor tests (AC1, AC2, AC4, AC5)
removed — pydantic-ai dependency dropped.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import (
    app_lifespan,
    search_knowledge,
)


# ---------------------------------------------------------------------------
# TestFromAC_GraphAugmentedRetrieverWiring — AC3a
# Verifies app_lifespan creates GraphAugmentedRetriever(vs, gs, emb) and passes it as
# KnowledgeQueryService(retriever=...).
# RED: patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever") raises AttributeError
# in all 3 tests — GraphAugmentedRetriever is not imported in server.py.
# ---------------------------------------------------------------------------


class TestFromAC_GraphAugmentedRetrieverWiring:
    """Tests that app_lifespan creates GraphAugmentedRetriever and wires it into KnowledgeQueryService."""

    @pytest.mark.asyncio
    async def test_app_lifespan_instantiates_graph_augmented_retriever(self) -> None:
        """app_lifespan constructs a GraphAugmentedRetriever during startup."""
        mock_gar_cls = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever", mock_gar_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_gar_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_knowledge_query_service_receives_retriever_kwarg(self) -> None:
        """KnowledgeQueryService is constructed with retriever= pointing to the GraphAugmentedRetriever."""
        mock_gar_instance = MagicMock(name="GraphAugmentedRetrieverInstance")
        mock_qs_cls = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService", mock_qs_cls),
            patch(
                "owlbear_mcp_knowledge.server.GraphAugmentedRetriever",
                return_value=mock_gar_instance,
            ),
        ):
            async with app_lifespan(MagicMock()):
                pass

        _, kwargs = mock_qs_cls.call_args
        assert "retriever" in kwargs, "KnowledgeQueryService must receive retriever= kwarg"
        assert kwargs["retriever"] is mock_gar_instance

    @pytest.mark.asyncio
    async def test_graph_augmented_retriever_receives_vs_gs_emb(self) -> None:
        """GraphAugmentedRetriever is constructed with the same vs, gs, and emb used by other services."""
        mock_vs = MagicMock(name="VectorStore")
        mock_gs = MagicMock(name="GraphStore")
        mock_emb = MagicMock(name="Embedder")
        mock_gar_cls = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore", return_value=mock_gs),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore", return_value=mock_vs),
            patch(
                "owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider",
                return_value=mock_emb,
            ),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever", mock_gar_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_gar_cls.assert_called_once_with(mock_vs, mock_gs, mock_emb)


# ---------------------------------------------------------------------------
# TestFromAC_SearchKnowledgeEntityType — AC3b
# Verifies search_knowledge response dicts include entity_type field.
# RED: server.py L227 maps only title/score/snippet — no entity_type → AssertionError.
# ---------------------------------------------------------------------------


class TestFromAC_SearchKnowledgeEntityType:
    """Tests that search_knowledge response dicts include the entity_type field."""

    @pytest.mark.asyncio
    async def test_search_knowledge_result_dict_has_entity_type_key(self) -> None:
        """Each result dict returned by search_knowledge includes an 'entity_type' key."""
        mock_result = MagicMock()
        mock_result.title = "Knowledge Article"
        mock_result.score = 0.9
        mock_result.snippet = "some context"
        mock_result.entity_type = "concept"

        mock_qs = AsyncMock()
        mock_qs.query.return_value = [mock_result]

        mcp_ctx = MagicMock()
        mcp_ctx.request_context.lifespan_context.query_service = mock_qs

        results = await search_knowledge(mcp_ctx, query="some query")

        assert isinstance(results, list)
        assert len(results) >= 1
        assert "entity_type" in results[0], "search_knowledge result dicts must include 'entity_type' key"

    @pytest.mark.asyncio
    async def test_search_knowledge_entity_type_value_matches_source_result(
        self,
    ) -> None:
        """The entity_type value in the response matches StructuredSearchResult.entity_type."""
        mock_result = MagicMock()
        mock_result.title = "Decision Doc"
        mock_result.score = 0.85
        mock_result.snippet = "decision context"
        mock_result.entity_type = "decision"

        mock_qs = AsyncMock()
        mock_qs.query.return_value = [mock_result]

        mcp_ctx = MagicMock()
        mcp_ctx.request_context.lifespan_context.query_service = mock_qs

        results = await search_knowledge(mcp_ctx, query="decision query")

        assert results[0]["entity_type"] == "decision"

    @pytest.mark.asyncio
    async def test_search_knowledge_entity_type_is_none_when_result_has_none(
        self,
    ) -> None:
        """entity_type is included and set to None in result dict when source result has entity_type=None."""
        mock_result = MagicMock()
        mock_result.title = "Generic Doc"
        mock_result.score = 0.7
        mock_result.snippet = "generic"
        mock_result.entity_type = None

        mock_qs = AsyncMock()
        mock_qs.query.return_value = [mock_result]

        mcp_ctx = MagicMock()
        mcp_ctx.request_context.lifespan_context.query_service = mock_qs

        results = await search_knowledge(mcp_ctx, query="generic")

        assert "entity_type" in results[0], "entity_type key must be present even when value is None"
        assert results[0]["entity_type"] is None
