"""Failing tests for GraphStore.get_counts() method required by task #55 (AC7).

Covers (TDD RED phase — all tests must FAIL until builder adds get_counts to GraphStore):
  - AC7: GraphStore.get_counts() returns tuple[int, int, int] (doc, entity, edge counts)
  - AC7: Empty database returns (0, 0, 0)
  - AC7: Results match actual data inserted into the graph
  - AC7: Method is O(1) — takes no filter parameters (SQL COUNT, not len(list_*()))

Tests use a real in-memory SQLite database seeded via the GraphStore public API.
"""

from __future__ import annotations

import inspect
import sqlite3

import pytest

from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Document, Edge, Entity, EntityType, RelationType
from owlbear_knowledge.schema import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_graph() -> GraphStore:
    """Return a GraphStore backed by a fresh in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return GraphStore(conn)


@pytest.fixture
def populated_graph() -> GraphStore:
    """Return a GraphStore with 2 documents, 3 entities, and 2 edges inserted."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    gs = GraphStore(conn)

    doc1 = Document(id="d1", title="Doc 1", content="content one", scope="global")
    doc2 = Document(id="d2", title="Doc 2", content="content two", scope="global")
    gs.insert_document(doc1)
    gs.insert_document(doc2)

    ent1 = Entity(
        id="e1",
        name="Alpha",
        entity_type=EntityType.CONCEPT,
        description="First entity",
        document_id="d1",
    )
    ent2 = Entity(
        id="e2",
        name="Beta",
        entity_type=EntityType.FUNCTION,
        description="Second entity",
        document_id="d1",
    )
    ent3 = Entity(
        id="e3",
        name="Gamma",
        entity_type=EntityType.DECISION,
        description="Third entity",
        document_id="d2",
    )
    gs.insert_entity(ent1)
    gs.insert_entity(ent2)
    gs.insert_entity(ent3)

    edge1 = Edge(
        id="edge1",
        source_id="e1",
        target_id="e2",
        relation=RelationType.RELATED_TO,
    )
    edge2 = Edge(
        id="edge2",
        source_id="e2",
        target_id="e3",
        relation=RelationType.DEPENDS_ON,
    )
    gs.insert_edge(edge1)
    gs.insert_edge(edge2)

    return gs


# ---------------------------------------------------------------------------
# TestFromAC_GraphStoreGetCounts
# ---------------------------------------------------------------------------


class TestFromAC_GraphStoreGetCounts:
    """Contract tests for GraphStore.get_counts() derived from AC7."""

    def test_get_counts_returns_tuple(self, empty_graph: GraphStore) -> None:
        """get_counts() returns a tuple."""
        result = empty_graph.get_counts()
        assert isinstance(result, tuple)

    def test_get_counts_returns_three_elements(self, empty_graph: GraphStore) -> None:
        """get_counts() returns a tuple with exactly 3 elements."""
        result = empty_graph.get_counts()
        assert len(result) == 3

    def test_get_counts_all_elements_are_ints(self, empty_graph: GraphStore) -> None:
        """All three elements of the get_counts() tuple are integers."""
        result = empty_graph.get_counts()
        doc_count, entity_count, edge_count = result
        assert isinstance(doc_count, int)
        assert isinstance(entity_count, int)
        assert isinstance(edge_count, int)

    def test_get_counts_empty_db_returns_all_zeros(self, empty_graph: GraphStore) -> None:
        """Empty database: get_counts() returns (0, 0, 0)."""
        doc_count, entity_count, edge_count = empty_graph.get_counts()
        assert doc_count == 0
        assert entity_count == 0
        assert edge_count == 0

    def test_get_counts_reflects_inserted_documents(self, populated_graph: GraphStore) -> None:
        """doc_count matches the number of documents inserted."""
        doc_count, _, _ = populated_graph.get_counts()
        assert doc_count == 2

    def test_get_counts_reflects_inserted_entities(self, populated_graph: GraphStore) -> None:
        """entity_count matches the number of entities inserted."""
        _, entity_count, _ = populated_graph.get_counts()
        assert entity_count == 3

    def test_get_counts_reflects_inserted_edges(self, populated_graph: GraphStore) -> None:
        """edge_count matches the number of edges inserted."""
        _, _, edge_count = populated_graph.get_counts()
        assert edge_count == 2

    def test_get_counts_order_is_doc_entity_edge(self, populated_graph: GraphStore) -> None:
        """Tuple order is (doc_count, entity_count, edge_count) — not reversed."""
        doc_count, entity_count, edge_count = populated_graph.get_counts()
        # With 2 docs, 3 entities, 2 edges — the unique value is entity_count=3
        assert entity_count == 3
        assert doc_count == 2
        assert edge_count == 2

    def test_get_counts_takes_no_filter_parameters(self, empty_graph: GraphStore) -> None:
        """get_counts() is O(1) — accepts no filter parameters (no entity_type, scope, etc)."""
        sig = inspect.signature(empty_graph.get_counts)
        non_self_params = [p for p in sig.parameters.values() if p.name != "self"]
        assert len(non_self_params) == 0, (
            f"get_counts() should take no params (SQL COUNT is O(1)), got: {[p.name for p in non_self_params]}"
        )


class TestFromAC_GraphStoreInsertEdgeDocumentId:
    """GraphStore.insert_edge keeps edge document provenance compatible with the schema."""

    def test_insert_edge_infers_document_id_from_source_entity(self) -> None:
        """insert_edge(edge) stores source entity document_id when no explicit document_id is provided."""
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        graph = GraphStore(conn)
        graph.insert_document(Document(id="d1", title="Doc 1", content="content one"))
        graph.insert_document(Document(id="d2", title="Doc 2", content="content two"))
        graph.insert_entity(Entity(id="e1", name="Alpha", entity_type=EntityType.CONCEPT, document_id="d1"))
        graph.insert_entity(Entity(id="e2", name="Beta", entity_type=EntityType.CONCEPT, document_id="d2"))

        graph.insert_edge(Edge(id="edge-source", source_id="e1", target_id="e2", relation=RelationType.RELATED_TO))

        row = conn.execute("SELECT document_id FROM edges WHERE id = 'edge-source'").fetchone()
        assert row == ("d1",)

    def test_insert_edge_raises_clear_error_when_document_id_unresolved(self) -> None:
        """insert_edge(edge) fails before SQLite when neither endpoint can provide document provenance."""
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        graph = GraphStore(conn)

        with pytest.raises(ValueError, match="edge document_id is required"):
            graph.insert_edge(
                Edge(
                    id="edge-missing",
                    source_id="missing-a",
                    target_id="missing-b",
                    relation=RelationType.RELATED_TO,
                )
            )


class TestFromAC_GraphStoreInsertEntityDocumentId:
    """GraphStore.insert_entity rejects missing document provenance before SQLite."""

    def test_insert_entity_rejects_none_document_id(self) -> None:
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        graph = GraphStore(conn)

        with pytest.raises(ValueError, match="entity document_id is required"):
            graph.insert_entity(Entity(id="entity-none", name="A", entity_type=EntityType.CONCEPT))

    def test_insert_entity_rejects_blank_document_id(self) -> None:
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        graph = GraphStore(conn)

        with pytest.raises(ValueError, match="entity document_id is required"):
            graph.insert_entity(Entity(id="entity-blank", name="A", entity_type=EntityType.CONCEPT, document_id="   "))
