"""Tests for GraphAugmentedRetriever — graph-enhanced knowledge retrieval.

TDD tests for #422 / #372.  Covers: basic retrieval with expansion,
kill switch (expansion_enabled=False), expansion_depth=0, token budget,
empty results, no-entities-for-chunks, max_neighbors_per_entity,
scopes passthrough.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.retrieval import GraphAugmentedRetriever, RetrievalResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EMBED_VEC = [0.1, 0.2, 0.3]


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Mock satisfying VectorStoreProtocol."""
    store = MagicMock()
    store.search_similar = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_graph_store() -> MagicMock:
    """Mock satisfying GraphStore interface."""
    store = MagicMock()
    store.list_entities = MagicMock(return_value=[])
    store.get_neighbors = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    """Mock with embed_hybrid support."""
    provider = MagicMock()
    provider.embed_hybrid = MagicMock(
        return_value=[HybridEmbedding(dense=_EMBED_VEC)],
    )
    provider.embed = MagicMock(return_value=[_EMBED_VEC])
    return provider


@pytest.fixture
def retriever(
    mock_vector_store: MagicMock,
    mock_graph_store: MagicMock,
    mock_embedding_provider: MagicMock,
) -> GraphAugmentedRetriever:
    """Default retriever with mocked dependencies."""
    return GraphAugmentedRetriever(
        vector_store=mock_vector_store,
        graph_store=mock_graph_store,
        embedding_provider=mock_embedding_provider,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(
    entity_id: str,
    name: str,
    *,
    chunk_id: str | None = None,
    description: str = "",
) -> Entity:
    return Entity(
        id=entity_id,
        name=name,
        entity_type=EntityType.CONCEPT,
        description=description,
        chunk_id=chunk_id,
    )


def _edge(source_id: str, target_id: str) -> Edge:
    return Edge(
        source_id=source_id,
        target_id=target_id,
        relation=RelationType.RELATED_TO,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRetrievalResult:
    """RetrievalResult is a frozen Pydantic model."""

    def test_frozen(self) -> None:
        result = RetrievalResult(chunks=[], expansion_text="", entities_found=0)
        with pytest.raises(Exception, match="frozen"):
            result.entities_found = 99  # type: ignore[misc]

    def test_defaults(self) -> None:
        result = RetrievalResult(chunks=[], expansion_text="", entities_found=0)
        assert result.chunks == []
        assert result.expansion_text == ""
        assert result.entities_found == 0


class TestBasicRetrieval:
    """retrieve() returns vector search results + neighbor descriptions."""

    def test_returns_chunks_sorted_by_score(
        self,
        retriever: GraphAugmentedRetriever,
        mock_vector_store: MagicMock,
    ) -> None:
        # Vector search returns two chunks (already sorted desc).
        mock_vector_store.search_similar.return_value = [
            ("doc1:chunk:0", 0.95),
            ("doc1:chunk:1", 0.80),
        ]
        result = retriever.retrieve("what is OwlBear?")
        assert result.chunks == [("doc1:chunk:0", 0.95), ("doc1:chunk:1", 0.80)]

    def test_expansion_adds_neighbor_descriptions(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            expansion_depth=1,
        )
        # Vector search finds one chunk.
        mock_vector_store.search_similar.return_value = [("doc1:chunk:0", 0.9)]

        # Chunk maps to an entity via chunk_id.
        seed = _entity("e1", "OwlBear", chunk_id="doc1:chunk:0")
        mock_graph_store.list_entities.return_value = [seed]

        # Entity has a neighbor.
        neighbor = _entity("e2", "PydanticAI", description="Agent framework")
        edge = _edge("e1", "e2")
        mock_graph_store.get_neighbors.return_value = [(neighbor, edge)]

        result = retriever.retrieve("what is OwlBear?")

        assert result.entities_found == 1
        assert "PydanticAI" in result.expansion_text
        assert "Agent framework" in result.expansion_text


class TestKillSwitch:
    """expansion_enabled=False disables graph expansion entirely."""

    def test_expansion_disabled_returns_only_chunks(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            expansion_enabled=False,
        )
        mock_vector_store.search_similar.return_value = [("c1", 0.9)]

        result = retriever.retrieve("query")

        assert result.chunks == [("c1", 0.9)]
        assert result.expansion_text == ""
        assert result.entities_found == 0
        mock_graph_store.list_entities.assert_not_called()
        mock_graph_store.get_neighbors.assert_not_called()


class TestExpansionDepthZero:
    """expansion_depth=0 returns only vector results (no graph traversal)."""

    def test_depth_zero_skips_graph(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            expansion_depth=0,
        )
        mock_vector_store.search_similar.return_value = [("c1", 0.85)]

        result = retriever.retrieve("query")

        assert result.chunks == [("c1", 0.85)]
        assert result.expansion_text == ""
        assert result.entities_found == 0
        mock_graph_store.get_neighbors.assert_not_called()


class TestTokenBudget:
    """expansion_text never exceeds max_expansion_tokens words."""

    def test_budget_caps_expansion(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            max_expansion_tokens=5,  # Very tight budget.
        )
        mock_vector_store.search_similar.return_value = [("c1", 0.9)]
        seed = _entity("e1", "Seed", chunk_id="c1")
        mock_graph_store.list_entities.return_value = [seed]

        # Two neighbors, each description > 5 words.
        n1 = _entity("n1", "Alpha", description="word one two three four five six")
        n2 = _entity("n2", "Beta", description="another long description here now")
        mock_graph_store.get_neighbors.return_value = [
            (n1, _edge("e1", "n1")),
            (n2, _edge("e1", "n2")),
        ]

        result = retriever.retrieve("query")
        word_count = len(result.expansion_text.split())
        assert word_count <= 5

    def test_zero_budget_returns_empty_expansion(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            max_expansion_tokens=0,
        )
        mock_vector_store.search_similar.return_value = [("c1", 0.9)]
        seed = _entity("e1", "Seed", chunk_id="c1")
        mock_graph_store.list_entities.return_value = [seed]
        neighbor = _entity("n1", "N", description="desc")
        mock_graph_store.get_neighbors.return_value = [(neighbor, _edge("e1", "n1"))]

        result = retriever.retrieve("query")
        assert result.expansion_text == ""


class TestEmptyResults:
    """When vector search returns nothing."""

    def test_empty_vector_results(
        self,
        retriever: GraphAugmentedRetriever,
        mock_vector_store: MagicMock,
    ) -> None:
        mock_vector_store.search_similar.return_value = []
        result = retriever.retrieve("query")
        assert result.chunks == []
        assert result.expansion_text == ""
        assert result.entities_found == 0


class TestNoEntitiesForChunks:
    """When vector results exist but no entities match chunk_ids."""

    def test_no_matching_entities(
        self,
        retriever: GraphAugmentedRetriever,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        mock_vector_store.search_similar.return_value = [("c1", 0.9)]
        # list_entities returns entities with different chunk_ids.
        mock_graph_store.list_entities.return_value = [
            _entity("e1", "Other", chunk_id="different_chunk"),
        ]

        result = retriever.retrieve("query")
        assert result.chunks == [("c1", 0.9)]
        assert result.expansion_text == ""
        assert result.entities_found == 0


class TestMaxNeighborsPerEntity:
    """max_neighbors_per_entity limits fan-out per seed entity."""

    def test_max_neighbors_passed_to_get_neighbors(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            max_neighbors_per_entity=3,
        )
        mock_vector_store.search_similar.return_value = [("c1", 0.9)]
        seed = _entity("e1", "Seed", chunk_id="c1")
        mock_graph_store.list_entities.return_value = [seed]
        mock_graph_store.get_neighbors.return_value = []

        retriever.retrieve("query")

        mock_graph_store.get_neighbors.assert_called_once_with(
            "e1", max_depth=1, max_nodes=3, scopes=None,
        )


class TestScopesPassthrough:
    """scopes parameter passed to both vector search and graph operations."""

    def test_scopes_forwarded(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
        )
        mock_vector_store.search_similar.return_value = [("c1", 0.9)]
        seed = _entity("e1", "Seed", chunk_id="c1")
        mock_graph_store.list_entities.return_value = [seed]
        mock_graph_store.get_neighbors.return_value = []

        retriever.retrieve("query", scopes=["project-x"])

        # Vector search got scopes.
        vs_call = mock_vector_store.search_similar.call_args
        assert vs_call.kwargs.get("scopes") == ["project-x"]

        # list_entities got scopes.
        mock_graph_store.list_entities.assert_called_once_with(scopes=["project-x"])

        # get_neighbors got scopes.
        mock_graph_store.get_neighbors.assert_called_once_with(
            "e1", max_depth=1, max_nodes=10, scopes=["project-x"],
        )


class TestEmbedHybridFallback:
    """Uses embed_hybrid when available, falls back to embed + HybridEmbedding."""

    def test_uses_embed_hybrid(
        self,
        retriever: GraphAugmentedRetriever,
        mock_vector_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        mock_vector_store.search_similar.return_value = []
        retriever.retrieve("query")
        mock_embedding_provider.embed_hybrid.assert_called_once_with(["query"])

    def test_falls_back_to_dense(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
    ) -> None:
        provider = MagicMock(spec=["embed"])  # No embed_hybrid.
        provider.embed = MagicMock(return_value=[_EMBED_VEC])

        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=provider,
        )
        mock_vector_store.search_similar.return_value = []
        retriever.retrieve("query")

        provider.embed.assert_called_once_with(["query"])
        # The search_similar call should receive a HybridEmbedding.
        vs_call = mock_vector_store.search_similar.call_args
        embedding_arg = vs_call.args[0] if vs_call.args else vs_call.kwargs.get("query_embedding")
        assert isinstance(embedding_arg, HybridEmbedding)


class TestMultipleSeedEntities:
    """Multiple chunk_ids resolve to multiple seed entities."""

    def test_multiple_seeds_expanded(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            max_expansion_tokens=2000,
        )
        mock_vector_store.search_similar.return_value = [
            ("c1", 0.95),
            ("c2", 0.85),
        ]
        e1 = _entity("e1", "Alpha", chunk_id="c1")
        e2 = _entity("e2", "Beta", chunk_id="c2")
        mock_graph_store.list_entities.return_value = [e1, e2]

        n1 = _entity("n1", "Gamma", description="Gamma desc")
        n2 = _entity("n2", "Delta", description="Delta desc")
        mock_graph_store.get_neighbors.side_effect = [
            [(n1, _edge("e1", "n1"))],
            [(n2, _edge("e2", "n2"))],
        ]

        result = retriever.retrieve("query")
        assert result.entities_found == 2
        assert "Gamma" in result.expansion_text
        assert "Delta" in result.expansion_text
        assert mock_graph_store.get_neighbors.call_count == 2
