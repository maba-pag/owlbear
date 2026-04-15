"""RED-phase tests for #863: Source-aware candidate filtering in InterDocGraphBuilder.

AC coverage:
  AC1: _collect_candidates() joins entities to their document's source_id
       (graph_store.get_document called for each entity.document_id)
  AC2: Cross-source pairs prioritized over same-source cross-document pairs
       (cross-source pairs appear first in candidates passed to extractor)
  AC3: Edge metadata includes doc_pair and source_pair (both NEW fields per arch review —
       neither exists in current _stamp_inter_edge implementation)
  AC4 (binding arch-review): document_id=None or source_id=None → unknown source,
       never prioritized as cross-source

All tests FAIL until #863 implements source-aware filtering in InterDocGraphBuilder.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.inter_doc_graph_builder import InterDocGraphBuilder
from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_builder import GraphBuildResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Document, Edge, Entity, EntityType, RelationType
from owlbear_knowledge.protocol import StructuredExtractor, VectorStoreProtocol


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(name: str, doc_id: str | None) -> Entity:
    return Entity(name=name, entity_type=EntityType.CONCEPT, scope="global", document_id=doc_id)


def _document(doc_id: str, source_id: str | None) -> Document:
    return Document(id=doc_id, title=doc_id, content="", source_id=source_id)


def _raw_edge(source_id: str, target_id: str) -> Edge:
    return Edge(source_id=source_id, target_id=target_id, relation=RelationType.RELATED_TO)


def _async_extractor(edges: list[Edge] | None = None) -> MagicMock:
    """Mock StructuredExtractor with AsyncMock extract()."""
    mock = MagicMock(spec=StructuredExtractor)
    mock.extract = AsyncMock(return_value=ExtractionResult(edges=edges or []))
    return mock


def _vector_store(similar: list[tuple[str, float]] | None = None) -> MagicMock:
    """Simple mock that returns the same similar results for every entity query."""
    mock = MagicMock(spec=VectorStoreProtocol)
    mock.get_embedding.return_value = [0.1] * 1024
    mock.search_similar.return_value = similar or []
    return mock


def _ordered_vector_store(per_call_similar: list[list[tuple[str, float]]]) -> MagicMock:
    """Vector store where the Nth search_similar call returns per_call_similar[N].

    Entities are processed in the order they appear in the list passed to
    InterDocGraphBuilder.build(), so per_call_similar[0] corresponds to the 1st
    entity, per_call_similar[1] to the 2nd, etc.
    """
    call_state: dict[str, int] = {"n": 0}
    mock = MagicMock(spec=VectorStoreProtocol)
    mock.get_embedding.return_value = [0.1] * 1024

    def search_similar(embedding: list[float], top_k: int = 10) -> list[tuple[str, float]]:  # noqa: ARG001
        idx = call_state["n"]
        call_state["n"] += 1
        return per_call_similar[idx] if idx < len(per_call_similar) else []

    mock.search_similar.side_effect = search_similar
    return mock


def _graph_store(
    doc_source_map: dict[str, str | None] | None = None,
    existing_edges: list[Edge] | None = None,
) -> MagicMock:
    """Mock GraphStore. get_document looks up source_id from doc_source_map; returns None if absent."""
    mock = MagicMock(spec=GraphStore)
    mock.list_edges.return_value = existing_edges or []
    ds_map = doc_source_map or {}

    def get_document(doc_id: str) -> Document | None:
        if doc_id not in ds_map:
            return None
        return _document(doc_id, ds_map[doc_id])

    mock.get_document.side_effect = get_document
    return mock


# ---------------------------------------------------------------------------
# TestFromAC_SourceLookup — AC1: _collect_candidates joins entities to source_id
# ---------------------------------------------------------------------------


class TestFromAC_SourceLookup:
    """AC1: _collect_candidates() consults graph_store.get_document() per entity.document_id."""

    @pytest.mark.asyncio
    async def test_get_document_called_for_each_entity_document_id(self) -> None:
        """get_document is called with each entity's document_id during candidate collection."""
        e1 = _entity("a", "doc_A")
        e2 = _entity("b", "doc_B")
        mock_gs = _graph_store({"doc_A": "src_1", "doc_B": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        await builder.build([e1, e2], scope="global")
        called_ids = {call.args[0] for call in mock_gs.get_document.call_args_list}
        assert "doc_A" in called_ids
        assert "doc_B" in called_ids

    @pytest.mark.asyncio
    async def test_entity_with_none_doc_id_does_not_trigger_get_document_with_none(self) -> None:
        """Entity with document_id=None must not cause get_document(None) call.

        After AC1 is implemented, get_document IS called for known doc_ids — this
        test validates that None is explicitly excluded from those calls.
        """
        e_none = _entity("no_doc", doc_id=None)
        e_other = _entity("other", "doc_B")
        mock_gs = _graph_store({"doc_B": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(),
            vector_store=_vector_store(similar=[(e_other.id, 0.9)]),
            graph_store=mock_gs,
        )
        await builder.build([e_none, e_other], scope="global")
        called_args = [call.args[0] for call in mock_gs.get_document.call_args_list]
        assert "doc_B" in called_args, "get_document must be called for e_other's doc_id"
        assert None not in called_args, "get_document must never be called with None"

    @pytest.mark.asyncio
    async def test_orphaned_entity_doc_id_consulted_in_get_document(self) -> None:
        """Orphaned entity's document_id is still passed to get_document (returns None gracefully)."""
        e1 = _entity("orphan", "orphaned_doc")  # not in doc_source_map → returns None
        e2 = _entity("known", "doc_B")
        mock_gs = _graph_store({"doc_B": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        await builder.build([e1, e2], scope="global")
        called_ids = {call.args[0] for call in mock_gs.get_document.call_args_list}
        assert "orphaned_doc" in called_ids, "get_document must be consulted even for orphaned doc_ids"

    @pytest.mark.asyncio
    async def test_get_document_called_for_all_unique_document_ids(self) -> None:
        """Every unique document_id in the entity list is passed to get_document at least once."""
        entities = [_entity(f"e{i}", f"doc_{i}") for i in range(4)]
        doc_source_map = {f"doc_{i}": f"src_{i % 2}" for i in range(4)}
        mock_gs = _graph_store(doc_source_map)
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(),
            vector_store=_vector_store(),
            graph_store=mock_gs,
        )
        await builder.build(entities, scope="global")
        called_ids = {call.args[0] for call in mock_gs.get_document.call_args_list}
        assert len(called_ids) >= 4


# ---------------------------------------------------------------------------
# TestFromAC_CrossSourcePriority — AC2: cross-source pairs before same-source cross-doc
# ---------------------------------------------------------------------------


class TestFromAC_CrossSourcePriority:
    """AC2: Cross-source pairs are prioritized over same-source cross-document pairs."""

    @pytest.mark.asyncio
    async def test_cross_source_pair_precedes_same_source_cross_doc_in_prompt(self) -> None:
        """In a single batch, cross-source pair appears before same-source cross-doc pair."""
        e_main = _entity("main", "doc_1")       # src_1
        e_same = _entity("same_src", "doc_2")   # src_1 — same source, different doc
        e_diff = _entity("diff_src", "doc_3")   # src_2 — different source

        mock_gs = _graph_store({"doc_1": "src_1", "doc_2": "src_1", "doc_3": "src_2"})
        # Only e_main finds similar entities; their order in the similar list has same_src first
        mock_vs = _ordered_vector_store([
            [(e_same.id, 0.95), (e_diff.id, 0.92)],  # e_main: same_src listed before diff_src
            [],  # e_same finds nothing
            [],  # e_diff finds nothing
        ])
        mock_ext = _async_extractor()
        builder = InterDocGraphBuilder(extractor=mock_ext, vector_store=mock_vs, graph_store=mock_gs)
        await builder.build([e_main, e_same, e_diff], scope="global")

        prompt: str = mock_ext.extract.call_args.args[0]
        assert prompt.index("diff_src") < prompt.index("same_src"), (
            "Cross-source pair (diff_src) must appear before same-source cross-doc pair (same_src)"
        )

    @pytest.mark.asyncio
    async def test_same_source_cross_doc_pairs_included_with_doc_pair_metadata(self) -> None:
        """Same-source cross-doc pairs are included (not filtered) and receive doc_pair metadata."""
        e1 = _entity("alpha", "doc_1")  # src_1
        e2 = _entity("beta", "doc_2")   # src_1 — same source, different doc
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_1": "src_1", "doc_2": "src_1"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        assert len(result.edges) > 0, "Same-source cross-doc pairs must not be excluded"
        for edge in result.edges:
            assert "doc_pair" in edge.metadata, "Same-source cross-doc edges must have doc_pair"

    @pytest.mark.asyncio
    async def test_cross_source_pair_in_first_batch_when_41_candidates(self) -> None:
        """Single cross-source pair among 41 candidates occupies slot in the first batch of 40."""
        e_main = _entity("main", "doc_main")  # src_main
        # 40 same-source cross-doc entities (src_main, distinct docs)
        same_src_entities = [_entity(f"same_{i}", f"doc_same_{i}") for i in range(40)]
        # 1 cross-source entity added LAST in the similar list (would appear in 2nd batch without sorting)
        e_cross = _entity("cross_entity", "doc_cross")  # src_other

        doc_src: dict[str, str | None] = {"doc_main": "src_main", "doc_cross": "src_other"}
        for i in range(40):
            doc_src[f"doc_same_{i}"] = "src_main"

        mock_gs = _graph_store(doc_src)
        # Only e_main gets similar results; cross entity is last in the list
        main_similar = [(e.id, 0.9) for e in same_src_entities] + [(e_cross.id, 0.9)]
        other_similar: list[list[tuple[str, float]]] = [[] for _ in range(len(same_src_entities) + 1)]
        mock_vs = _ordered_vector_store([main_similar, *other_similar])
        mock_ext = _async_extractor()

        all_entities = [e_main, *same_src_entities, e_cross]
        builder = InterDocGraphBuilder(extractor=mock_ext, vector_store=mock_vs, graph_store=mock_gs)
        await builder.build(all_entities, scope="global")

        assert mock_ext.extract.await_count == 2, "41 pairs must produce exactly 2 batches"
        first_prompt: str = mock_ext.extract.call_args_list[0].args[0]
        assert "cross_entity" in first_prompt, "Cross-source pair must be promoted to the first batch"


# ---------------------------------------------------------------------------
# TestFromAC_EdgeMetadataStamping — AC3: doc_pair and source_pair (new fields)
# ---------------------------------------------------------------------------


class TestFromAC_EdgeMetadataStamping:
    """AC3: Stamped edges include doc_pair and source_pair — both are NEW fields."""

    @pytest.mark.asyncio
    async def test_stamped_edge_has_doc_pair(self) -> None:
        """Each edge in the result has 'doc_pair' in its metadata."""
        e1 = _entity("a", "doc_A")
        e2 = _entity("b", "doc_B")
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_A": "src_1", "doc_B": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        assert len(result.edges) > 0
        for edge in result.edges:
            assert "doc_pair" in edge.metadata, "'doc_pair' missing from edge metadata"

    @pytest.mark.asyncio
    async def test_doc_pair_contains_both_document_ids(self) -> None:
        """doc_pair contains the document IDs of both entities in the pair."""
        e1 = _entity("a", "doc_A")
        e2 = _entity("b", "doc_B")
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_A": "src_1", "doc_B": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        doc_pair = result.edges[0].metadata["doc_pair"]
        assert set(doc_pair) == {"doc_A", "doc_B"}

    @pytest.mark.asyncio
    async def test_doc_pair_is_sorted_ascending(self) -> None:
        """doc_pair is sorted ascending for stable cross-edge comparison."""
        e1 = _entity("a", "doc_Z")  # intentionally lexicographically larger
        e2 = _entity("b", "doc_A")
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_Z": "src_1", "doc_A": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        doc_pair = result.edges[0].metadata["doc_pair"]
        assert doc_pair == sorted(doc_pair), f"Expected sorted doc_pair, got {doc_pair}"

    @pytest.mark.asyncio
    async def test_stamped_edge_has_source_pair(self) -> None:
        """Each edge in the result has 'source_pair' in its metadata."""
        e1 = _entity("a", "doc_A")
        e2 = _entity("b", "doc_B")
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_A": "src_1", "doc_B": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        assert len(result.edges) > 0
        for edge in result.edges:
            assert "source_pair" in edge.metadata, "'source_pair' missing from edge metadata"

    @pytest.mark.asyncio
    async def test_source_pair_contains_both_source_ids(self) -> None:
        """source_pair contains the source_ids of both entities' documents."""
        e1 = _entity("a", "doc_A")
        e2 = _entity("b", "doc_B")
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_A": "src_1", "doc_B": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        source_pair = result.edges[0].metadata["source_pair"]
        assert set(source_pair) == {"src_1", "src_2"}

    @pytest.mark.asyncio
    async def test_source_pair_is_sorted_ascending(self) -> None:
        """source_pair is sorted ascending for stable comparison."""
        e1 = _entity("a", "doc_A")
        e2 = _entity("b", "doc_B")
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_A": "src_z", "doc_B": "src_a"})  # reversed lexicographic order
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        source_pair = result.edges[0].metadata["source_pair"]
        assert source_pair == sorted(source_pair), f"Expected sorted source_pair, got {source_pair}"

    @pytest.mark.asyncio
    async def test_doc_pair_and_source_pair_coexist_with_existing_source_field(self) -> None:
        """doc_pair and source_pair exist alongside the pre-existing 'source' metadata field."""
        e1 = _entity("a", "doc_A")
        e2 = _entity("b", "doc_B")
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_A": "src_1", "doc_B": "src_2"})
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        edge = result.edges[0]
        assert edge.metadata.get("source") == "inter_doc_inference"
        assert "doc_pair" in edge.metadata
        assert "source_pair" in edge.metadata


# ---------------------------------------------------------------------------
# TestFromAC_NoneSourceHandling — Binding arch-review AC
# ---------------------------------------------------------------------------


class TestFromAC_NoneSourceHandling:
    """Binding arch-review AC: document_id=None or source_id=None → unknown, not prioritized."""

    @pytest.mark.asyncio
    async def test_none_document_id_entity_not_prioritized_over_real_cross_source(self) -> None:
        """Entity with document_id=None is not treated as cross-source and appears after real cross-source."""
        e_main = _entity("main", "doc_1")          # src_1
        e_no_doc = _entity("no_doc_ent", doc_id=None)  # unknown source
        e_cross = _entity("cross_ent", "doc_3")    # src_2 — real cross-source

        mock_gs = _graph_store({"doc_1": "src_1", "doc_3": "src_2"})
        # no_doc_ent has higher similarity score but must not be prioritized over cross_ent
        mock_vs = _ordered_vector_store([
            [(e_no_doc.id, 0.97), (e_cross.id, 0.92)],  # e_main finds both; no_doc listed first
            [],  # e_no_doc finds nothing
            [],  # e_cross finds nothing
        ])
        mock_ext = _async_extractor()
        builder = InterDocGraphBuilder(extractor=mock_ext, vector_store=mock_vs, graph_store=mock_gs)
        await builder.build([e_main, e_no_doc, e_cross], scope="global")

        prompt: str = mock_ext.extract.call_args.args[0]
        assert prompt.index("cross_ent") < prompt.index("no_doc_ent"), (
            "Real cross-source pair 'cross_ent' must appear before unknown-source 'no_doc_ent'"
        )

    @pytest.mark.asyncio
    async def test_none_source_id_entity_not_prioritized_over_real_cross_source(self) -> None:
        """Entity whose document has source_id=None is not treated as cross-source."""
        e_main = _entity("main", "doc_1")          # src_1
        e_no_src = _entity("no_src_ent", "doc_2")  # document.source_id = None
        e_cross = _entity("cross_ent", "doc_3")    # src_2 — real cross-source

        mock_gs = _graph_store({"doc_1": "src_1", "doc_2": None, "doc_3": "src_2"})
        # no_src_ent has higher similarity but must not be prioritized over cross_ent
        mock_vs = _ordered_vector_store([
            [(e_no_src.id, 0.97), (e_cross.id, 0.92)],  # e_main finds both; no_src listed first
            [],  # e_no_src finds nothing
            [],  # e_cross finds nothing
        ])
        mock_ext = _async_extractor()
        builder = InterDocGraphBuilder(extractor=mock_ext, vector_store=mock_vs, graph_store=mock_gs)
        await builder.build([e_main, e_no_src, e_cross], scope="global")

        prompt: str = mock_ext.extract.call_args.args[0]
        assert prompt.index("cross_ent") < prompt.index("no_src_ent"), (
            "Real cross-source pair 'cross_ent' must appear before None-source 'no_src_ent'"
        )

    @pytest.mark.asyncio
    async def test_build_with_none_source_id_stamps_source_pair_in_metadata(self) -> None:
        """build() completes and stamps source_pair even when one entity's document has source_id=None."""
        e1 = _entity("a", "doc_A")
        e2 = _entity("b", "doc_B")
        raw = _raw_edge(e1.id, e2.id)
        mock_gs = _graph_store({"doc_A": "src_1", "doc_B": None})  # doc_B has no source
        builder = InterDocGraphBuilder(
            extractor=_async_extractor(edges=[raw]),
            vector_store=_vector_store(similar=[(e2.id, 0.9)]),
            graph_store=mock_gs,
        )
        result = await builder.build([e1, e2], scope="global")
        assert isinstance(result, GraphBuildResult)
        assert len(result.edges) > 0
        assert "source_pair" in result.edges[0].metadata, "source_pair must be present even with None source_id"
