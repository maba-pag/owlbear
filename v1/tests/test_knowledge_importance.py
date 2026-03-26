"""Tests for importance scoring across Entity, EntityExtractor, GraphStore, and retrieval.

RED-phase tests for task #768 / feature #722.
All tests must FAIL until the importance field and weight_by_importance
feature are implemented.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pydantic_ai.models
import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.extractor import EXTRACTION_PROMPT, EntityExtractor, ExtractionResult
from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.protocol import HybridEmbedding
from owlbear.memory.knowledge.retrieval import GraphAugmentedRetriever
from owlbear.memory.knowledge.schema import init_db

# Block real LLM calls.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """In-memory SQLite connection with init_db applied."""
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    return conn


@pytest.fixture
def graph_store(db_conn: sqlite3.Connection) -> GraphStore:
    """GraphStore backed by the in-memory database."""
    return GraphStore(db_conn)


@pytest.fixture
def mock_vector_store() -> MagicMock:
    store = MagicMock()
    store.search_similar = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_graph_store() -> MagicMock:
    store = MagicMock()
    store.list_entities = MagicMock(return_value=[])
    store.get_neighbors = MagicMock(return_value=[])
    return store


@pytest.fixture
def mock_embedding_provider() -> MagicMock:
    provider = MagicMock()
    provider.embed_hybrid = MagicMock(
        return_value=[HybridEmbedding(dense=[0.1, 0.2, 0.3])],
    )
    return provider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(
    entity_id: str,
    name: str,
    *,
    importance: float = 0.5,
    chunk_id: str | None = None,
    description: str = "",
) -> Entity:
    return Entity(
        id=entity_id,
        name=name,
        entity_type=EntityType.CONCEPT,
        description=description,
        chunk_id=chunk_id,
        importance=importance,
    )


def _edge(source_id: str, target_id: str) -> Edge:
    return Edge(
        source_id=source_id,
        target_id=target_id,
        relation=RelationType.RELATED_TO,
    )


# ===========================================================================
# AC 1 — Entity model accepts importance: float, default 0.5, [0.0, 1.0]
# ===========================================================================


class TestFromAC_EntityImportanceField:  # noqa: N801
    """Entity.importance is a float, default 0.5, constrained to [0.0, 1.0]."""

    def test_default_importance_is_half(self) -> None:
        entity = Entity(
            name="thing",
            entity_type=EntityType.CONCEPT,
        )
        assert entity.importance == 0.5

    def test_custom_importance_accepted(self) -> None:
        entity = Entity(
            name="thing",
            entity_type=EntityType.CONCEPT,
            importance=0.9,
        )
        assert entity.importance == 0.9

    def test_importance_zero_allowed(self) -> None:
        entity = Entity(
            name="thing",
            entity_type=EntityType.CONCEPT,
            importance=0.0,
        )
        assert entity.importance == 0.0

    def test_importance_one_allowed(self) -> None:
        entity = Entity(
            name="thing",
            entity_type=EntityType.CONCEPT,
            importance=1.0,
        )
        assert entity.importance == 1.0

    def test_importance_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Entity(
                name="thing",
                entity_type=EntityType.CONCEPT,
                importance=-0.01,
            )

    def test_importance_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Entity(
                name="thing",
                entity_type=EntityType.CONCEPT,
                importance=1.01,
            )

    def test_importance_near_boundaries(self) -> None:
        """Values just inside the valid range are accepted."""
        low = Entity(name="lo", entity_type=EntityType.CONCEPT, importance=0.001)
        high = Entity(name="hi", entity_type=EntityType.CONCEPT, importance=0.999)
        assert low.importance == pytest.approx(0.001)
        assert high.importance == pytest.approx(0.999)


# ===========================================================================
# AC 2 — EntityExtractor.extract() populates importance on entities
# ===========================================================================


class TestFromAC_ExtractorImportance:  # noqa: N801
    """EntityExtractor.extract() returns entities with importance populated."""

    def test_extraction_prompt_mentions_importance(self) -> None:
        """EXTRACTION_PROMPT instructs the LLM to output an importance score."""
        prompt_lower = EXTRACTION_PROMPT.lower()
        assert "importance" in prompt_lower, (
            "EXTRACTION_PROMPT must instruct the LLM to output a 0.0-1.0 "
            "importance score per entity"
        )

    def test_extraction_prompt_specifies_importance_range(self) -> None:
        """EXTRACTION_PROMPT specifies the 0.0-1.0 range for importance."""
        assert "0.0" in EXTRACTION_PROMPT, (
            "EXTRACTION_PROMPT must mention 0.0 lower bound for importance"
        )
        assert "1.0" in EXTRACTION_PROMPT, (
            "EXTRACTION_PROMPT must mention 1.0 upper bound for importance"
        )

    @pytest.mark.asyncio
    async def test_extracted_entities_have_importance(self) -> None:
        """Entities produced by extract() carry a non-None importance value."""
        sample_entity = Entity(
            name="Widget",
            entity_type=EntityType.CLASS_,
            description="A widget class",
            importance=0.7,
        )
        sample_result = ExtractionResult(entities=[sample_entity], edges=[])

        mock_run_result = MagicMock()
        mock_run_result.output = sample_result

        extractor = EntityExtractor(model="test")
        extractor._agent = MagicMock()
        extractor._agent.run = AsyncMock(return_value=mock_run_result)

        result = await extractor.extract("class Widget: pass")

        assert len(result.entities) == 1
        assert hasattr(result.entities[0], "importance")
        assert result.entities[0].importance == 0.7


# ===========================================================================
# AC 3 — GraphStore.insert_entity() round-trips importance
# ===========================================================================


class TestFromAC_GraphStoreImportanceRoundTrip:  # noqa: N801
    """insert_entity / get_entity / list_entities preserve importance."""

    def test_round_trip_via_get(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="imp-001",
            name="important_thing",
            entity_type=EntityType.DECISION,
            importance=0.85,
        )
        graph_store.insert_entity(entity)
        fetched = graph_store.get_entity("imp-001")
        assert fetched is not None
        assert fetched.importance == pytest.approx(0.85)

    def test_round_trip_via_list(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="imp-002",
            name="another_thing",
            entity_type=EntityType.PATTERN,
            importance=0.3,
        )
        graph_store.insert_entity(entity)
        entities = graph_store.list_entities()
        match = [e for e in entities if e.id == "imp-002"]
        assert len(match) == 1
        assert match[0].importance == pytest.approx(0.3)

    def test_default_importance_round_trips(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="imp-003",
            name="default_importance",
            entity_type=EntityType.CONCEPT,
        )
        graph_store.insert_entity(entity)
        fetched = graph_store.get_entity("imp-003")
        assert fetched is not None
        assert fetched.importance == pytest.approx(0.5)

    def test_boundary_values_round_trip(self, graph_store: GraphStore) -> None:
        e_zero = Entity(
            id="imp-lo",
            name="low",
            entity_type=EntityType.FILE,
            importance=0.0,
        )
        e_one = Entity(
            id="imp-hi",
            name="high",
            entity_type=EntityType.FUNCTION,
            importance=1.0,
        )
        graph_store.insert_entity(e_zero)
        graph_store.insert_entity(e_one)

        assert graph_store.get_entity("imp-lo").importance == pytest.approx(0.0)  # type: ignore[union-attr]
        assert graph_store.get_entity("imp-hi").importance == pytest.approx(1.0)  # type: ignore[union-attr]


# ===========================================================================
# AC 4 — _expand() sorts by importance DESC when weight_by_importance=True
# ===========================================================================


class TestFromAC_ExpandSortsByImportance:  # noqa: N801
    """_expand() orders neighbors by importance DESC when weight_by_importance=True."""

    def test_higher_importance_first(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            weight_by_importance=True,
        )

        mock_vector_store.search_similar.return_value = [("c1", 0.9)]

        seed = _entity("seed", "Root", chunk_id="c1")
        mock_graph_store.list_entities.return_value = [seed]

        # Neighbors with varying importance.
        low = _entity("n-lo", "LowImportance", importance=0.2, description="low")
        mid = _entity("n-mid", "MidImportance", importance=0.5, description="mid")
        high = _entity("n-hi", "HighImportance", importance=0.9, description="high")

        # Return in ascending order — retriever should re-sort descending.
        mock_graph_store.get_neighbors.return_value = [
            (low, _edge("seed", "n-lo")),
            (mid, _edge("seed", "n-mid")),
            (high, _edge("seed", "n-hi")),
        ]

        result = retriever.retrieve("query")
        lines = result.expansion_text.strip().split("\n")

        assert len(lines) == 3
        assert "HighImportance" in lines[0]
        assert "MidImportance" in lines[1]
        assert "LowImportance" in lines[2]

    def test_same_importance_stable_order(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Neighbors with equal importance keep their original order."""
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            weight_by_importance=True,
        )

        mock_vector_store.search_similar.return_value = [("c1", 0.9)]

        seed = _entity("seed", "Root", chunk_id="c1")
        mock_graph_store.list_entities.return_value = [seed]

        a = _entity("n-a", "Alpha", importance=0.5, description="alpha")
        b = _entity("n-b", "Beta", importance=0.5, description="beta")

        mock_graph_store.get_neighbors.return_value = [
            (a, _edge("seed", "n-a")),
            (b, _edge("seed", "n-b")),
        ]

        result = retriever.retrieve("query")
        lines = result.expansion_text.strip().split("\n")

        assert "Alpha" in lines[0]
        assert "Beta" in lines[1]


# ===========================================================================
# AC 5 — weight_by_importance=False (default) ignores importance sorting
# ===========================================================================


class TestFromAC_ImportanceIgnoredByDefault:  # noqa: N801
    """Default behavior does not sort by importance."""

    def test_default_weight_by_importance_is_false(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        """Constructor exposes weight_by_importance kwarg that defaults to False."""
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
        )
        # The attribute must exist and default to False.
        assert hasattr(retriever, "_weight_by_importance")
        assert retriever._weight_by_importance is False

    def test_explicit_false_preserves_traversal_order(
        self,
        mock_vector_store: MagicMock,
        mock_graph_store: MagicMock,
        mock_embedding_provider: MagicMock,
    ) -> None:
        retriever = GraphAugmentedRetriever(
            vector_store=mock_vector_store,
            graph_store=mock_graph_store,
            embedding_provider=mock_embedding_provider,
            weight_by_importance=False,
        )

        mock_vector_store.search_similar.return_value = [("c1", 0.9)]

        seed = _entity("seed", "Root", chunk_id="c1")
        mock_graph_store.list_entities.return_value = [seed]

        low = _entity("n-lo", "LowFirst", importance=0.1, description="low")
        high = _entity("n-hi", "HighSecond", importance=0.9, description="high")

        mock_graph_store.get_neighbors.return_value = [
            (low, _edge("seed", "n-lo")),
            (high, _edge("seed", "n-hi")),
        ]

        result = retriever.retrieve("query")
        lines = result.expansion_text.strip().split("\n")

        assert "LowFirst" in lines[0]
        assert "HighSecond" in lines[1]
