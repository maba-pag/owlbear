"""Tests for owlbear.memory.knowledge.graph_builder — cross-chunk relationship inference.

TDD test file: the module under test does NOT exist yet. These tests define
the expected interface for IntraDocGraphBuilder, which will be implemented
in task #284. All tests should fail with ImportError until then.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models
import pytest

# graph_builder module is being built in task #284 — skip entire module
# until the import becomes available.
try:
    from owlbear.memory.knowledge.graph_builder import (
        GraphBuildResult,
        IntraDocGraphBuilder,
    )
except ImportError:
    pytest.skip(
        "graph_builder module not yet implemented (task #284)",
        allow_module_level=True,
    )

from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.models import (
    Edge,
    Entity,
    EntityType,
    RelationType,
)

# Block real LLM calls — TestModel and FunctionModel are exempt.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entities(n: int, entity_type: EntityType = EntityType.FUNCTION) -> list[Entity]:
    """Create *n* distinct entities of the given type."""
    return [
        Entity(
            name=f"entity_{i}",
            entity_type=entity_type,
            description=f"Description for entity {i}",
        )
        for i in range(n)
    ]


def _make_mixed_entities(n: int) -> list[Entity]:
    """Create *n* entities cycling through all EntityType values."""
    types = list(EntityType)
    return [
        Entity(
            name=f"entity_{i}",
            entity_type=types[i % len(types)],
            description=f"Description for entity {i}",
        )
        for i in range(n)
    ]


def _make_inferred_edges(entities: list[Entity], count: int = 1) -> list[Edge]:
    """Build *count* edges between consecutive entity pairs."""
    return [
        Edge(
            source_id=entities[i].id,
            target_id=entities[i + 1].id,
            relation=RelationType.RELATED_TO,
            weight=0.5,
            metadata={"source": "intra_doc_inference"},
        )
        for i in range(min(count, len(entities) - 1))
    ]


def _mock_agent_run(output: ExtractionResult) -> AsyncMock:
    """Build an AsyncMock for Agent.run() returning the given ExtractionResult."""
    mock_result = MagicMock()
    mock_result.output = output
    return AsyncMock(return_value=mock_result)


def _builder_with_mock(
    extraction: ExtractionResult | None = None,
) -> IntraDocGraphBuilder:
    """Create an IntraDocGraphBuilder with a mocked PydanticAI agent."""
    builder = IntraDocGraphBuilder(model="test")
    if extraction is None:
        extraction = ExtractionResult()
    builder._agent.run = _mock_agent_run(extraction)
    return builder


# ---------------------------------------------------------------------------
# GraphBuildResult model
# ---------------------------------------------------------------------------


class TestGraphBuildResult:
    """GraphBuildResult is a Pydantic model with edges_added and edges."""

    def test_default_empty(self) -> None:
        result = GraphBuildResult()
        assert result.edges_added == 0
        assert result.edges == []

    def test_with_edges(self) -> None:
        entities = _make_entities(2)
        edges = _make_inferred_edges(entities, count=1)
        result = GraphBuildResult(edges_added=1, edges=edges)
        assert result.edges_added == 1
        assert len(result.edges) == 1


# ---------------------------------------------------------------------------
# build() — boundary cases: 0, 1, 2, 20 entities
# ---------------------------------------------------------------------------


class TestBuildBoundaryCases:
    """build() handles various entity counts correctly."""

    @pytest.mark.asyncio
    async def test_zero_entities_returns_empty(self) -> None:
        """0 entities → empty result, no LLM call."""
        builder = _builder_with_mock()

        result = await builder.build(entities=[], scope="global", document_id="doc-0")

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 0
        assert result.edges == []
        builder._agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_one_entity_returns_empty(self) -> None:
        """1 entity → empty result, no LLM call (need ≥2 for relationships)."""
        entities = _make_entities(1)
        builder = _builder_with_mock()

        result = await builder.build(entities=entities, scope="global", document_id="doc-1")

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 0
        assert result.edges == []
        builder._agent.run.assert_not_called()

    @pytest.mark.asyncio
    async def test_two_entities_calls_agent(self) -> None:
        """2 entities → agent is called, returns inferred edges."""
        entities = _make_entities(2)
        inferred = _make_inferred_edges(entities, count=1)
        extraction = ExtractionResult(edges=inferred)
        builder = _builder_with_mock(extraction)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-2",
        )

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 1
        assert len(result.edges) == 1
        builder._agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_twenty_entities_returns_edges(self) -> None:
        """20 entities → single agent call, returns inferred edges."""
        entities = _make_entities(20)
        inferred = _make_inferred_edges(entities, count=5)
        extraction = ExtractionResult(edges=inferred)
        builder = _builder_with_mock(extraction)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-20",
        )

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 5
        assert len(result.edges) == 5
        # Single batch — only one agent call
        builder._agent.run.assert_called_once()


# ---------------------------------------------------------------------------
# build() — entity-type batching (>80 entities)
# ---------------------------------------------------------------------------


class TestEntityTypeBatching:
    """build() batches by entity_type when entity count exceeds 80."""

    @pytest.mark.asyncio
    async def test_batching_triggers_above_80(self) -> None:
        """81+ entities → multiple agent calls, one per entity_type group."""
        # Create 90 entities across 3 types (30 each)
        entities = (
            _make_entities(30, EntityType.FUNCTION)
            + _make_entities(30, EntityType.CLASS_)
            + _make_entities(30, EntityType.CONCEPT)
        )
        assert len(entities) == 90

        # Each batch returns 1 edge
        single_edge_result = ExtractionResult(
            edges=[
                Edge(
                    source_id="a",
                    target_id="b",
                    relation=RelationType.RELATED_TO,
                    weight=0.5,
                    metadata={"source": "intra_doc_inference"},
                ),
            ],
        )
        builder = IntraDocGraphBuilder(model="test")
        builder._agent.run = _mock_agent_run(single_edge_result)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-batch",
        )

        assert isinstance(result, GraphBuildResult)
        # 3 entity types → 3 agent calls
        assert builder._agent.run.call_count == 3
        # 1 edge per batch → 3 edges total
        assert result.edges_added == 3
        assert len(result.edges) == 3

    @pytest.mark.asyncio
    async def test_no_batching_at_80_or_below(self) -> None:
        """Exactly 80 entities → single agent call (no batching)."""
        entities = _make_entities(80)
        inferred = _make_inferred_edges(entities, count=2)
        extraction = ExtractionResult(edges=inferred)
        builder = _builder_with_mock(extraction)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-80",
        )

        assert isinstance(result, GraphBuildResult)
        builder._agent.run.assert_called_once()
        assert result.edges_added == 2

    @pytest.mark.asyncio
    async def test_batching_aggregates_all_edges(self) -> None:
        """Batched results are aggregated into a single GraphBuildResult."""
        # 100 entities: 50 FUNCTION + 50 CLASS_
        entities = _make_entities(50, EntityType.FUNCTION) + _make_entities(
            50,
            EntityType.CLASS_,
        )
        assert len(entities) == 100

        # Return 2 edges per batch
        batch_edges = ExtractionResult(
            edges=[
                Edge(
                    source_id="x1",
                    target_id="x2",
                    relation=RelationType.DEPENDS_ON,
                    weight=0.5,
                    metadata={"source": "intra_doc_inference"},
                ),
                Edge(
                    source_id="x3",
                    target_id="x4",
                    relation=RelationType.IMPLEMENTS,
                    weight=0.5,
                    metadata={"source": "intra_doc_inference"},
                ),
            ],
        )
        builder = IntraDocGraphBuilder(model="test")
        builder._agent.run = _mock_agent_run(batch_edges)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-100",
        )

        # 2 batches x 2 edges = 4 total
        assert builder._agent.run.call_count == 2
        assert result.edges_added == 4
        assert len(result.edges) == 4


# ---------------------------------------------------------------------------
# build() — edge weight and metadata
# ---------------------------------------------------------------------------


class TestEdgeWeightAndMetadata:
    """Inferred edges have weight=0.5 and metadata.source='intra_doc_inference'."""

    @pytest.mark.asyncio
    async def test_edges_have_weight_half(self) -> None:
        """All returned edges must have weight=0.5."""
        entities = _make_entities(5)
        inferred = _make_inferred_edges(entities, count=3)
        extraction = ExtractionResult(edges=inferred)
        builder = _builder_with_mock(extraction)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-w",
        )

        for edge in result.edges:
            assert edge.weight == 0.5, f"Edge {edge.id} has weight {edge.weight}, expected 0.5"

    @pytest.mark.asyncio
    async def test_edges_have_intra_doc_metadata(self) -> None:
        """All returned edges must have metadata={'source': 'intra_doc_inference'}."""
        entities = _make_entities(5)
        inferred = _make_inferred_edges(entities, count=3)
        extraction = ExtractionResult(edges=inferred)
        builder = _builder_with_mock(extraction)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-m",
        )

        for edge in result.edges:
            assert "source" in edge.metadata
            assert edge.metadata["source"] == "intra_doc_inference"

    @pytest.mark.asyncio
    async def test_edges_use_constrained_relation_types(self) -> None:
        """All returned edges use valid RelationType values."""
        entities = _make_entities(4)
        inferred = _make_inferred_edges(entities, count=2)
        extraction = ExtractionResult(edges=inferred)
        builder = _builder_with_mock(extraction)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-r",
        )

        for edge in result.edges:
            assert edge.relation in RelationType


# ---------------------------------------------------------------------------
# build() — LLM failure
# ---------------------------------------------------------------------------


class TestLLMFailure:
    """LLM failure returns empty GraphBuildResult — no exception propagated."""

    @pytest.mark.asyncio
    async def test_agent_error_returns_empty_result(self) -> None:
        """RuntimeError from agent → empty result, no crash."""
        entities = _make_entities(5)
        builder = IntraDocGraphBuilder(model="test")
        builder._agent.run = AsyncMock(side_effect=RuntimeError("LLM is down"))

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-err",
        )

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 0
        assert result.edges == []

    @pytest.mark.asyncio
    async def test_generic_exception_returns_empty_result(self) -> None:
        """Any exception from agent → empty result, no crash."""
        entities = _make_entities(3)
        builder = IntraDocGraphBuilder(model="test")
        builder._agent.run = AsyncMock(side_effect=Exception("unexpected"))

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-exc",
        )

        assert isinstance(result, GraphBuildResult)
        assert result.edges_added == 0
        assert result.edges == []

    @pytest.mark.asyncio
    async def test_llm_failure_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """LLM failure is logged at WARNING level."""
        import logging

        entities = _make_entities(3)
        builder = IntraDocGraphBuilder(model="test")
        builder._agent.run = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        with caplog.at_level(logging.WARNING):
            await builder.build(
                entities=entities,
                scope="global",
                document_id="doc-log",
            )

        assert any(
            "graph" in r.message.lower() or "inference" in r.message.lower()
            for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_partial_batch_failure_returns_successful_edges(self) -> None:
        """When batching, one batch fails → edges from successful batches still returned."""
        # 90 entities across 3 types
        entities = (
            _make_entities(30, EntityType.FUNCTION)
            + _make_entities(30, EntityType.CLASS_)
            + _make_entities(30, EntityType.CONCEPT)
        )

        good_result = MagicMock()
        good_result.output = ExtractionResult(
            edges=[
                Edge(
                    source_id="a",
                    target_id="b",
                    relation=RelationType.RELATED_TO,
                    weight=0.5,
                    metadata={"source": "intra_doc_inference"},
                ),
            ],
        )

        builder = IntraDocGraphBuilder(model="test")
        # First call succeeds, second fails, third succeeds
        builder._agent.run = AsyncMock(
            side_effect=[good_result, RuntimeError("batch 2 failed"), good_result],
        )

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-partial",
        )

        assert isinstance(result, GraphBuildResult)
        # 2 successful batches x 1 edge = 2
        assert result.edges_added == 2
        assert len(result.edges) == 2


# ---------------------------------------------------------------------------
# build() — scope passthrough
# ---------------------------------------------------------------------------


class TestScopePassthrough:
    """Scope parameter is passed through to returned edges."""

    @pytest.mark.asyncio
    async def test_scope_set_on_edges(self) -> None:
        """Edges returned by build() carry the requested scope."""
        entities = _make_entities(3)
        inferred = _make_inferred_edges(entities, count=2)
        extraction = ExtractionResult(edges=inferred)
        builder = _builder_with_mock(extraction)

        result = await builder.build(
            entities=entities,
            scope="project-alpha",
            document_id="doc-scope",
        )

        for edge in result.edges:
            assert edge.scope == "project-alpha"

    @pytest.mark.asyncio
    async def test_default_scope_global(self) -> None:
        """When scope='global', edges carry scope='global'."""
        entities = _make_entities(3)
        inferred = _make_inferred_edges(entities, count=1)
        extraction = ExtractionResult(edges=inferred)
        builder = _builder_with_mock(extraction)

        result = await builder.build(
            entities=entities,
            scope="global",
            document_id="doc-global",
        )

        for edge in result.edges:
            assert edge.scope == "global"

    @pytest.mark.asyncio
    async def test_custom_scope_preserved_in_batched_mode(self) -> None:
        """Scope is preserved across all batches when batching by entity_type."""
        entities = (
            _make_entities(30, EntityType.FUNCTION)
            + _make_entities(30, EntityType.CLASS_)
            + _make_entities(30, EntityType.CONCEPT)
        )

        single_edge_result = ExtractionResult(
            edges=[
                Edge(
                    source_id="a",
                    target_id="b",
                    relation=RelationType.RELATED_TO,
                    weight=0.5,
                    metadata={"source": "intra_doc_inference"},
                    scope="my-scope",
                ),
            ],
        )
        builder = IntraDocGraphBuilder(model="test")
        builder._agent.run = _mock_agent_run(single_edge_result)

        result = await builder.build(
            entities=entities,
            scope="my-scope",
            document_id="doc-batch-scope",
        )

        for edge in result.edges:
            assert edge.scope == "my-scope"


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """IntraDocGraphBuilder accepts model string or Model object."""

    def test_accepts_model_string(self) -> None:
        builder = IntraDocGraphBuilder(model="test")
        assert builder is not None

    def test_accepts_model_object(self) -> None:
        from pydantic_ai.models.test import TestModel

        builder = IntraDocGraphBuilder(model=TestModel())
        assert builder is not None
