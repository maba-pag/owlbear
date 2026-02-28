"""Tests for owlbear.memory.knowledge.dedup — entity deduplication.

TDD red-phase: tests define the contract for tasks #190 / #178.
"""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.dedup import DeduplicationResult, deduplicate_entities
from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear.memory.knowledge.schema import init_db

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
def graph(db_conn: sqlite3.Connection) -> GraphStore:
    """GraphStore backed by the in-memory database."""
    return GraphStore(db_conn)


# ---------------------------------------------------------------------------
# DeduplicationResult model
# ---------------------------------------------------------------------------


class TestDeduplicationResult:
    """DeduplicationResult is a frozen Pydantic model with expected fields."""

    def test_fields(self) -> None:
        result = DeduplicationResult(merged_count=3, canonical_ids=["a", "b"])
        assert result.merged_count == 3
        assert result.canonical_ids == ["a", "b"]

    def test_frozen(self) -> None:
        result = DeduplicationResult(merged_count=0, canonical_ids=[])
        with pytest.raises(ValidationError):
            result.merged_count = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Near-duplicate detection via SequenceMatcher
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    """deduplicate_entities detects near-duplicate entity names."""

    def test_detects_near_duplicate_names(self, graph: GraphStore) -> None:
        """Two entities with very similar names are merged."""
        e1 = Entity(
            id="e1",
            name="PydanticAI Agent",
            entity_type=EntityType.CONCEPT,
            description="Short desc",
        )
        e2 = Entity(
            id="e2",
            name="Pydantic AI Agent",
            entity_type=EntityType.CONCEPT,
            description="A much longer and more detailed description",
        )
        graph.insert_entity(e1)
        graph.insert_entity(e2)

        result = deduplicate_entities(graph)

        assert result.merged_count == 1
        # Only one entity should remain
        remaining = graph.list_entities()
        assert len(remaining) == 1

    def test_no_merges_when_all_distinct(self, graph: GraphStore) -> None:
        """No merges when all entity names are clearly different."""
        entities = [
            Entity(id="a", name="Alpha", entity_type=EntityType.CONCEPT),
            Entity(id="b", name="Bravo", entity_type=EntityType.CLASS_),
            Entity(id="c", name="Charlie", entity_type=EntityType.FUNCTION),
        ]
        for e in entities:
            graph.insert_entity(e)

        result = deduplicate_entities(graph)

        assert result.merged_count == 0
        assert result.canonical_ids == []
        assert len(graph.list_entities()) == 3


# ---------------------------------------------------------------------------
# Threshold parameter
# ---------------------------------------------------------------------------


class TestThreshold:
    """Threshold parameter controls merge sensitivity."""

    def test_default_threshold_is_085(self, graph: GraphStore) -> None:
        """Default threshold of 0.85 merges very similar names."""
        # "GraphStore" vs "Graph Store" → SequenceMatcher ratio ≈ 0.89
        e1 = Entity(id="e1", name="GraphStore", entity_type=EntityType.CLASS_)
        e2 = Entity(id="e2", name="Graph Store", entity_type=EntityType.CLASS_)
        graph.insert_entity(e1)
        graph.insert_entity(e2)

        result = deduplicate_entities(graph)  # default threshold=0.85

        assert result.merged_count == 1

    def test_high_threshold_prevents_merge(self, graph: GraphStore) -> None:
        """A very high threshold prevents merges of similar-but-not-identical names."""
        e1 = Entity(id="e1", name="GraphStore", entity_type=EntityType.CLASS_)
        e2 = Entity(id="e2", name="Graph Store", entity_type=EntityType.CLASS_)
        graph.insert_entity(e1)
        graph.insert_entity(e2)

        result = deduplicate_entities(graph, threshold=0.99)

        assert result.merged_count == 0
        assert len(graph.list_entities()) == 2

    def test_low_threshold_merges_loosely(self, graph: GraphStore) -> None:
        """A low threshold merges even loosely similar names."""
        e1 = Entity(id="e1", name="data_store", entity_type=EntityType.CONCEPT)
        e2 = Entity(id="e2", name="datastore", entity_type=EntityType.CONCEPT)
        graph.insert_entity(e1)
        graph.insert_entity(e2)

        result = deduplicate_entities(graph, threshold=0.5)

        assert result.merged_count == 1


# ---------------------------------------------------------------------------
# Canonical entity selection
# ---------------------------------------------------------------------------


class TestCanonicalSelection:
    """Canonical entity keeps longer description; tie-break alphabetically first."""

    def test_longer_description_wins(self, graph: GraphStore) -> None:
        """The entity with the longer description becomes canonical."""
        e1 = Entity(
            id="short",
            name="PydanticAI Agent",
            entity_type=EntityType.CONCEPT,
            description="Brief.",
        )
        e2 = Entity(
            id="long",
            name="Pydantic AI Agent",
            entity_type=EntityType.CONCEPT,
            description="A comprehensive description of the PydanticAI agent pattern.",
        )
        graph.insert_entity(e1)
        graph.insert_entity(e2)

        result = deduplicate_entities(graph)

        assert result.merged_count == 1
        assert result.canonical_ids == ["long"]
        remaining = graph.list_entities()
        assert len(remaining) == 1
        assert remaining[0].id == "long"

    def test_tie_break_alphabetically_first(self, graph: GraphStore) -> None:
        """When descriptions are same length, alphabetically first name wins."""
        e1 = Entity(
            id="e1",
            name="Bravo_handler",
            entity_type=EntityType.FUNCTION,
            description="Same length!",
        )
        e2 = Entity(
            id="e2",
            name="Bravo handler",
            entity_type=EntityType.FUNCTION,
            description="Same length!",
        )
        graph.insert_entity(e1)
        graph.insert_entity(e2)

        result = deduplicate_entities(graph)

        assert result.merged_count == 1
        # "Bravo handler" < "Bravo_handler" alphabetically
        remaining = graph.list_entities()
        assert len(remaining) == 1
        assert remaining[0].name == "Bravo handler"


# ---------------------------------------------------------------------------
# Metadata merging
# ---------------------------------------------------------------------------


class TestMetadataMerge:
    """Metadata dicts are merged; canonical wins on key conflicts."""

    def test_metadata_merged(self, graph: GraphStore) -> None:
        """Non-conflicting metadata keys from both entities are kept."""
        e1 = Entity(
            id="e1",
            name="PydanticAI Agent",
            entity_type=EntityType.CONCEPT,
            description="A longer description for canonical selection.",
            metadata={"source": "docs", "version": 2},
        )
        e2 = Entity(
            id="e2",
            name="Pydantic AI Agent",
            entity_type=EntityType.CONCEPT,
            description="Short.",
            metadata={"author": "alice", "draft": True},
        )
        graph.insert_entity(e1)
        graph.insert_entity(e2)

        deduplicate_entities(graph)

        remaining = graph.list_entities()
        assert len(remaining) == 1
        meta = remaining[0].metadata
        # All keys present
        assert meta["source"] == "docs"
        assert meta["version"] == 2
        assert meta["author"] == "alice"
        assert meta["draft"] is True

    def test_canonical_wins_on_conflict(self, graph: GraphStore) -> None:
        """On key conflicts, canonical entity's value is kept."""
        e1 = Entity(
            id="e1",
            name="PydanticAI Agent",
            entity_type=EntityType.CONCEPT,
            description="Canonical — this description is longer.",
            metadata={"source": "research", "priority": "high"},
        )
        e2 = Entity(
            id="e2",
            name="Pydantic AI Agent",
            entity_type=EntityType.CONCEPT,
            description="Dup.",
            metadata={"source": "unknown", "extra": "data"},
        )
        graph.insert_entity(e1)
        graph.insert_entity(e2)

        deduplicate_entities(graph)

        remaining = graph.list_entities()
        meta = remaining[0].metadata
        assert meta["source"] == "research"  # canonical wins
        assert meta["priority"] == "high"
        assert meta["extra"] == "data"  # from duplicate


# ---------------------------------------------------------------------------
# Edge redirection
# ---------------------------------------------------------------------------


class TestEdgeRedirection:
    """All edges referencing duplicate entity are updated to canonical."""

    def test_source_edges_redirected(self, graph: GraphStore) -> None:
        """Edge with source_id pointing to duplicate is redirected to canonical."""
        canonical = Entity(
            id="canon",
            name="PydanticAI Agent",
            entity_type=EntityType.CONCEPT,
            description="Canonical entity with a longer description.",
        )
        duplicate = Entity(
            id="dup",
            name="Pydantic AI Agent",
            entity_type=EntityType.CONCEPT,
            description="Short.",
        )
        target = Entity(id="target", name="Unrelated", entity_type=EntityType.FILE)
        graph.insert_entity(canonical)
        graph.insert_entity(duplicate)
        graph.insert_entity(target)

        edge = Edge(
            id="edge1",
            source_id="dup",
            target_id="target",
            relation=RelationType.RELATED_TO,
        )
        graph.insert_edge(edge)

        deduplicate_entities(graph)

        # Edge should now point to canonical
        updated = graph.get_edge("edge1")
        assert updated is not None
        assert updated.source_id == "canon"
        assert updated.target_id == "target"

    def test_target_edges_redirected(self, graph: GraphStore) -> None:
        """Edge with target_id pointing to duplicate is redirected to canonical."""
        canonical = Entity(
            id="canon",
            name="PydanticAI Agent",
            entity_type=EntityType.CONCEPT,
            description="Canonical — this description is longer.",
        )
        duplicate = Entity(
            id="dup",
            name="Pydantic AI Agent",
            entity_type=EntityType.CONCEPT,
            description="Dup.",
        )
        source = Entity(id="src", name="Unrelated", entity_type=EntityType.FILE)
        graph.insert_entity(canonical)
        graph.insert_entity(duplicate)
        graph.insert_entity(source)

        edge = Edge(
            id="edge2",
            source_id="src",
            target_id="dup",
            relation=RelationType.DEPENDS_ON,
        )
        graph.insert_edge(edge)

        deduplicate_entities(graph)

        updated = graph.get_edge("edge2")
        assert updated is not None
        assert updated.source_id == "src"
        assert updated.target_id == "canon"

    def test_both_ends_redirected(self, graph: GraphStore) -> None:
        """Edge between two duplicates of same group: both ends redirect to canonical."""
        canonical = Entity(
            id="canon",
            name="PydanticAI Agent",
            entity_type=EntityType.CONCEPT,
            description="Canonical with the longest description of them all.",
        )
        dup1 = Entity(
            id="dup1",
            name="Pydantic AI Agent",
            entity_type=EntityType.CONCEPT,
            description="Dup 1",
        )
        dup2 = Entity(
            id="dup2",
            name="PydanticAi Agent",
            entity_type=EntityType.CONCEPT,
            description="Dup 2",
        )
        graph.insert_entity(canonical)
        graph.insert_entity(dup1)
        graph.insert_entity(dup2)

        edge = Edge(
            id="self_edge",
            source_id="dup1",
            target_id="dup2",
            relation=RelationType.RELATED_TO,
        )
        graph.insert_edge(edge)

        deduplicate_entities(graph)

        updated = graph.get_edge("self_edge")
        assert updated is not None
        assert updated.source_id == "canon"
        assert updated.target_id == "canon"


# ---------------------------------------------------------------------------
# Works on existing GraphStore data (integration)
# ---------------------------------------------------------------------------


class TestIntegration:
    """Full integration: entities + edges + dedup on a populated graph."""

    def test_multi_group_dedup(self, graph: GraphStore) -> None:
        """Multiple independent duplicate groups are each handled correctly."""
        # Group 1: PydanticAI variants
        g1a = Entity(
            id="g1a",
            name="PydanticAI Agent",
            entity_type=EntityType.CONCEPT,
            description="The PydanticAI agent pattern for structured output.",
        )
        g1b = Entity(
            id="g1b",
            name="Pydantic AI Agent",
            entity_type=EntityType.CONCEPT,
            description="Short.",
        )
        # Group 2: GraphStore variants
        g2a = Entity(
            id="g2a",
            name="GraphStore",
            entity_type=EntityType.CLASS_,
            description="CRUD façade for knowledge graph.",
        )
        g2b = Entity(
            id="g2b",
            name="Graph Store",
            entity_type=EntityType.CLASS_,
            description="A comprehensive data access layer for the knowledge graph database.",
        )
        # Standalone entity (no duplicates)
        solo = Entity(id="solo", name="Unrelated", entity_type=EntityType.FILE)

        for e in [g1a, g1b, g2a, g2b, solo]:
            graph.insert_entity(e)

        # Edges crossing groups
        edge1 = Edge(id="e1", source_id="g1b", target_id="g2a", relation=RelationType.DEPENDS_ON)
        edge2 = Edge(id="e2", source_id="solo", target_id="g2b", relation=RelationType.RELATED_TO)
        graph.insert_edge(edge1)
        graph.insert_edge(edge2)

        result = deduplicate_entities(graph)

        assert result.merged_count == 2  # two groups, each merged one duplicate
        assert len(graph.list_entities()) == 3  # g1 canonical, g2 canonical, solo

        # Verify edge1: source was g1b (dup) → g1a (canonical), target was g2a
        e1 = graph.get_edge("e1")
        assert e1 is not None
        assert e1.source_id == "g1a"  # g1a has longer desc → canonical

        # Verify edge2: target was g2b (canonical for group 2 since longer desc)
        e2 = graph.get_edge("e2")
        assert e2 is not None
        assert e2.target_id == "g2b"  # g2b has longer desc → canonical

    def test_empty_graph(self, graph: GraphStore) -> None:
        """Dedup on empty graph returns zero merges."""
        result = deduplicate_entities(graph)
        assert result.merged_count == 0
        assert result.canonical_ids == []

    def test_single_entity(self, graph: GraphStore) -> None:
        """Single entity — nothing to deduplicate."""
        graph.insert_entity(Entity(id="only", name="OnlyOne", entity_type=EntityType.CONCEPT))

        result = deduplicate_entities(graph)

        assert result.merged_count == 0
        assert result.canonical_ids == []
        assert len(graph.list_entities()) == 1
