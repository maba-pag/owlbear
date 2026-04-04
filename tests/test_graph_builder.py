"""RED-phase tests for IntraDocGraphBuilder DI constructor (task #203 / #33).

Covers all AC lines from #203 for tests/test_graph_builder.py:
  - fewer than 2 entities returns empty GraphBuildResult
  - <=80 entities: single LLM call
  - >80 entities: batched by entity_type, one call per type
  - all returned edges stamped with weight=0.5 and metadata["source"]=="intra_doc_inference"
  - scope and document_id forwarded correctly to the extractor prompt

All tests must FAIL until #33 implements the DI-based IntraDocGraphBuilder.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_builder import GraphBuildResult, InterDocGraphBuilder, IntraDocGraphBuilder
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.protocol import StructuredExtractor  # noqa: F401 — RED: not in protocol.py yet

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity(name: str, etype: EntityType = EntityType.CONCEPT) -> Entity:
    return Entity(name=name, entity_type=etype, scope="global", document_id="doc1")


def _make_raw_edge(source_id: str, target_id: str) -> Edge:
    """Return an unstamped edge — the builder must stamp it."""
    return Edge(source_id=source_id, target_id=target_id, relation=RelationType.RELATED_TO)


def _make_mock_extractor(edges: list[Edge] | None = None) -> MagicMock:
    """Return a mock StructuredExtractor returning ExtractionResult with given edges."""
    mock = MagicMock(spec=StructuredExtractor)
    mock.extract.return_value = ExtractionResult(edges=edges or [])
    return mock


# ---------------------------------------------------------------------------
# TestFromAC_IntraDocGraphBuilder
# ---------------------------------------------------------------------------


class TestFromAC_IntraDocGraphBuilder:
    """AC: IntraDocGraphBuilder with injected StructuredExtractor (task #203/#33)."""

    # --- fewer than 2 entities guard ---

    @pytest.mark.asyncio
    async def test_zero_entities_returns_empty_without_calling_extractor(self) -> None:
        """Zero entities returns empty GraphBuildResult without invoking the extractor."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        result = await builder.build([], scope="global", document_id="doc1")
        assert result == GraphBuildResult()
        mock_ext.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_one_entity_returns_empty_without_calling_extractor(self) -> None:
        """Single entity returns empty GraphBuildResult without invoking the extractor."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        result = await builder.build([_make_entity("solo")], scope="global", document_id="doc1")
        assert result == GraphBuildResult()
        mock_ext.extract.assert_not_called()

    # --- <=80 entities: single LLM call ---

    @pytest.mark.asyncio
    async def test_two_entities_produces_single_extractor_call(self) -> None:
        """Two entities (minimum viable) trigger exactly one extractor call."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        entities = [_make_entity(f"e{i}") for i in range(2)]
        await builder.build(entities, scope="global", document_id="doc1")
        assert mock_ext.extract.call_count == 1

    @pytest.mark.asyncio
    async def test_80_entities_single_call(self) -> None:
        """80 entities (at threshold boundary) produces exactly one extractor call."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        entities = [_make_entity(f"e{i}") for i in range(80)]
        await builder.build(entities, scope="global", document_id="doc1")
        assert mock_ext.extract.call_count == 1

    @pytest.mark.asyncio
    async def test_80_entities_two_types_still_single_call(self) -> None:
        """80 entities split across 2 types: still one call (threshold not exceeded)."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        entities = [_make_entity(f"c{i}", EntityType.CONCEPT) for i in range(40)]
        entities += [_make_entity(f"f{i}", EntityType.FILE) for i in range(40)]
        assert len(entities) == 80
        await builder.build(entities, scope="global", document_id="doc1")
        assert mock_ext.extract.call_count == 1

    # --- >80 entities: batched by entity_type, one call per type ---

    @pytest.mark.asyncio
    async def test_81_entities_two_types_produces_two_calls(self) -> None:
        """81 entities with 2 types → batching mode → 2 extractor calls (one per type)."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        entities = [_make_entity(f"c{i}", EntityType.CONCEPT) for i in range(41)]
        entities += [_make_entity(f"f{i}", EntityType.FILE) for i in range(40)]
        assert len(entities) == 81
        await builder.build(entities, scope="global", document_id="doc1")
        assert mock_ext.extract.call_count == 2

    @pytest.mark.asyncio
    async def test_81_entities_single_type_one_call_in_batch_mode(self) -> None:
        """81 entities all same type → 1 batch (one type) → 1 extractor call."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        entities = [_make_entity(f"c{i}", EntityType.CONCEPT) for i in range(81)]
        await builder.build(entities, scope="global", document_id="doc1")
        assert mock_ext.extract.call_count == 1

    @pytest.mark.asyncio
    async def test_large_batch_three_types_three_calls(self) -> None:
        """100 entities with 3 types → 3 extractor calls."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        entities = [_make_entity(f"c{i}", EntityType.CONCEPT) for i in range(34)]
        entities += [_make_entity(f"f{i}", EntityType.FILE) for i in range(33)]
        entities += [_make_entity(f"p{i}", EntityType.PATTERN) for i in range(33)]
        assert len(entities) == 100
        await builder.build(entities, scope="global", document_id="doc1")
        assert mock_ext.extract.call_count == 3

    # --- edge stamping ---

    @pytest.mark.asyncio
    async def test_returned_edges_all_have_weight_0_5(self) -> None:
        """All edges in GraphBuildResult carry weight=0.5 regardless of extractor output."""
        entities = [_make_entity("a"), _make_entity("b")]
        raw_edge = _make_raw_edge(entities[0].id, entities[1].id)
        mock_ext = _make_mock_extractor(edges=[raw_edge])
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        result = await builder.build(entities, scope="global", document_id="doc1")
        assert len(result.edges) > 0
        for edge in result.edges:
            assert edge.weight == 0.5

    @pytest.mark.asyncio
    async def test_returned_edges_source_is_intra_doc_inference(self) -> None:
        """All edges carry metadata['source'] == 'intra_doc_inference'."""
        entities = [_make_entity("a"), _make_entity("b")]
        raw_edge = _make_raw_edge(entities[0].id, entities[1].id)
        mock_ext = _make_mock_extractor(edges=[raw_edge])
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        result = await builder.build(entities, scope="global", document_id="doc1")
        assert len(result.edges) > 0
        for edge in result.edges:
            assert edge.metadata.get("source") == "intra_doc_inference"

    @pytest.mark.asyncio
    async def test_stamp_overrides_extractor_provided_weight(self) -> None:
        """Builder stamps weight=0.5 even when extractor returns a different weight."""
        entities = [_make_entity("a"), _make_entity("b")]
        heavy_edge = Edge(
            source_id=entities[0].id,
            target_id=entities[1].id,
            relation=RelationType.RELATED_TO,
            weight=0.99,  # intentionally wrong — builder must override
        )
        mock_ext = _make_mock_extractor(edges=[heavy_edge])
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        result = await builder.build(entities, scope="global", document_id="doc1")
        for edge in result.edges:
            assert edge.weight == 0.5

    @pytest.mark.asyncio
    async def test_edges_added_equals_number_of_edges_returned(self) -> None:
        """GraphBuildResult.edges_added matches len(GraphBuildResult.edges)."""
        entities = [_make_entity("a"), _make_entity("b")]
        raw_edges = [
            _make_raw_edge(entities[0].id, entities[1].id),
            _make_raw_edge(entities[1].id, entities[0].id),
        ]
        mock_ext = _make_mock_extractor(edges=raw_edges)
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        result = await builder.build(entities, scope="global", document_id="doc1")
        assert result.edges_added == len(result.edges)

    # --- scope and document_id forwarded correctly ---

    @pytest.mark.asyncio
    async def test_scope_value_forwarded_to_extractor_prompt(self) -> None:
        """The scope parameter value is included in the prompt sent to the extractor."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        entities = [_make_entity("a"), _make_entity("b")]
        await builder.build(entities, scope="custom_scope_xyz", document_id="doc1")
        prompt = mock_ext.extract.call_args[0][0]
        assert "custom_scope_xyz" in prompt

    @pytest.mark.asyncio
    async def test_document_id_forwarded_to_extractor_prompt(self) -> None:
        """The document_id parameter value is included in the prompt sent to the extractor."""
        mock_ext = _make_mock_extractor()
        builder = IntraDocGraphBuilder(extractor=mock_ext)
        entities = [_make_entity("a"), _make_entity("b")]
        await builder.build(entities, scope="global", document_id="unique_doc_id_99")
        prompt = mock_ext.extract.call_args[0][0]
        assert "unique_doc_id_99" in prompt


# ---------------------------------------------------------------------------
# TestBuilderDiscovered — backward-compat no-op paths
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered tests for no-op (extractor=None) compatibility."""

    @pytest.mark.asyncio
    async def test_no_extractor_two_entities_returns_empty(self) -> None:
        """IntraDocGraphBuilder with no extractor returns empty GraphBuildResult for 2 entities."""
        builder = IntraDocGraphBuilder()
        entities = [_make_entity("a"), _make_entity("b")]
        result = await builder.build(entities, scope="global", document_id="doc1")
        assert result == GraphBuildResult()

    @pytest.mark.asyncio
    async def test_no_extractor_many_entities_returns_empty(self) -> None:
        """IntraDocGraphBuilder with no extractor returns empty GraphBuildResult for 90 entities."""
        builder = IntraDocGraphBuilder()
        entities = [_make_entity(f"e{i}") for i in range(90)]
        result = await builder.build(entities, scope="global", document_id="doc1")
        assert result == GraphBuildResult()

    @pytest.mark.asyncio
    async def test_legacy_inter_doc_empty_entities_returns_empty(self) -> None:
        """Legacy InterDocGraphBuilder.build([]) returns empty GraphBuildResult (no-op)."""
        builder = InterDocGraphBuilder(model="stub")
        result = await builder.build([], vector_store=MagicMock(), scope="global")
        assert result == GraphBuildResult()

    @pytest.mark.asyncio
    async def test_legacy_inter_doc_calls_search_similar(self) -> None:
        """Legacy InterDocGraphBuilder calls vector_store.search_similar for pre-filtering."""
        mock_vs = MagicMock()
        mock_vs.search_similar.return_value = []
        builder = InterDocGraphBuilder(model="stub")
        entities = [_make_entity("a"), _make_entity("b")]
        result = await builder.build(entities, vector_store=mock_vs, scope="global")
        mock_vs.search_similar.assert_called_once()
        assert result == GraphBuildResult()
