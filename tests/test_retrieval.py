"""TDD RED tests for GraphAugmentedRetriever and RetrievalResult (task #205).

All tests must FAIL until the builder implements owlbear_knowledge.retrieval.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.retrieval import GraphAugmentedRetriever, RetrievalResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_retriever(**kwargs: object) -> tuple[GraphAugmentedRetriever, MagicMock, MagicMock, MagicMock]:
    """Return (retriever, vector_store, graph_store, embedding_provider) mocks."""
    vector_store = MagicMock()
    graph_store = MagicMock()
    embedding_provider = MagicMock()
    embedding_provider.embed.return_value = [[0.1, 0.2, 0.3]]
    retriever = GraphAugmentedRetriever(
        vector_store=vector_store,
        graph_store=graph_store,
        embedding_provider=embedding_provider,
        **kwargs,
    )
    return retriever, vector_store, graph_store, embedding_provider


def _make_entity(entity_id: str, name: str, *, chunk_id: str | None = None, importance: float = 0.5) -> Entity:
    return Entity(
        id=entity_id,
        name=name,
        entity_type=EntityType.CONCEPT,
        description=f"{name} description",
        chunk_id=chunk_id,
        importance=importance,
    )


def _make_edge(edge_id: str, source_id: str, target_id: str) -> Edge:
    return Edge(
        id=edge_id,
        source_id=source_id,
        target_id=target_id,
        relation=RelationType.RELATED_TO,
    )


# ---------------------------------------------------------------------------
# AC: RetrievalResult is a frozen Pydantic model with chunks, expansion_text,
#     and entities_found fields.
# ---------------------------------------------------------------------------


class TestFromAC_RetrievalResult:
    """Contract tests for the RetrievalResult model."""

    def test_has_chunks_field(self) -> None:
        """RetrievalResult.chunks holds (id, score) pairs."""
        result = RetrievalResult(
            chunks=[("chunk1", 0.9), ("chunk2", 0.75)],
            expansion_text="",
            entities_found=0,
        )
        assert result.chunks == [("chunk1", 0.9), ("chunk2", 0.75)]

    def test_has_expansion_text_field(self) -> None:
        """RetrievalResult.expansion_text holds formatted neighbor text."""
        result = RetrievalResult(chunks=[], expansion_text="Alpha -> Beta: desc", entities_found=1)
        assert result.expansion_text == "Alpha -> Beta: desc"

    def test_has_entities_found_field(self) -> None:
        """RetrievalResult.entities_found holds the count of resolved seed entities."""
        result = RetrievalResult(chunks=[("c1", 0.8)], expansion_text="", entities_found=3)
        assert result.entities_found == 3

    def test_is_frozen_immutable(self) -> None:
        """AC: RetrievalResult is frozen — mutation raises ValidationError."""
        result = RetrievalResult(chunks=[], expansion_text="", entities_found=0)
        with pytest.raises(ValidationError):
            result.chunks = [("new", 0.5)]  # type: ignore[misc]

    def test_chunks_type_is_list_of_str_float_tuples(self) -> None:
        """AC: chunks field type is list[tuple[str, float]]."""
        result = RetrievalResult(chunks=[("id1", 0.95)], expansion_text="", entities_found=0)
        chunk_id, score = result.chunks[0]
        assert isinstance(chunk_id, str)
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# AC: retrieve() returns RetrievalResult with chunks + expansion_text from
#     graph neighbors.
# ---------------------------------------------------------------------------


class TestFromAC_Retrieve:
    """Contract tests for GraphAugmentedRetriever.retrieve()."""

    def test_retrieve_returns_retrieval_result_type(self) -> None:
        """retrieve() returns an instance of RetrievalResult."""
        retriever, vector_store, graph_store, _ = _make_retriever()
        vector_store.search_similar.return_value = [("chunk1", 0.9)]
        graph_store.list_entities.return_value = []

        result = retriever.retrieve("test query")

        assert isinstance(result, RetrievalResult)

    def test_retrieve_returns_chunks_from_vector_search(self) -> None:
        """AC: chunks in result match what vector_store.search_similar returns."""
        retriever, vector_store, graph_store, _ = _make_retriever()
        vector_store.search_similar.return_value = [("doc-a", 0.92), ("doc-b", 0.75)]
        graph_store.list_entities.return_value = []

        result = retriever.retrieve("test query")

        assert result.chunks == [("doc-a", 0.92), ("doc-b", 0.75)]

    def test_retrieve_includes_expansion_text_when_graph_has_neighbors(self) -> None:
        """AC: expansion_text is non-empty when graph neighbors exist for seed entities."""
        retriever, vector_store, graph_store, _ = _make_retriever()
        vector_store.search_similar.return_value = [("chunk-alpha", 0.9)]

        seed = _make_entity("e1", "Alpha", chunk_id="chunk-alpha")
        neighbor = _make_entity("e2", "Beta")
        edge = _make_edge("eg1", "e1", "e2")

        graph_store.list_entities.return_value = [seed]
        graph_store.get_neighbors.return_value = [(neighbor, edge)]

        result = retriever.retrieve("test query")

        assert result.expansion_text != ""

    def test_retrieve_expansion_text_references_seed_and_neighbor(self) -> None:
        """AC: expansion_text contains seed and neighbor names."""
        retriever, vector_store, graph_store, _ = _make_retriever()
        vector_store.search_similar.return_value = [("chunk-alpha", 0.9)]

        seed = _make_entity("e1", "AlphaSeed", chunk_id="chunk-alpha")
        neighbor = _make_entity("e2", "BetaNeighbor")
        edge = _make_edge("eg1", "e1", "e2")

        graph_store.list_entities.return_value = [seed]
        graph_store.get_neighbors.return_value = [(neighbor, edge)]

        result = retriever.retrieve("test query")

        assert "AlphaSeed" in result.expansion_text
        assert "BetaNeighbor" in result.expansion_text

    def test_retrieve_with_expansion_disabled_returns_empty_expansion_text(self) -> None:
        """AC: retrieve() with expansion_enabled=False returns empty expansion_text."""
        retriever, vector_store, graph_store, _ = _make_retriever(expansion_enabled=False)
        vector_store.search_similar.return_value = [("chunk1", 0.9)]

        seed = _make_entity("e1", "Alpha", chunk_id="chunk1")
        neighbor = _make_entity("e2", "Beta")
        edge = _make_edge("eg1", "e1", "e2")

        graph_store.list_entities.return_value = [seed]
        graph_store.get_neighbors.return_value = [(neighbor, edge)]

        result = retriever.retrieve("test query")

        assert result.expansion_text == ""

    def test_retrieve_with_expansion_disabled_still_returns_chunks(self) -> None:
        """AC: expand disabled still returns the vector-search chunks."""
        retriever, vector_store, graph_store, _ = _make_retriever(expansion_enabled=False)
        vector_store.search_similar.return_value = [("chunk1", 0.9)]
        graph_store.list_entities.return_value = []

        result = retriever.retrieve("test query")

        assert result.chunks == [("chunk1", 0.9)]

    def test_retrieve_empty_vector_results_returns_empty_retrieval_result(self) -> None:
        """AC: retrieve() with empty vector results returns empty RetrievalResult."""
        retriever, vector_store, _graph_store, _ = _make_retriever()
        vector_store.search_similar.return_value = []

        result = retriever.retrieve("empty query")

        assert result.chunks == []
        assert result.expansion_text == ""
        assert result.entities_found == 0

    def test_retrieve_entities_found_reflects_seed_count(self) -> None:
        """AC: entities_found equals the number of resolved seed entities."""
        retriever, vector_store, graph_store, _ = _make_retriever()
        vector_store.search_similar.return_value = [("c1", 0.9), ("c2", 0.8)]

        seed1 = _make_entity("e1", "Alpha", chunk_id="c1")
        seed2 = _make_entity("e2", "Beta", chunk_id="c2")
        graph_store.list_entities.return_value = [seed1, seed2]
        graph_store.get_neighbors.return_value = []

        result = retriever.retrieve("two-seed query")

        assert result.entities_found == 2


# ---------------------------------------------------------------------------
# AC: _resolve_seeds finds entities where chunk_id matches a vector search
#     result ID.
# ---------------------------------------------------------------------------


class TestFromAC_ResolveSeeds:
    """Contract tests for GraphAugmentedRetriever._resolve_seeds."""

    def test_resolve_seeds_returns_matching_entities(self) -> None:
        """AC: _resolve_seeds returns only entities whose chunk_id is in the chunk list."""
        retriever, _vs, graph_store, _ = _make_retriever()

        matching = _make_entity("e1", "Match", chunk_id="chunk-abc")
        non_matching = _make_entity("e2", "NoMatch", chunk_id="chunk-xyz")
        graph_store.list_entities.return_value = [matching, non_matching]

        seeds = retriever._resolve_seeds([("chunk-abc", 0.9)], scopes=None)

        assert len(seeds) == 1
        assert seeds[0].id == "e1"

    def test_resolve_seeds_no_match_returns_empty(self) -> None:
        """AC: _resolve_seeds returns [] when no entity chunk_id matches."""
        retriever, _vs, graph_store, _ = _make_retriever()

        entity = _make_entity("e1", "Thing", chunk_id="different-chunk")
        graph_store.list_entities.return_value = [entity]

        seeds = retriever._resolve_seeds([("chunk-xyz", 0.8)], scopes=None)

        assert seeds == []

    def test_resolve_seeds_entity_without_chunk_id_is_excluded(self) -> None:
        """AC: entities with chunk_id=None are never returned as seeds."""
        retriever, _vs, graph_store, _ = _make_retriever()

        no_chunk = _make_entity("e1", "NoChunk", chunk_id=None)
        graph_store.list_entities.return_value = [no_chunk]

        seeds = retriever._resolve_seeds([("chunk-abc", 0.9)], scopes=None)

        assert seeds == []

    def test_resolve_seeds_multiple_matches(self) -> None:
        """AC: _resolve_seeds finds all matching entities, not just the first."""
        retriever, _vs, graph_store, _ = _make_retriever()

        e1 = _make_entity("e1", "First", chunk_id="c1")
        e2 = _make_entity("e2", "Second", chunk_id="c2")
        e3 = _make_entity("e3", "Third", chunk_id="c3-other")
        graph_store.list_entities.return_value = [e1, e2, e3]

        seeds = retriever._resolve_seeds([("c1", 0.9), ("c2", 0.8)], scopes=None)

        assert len(seeds) == 2
        assert {s.id for s in seeds} == {"e1", "e2"}


# ---------------------------------------------------------------------------
# AC: _expand stops appending when max_expansion_tokens budget is exhausted.
# ---------------------------------------------------------------------------


class TestFromAC_ExpandBudget:
    """Contract tests for _expand token-budget enforcement."""

    def test_expand_stops_at_token_budget(self) -> None:
        """AC: _expand stops adding lines when word-count budget is exhausted."""
        retriever, _vs, graph_store, _ = _make_retriever(max_expansion_tokens=5)

        seed = _make_entity("e1", "Seed")
        # Each line: "Seed --[related_to]--> NameN: description" ~6+ words
        neighbor1 = Entity(
            id="e2",
            name="Name1",
            entity_type=EntityType.CONCEPT,
            description="brief",
        )
        neighbor2 = Entity(
            id="e3",
            name="Name2",
            entity_type=EntityType.CONCEPT,
            description="breif two",
        )
        edge1 = _make_edge("eg1", "e1", "e2")
        edge2 = _make_edge("eg2", "e1", "e3")
        graph_store.get_neighbors.return_value = [(neighbor1, edge1), (neighbor2, edge2)]

        text = retriever._expand([seed], scopes=None)

        # With budget of 5 words, at most one line should fit; second is cut
        lines = [ln for ln in text.split("\n") if ln.strip()]
        assert len(lines) <= 1

    def test_expand_zero_budget_returns_empty_string(self) -> None:
        """AC: _expand with max_expansion_tokens=0 returns empty string."""
        retriever, _vs, graph_store, _ = _make_retriever(max_expansion_tokens=0)

        seed = _make_entity("e1", "Seed")
        neighbor = _make_entity("e2", "Nbr")
        edge = _make_edge("eg1", "e1", "e2")
        graph_store.get_neighbors.return_value = [(neighbor, edge)]

        text = retriever._expand([seed], scopes=None)

        assert text == ""

    def test_expand_large_budget_includes_all_neighbors(self) -> None:
        """AC: _expand includes all neighbors when budget is not exhausted."""
        retriever, _vs, graph_store, _ = _make_retriever(max_expansion_tokens=10_000)

        seed = _make_entity("e1", "Seed")
        neighbors_and_edges = [
            (_make_entity(f"e{i}", f"Nbr{i}"), _make_edge(f"eg{i}", "e1", f"e{i}")) for i in range(2, 6)
        ]
        graph_store.get_neighbors.return_value = neighbors_and_edges

        text = retriever._expand([seed], scopes=None)

        for i in range(2, 6):
            assert f"Nbr{i}" in text


# ---------------------------------------------------------------------------
# AC: weight_by_importance=True sorts expanded neighbors descending by
#     importance.
# ---------------------------------------------------------------------------


class TestFromAC_WeightByImportance:
    """Contract tests for importance-sorted neighbor expansion."""

    def test_weight_by_importance_sorts_high_to_low(self) -> None:
        """AC: weight_by_importance=True puts high-importance neighbors first."""
        retriever, _vs, graph_store, _ = _make_retriever(
            weight_by_importance=True,
            max_expansion_tokens=10_000,
        )

        seed = _make_entity("e1", "Seed")
        low = _make_entity("e2", "LowImp", importance=0.1)
        high = _make_entity("e3", "HighImp", importance=0.9)
        edge_low = _make_edge("eg1", "e1", "e2")
        edge_high = _make_edge("eg2", "e1", "e3")

        # Provide low-importance first, high-importance second
        graph_store.get_neighbors.return_value = [(low, edge_low), (high, edge_high)]

        text = retriever._expand([seed], scopes=None)

        # HighImp must appear before LowImp in the formatted output
        assert text.index("HighImp") < text.index("LowImp")

    def test_weight_by_importance_false_preserves_insertion_order(self) -> None:
        """AC: weight_by_importance=False does not reorder neighbors."""
        retriever, _vs, graph_store, _ = _make_retriever(
            weight_by_importance=False,
            max_expansion_tokens=10_000,
        )

        seed = _make_entity("e1", "Seed")
        first = _make_entity("e2", "FirstEntity", importance=0.1)
        second = _make_entity("e3", "SecondEntity", importance=0.9)
        edge1 = _make_edge("eg1", "e1", "e2")
        edge2 = _make_edge("eg2", "e1", "e3")

        # Low-importance entity listed first
        graph_store.get_neighbors.return_value = [(first, edge1), (second, edge2)]

        text = retriever._expand([seed], scopes=None)

        # Original order must be preserved: FirstEntity before SecondEntity
        assert text.index("FirstEntity") < text.index("SecondEntity")
