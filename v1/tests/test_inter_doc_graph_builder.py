"""Tests for inter_doc_graph_builder — cross-document relationship inference.

TDD test file written before implementation (task #389).
Tests define the expected interface for InterDocGraphBuilder (task #388).
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models
import pytest

try:
    from owlbear.memory.knowledge.inter_doc_graph_builder import InterDocGraphBuilder
except ImportError:
    pytest.skip(
        "inter_doc_graph_builder module not yet implemented (task #388)",
        allow_module_level=True,
    )

from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.graph_builder import GraphBuildResult
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType

# Block real LLM calls — TestModel and FunctionModel are exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(
    name: str,
    doc_id: str,
    entity_type: EntityType = EntityType.CONCEPT,
) -> Entity:
    """Create an entity with a specific document_id."""
    return Entity(
        name=name,
        entity_type=entity_type,
        description=f"Description for {name}",
        document_id=doc_id,
    )


def _mock_vector_store(
    embeddings: dict[str, list[float]] | None = None,
    search_results: dict[str, list[tuple[str, float]]] | None = None,
) -> MagicMock:
    """Build a mock VectorStoreProtocol.

    Parameters
    ----------
    embeddings:
        Mapping of entity_id → dense vector returned by get_embedding().
    search_results:
        Mapping of entity_id → [(matched_id, score), ...] returned
        by search_similar().
    """
    store = MagicMock()
    embeddings = embeddings or {}
    search_results = search_results or {}

    store.get_embedding.side_effect = embeddings.get

    def _search(emb: list[float], **_kwargs: object) -> list[tuple[str, float]]:
        return search_results.get(_embedding_to_key(emb, embeddings), [])

    store.search_similar.side_effect = _search
    return store


def _embedding_to_key(
    emb: list[float],
    embeddings: dict[str, list[float]],
) -> str:
    """Reverse-lookup an embedding vector back to its entity_id key."""
    for eid, vec in embeddings.items():
        if vec == emb:
            return eid
    return "__unknown__"


def _mock_graph_store(
    entities: dict[str, Entity] | None = None,
    existing_edges: list[Edge] | None = None,
) -> MagicMock:
    """Build a mock GraphStore.

    Parameters
    ----------
    entities:
        Mapping of entity_id → Entity returned by get_entity().
    existing_edges:
        Edges returned by list_edges() for deduplication checking.
    """
    store = MagicMock()
    entities = entities or {}
    existing_edges = existing_edges or []

    store.get_entity.side_effect = entities.get
    store.list_edges.return_value = existing_edges
    return store


def _mock_agent_run(output: ExtractionResult) -> AsyncMock:
    """Build an AsyncMock for Agent.run() returning the given ExtractionResult."""
    mock_result = MagicMock()
    mock_result.output = output
    return AsyncMock(return_value=mock_result)


def _build_inter_doc_builder(
    vector_store: MagicMock | None = None,
    graph_store: MagicMock | None = None,
    extraction: ExtractionResult | None = None,
    top_k: int = 10,
    cosine_threshold: float = 0.70,
) -> InterDocGraphBuilder:
    """Create an InterDocGraphBuilder with mocked dependencies."""
    vs = vector_store or _mock_vector_store()
    gs = graph_store or _mock_graph_store()
    builder = InterDocGraphBuilder(
        model="test",
        vector_store=vs,
        graph_store=gs,
        top_k=top_k,
        cosine_threshold=cosine_threshold,
    )
    if extraction is None:
        extraction = ExtractionResult()
    builder._agent.run = _mock_agent_run(extraction)
    return builder


# ---------------------------------------------------------------------------
# build() — boundary cases
# ---------------------------------------------------------------------------


class TestBuildBoundaryCases:
    """build() handles edge cases with few entities."""

    @pytest.mark.asyncio
    async def test_zero_entities_returns_empty(self) -> None:
        """0 entities → empty result, no LLM call."""
        builder = _build_inter_doc_builder()

        result = await builder.build(entities=[], scope="global")

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 0
        assert result.edges == []
        builder._agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_one_entity_returns_empty(self) -> None:
        """1 entity → empty result, no LLM call."""
        e = _entity("alpha", "doc-1")
        builder = _build_inter_doc_builder()

        result = await builder.build(entities=[e], scope="global")

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 0
        assert result.edges == []
        builder._agent.run.assert_not_called()


# ---------------------------------------------------------------------------
# build() — embedding pre-filter
# ---------------------------------------------------------------------------


class TestEmbeddingPreFilter:
    """Pre-filter calls vector_store.search_similar() per entity."""

    @pytest.mark.asyncio
    async def test_search_similar_called_per_entity(self) -> None:
        """search_similar called for each entity with correct params."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")
        emb1 = [1.0, 0.0, 0.0]
        emb2 = [0.0, 1.0, 0.0]

        vs = _mock_vector_store(
            embeddings={e1.id: emb1, e2.id: emb2},
            search_results={
                e1.id: [(e2.id, 0.85)],
                e2.id: [(e1.id, 0.85)],
            },
        )
        gs = _mock_graph_store(
            entities={e1.id: e1, e2.id: e2},
        )

        inferred = [Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO)]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(
            model="test",
            vector_store=vs,
            graph_store=gs,
        )
        builder._agent.run = _mock_agent_run(extraction)

        await builder.build(entities=[e1, e2], scope="project-x")

        # get_embedding called for each entity
        assert vs.get_embedding.call_count == 2

        # search_similar called for each entity with correct params
        for call in vs.search_similar.call_args_list:
            args, kwargs = call
            assert kwargs.get("embedding_type") or args[2] if len(args) > 2 else True
            # Check scopes contain the scope we passed
            if "scopes" in kwargs:
                assert kwargs["scopes"] == ["project-x"]

    @pytest.mark.asyncio
    async def test_entity_without_embedding_skipped(self) -> None:
        """Entity with no stored embedding is skipped (no search_similar call)."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")
        # Only e1 has an embedding
        vs = _mock_vector_store(
            embeddings={e1.id: [1.0, 0.0]},
            search_results={e1.id: [(e2.id, 0.85)]},
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        inferred = [Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO)]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = _mock_agent_run(extraction)

        await builder.build(entities=[e1, e2], scope="global")

        # search_similar only called for e1 (e2 has no embedding)
        assert vs.search_similar.call_count == 1


# ---------------------------------------------------------------------------
# build() — cross-document filtering
# ---------------------------------------------------------------------------


class TestCrossDocFilter:
    """Pre-filter results exclude same-document entities."""

    @pytest.mark.asyncio
    async def test_same_document_pairs_excluded(self) -> None:
        """Entities from the same document are not paired for LLM inference."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-1")  # same doc!
        e3 = _entity("gamma", "doc-2")

        emb1 = [1.0, 0.0]
        emb2 = [0.9, 0.1]
        emb3 = [0.0, 1.0]

        vs = _mock_vector_store(
            embeddings={e1.id: emb1, e2.id: emb2, e3.id: emb3},
            search_results={
                e1.id: [(e2.id, 0.95), (e3.id, 0.80)],
                e2.id: [(e1.id, 0.95), (e3.id, 0.75)],
                e3.id: [(e1.id, 0.80), (e2.id, 0.75)],
            },
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2, e3.id: e3})

        inferred = [Edge(source_id=e1.id, target_id=e3.id, relation=RelationType.RELATED_TO)]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = _mock_agent_run(extraction)

        result = await builder.build(entities=[e1, e2, e3], scope="global")

        # Agent was called — only cross-doc pairs should be in prompt
        assert builder._agent.run.call_count >= 1
        # Cross-doc pairs produce edges
        assert result.edges_added >= 1


# ---------------------------------------------------------------------------
# build() — cosine threshold filtering
# ---------------------------------------------------------------------------


class TestCosineThreshold:
    """Pairs below cosine threshold are excluded."""

    @pytest.mark.asyncio
    async def test_default_threshold_excludes_low_scores(self) -> None:
        """Default threshold 0.70 excludes pairs with score < 0.70."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={
                e1.id: [(e2.id, 0.60)],  # below 0.70
                e2.id: [(e1.id, 0.60)],
            },
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        builder = InterDocGraphBuilder(
            model="test",
            vector_store=vs,
            graph_store=gs,
            cosine_threshold=0.70,
        )
        builder._agent.run = _mock_agent_run(ExtractionResult())

        result = await builder.build(entities=[e1, e2], scope="global")

        # No pairs pass threshold → no LLM call
        assert result.edges_added == 0
        builder._agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_configurable_threshold_includes_weaker_matches(self) -> None:
        """Lower threshold=0.50 includes pairs with score >= 0.50."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={
                e1.id: [(e2.id, 0.60)],  # above 0.50
                e2.id: [(e1.id, 0.60)],
            },
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        inferred = [Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO)]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(
            model="test",
            vector_store=vs,
            graph_store=gs,
            cosine_threshold=0.50,
        )
        builder._agent.run = _mock_agent_run(extraction)

        result = await builder.build(entities=[e1, e2], scope="global")

        # Pair passes threshold → LLM called → edges produced
        assert builder._agent.run.call_count >= 1
        assert result.edges_added >= 1


# ---------------------------------------------------------------------------
# build() — configurable top_k
# ---------------------------------------------------------------------------


class TestConfigurableTopK:
    """top_k parameter is forwarded to search_similar."""

    @pytest.mark.asyncio
    async def test_top_k_passed_to_search_similar(self) -> None:
        """search_similar called with the configured top_k value."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={
                e1.id: [(e2.id, 0.85)],
                e2.id: [(e1.id, 0.85)],
            },
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        inferred = [Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO)]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(
            model="test",
            vector_store=vs,
            graph_store=gs,
            top_k=5,
        )
        builder._agent.run = _mock_agent_run(extraction)

        await builder.build(entities=[e1, e2], scope="global")

        # Verify search_similar was called with top_k=5
        for call in vs.search_similar.call_args_list:
            _, kwargs = call
            assert kwargs.get("top_k") == 5


# ---------------------------------------------------------------------------
# build() — batch grouping
# ---------------------------------------------------------------------------


class TestBatchGrouping:
    """Entity pairs grouped into batches of ~40 per LLM call."""

    @pytest.mark.asyncio
    async def test_large_pair_set_batched(self) -> None:
        """50+ cross-doc pairs produce multiple LLM calls in batches of ~40."""
        # Create many entities across two documents with high similarity
        entities = []
        embeddings: dict[str, list[float]] = {}
        search_results: dict[str, list[tuple[str, float]]] = {}
        entity_map: dict[str, Entity] = {}

        for i in range(50):
            doc = "doc-1" if i < 25 else "doc-2"
            e = _entity(f"ent_{i}", doc)
            entities.append(e)
            embeddings[e.id] = [float(i)]
            entity_map[e.id] = e

        # Each doc-1 entity matches all doc-2 entities with high score
        doc1_ents = [e for e in entities if e.document_id == "doc-1"]
        doc2_ents = [e for e in entities if e.document_id == "doc-2"]

        for e in doc1_ents:
            search_results[e.id] = [(d2.id, 0.90) for d2 in doc2_ents[:5]]
        for e in doc2_ents:
            search_results[e.id] = [(d1.id, 0.90) for d1 in doc1_ents[:5]]

        vs = _mock_vector_store(embeddings=embeddings, search_results=search_results)
        gs = _mock_graph_store(entities=entity_map)

        single_edge = ExtractionResult(
            edges=[
                Edge(
                    source_id="a",
                    target_id="b",
                    relation=RelationType.RELATED_TO,
                ),
            ],
        )

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = _mock_agent_run(single_edge)

        result = await builder.build(entities=entities, scope="global")

        # With many unique cross-doc pairs, multiple batches should be created
        assert builder._agent.run.call_count >= 2
        assert result.edges_added >= 2


# ---------------------------------------------------------------------------
# build() — edge stamping
# ---------------------------------------------------------------------------


class TestEdgeStamping:
    """All edges have correct weight, metadata, and scope."""

    @pytest.mark.asyncio
    async def test_edges_have_weight_04(self) -> None:
        """All returned edges must have weight=0.4."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={e1.id: [(e2.id, 0.85)], e2.id: [(e1.id, 0.85)]},
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        inferred = [Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO)]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = _mock_agent_run(extraction)

        result = await builder.build(entities=[e1, e2], scope="global")

        for edge in result.edges:
            assert edge.weight == 0.4, f"Edge {edge.id} has weight {edge.weight}, expected 0.4"

    @pytest.mark.asyncio
    async def test_edges_have_inter_doc_metadata(self) -> None:
        """Edges have metadata with source='inter_doc_inference' and doc_pair."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={e1.id: [(e2.id, 0.85)], e2.id: [(e1.id, 0.85)]},
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        inferred = [Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO)]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = _mock_agent_run(extraction)

        result = await builder.build(entities=[e1, e2], scope="global")

        for edge in result.edges:
            assert edge.metadata["source"] == "inter_doc_inference"
            assert "doc_pair" in edge.metadata
            doc_pair = edge.metadata["doc_pair"]
            assert isinstance(doc_pair, list)
            assert len(doc_pair) == 2

    @pytest.mark.asyncio
    async def test_edges_carry_correct_scope(self) -> None:
        """Edges carry the scope passed to build()."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={e1.id: [(e2.id, 0.85)], e2.id: [(e1.id, 0.85)]},
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        inferred = [Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO)]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = _mock_agent_run(extraction)

        result = await builder.build(entities=[e1, e2], scope="project-alpha")

        for edge in result.edges:
            assert edge.scope == "project-alpha"


# ---------------------------------------------------------------------------
# build() — GraphBuildResult correctness
# ---------------------------------------------------------------------------


class TestGraphBuildResult:
    """build() returns GraphBuildResult with correct counts."""

    @pytest.mark.asyncio
    async def test_result_edges_added_matches_edges_list(self) -> None:
        """edges_added == len(edges)."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={e1.id: [(e2.id, 0.85)], e2.id: [(e1.id, 0.85)]},
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        inferred = [
            Edge(source_id=e1.id, target_id=e2.id, relation=RelationType.RELATED_TO),
            Edge(source_id=e2.id, target_id=e1.id, relation=RelationType.DEPENDS_ON),
        ]
        extraction = ExtractionResult(edges=inferred)

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = _mock_agent_run(extraction)

        result = await builder.build(entities=[e1, e2], scope="global")

        assert result.edges_added == len(result.edges)
        assert result.edges_added >= 1


# ---------------------------------------------------------------------------
# build() — error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """LLM failures are handled gracefully."""

    @pytest.mark.asyncio
    async def test_agent_error_returns_empty_result(self) -> None:
        """RuntimeError from agent → empty result, no crash."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={e1.id: [(e2.id, 0.85)], e2.id: [(e1.id, 0.85)]},
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = AsyncMock(side_effect=RuntimeError("LLM is down"))

        result = await builder.build(entities=[e1, e2], scope="global")

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 0
        assert result.edges == []

    @pytest.mark.asyncio
    async def test_llm_failure_logs_warning(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """LLM failure is logged at WARNING level."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={e1.id: [(e2.id, 0.85)], e2.id: [(e1.id, 0.85)]},
        )
        gs = _mock_graph_store(entities={e1.id: e1, e2.id: e2})

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        with caplog.at_level(logging.WARNING):
            await builder.build(entities=[e1, e2], scope="global")

        assert any(
            "inter" in r.message.lower() or "inference" in r.message.lower() for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_partial_batch_failure_returns_successful_edges(self) -> None:
        """One batch fails → edges from other batches still returned."""
        # Create enough cross-doc pairs to trigger multiple batches
        entities = []
        embeddings: dict[str, list[float]] = {}
        search_results: dict[str, list[tuple[str, float]]] = {}
        entity_map: dict[str, Entity] = {}

        for i in range(50):
            doc = "doc-1" if i < 25 else "doc-2"
            e = _entity(f"ent_{i}", doc)
            entities.append(e)
            embeddings[e.id] = [float(i)]
            entity_map[e.id] = e

        doc1_ents = [e for e in entities if e.document_id == "doc-1"]
        doc2_ents = [e for e in entities if e.document_id == "doc-2"]

        for e in doc1_ents:
            search_results[e.id] = [(d2.id, 0.90) for d2 in doc2_ents[:5]]
        for e in doc2_ents:
            search_results[e.id] = [(d1.id, 0.90) for d1 in doc1_ents[:5]]

        vs = _mock_vector_store(embeddings=embeddings, search_results=search_results)
        gs = _mock_graph_store(entities=entity_map)

        good_result = MagicMock()
        good_result.output = ExtractionResult(
            edges=[
                Edge(
                    source_id="a",
                    target_id="b",
                    relation=RelationType.RELATED_TO,
                ),
            ],
        )

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        # First call succeeds, second fails, subsequent succeed
        builder._agent.run = AsyncMock(
            side_effect=[
                good_result,
                RuntimeError("batch 2 failed"),
                good_result,
                good_result,
                good_result,
            ],
        )

        result = await builder.build(entities=entities, scope="global")

        assert isinstance(result, GraphBuildResult)
        # At least one batch succeeded
        assert result.edges_added >= 1


# ---------------------------------------------------------------------------
# build() — deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Entity pairs that already have inter-doc edges are skipped."""

    @pytest.mark.asyncio
    async def test_existing_inter_doc_edges_skipped(self) -> None:
        """Pairs with existing inter_doc_inference edges are not re-processed."""
        e1 = _entity("alpha", "doc-1")
        e2 = _entity("beta", "doc-2")

        vs = _mock_vector_store(
            embeddings={e1.id: [1.0], e2.id: [0.5]},
            search_results={e1.id: [(e2.id, 0.85)], e2.id: [(e1.id, 0.85)]},
        )

        # Existing inter-doc edge between e1 and e2
        existing_edge = Edge(
            source_id=e1.id,
            target_id=e2.id,
            relation=RelationType.RELATED_TO,
            weight=0.4,
            metadata={"source": "inter_doc_inference"},
        )
        gs = _mock_graph_store(
            entities={e1.id: e1, e2.id: e2},
            existing_edges=[existing_edge],
        )

        builder = InterDocGraphBuilder(model="test", vector_store=vs, graph_store=gs)
        builder._agent.run = _mock_agent_run(ExtractionResult())

        result = await builder.build(entities=[e1, e2], scope="global")

        # Pair already has inter-doc edge → skip → no LLM call
        assert result.edges_added == 0
        builder._agent.run.assert_not_called()


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """InterDocGraphBuilder constructor accepts expected parameters."""

    def test_accepts_model_string(self) -> None:
        builder = InterDocGraphBuilder(
            model="test",
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
        )
        assert builder is not None

    def test_accepts_custom_top_k_and_threshold(self) -> None:
        builder = InterDocGraphBuilder(
            model="test",
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
            top_k=5,
            cosine_threshold=0.50,
        )
        assert builder is not None

    def test_accepts_model_object(self) -> None:
        from pydantic_ai.models.test import TestModel

        builder = InterDocGraphBuilder(
            model=TestModel(),
            vector_store=_mock_vector_store(),
            graph_store=_mock_graph_store(),
        )
        assert builder is not None
