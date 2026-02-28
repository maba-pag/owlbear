"""Tests for document_id provenance in Entity, GraphStore, and IngestPipeline.

AC from task #283:
- Entity model gains optional document_id: str | None = None
- GraphStore.insert_entity() accepts and stores document_id column
- GraphStore.list_entities_for_document(doc_id, scopes) -> list[Entity]
- IngestPipeline._store_extractions() passes document_id when inserting entities
- Tests: inserted entity has document_id,
  list_entities_for_document returns correct set, scope filtering works
"""

from __future__ import annotations

import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.memory.knowledge.extractor import ExtractionResult
from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.ingest import IngestPipeline
from owlbear.memory.knowledge.models import (
    Edge,
    Entity,
    EntityType,
    RelationType,
)
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    """In-memory SQLite database with knowledge schema."""
    c = sqlite3.Connection(":memory:")
    init_db(c)
    return c


@pytest.fixture
def graph_store(conn: sqlite3.Connection) -> GraphStore:
    """GraphStore backed by the in-memory database."""
    return GraphStore(conn)


# ---------------------------------------------------------------------------
# Entity model — document_id field
# ---------------------------------------------------------------------------


class TestEntityDocumentIdField:
    """Entity model gains optional document_id: str | None = None."""

    def test_entity_default_document_id_is_none(self) -> None:
        entity = Entity(name="foo", entity_type=EntityType.FUNCTION)
        assert entity.document_id is None

    def test_entity_accepts_document_id(self) -> None:
        entity = Entity(
            name="foo",
            entity_type=EntityType.FUNCTION,
            document_id="doc-abc",
        )
        assert entity.document_id == "doc-abc"


# ---------------------------------------------------------------------------
# GraphStore.insert_entity — stores document_id
# ---------------------------------------------------------------------------


class TestInsertEntityDocumentId:
    """GraphStore.insert_entity() accepts and stores document_id column."""

    def test_insert_entity_with_document_id_roundtrip(
        self, graph_store: GraphStore
    ) -> None:
        entity = Entity(
            id="ent-100",
            name="my_func",
            entity_type=EntityType.FUNCTION,
            description="A function",
            document_id="doc-42",
        )
        graph_store.insert_entity(entity)
        result = graph_store.get_entity("ent-100")

        assert result is not None
        assert result.document_id == "doc-42"

    def test_insert_entity_without_document_id_stores_none(
        self, graph_store: GraphStore
    ) -> None:
        entity = Entity(
            id="ent-101",
            name="my_class",
            entity_type=EntityType.CLASS_,
        )
        graph_store.insert_entity(entity)
        result = graph_store.get_entity("ent-101")

        assert result is not None
        assert result.document_id is None

    def test_list_entities_includes_document_id(
        self, graph_store: GraphStore
    ) -> None:
        e1 = Entity(
            id="e1", name="a", entity_type=EntityType.FILE, document_id="doc-1"
        )
        e2 = Entity(
            id="e2", name="b", entity_type=EntityType.FUNCTION, document_id="doc-2"
        )
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        result = graph_store.list_entities()
        doc_ids = {e.id: e.document_id for e in result}
        assert doc_ids == {"e1": "doc-1", "e2": "doc-2"}


# ---------------------------------------------------------------------------
# GraphStore.list_entities_for_document
# ---------------------------------------------------------------------------


class TestListEntitiesForDocument:
    """GraphStore.list_entities_for_document(doc_id, scopes) -> list[Entity]."""

    def test_returns_entities_for_given_document(
        self, graph_store: GraphStore
    ) -> None:
        e1 = Entity(
            id="e1", name="a", entity_type=EntityType.FILE, document_id="doc-A"
        )
        e2 = Entity(
            id="e2", name="b", entity_type=EntityType.FUNCTION, document_id="doc-A"
        )
        e3 = Entity(
            id="e3", name="c", entity_type=EntityType.CONCEPT, document_id="doc-B"
        )
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)
        graph_store.insert_entity(e3)

        result = graph_store.list_entities_for_document("doc-A")
        ids = {e.id for e in result}
        assert ids == {"e1", "e2"}

    def test_returns_empty_for_unknown_document(
        self, graph_store: GraphStore
    ) -> None:
        e1 = Entity(
            id="e1", name="a", entity_type=EntityType.FILE, document_id="doc-A"
        )
        graph_store.insert_entity(e1)

        result = graph_store.list_entities_for_document("doc-UNKNOWN")
        assert result == []

    def test_scope_filtering(self, graph_store: GraphStore) -> None:
        """Only entities matching both doc_id AND scope are returned."""
        e1 = Entity(
            id="e1",
            name="a",
            entity_type=EntityType.FILE,
            document_id="doc-A",
            scope="project-x",
        )
        e2 = Entity(
            id="e2",
            name="b",
            entity_type=EntityType.FUNCTION,
            document_id="doc-A",
            scope="global",
        )
        e3 = Entity(
            id="e3",
            name="c",
            entity_type=EntityType.CONCEPT,
            document_id="doc-A",
            scope="project-y",
        )
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)
        graph_store.insert_entity(e3)

        result = graph_store.list_entities_for_document(
            "doc-A", scopes=["project-x", "global"]
        )
        ids = {e.id for e in result}
        assert ids == {"e1", "e2"}

    def test_scope_none_returns_all_scopes(
        self, graph_store: GraphStore
    ) -> None:
        """scopes=None (default) returns all entities for the document."""
        e1 = Entity(
            id="e1",
            name="a",
            entity_type=EntityType.FILE,
            document_id="doc-A",
            scope="project-x",
        )
        e2 = Entity(
            id="e2",
            name="b",
            entity_type=EntityType.FUNCTION,
            document_id="doc-A",
            scope="global",
        )
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        result = graph_store.list_entities_for_document("doc-A")
        assert len(result) == 2

    def test_empty_scopes_returns_empty(
        self, graph_store: GraphStore
    ) -> None:
        """scopes=[] is a valid edge case — returns nothing."""
        e1 = Entity(
            id="e1",
            name="a",
            entity_type=EntityType.FILE,
            document_id="doc-A",
        )
        graph_store.insert_entity(e1)

        result = graph_store.list_entities_for_document("doc-A", scopes=[])
        assert result == []


# ---------------------------------------------------------------------------
# IngestPipeline._store_extractions — passes document_id
# ---------------------------------------------------------------------------


class TestStoreExtractionsDocumentId:
    """IngestPipeline._store_extractions() passes document_id to entities."""

    @pytest.fixture
    def pipeline(self, conn: sqlite3.Connection) -> IngestPipeline:
        """IngestPipeline with mock dependencies."""
        mock_graph = MagicMock()
        mock_vector = MagicMock()
        mock_embedder = MagicMock()
        mock_extractor = AsyncMock()
        mock_chunker = MagicMock()
        return IngestPipeline(
            conn=conn,
            graph_store=mock_graph,
            vector_store=mock_vector,
            embedding_provider=mock_embedder,
            entity_extractor=mock_extractor,
            text_chunker=mock_chunker,
        )

    def test_store_extractions_stamps_document_id(
        self, pipeline: IngestPipeline
    ) -> None:
        """Entities are stamped with document_id during _store_extractions."""
        entities = [
            Entity(name="func_a", entity_type=EntityType.FUNCTION, description="A"),
            Entity(name="func_b", entity_type=EntityType.FUNCTION, description="B"),
        ]
        edges = [
            Edge(source_id="s1", target_id="t1", relation=RelationType.DEFINES),
        ]
        extractions = [ExtractionResult(entities=entities, edges=edges)]

        entity_count, edge_count = pipeline._store_extractions(
            extractions, scope="global", document_id="doc-XYZ"
        )

        assert entity_count == 2
        assert edge_count == 1

        # Verify insert_entity was called with entities that have document_id set.
        calls = pipeline._graph.insert_entity.call_args_list
        for call in calls:
            inserted_entity = call[0][0]
            assert inserted_entity.document_id == "doc-XYZ"

    def test_store_extractions_without_document_id(
        self, pipeline: IngestPipeline
    ) -> None:
        """When document_id is not provided, entities keep their original document_id (None)."""
        entities = [
            Entity(name="func_c", entity_type=EntityType.FUNCTION),
        ]
        extractions = [ExtractionResult(entities=entities, edges=[])]

        entity_count, _edge_count = pipeline._store_extractions(
            extractions, scope="global"
        )

        assert entity_count == 1
        calls = pipeline._graph.insert_entity.call_args_list
        inserted = calls[0][0][0]
        assert inserted.document_id is None
