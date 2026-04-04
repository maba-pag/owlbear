"""RED-phase tests for InterDocGraphBuilder in separate module (task #203 / #33).

Covers all AC lines from #203 for tests/test_inter_doc_graph_builder.py:
  - fewer than 2 entities returns empty GraphBuildResult
  - vector pre-filtering calls get_embedding and search_similar per entity
  - cross-doc filter: same document_id pairs skipped
  - existing inter-doc edges skipped (dedup via list_edges)
  - pairs batched in groups of 40
  - all returned edges stamped with weight=0.4 and metadata["source"]=="inter_doc_inference"

All tests must FAIL until #33 creates owlbear_knowledge/inter_doc_graph_builder.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# RED: owlbear_knowledge.inter_doc_graph_builder does not exist yet — ImportError expected
from owlbear_knowledge.inter_doc_graph_builder import InterDocGraphBuilder
from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_builder import GraphBuildResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.protocol import VectorStoreProtocol
from owlbear_knowledge.protocol import StructuredExtractor  # noqa: F401 — RED: not in protocol.py yet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entity(name: str, doc_id: str = "doc1", etype: EntityType = EntityType.CONCEPT) -> Entity:
    return Entity(name=name, entity_type=etype, scope="global", document_id=doc_id)


def _make_raw_edge(source_id: str, target_id: str) -> Edge:
    return Edge(source_id=source_id, target_id=target_id, relation=RelationType.RELATED_TO)


def _make_mock_extractor(edges: list[Edge] | None = None) -> MagicMock:
    mock = MagicMock(spec=StructuredExtractor)
    mock.extract.return_value = ExtractionResult(edges=edges or [])
    return mock


def _make_mock_vector_store(similar: list[tuple[str, float]] | None = None) -> MagicMock:
    """Return a mock VectorStoreProtocol. `similar` is what search_similar returns."""
    mock = MagicMock(spec=VectorStoreProtocol)
    mock.get_embedding.return_value = [0.1] * 1024
    mock.search_similar.return_value = similar or []
    return mock


def _make_mock_graph_store(existing_edges: list[Edge] | None = None) -> MagicMock:
    mock = MagicMock(spec=GraphStore)
    mock.list_edges.return_value = existing_edges or []
    return mock


# ---------------------------------------------------------------------------
# TestFromAC_InterDocGraphBuilder
# ---------------------------------------------------------------------------


class TestFromAC_InterDocGraphBuilder:
    """AC: InterDocGraphBuilder in separate module with DI (task #203/#33)."""

    # --- fewer than 2 entities guard ---

    @pytest.mark.asyncio
    async def test_zero_entities_returns_empty(self) -> None:
        """Zero entities returns empty GraphBuildResult without any LLM or vector calls."""
        builder = InterDocGraphBuilder(
            extractor=_make_mock_extractor(),
            vector_store=_make_mock_vector_store(),
            graph_store=_make_mock_graph_store(),
        )
        result = await builder.build([], scope="global")
        assert result == GraphBuildResult()

    @pytest.mark.asyncio
    async def test_one_entity_returns_empty(self) -> None:
        """Single entity returns empty GraphBuildResult (no pairs possible)."""
        builder = InterDocGraphBuilder(
            extractor=_make_mock_extractor(),
            vector_store=_make_mock_vector_store(),
            graph_store=_make_mock_graph_store(),
        )
        result = await builder.build([_make_entity("solo", doc_id="doc1")], scope="global")
        assert result == GraphBuildResult()

    # --- vector pre-filtering: get_embedding + search_similar per entity ---

    @pytest.mark.asyncio
    async def test_get_embedding_called_once_per_entity(self) -> None:
        """get_embedding is called exactly once for each entity."""
        mock_vs = _make_mock_vector_store()
        entities = [_make_entity(f"e{i}", doc_id=f"doc{i}") for i in range(3)]
        builder = InterDocGraphBuilder(
            extractor=_make_mock_extractor(),
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build(entities, scope="global")
        assert mock_vs.get_embedding.call_count == 3

    @pytest.mark.asyncio
    async def test_search_similar_called_once_per_entity(self) -> None:
        """search_similar is called exactly once for each entity."""
        mock_vs = _make_mock_vector_store()
        entities = [_make_entity(f"e{i}", doc_id=f"doc{i}") for i in range(3)]
        builder = InterDocGraphBuilder(
            extractor=_make_mock_extractor(),
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build(entities, scope="global")
        assert mock_vs.search_similar.call_count == 3

    @pytest.mark.asyncio
    async def test_get_embedding_called_with_entity_id(self) -> None:
        """get_embedding is called with the entity's own ID."""
        mock_vs = _make_mock_vector_store()
        entity_a = _make_entity("alpha", doc_id="doc_A")
        entity_b = _make_entity("beta", doc_id="doc_B")
        builder = InterDocGraphBuilder(
            extractor=_make_mock_extractor(),
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build([entity_a, entity_b], scope="global")
        called_ids = {c[0][0] for c in mock_vs.get_embedding.call_args_list}
        assert entity_a.id in called_ids
        assert entity_b.id in called_ids

    # --- cross-doc filter: same document_id pairs skipped ---

    @pytest.mark.asyncio
    async def test_same_doc_pairs_not_passed_to_extractor(self) -> None:
        """Entity pairs from the same document_id are filtered out before LLM inference."""
        e1 = _make_entity("a", doc_id="same_doc")
        e2 = _make_entity("b", doc_id="same_doc")
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.95)])
        mock_ext = _make_mock_extractor()
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build([e1, e2], scope="global")
        mock_ext.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_cross_doc_pairs_are_passed_to_extractor(self) -> None:
        """Entity pairs from different documents are passed to the LLM extractor."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.95)])
        mock_ext = _make_mock_extractor()
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build([e1, e2], scope="global")
        mock_ext.extract.assert_called()

    # --- dedup existing inter-doc edges via list_edges ---

    @pytest.mark.asyncio
    async def test_existing_edge_pair_skipped_by_dedup(self) -> None:
        """Candidate pairs that already have an edge in the graph store are skipped."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        existing_edge = _make_raw_edge(e1.id, e2.id)
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.95)])
        mock_ext = _make_mock_extractor()
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(existing_edges=[existing_edge]),
        )
        await builder.build([e1, e2], scope="global")
        mock_ext.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_edges_consulted_for_dedup(self) -> None:
        """The graph store's list_edges is called to check for existing edges."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.95)])
        mock_gs = _make_mock_graph_store()
        builder = InterDocGraphBuilder(
            extractor=_make_mock_extractor(),
            vector_store=mock_vs,
            graph_store=mock_gs,
        )
        await builder.build([e1, e2], scope="global")
        mock_gs.list_edges.assert_called()

    # --- batching in groups of 40 ---

    @pytest.mark.asyncio
    async def test_40_candidate_pairs_single_batch_call(self) -> None:
        """40 candidate pairs fit in one batch → exactly 1 extractor call."""
        entity_b = _make_entity("b", doc_id="doc_B")
        entities_a = [_make_entity(f"a{i}", doc_id="doc_A") for i in range(40)]
        all_entities = [*entities_a, entity_b]
        mock_vs = _make_mock_vector_store(similar=[(entity_b.id, 0.9)])
        mock_ext = _make_mock_extractor()
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build(all_entities, scope="global")
        assert mock_ext.extract.call_count == 1

    @pytest.mark.asyncio
    async def test_41_candidate_pairs_two_batch_calls(self) -> None:
        """41 candidate pairs exceed batch size of 40 → exactly 2 extractor calls."""
        entity_b = _make_entity("b", doc_id="doc_B")
        entities_a = [_make_entity(f"a{i}", doc_id="doc_A") for i in range(41)]
        all_entities = [*entities_a, entity_b]
        mock_vs = _make_mock_vector_store(similar=[(entity_b.id, 0.9)])
        mock_ext = _make_mock_extractor()
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build(all_entities, scope="global")
        assert mock_ext.extract.call_count == 2

    @pytest.mark.asyncio
    async def test_80_candidate_pairs_two_batch_calls(self) -> None:
        """80 candidate pairs → 2 batches of 40 → exactly 2 extractor calls."""
        entity_b = _make_entity("b", doc_id="doc_B")
        entities_a = [_make_entity(f"a{i}", doc_id="doc_A") for i in range(80)]
        all_entities = [*entities_a, entity_b]
        mock_vs = _make_mock_vector_store(similar=[(entity_b.id, 0.9)])
        mock_ext = _make_mock_extractor()
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build(all_entities, scope="global")
        assert mock_ext.extract.call_count == 2

    # --- edge stamping: weight=0.4, source="inter_doc_inference" ---

    @pytest.mark.asyncio
    async def test_returned_edges_all_have_weight_0_4(self) -> None:
        """All edges in GraphBuildResult carry weight=0.4."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        raw_edge = _make_raw_edge(e1.id, e2.id)
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.9)])
        mock_ext = _make_mock_extractor(edges=[raw_edge])
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        result = await builder.build([e1, e2], scope="global")
        assert len(result.edges) > 0
        for edge in result.edges:
            assert edge.weight == 0.4

    @pytest.mark.asyncio
    async def test_returned_edges_source_is_inter_doc_inference(self) -> None:
        """All edges carry metadata['source'] == 'inter_doc_inference'."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        raw_edge = _make_raw_edge(e1.id, e2.id)
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.9)])
        mock_ext = _make_mock_extractor(edges=[raw_edge])
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        result = await builder.build([e1, e2], scope="global")
        assert len(result.edges) > 0
        for edge in result.edges:
            assert edge.metadata.get("source") == "inter_doc_inference"

    @pytest.mark.asyncio
    async def test_stamp_overrides_extractor_weight(self) -> None:
        """Builder stamps weight=0.4 even when extractor returns a different weight."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        heavy_edge = Edge(
            source_id=e1.id,
            target_id=e2.id,
            relation=RelationType.RELATED_TO,
            weight=0.99,  # intentionally wrong — builder must override
        )
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.9)])
        mock_ext = _make_mock_extractor(edges=[heavy_edge])
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        result = await builder.build([e1, e2], scope="global")
        for edge in result.edges:
            assert edge.weight == 0.4


# ---------------------------------------------------------------------------
# TestFromAC_InterDocGraphBuilderConstructorParams
# ---------------------------------------------------------------------------


class TestFromAC_InterDocGraphBuilderConstructorParams:
    """AC: InterDocGraphBuilder(top_k: int = 10, cosine_threshold: float = 0.70) (task #33 retry)."""

    # --- cosine_threshold: default 0.70 excludes low-similarity candidates ---

    @pytest.mark.asyncio
    async def test_default_cosine_threshold_excludes_low_similarity_candidate(self) -> None:
        """Score=0.60 is below default threshold 0.70 — extractor must not be called."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.60)])
        mock_ext = _make_mock_extractor()
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build([e1, e2], scope="global")
        mock_ext.extract.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_cosine_threshold_excludes_borderline_candidate(self) -> None:
        """Score=0.75 passes default 0.70 but must be excluded when cosine_threshold=0.80."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        mock_vs = _make_mock_vector_store(similar=[(e2.id, 0.75)])
        mock_ext = _make_mock_extractor()
        builder = InterDocGraphBuilder(
            extractor=mock_ext,
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
            cosine_threshold=0.80,
        )
        await builder.build([e1, e2], scope="global")
        mock_ext.extract.assert_not_called()

    # --- top_k: passed to search_similar ---

    @pytest.mark.asyncio
    async def test_search_similar_receives_configured_top_k(self) -> None:
        """search_similar is called with top_k matching the constructor argument."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        mock_vs = _make_mock_vector_store()
        builder = InterDocGraphBuilder(
            extractor=_make_mock_extractor(),
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
            top_k=7,
        )
        await builder.build([e1, e2], scope="global")
        for call in mock_vs.search_similar.call_args_list:
            args, kwargs = call
            top_k_used = kwargs.get("top_k") if "top_k" in kwargs else (args[1] if len(args) > 1 else None)
            assert top_k_used == 7, f"Expected top_k=7, got {top_k_used}"

    @pytest.mark.asyncio
    async def test_default_top_k_is_10(self) -> None:
        """search_similar is called with top_k=10 when top_k is not specified in constructor."""
        e1 = _make_entity("a", doc_id="doc_A")
        e2 = _make_entity("b", doc_id="doc_B")
        mock_vs = _make_mock_vector_store()
        builder = InterDocGraphBuilder(
            extractor=_make_mock_extractor(),
            vector_store=mock_vs,
            graph_store=_make_mock_graph_store(),
        )
        await builder.build([e1, e2], scope="global")
        for call in mock_vs.search_similar.call_args_list:
            args, kwargs = call
            top_k_used = kwargs.get("top_k") if "top_k" in kwargs else (args[1] if len(args) > 1 else None)
            assert top_k_used == 10, f"Expected default top_k=10, got {top_k_used}"
