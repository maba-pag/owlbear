"""Failing tests for task #699: MCP knowledge graph wiring and integration.

TDD RED phase for #690. All tests must FAIL before builder implements #690.

RED failure modes by AC:
  - AC1:  AttributeError — LLMExtractor not imported in server.py; patch target absent.
  - AC2:  AttributeError — LLMExtractor not imported in server.py; patch target absent.
          (test uses thread-safe in-memory SQLite to avoid sqlite3.ProgrammingError)
  - AC3a: AttributeError — GraphAugmentedRetriever not imported in server.py; patch target absent.
  - AC3b: AssertionError — search_knowledge response dict missing 'entity_type' key.
  - AC4:  AttributeError — LLMExtractor not in server.py namespace; patch target absent.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_knowledge.server import (
    app_lifespan,
    get_stats,
    ingest_document,
    search_knowledge,
)


# ---------------------------------------------------------------------------
# TestFromAC_LLMExtractorWiring — AC1
# Verifies app_lifespan creates LLMExtractor and passes it as EntityExtractor(extractor=...)
# RED: patch("owlbear_mcp_knowledge.server.LLMExtractor") raises AttributeError in all 3 tests.
# ---------------------------------------------------------------------------


class TestFromAC_LLMExtractorWiring:
    """Tests that app_lifespan creates LLMExtractor and wires it into EntityExtractor."""

    @pytest.mark.asyncio
    async def test_app_lifespan_instantiates_llm_extractor(self) -> None:
        """app_lifespan constructs an LLMExtractor instance during startup."""
        mock_llm_cls = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor"),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            patch("owlbear_mcp_knowledge.server.LLMExtractor", mock_llm_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_llm_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_extractor_receives_llm_extractor_as_extractor_kwarg(self) -> None:
        """EntityExtractor is constructed with extractor= pointing to the LLMExtractor instance."""
        mock_llm_instance = MagicMock(name="LLMExtractorInstance")
        mock_entity_cls = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor", mock_entity_cls),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            patch("owlbear_mcp_knowledge.server.LLMExtractor", return_value=mock_llm_instance),
        ):
            async with app_lifespan(MagicMock()):
                pass

        _, kwargs = mock_entity_cls.call_args
        assert "extractor" in kwargs, "EntityExtractor must receive extractor= kwarg"
        assert kwargs["extractor"] is mock_llm_instance

    @pytest.mark.asyncio
    async def test_llm_extractor_constructed_with_owlbear_model_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLMExtractor is constructed using the OWLBEAR_MODEL environment variable value."""
        monkeypatch.setenv("OWLBEAR_MODEL", "gpt-4-turbo")
        mock_llm_cls = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor"),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            patch("owlbear_mcp_knowledge.server.LLMExtractor", mock_llm_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        args, kwargs = mock_llm_cls.call_args
        all_args = list(args) + list(kwargs.values())
        assert "gpt-4-turbo" in all_args, "LLMExtractor must be constructed with OWLBEAR_MODEL value"


# ---------------------------------------------------------------------------
# TestFromAC_IngestWithLLMExtractor — AC2
# Verifies ingest produces entity_count > 0 and edge_count > 0 in get_stats.
# RED: patch("owlbear_mcp_knowledge.server.LLMExtractor") raises AttributeError —
# LLMExtractor is not imported in server.py; server never wires it into EntityExtractor.
# GREEN: builder adds import + wiring → mock.extract returns entities/edges → counts > 0.
#
# Uses a thread-safe in-memory SQLite (check_same_thread=False) via a patched init_db
# to avoid sqlite3.ProgrammingError from asyncio.to_thread context in the pipeline.
# ---------------------------------------------------------------------------


class TestFromAC_IngestWithLLMExtractor:
    """Tests that ingest with a wired LLMExtractor produces entity/edge counts > 0 via get_stats."""

    @pytest.mark.asyncio
    async def test_ingest_produces_entity_count_and_edge_count_gt_zero(
        self,
    ) -> None:
        """After ingesting text with a wired LLMExtractor, get_stats reports entity_count > 0 and edge_count > 0.

        Uses a real GraphStore backed by a thread-safe in-memory SQLite connection so that
        asyncio.to_thread calls inside the pipeline and get_stats do not raise
        sqlite3.ProgrammingError.  LLMExtractor is patched at the server module level —
        RED failure is AttributeError (no attribute 'LLMExtractor' in server), consistent
        with AC1/AC3a/AC4.
        """
        from owlbear_knowledge.extractor import ExtractionResult
        from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
        from owlbear_knowledge.schema import init_db as schema_init_db

        entity_a = Entity(name="ConceptA", entity_type=EntityType.CONCEPT)
        entity_b = Entity(name="ConceptB", entity_type=EntityType.CONCEPT)
        link = Edge(
            source_id=entity_a.id,
            target_id=entity_b.id,
            relation=RelationType.DEPENDS_ON,
        )
        mock_extraction = ExtractionResult(entities=[entity_a, entity_b], edges=[link])
        mock_llm_instance = MagicMock()
        mock_llm_instance.extract = AsyncMock(return_value=mock_extraction)

        # Thread-safe in-memory SQLite avoids sqlite3.ProgrammingError from asyncio.to_thread.
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        schema_init_db(conn)

        mock_vs = MagicMock()
        mock_emb = MagicMock()
        mock_emb.embed.side_effect = lambda texts: [[0.1] * 64 for _ in texts]

        stats: dict = {}

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=conn),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore", return_value=mock_vs),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider", return_value=mock_emb),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            # RED: server.py has no LLMExtractor attribute → AttributeError → test fails.
            # GREEN: builder adds import; mock returns mock_llm_instance whose .extract
            # returns mock_extraction (2 entities, 1 edge) → counts stored → get_stats > 0.
            patch("owlbear_mcp_knowledge.server.LLMExtractor", return_value=mock_llm_instance),
        ):
            fake_server = MagicMock()
            async with app_lifespan(fake_server) as ctx:
                ingest_ctx = MagicMock()
                ingest_ctx.request_context.lifespan_context = ctx
                await ingest_document(ingest_ctx, text="ConceptA depends on ConceptB.")

                stats_ctx = MagicMock()
                stats_ctx.request_context.lifespan_context = ctx
                stats = await get_stats(stats_ctx)

        assert stats["entities"] > 0, "entity_count must be > 0 when LLMExtractor is wired"
        assert stats["edges"] > 0, "edge_count must be > 0 when LLMExtractor is wired"


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
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
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
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
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
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider", return_value=mock_emb),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever", mock_gar_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        args, kwargs = mock_gar_cls.call_args
        positional = list(args)
        assert mock_vs in positional or kwargs.get("vector_store") is mock_vs, (
            "GraphAugmentedRetriever must receive the QdrantVectorStore instance"
        )
        assert mock_gs in positional or kwargs.get("graph_store") is mock_gs, (
            "GraphAugmentedRetriever must receive the GraphStore instance"
        )
        assert mock_emb in positional or kwargs.get("embedding_provider") is mock_emb, (
            "GraphAugmentedRetriever must receive the BgeM3EmbeddingProvider instance"
        )


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
        assert "entity_type" in results[0], (
            "search_knowledge result dicts must include 'entity_type' key"
        )

    @pytest.mark.asyncio
    async def test_search_knowledge_entity_type_value_matches_source_result(self) -> None:
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
    async def test_search_knowledge_entity_type_is_none_when_result_has_none(self) -> None:
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


# ---------------------------------------------------------------------------
# TestFromAC_LLMExtractorImportError — AC4
# Verifies graceful degradation when LLMExtractor instantiation raises ImportError.
# RED: patch("owlbear_mcp_knowledge.server.LLMExtractor", ...) raises AttributeError in
# both tests — LLMExtractor is not a module-level attribute of server.py.
# ---------------------------------------------------------------------------


class TestFromAC_LLMExtractorImportError:
    """Tests that app_lifespan degrades gracefully when LLMExtractor raises ImportError."""

    @pytest.mark.asyncio
    async def test_app_lifespan_yields_context_when_llm_extractor_raises_import_error(
        self,
    ) -> None:
        """app_lifespan yields a valid AppContext even when LLMExtractor(...) raises ImportError."""
        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor"),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            patch(
                "owlbear_mcp_knowledge.server.LLMExtractor",
                side_effect=ImportError("pydantic_ai not installed"),
            ),
        ):
            ctx_yielded = None
            async with app_lifespan(MagicMock()) as ctx:
                ctx_yielded = ctx

        assert ctx_yielded is not None, (
            "app_lifespan must yield a valid AppContext even after LLMExtractor ImportError"
        )

    @pytest.mark.asyncio
    async def test_fallback_entity_extractor_constructed_without_extractor_kwarg(
        self,
    ) -> None:
        """On ImportError, EntityExtractor falls back to bare construction (no extractor= kwarg)."""
        mock_entity_cls = MagicMock()

        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor", mock_entity_cls),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            patch(
                "owlbear_mcp_knowledge.server.LLMExtractor",
                side_effect=ImportError("pydantic_ai not installed"),
            ),
        ):
            async with app_lifespan(MagicMock()):
                pass

        _, kwargs = mock_entity_cls.call_args
        assert "extractor" not in kwargs, (
            "Fallback EntityExtractor must NOT receive extractor= kwarg when LLMExtractor fails"
        )


# ---------------------------------------------------------------------------
# TestFromAC_PyprojectDependency — AC2
# Verifies owlbear-mcp-knowledge/pyproject.toml declares owlbear-knowledge[llm].
# RED: current pyproject.toml lists "owlbear-knowledge" (no [llm] extra) → AssertionError.
# ---------------------------------------------------------------------------


class TestFromAC_PyprojectDependency:
    """Tests that owlbear-mcp-knowledge pyproject.toml declares the owlbear-knowledge[llm] extra."""

    def test_pyproject_declares_owlbear_knowledge_llm_extra(self) -> None:
        """owlbear-mcp-knowledge/pyproject.toml lists owlbear-knowledge[llm] as a dependency."""
        import tomllib  # noqa: PLC0415

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            config = tomllib.load(f)
        deps: list[str] = config["project"]["dependencies"]
        assert any("owlbear-knowledge[llm]" in d for d in deps), (
            "owlbear-mcp-knowledge must declare owlbear-knowledge[llm] as a dependency. "
            f"Current dependencies: {deps}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_GracefulDegradation — AC5 (boundary/edge)
# AC5: graceful degradation when OWLBEAR_MODEL is unset OR LLM is unavailable.
# TestFromAC_LLMExtractorImportError covers ImportError; these tests cover:
#   1. Generic Exception (RuntimeError) from LLMExtractor construction → degrade not crash.
#   2. OWLBEAR_MODEL unset → app_lifespan still yields a valid context.
# RED: all fail with AttributeError — LLMExtractor not a module attribute of server.py.
# ---------------------------------------------------------------------------


class TestFromAC_GracefulDegradation:
    """Tests graceful degradation edge cases for AC5: generic exception and unset OWLBEAR_MODEL."""

    @pytest.mark.asyncio
    async def test_app_lifespan_yields_context_when_llm_extractor_raises_generic_exception(
        self,
    ) -> None:
        """app_lifespan yields AppContext when LLMExtractor raises a non-ImportError exception."""
        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor"),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            patch(
                "owlbear_mcp_knowledge.server.LLMExtractor",
                side_effect=RuntimeError("unexpected construction failure"),
            ),
        ):
            ctx_yielded = None
            async with app_lifespan(MagicMock()) as ctx:
                ctx_yielded = ctx

        assert ctx_yielded is not None, (
            "app_lifespan must yield a valid AppContext even after generic LLMExtractor failure"
        )

    @pytest.mark.asyncio
    async def test_app_lifespan_yields_context_when_owlbear_model_env_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """app_lifespan yields AppContext when OWLBEAR_MODEL is not set (uses default + degrades gracefully)."""
        monkeypatch.delenv("OWLBEAR_MODEL", raising=False)
        with (
            patch("owlbear_mcp_knowledge.server.init_db", return_value=MagicMock()),
            patch("owlbear_mcp_knowledge.server.GraphStore"),
            patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
            patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
            patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
            patch("owlbear_mcp_knowledge.server.EntityExtractor"),
            patch("owlbear_mcp_knowledge.server.make_evaluate_fn", return_value=AsyncMock()),
            patch(
                "owlbear_mcp_knowledge.server.LLMExtractor",
                side_effect=ImportError("pydantic_ai not available"),
            ),
        ):
            ctx_yielded = None
            async with app_lifespan(MagicMock()) as ctx:
                ctx_yielded = ctx

        assert ctx_yielded is not None, (
            "app_lifespan must yield a valid AppContext when OWLBEAR_MODEL is not set"
        )
