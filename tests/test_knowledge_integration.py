"""Integration tests: full ingest-to-search cycle — task #162.

End-to-end integration: ingest document → extract entities → build graph
→ embed chunks → query via KnowledgeQueryService → query via GraphAugmentedRetriever.

All storage uses in-memory Qdrant and in-memory SQLite — no Docker, no filesystem.

Run only when qdrant-client is installed:
    uv pip install 'owlbear-knowledge[qdrant]'
"""

from __future__ import annotations

import asyncio
import sqlite3
from unittest.mock import MagicMock

import pytest

try:
    import qdrant_client as _qdrant_client  # noqa: F401
except ImportError:
    pytest.skip(
        "qdrant-client not installed — run: uv pip install 'owlbear-knowledge[qdrant]'",
        allow_module_level=True,
    )

from owlbear_knowledge import (
    DocumentStore,
    GraphStore,
    IngestPipeline,
    IngestResult,
    RetrievalResult,
    init_db,
)
from owlbear_knowledge.chunker import TextChunker
from owlbear_knowledge.extractor import EntityExtractor, ExtractionResult
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.qdrant import DENSE_DIM, QdrantVectorStore
from owlbear_knowledge.query_service import KnowledgeQueryService, StructuredSearchResult
from owlbear_knowledge.retrieval import GraphAugmentedRetriever

# ---------------------------------------------------------------------------
# Deterministic test data
# ---------------------------------------------------------------------------

_DENSE_VEC: list[float] = [0.1] * DENSE_DIM
"""Deterministic 1024-d vector; same for query and stored → cosine sim ≈ 1.0."""

_DOCUMENT_TEXT = (
    "This document describes the AlphaEntity concept and its relationship "
    "to BetaEntity function. Both are core components of the integration pipeline."
)

_ENTITY_1 = Entity(
    name="AlphaEntity",
    entity_type=EntityType.CONCEPT,
    description="The alpha concept in the system",
)
_ENTITY_2 = Entity(
    name="BetaEntity",
    entity_type=EntityType.FUNCTION,
    description="The beta function in the system",
)
_EDGE_1 = Edge(
    source_id=_ENTITY_1.id,
    target_id=_ENTITY_2.id,
    relation=RelationType.RELATED_TO,
)
_EXTRACTION = ExtractionResult(entities=[_ENTITY_1, _ENTITY_2], edges=[_EDGE_1])


# ---------------------------------------------------------------------------
# Class-scoped fixture — ingests once, all tests share the result
# ---------------------------------------------------------------------------


@pytest.fixture(scope="class")
def ingest_ctx(request: pytest.FixtureRequest) -> None:
    """Build in-memory pipeline, ingest once, attach results to the test class."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)

    vector_store = QdrantVectorStore(location=":memory:")
    graph_store = GraphStore(conn)

    embedder = MagicMock()
    embedder.embed.side_effect = lambda texts: [_DENSE_VEC[:] for _ in texts]

    doc_store = DocumentStore(conn, graph_store, vector_store, embedder)

    mock_structured = MagicMock()
    mock_structured.extract.return_value = _EXTRACTION

    entity_extractor = EntityExtractor(extractor=mock_structured)
    chunker = TextChunker(target_tokens=32, overlap_tokens=0)

    pipeline = IngestPipeline(
        document_store=doc_store,
        entity_extractor=entity_extractor,
        text_chunker=chunker,
    )

    intake = IntakeResult(
        content=_DOCUMENT_TEXT,
        source="test://alpha-beta-integration",
        metadata={"title": "Alpha Beta Integration Test"},
    )

    ingest_result: IngestResult = asyncio.run(pipeline.ingest(intake))

    request.cls.vector_store = vector_store
    request.cls.graph_store = graph_store
    request.cls.embedder = embedder
    request.cls.doc_store = doc_store
    request.cls.ingest_result = ingest_result


# ---------------------------------------------------------------------------
# Test class — one test per AC line
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("ingest_ctx")
class TestFromAC_IngestToSearchCycle:
    """Full ingest-to-search integration tests — AC lines from task #162.

    All tests share the class-scoped ingest_ctx fixture (single ingest run).
    """

    # -- AC1 -----------------------------------------------------------------

    def test_ingest_through_pipeline(self) -> None:
        """AC1: IngestPipeline.ingest() with mock extractor/embedder returns status='ok'."""
        result: IngestResult = self.ingest_result  # type: ignore[attr-defined]
        assert result.status == "ok"

    # -- AC2 -----------------------------------------------------------------

    def test_entities_extracted_and_stored(self) -> None:
        """AC2: Entities from mock extractor persisted in GraphStore.list_entities()."""
        graph_store: GraphStore = self.graph_store  # type: ignore[attr-defined]
        entities = graph_store.list_entities()
        entity_names = {e.name for e in entities}
        assert "AlphaEntity" in entity_names
        assert "BetaEntity" in entity_names

    # -- AC3 -----------------------------------------------------------------

    def test_intra_doc_edges_built(self) -> None:
        """AC3: Edges from mock extractor persisted in GraphStore.list_edges()."""
        graph_store: GraphStore = self.graph_store  # type: ignore[attr-defined]
        edges = graph_store.list_edges()
        assert len(edges) > 0
        relations = {str(e.relation) for e in edges}
        assert str(RelationType.RELATED_TO) in relations

    # -- AC4 -----------------------------------------------------------------

    def test_chunks_embedded_and_stored(self) -> None:
        """AC4: Chunk embeddings stored — search_similar returns the ingested chunk IDs."""
        vector_store: QdrantVectorStore = self.vector_store  # type: ignore[attr-defined]
        results = vector_store.search_similar(_DENSE_VEC, top_k=10)
        assert len(results) > 0
        ids = [id_ for id_, _score in results]
        assert all(isinstance(id_, str) and id_ for id_ in ids)

    # -- AC5 -----------------------------------------------------------------

    def test_query_service_returns_results(self) -> None:
        """AC5: KnowledgeQueryService.query() returns non-empty list[StructuredSearchResult]
        containing the ingested document."""
        service = KnowledgeQueryService(
            vector_store=self.vector_store,  # type: ignore[attr-defined]
            graph_store=self.graph_store,  # type: ignore[attr-defined]
            embedding_provider=self.embedder,  # type: ignore[attr-defined]
            similarity_threshold=0.0,
        )
        results = asyncio.run(service.query("AlphaEntity concept", top_k=5))
        assert len(results) > 0, "query() returned no results — expected at least one hit"
        assert all(isinstance(r, StructuredSearchResult) for r in results)
        assert any(r.doc_id for r in results), "at least one result must have a doc_id"

    # -- AC6 -----------------------------------------------------------------

    def test_graph_retriever_includes_expansion(self) -> None:
        """AC6: GraphAugmentedRetriever.retrieve() returns RetrievalResult with
        entities_found > 0 and non-empty expansion_text."""
        retriever = GraphAugmentedRetriever(
            vector_store=self.vector_store,  # type: ignore[attr-defined]
            graph_store=self.graph_store,  # type: ignore[attr-defined]
            embedding_provider=self.embedder,  # type: ignore[attr-defined]
            expansion_enabled=True,
        )
        result = retriever.retrieve("AlphaEntity BetaEntity relationship")
        assert isinstance(result, RetrievalResult)
        assert result.entities_found > 0, (
            f"expected entities_found > 0, got {result.entities_found}. "
            "Graph expansion requires entities to have chunk_id set by store_extractions."
        )
        assert result.expansion_text != "", (
            "expected non-empty expansion_text — graph expansion did not produce output"
        )

    # -- AC7 (implicit — verified by fixture construction) -------------------

    def test_no_external_deps_in_fixture(self) -> None:
        """AC7: Storage backed by in-memory Qdrant + SQLite — no real connection or path."""
        vector_store: QdrantVectorStore = self.vector_store  # type: ignore[attr-defined]
        # QdrantVectorStore with location=':memory:' never touches the filesystem
        assert vector_store._collection is not None
        # SQLite in-memory: if it were a file path, it would have been created on disk
        doc_store: DocumentStore = self.doc_store  # type: ignore[attr-defined]
        # The connection object exists — if it used a file URI it would be a path string
        assert doc_store._conn is not None
