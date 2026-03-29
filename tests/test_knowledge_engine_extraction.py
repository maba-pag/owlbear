"""RED-phase tests for missing knowledge engine AC items (#15).

Covers the 5 AC items identified as untested by the reviewer:
  - AC3: Qdrant vector store integration extracted (TestFromAC_QdrantExtraction)
  - AC4: BGE-M3 embedding model support extracted (TestFromAC_EmbeddingsExtraction)
  - AC5: Entity extraction pipeline extracted (TestFromAC_EntityExtractionPipeline)
  - AC6: IntraDocGraphBuilder and InterDocGraphBuilder extracted (TestFromAC_GraphBuildersExtraction)
  - AC7: Hybrid search (graph + vector) working (TestFromAC_HybridSearchExtraction)
  - AC10: Package has correct dependencies (TestFromAC_PackageDependencies)

All tests fail in RED phase — stub implementations raise NotImplementedError.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge import GraphStore, init_db
from owlbear_knowledge.chunker import Chunk, TextChunker
from owlbear_knowledge.embeddings import BgeM3EmbeddingProvider, EmbeddingProvider
from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
from owlbear_knowledge.graph_builder import (
    GraphBuildResult,
    InterDocGraphBuilder,
    IntraDocGraphBuilder,
)
from owlbear_knowledge.models import Entity, EntityType
from owlbear_knowledge.protocol import VectorStoreProtocol
from owlbear_knowledge.qdrant import QdrantVectorStore
from owlbear_knowledge.query_service import KnowledgeQueryService, StructuredSearchResult

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DENSE_DIM = 1024


def _dense_vec(val: float = 0.1) -> list[float]:
    """Return a 1024-d dense vector filled with *val*."""
    return [val] * _DENSE_DIM


def _make_graph_store() -> GraphStore:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return GraphStore(conn)


def _make_entity(name: str, etype: EntityType = EntityType.CONCEPT) -> Entity:
    return Entity(name=name, entity_type=etype, scope="global")


# ---------------------------------------------------------------------------
# AC3 — Qdrant vector store extracted
# ---------------------------------------------------------------------------


class TestFromAC_QdrantExtraction:  # noqa: N801
    """AC: Qdrant vector store integration extracted."""

    def test_qdrant_store_and_retrieve_embedding_roundtrip(self) -> None:
        """store_embedding then get_embedding returns the same dense vector."""
        store = QdrantVectorStore(":memory:")
        vec = _dense_vec(0.3)
        store.store_embedding("e1", vec, "entity", scope="global")
        result = store.get_embedding("e1")
        assert result is not None
        assert len(result) == _DENSE_DIM

    def test_qdrant_search_returns_id_score_tuples(self) -> None:
        """search_similar returns list[tuple[str, float]], best match first."""
        store = QdrantVectorStore(":memory:")
        vec = _dense_vec(0.5)
        store.store_embedding("e1", vec, "entity")
        results = store.search_similar(vec, top_k=1)
        assert isinstance(results, list)
        assert len(results) == 1
        doc_id, score = results[0]
        assert isinstance(doc_id, str)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_qdrant_delete_existing_embedding_returns_true(self) -> None:
        """delete_embedding returns True when the entry existed."""
        store = QdrantVectorStore(":memory:")
        store.store_embedding("e2", _dense_vec(), "document")
        deleted = store.delete_embedding("e2")
        assert deleted is True

    def test_qdrant_delete_nonexistent_embedding_returns_false(self) -> None:
        """delete_embedding returns False for an ID that was never stored."""
        store = QdrantVectorStore(":memory:")
        deleted = store.delete_embedding("ghost-id")
        assert deleted is False

    def test_qdrant_search_on_empty_store_returns_empty_list(self) -> None:
        """search_similar on a fresh store returns [], not an error."""
        store = QdrantVectorStore(":memory:")
        results = store.search_similar(_dense_vec(), top_k=5)
        assert results == []

    def test_qdrant_implements_vector_store_protocol(self) -> None:
        """QdrantVectorStore is a runtime instance of VectorStoreProtocol."""
        store = QdrantVectorStore(":memory:")
        assert isinstance(store, VectorStoreProtocol)


# ---------------------------------------------------------------------------
# AC4 — BGE-M3 embedding model support extracted
# ---------------------------------------------------------------------------


class TestFromAC_EmbeddingsExtraction:  # noqa: N801
    """AC: BGE-M3 embedding model support extracted."""

    def test_bgem3_embed_empty_texts_returns_empty_list(self) -> None:
        """embed([]) must return [] without loading the model."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0)
        result = provider.embed([])
        assert result == []

    def test_bgem3_embed_hybrid_empty_texts_returns_empty_list(self) -> None:
        """embed_hybrid([]) must return [] without loading the model."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0)
        result = provider.embed_hybrid([])
        assert result == []

    def test_bgem3_embed_raises_import_error_if_flag_embedding_missing(self) -> None:
        """embed(texts) raises ImportError with install hint if FlagEmbedding absent."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0)
        with pytest.raises(ImportError, match="FlagEmbedding"):
            provider.embed(["def hello(): pass"])

    def test_bgem3_implements_embedding_provider_protocol(self) -> None:
        """BgeM3EmbeddingProvider satisfies EmbeddingProvider at runtime."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0)
        assert isinstance(provider, EmbeddingProvider)

    def test_bgem3_embed_hybrid_raises_import_error_if_flag_embedding_missing(self) -> None:
        """embed_hybrid(texts) raises ImportError with install hint if FlagEmbedding absent."""
        provider = BgeM3EmbeddingProvider(idle_timeout=0)
        with pytest.raises(ImportError, match="FlagEmbedding"):
            provider.embed_hybrid(["hello world"])


# ---------------------------------------------------------------------------
# AC5 — Entity extraction pipeline extracted
# ---------------------------------------------------------------------------


class TestFromAC_EntityExtractionPipeline:  # noqa: N801
    """AC: Entity extraction pipeline extracted (extractor + chunker)."""

    @pytest.mark.asyncio
    async def test_entity_extractor_returns_extraction_result(self) -> None:
        """extract() returns an ExtractionResult instance."""
        extractor = EntityExtractor(model="openai:gpt-4o")
        result = await extractor.extract("def hello(): pass")
        assert isinstance(result, ExtractionResult)

    @pytest.mark.asyncio
    async def test_entity_extractor_entities_have_name_and_entity_type(self) -> None:
        """All entities in the result have non-empty name and valid entity_type."""
        extractor = EntityExtractor(model="openai:gpt-4o")
        result = await extractor.extract("class Foo:\n    def bar(self): pass\n")
        for entity in result.entities:
            assert isinstance(entity, Entity)
            assert entity.name
            assert entity.entity_type in EntityType

    @pytest.mark.asyncio
    async def test_entity_extractor_extract_is_coroutine(self) -> None:
        """EntityExtractor.extract must be an async method (awaitable)."""
        import inspect

        extractor = EntityExtractor(model="openai:gpt-4o")
        coro = extractor.extract("text")
        assert inspect.isawaitable(coro)
        coro.close()  # avoid RuntimeWarning

    def test_text_chunker_splits_long_text_into_multiple_chunks(self) -> None:
        """TextChunker.chunk() splits long text into >1 Chunk objects."""
        chunker = TextChunker(target_tokens=10, overlap_tokens=0)
        text = " ".join(["word"] * 60)
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        for c in chunks:
            assert isinstance(c, Chunk)
            assert c.text
            assert isinstance(c.index, int)

    def test_text_chunker_short_text_is_single_chunk(self) -> None:
        """A text that fits within target_tokens yields exactly one chunk."""
        chunker = TextChunker(target_tokens=200)
        chunks = chunker.chunk("hello world")
        assert len(chunks) == 1
        assert chunks[0].index == 0

    def test_text_chunker_all_words_preserved_across_chunks(self) -> None:
        """Every word from the source text appears in at least one chunk."""
        chunker = TextChunker(target_tokens=5, overlap_tokens=0)
        words = [f"w{i}" for i in range(20)]
        text = " ".join(words)
        chunks = chunker.chunk(text)
        combined = " ".join(c.text for c in chunks)
        for w in words:
            assert w in combined


# ---------------------------------------------------------------------------
# AC6 — IntraDocGraphBuilder and InterDocGraphBuilder extracted
# ---------------------------------------------------------------------------


class TestFromAC_GraphBuildersExtraction:  # noqa: N801
    """AC: IntraDocGraphBuilder and InterDocGraphBuilder extracted."""

    @pytest.mark.asyncio
    async def test_intra_doc_builder_returns_graph_build_result(self) -> None:
        """IntraDocGraphBuilder.build() returns a GraphBuildResult."""
        builder = IntraDocGraphBuilder(model="openai:gpt-4o")
        entities = [_make_entity("Foo", EntityType.CLASS_), _make_entity("bar", EntityType.FUNCTION)]
        result = await builder.build(entities, scope="global", document_id="doc-1")
        assert isinstance(result, GraphBuildResult)
        assert isinstance(result.edges_added, int)
        assert isinstance(result.edges, list)

    @pytest.mark.asyncio
    async def test_intra_doc_builder_empty_entities_returns_zero_edges(self) -> None:
        """build([]) with no entities must return edges_added=0 and edges=[]."""
        builder = IntraDocGraphBuilder(model="openai:gpt-4o")
        result = await builder.build([], scope="global", document_id="doc-empty")
        assert result.edges_added == 0
        assert result.edges == []

    @pytest.mark.asyncio
    async def test_inter_doc_builder_returns_graph_build_result(self) -> None:
        """InterDocGraphBuilder.build() returns a GraphBuildResult."""
        mock_vector_store = MagicMock(spec=VectorStoreProtocol)
        mock_vector_store.search_similar.return_value = []
        builder = InterDocGraphBuilder(model="openai:gpt-4o")
        entities = [_make_entity("X", EntityType.CONCEPT)]
        result = await builder.build(entities, vector_store=mock_vector_store, scope="global")
        assert isinstance(result, GraphBuildResult)

    @pytest.mark.asyncio
    async def test_inter_doc_builder_uses_vector_store_for_candidate_pre_filter(self) -> None:
        """InterDocGraphBuilder calls vector_store.search_similar for pre-filtering."""
        mock_vector_store = MagicMock(spec=VectorStoreProtocol)
        mock_vector_store.search_similar.return_value = []
        builder = InterDocGraphBuilder(model="openai:gpt-4o")
        entities = [_make_entity("A"), _make_entity("B")]
        await builder.build(entities, vector_store=mock_vector_store, scope="global")
        mock_vector_store.search_similar.assert_called()


# ---------------------------------------------------------------------------
# AC7 — Hybrid search (graph + vector) working
# ---------------------------------------------------------------------------


class TestFromAC_HybridSearchExtraction:  # noqa: N801
    """AC: Hybrid search (graph + vector) working."""

    @pytest.fixture
    def mock_vector_store(self) -> MagicMock:
        store = MagicMock(spec=VectorStoreProtocol)
        store.search_similar.return_value = [("doc-1", 0.9)]
        return store

    @pytest.fixture
    def mock_embedding_provider(self) -> MagicMock:
        provider = MagicMock()
        provider.embed.return_value = [_dense_vec()]
        return provider

    @pytest.mark.asyncio
    async def test_query_service_query_returns_list(
        self, mock_vector_store: MagicMock, mock_embedding_provider: MagicMock
    ) -> None:
        """query() returns a list (possibly empty) without raising."""
        service = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=_make_graph_store(),
            embedding_provider=mock_embedding_provider,
        )
        results = await service.query("what is a pattern?")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_query_service_top_k_limits_result_count(
        self, mock_embedding_provider: MagicMock
    ) -> None:
        """query() returns no more than top_k results."""
        many_results = [(f"doc-{i}", 0.9 - i * 0.05) for i in range(12)]
        store = MagicMock(spec=VectorStoreProtocol)
        store.search_similar.return_value = many_results
        service = KnowledgeQueryService(
            vector_store=store,
            graph_store=_make_graph_store(),
            embedding_provider=mock_embedding_provider,
        )
        results = await service.query("test", top_k=3)
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_query_service_filters_results_below_similarity_threshold(
        self, mock_embedding_provider: MagicMock
    ) -> None:
        """Results with score below similarity_threshold are excluded."""
        store = MagicMock(spec=VectorStoreProtocol)
        store.search_similar.return_value = [("doc-high", 0.85), ("doc-low", 0.1)]
        service = KnowledgeQueryService(
            vector_store=store,
            graph_store=_make_graph_store(),
            embedding_provider=mock_embedding_provider,
            similarity_threshold=0.5,
        )
        results = await service.query("test")
        doc_ids = [r.doc_id for r in results]
        assert "doc-low" not in doc_ids

    @pytest.mark.asyncio
    async def test_query_service_results_are_structured_search_result_instances(
        self, mock_vector_store: MagicMock, mock_embedding_provider: MagicMock
    ) -> None:
        """Every element in query() result is a StructuredSearchResult."""
        service = KnowledgeQueryService(
            vector_store=mock_vector_store,
            graph_store=_make_graph_store(),
            embedding_provider=mock_embedding_provider,
        )
        results = await service.query("search me")
        assert all(isinstance(r, StructuredSearchResult) for r in results)


# ---------------------------------------------------------------------------
# AC10 — Package has correct dependencies in pyproject.toml
# ---------------------------------------------------------------------------


class TestFromAC_PackageDependencies:  # noqa: N801
    """AC: Package has its own pyproject.toml with correct dependencies."""

    def _pyproject_content(self) -> str:
        path = Path(__file__).parent.parent / "packages" / "knowledge" / "pyproject.toml"
        return path.read_text(encoding="utf-8")

    def test_pyproject_lists_qdrant_client_dependency(self) -> None:
        """packages/knowledge/pyproject.toml must declare qdrant-client."""
        assert "qdrant-client" in self._pyproject_content()

    def test_pyproject_lists_embedding_library_dependency(self) -> None:
        """packages/knowledge/pyproject.toml must declare FlagEmbedding or fastembed."""
        content = self._pyproject_content()
        has_embedding_lib = (
            "FlagEmbedding" in content
            or "fastembed" in content
            or "sentence-transformers" in content
        )
        assert has_embedding_lib, (
            "pyproject.toml must declare an embedding library "
            "(FlagEmbedding, fastembed, or sentence-transformers)"
        )
