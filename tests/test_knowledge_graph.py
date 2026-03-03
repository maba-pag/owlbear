"""Tests for owlbear.memory.knowledge.graph — GraphStore CRUD operations.

TDD red-phase: these tests define the contract for task #109.
All imports from owlbear.memory.knowledge.graph will fail until
that module is implemented.
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear.memory.knowledge.graph import GraphStore
from owlbear.memory.knowledge.models import (
    Document,
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
def db_conn() -> sqlite3.Connection:
    """In-memory SQLite connection with init_db applied."""
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    return conn


@pytest.fixture
def graph_store(db_conn: sqlite3.Connection) -> GraphStore:
    """GraphStore backed by the in-memory database."""
    return GraphStore(db_conn)


# ---------------------------------------------------------------------------
# Entity operations
# ---------------------------------------------------------------------------


class TestInsertAndGetEntity:
    """insert_entity + get_entity round-trip."""

    def test_round_trip(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="ent-001",
            name="my_func",
            entity_type=EntityType.FUNCTION,
            description="A helper function",
            metadata={"lang": "python"},
        )
        graph_store.insert_entity(entity)
        result = graph_store.get_entity("ent-001")

        assert result is not None
        assert result.id == entity.id
        assert result.name == entity.name
        assert result.entity_type == entity.entity_type
        assert result.description == entity.description
        assert result.metadata == entity.metadata

    def test_get_entity_nonexistent_returns_none(self, graph_store: GraphStore) -> None:
        assert graph_store.get_entity("does-not-exist") is None

    def test_insert_duplicate_id_raises(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="dup-001",
            name="first",
            entity_type=EntityType.FILE,
        )
        graph_store.insert_entity(entity)
        duplicate = Entity(
            id="dup-001",
            name="second",
            entity_type=EntityType.CLASS_,
        )
        with pytest.raises(sqlite3.IntegrityError):
            graph_store.insert_entity(duplicate)


class TestListEntities:
    """list_entities returns all or filters by entity_type."""

    def test_list_all(self, graph_store: GraphStore) -> None:
        e1 = Entity(id="e1", name="a", entity_type=EntityType.FILE)
        e2 = Entity(id="e2", name="b", entity_type=EntityType.FUNCTION)
        e3 = Entity(id="e3", name="c", entity_type=EntityType.CONCEPT)
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)
        graph_store.insert_entity(e3)

        result = graph_store.list_entities()
        assert len(result) == 3
        ids = {e.id for e in result}
        assert ids == {"e1", "e2", "e3"}

    def test_filter_by_type(self, graph_store: GraphStore) -> None:
        e1 = Entity(id="e1", name="a", entity_type=EntityType.FILE)
        e2 = Entity(id="e2", name="b", entity_type=EntityType.FUNCTION)
        e3 = Entity(id="e3", name="c", entity_type=EntityType.FILE)
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)
        graph_store.insert_entity(e3)

        result = graph_store.list_entities(entity_type=EntityType.FILE)
        assert len(result) == 2
        assert all(e.entity_type == EntityType.FILE for e in result)

    def test_filter_returns_empty_for_absent_type(self, graph_store: GraphStore) -> None:
        e1 = Entity(id="e1", name="a", entity_type=EntityType.FILE)
        graph_store.insert_entity(e1)

        result = graph_store.list_entities(entity_type=EntityType.DECISION)
        assert result == []


class TestDeleteEntity:
    """delete_entity removes entity and cascades to edges."""

    def test_delete_existing_returns_true(self, graph_store: GraphStore) -> None:
        entity = Entity(id="del-001", name="x", entity_type=EntityType.FILE)
        graph_store.insert_entity(entity)

        assert graph_store.delete_entity("del-001") is True
        assert graph_store.get_entity("del-001") is None

    def test_delete_nonexistent_returns_false(self, graph_store: GraphStore) -> None:
        assert graph_store.delete_entity("no-such-id") is False

    def test_delete_cascades_edges(self, graph_store: GraphStore) -> None:
        e1 = Entity(id="src", name="source", entity_type=EntityType.FILE)
        e2 = Entity(id="tgt", name="target", entity_type=EntityType.FUNCTION)
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        edge = Edge(
            id="edge-1",
            source_id="src",
            target_id="tgt",
            relation=RelationType.DEFINES,
        )
        graph_store.insert_edge(edge)

        # Deleting source entity should cascade-remove the edge.
        graph_store.delete_entity("src")
        assert graph_store.get_edge("edge-1") is None


# ---------------------------------------------------------------------------
# Edge operations
# ---------------------------------------------------------------------------


class TestInsertAndGetEdge:
    """insert_edge + get_edge round-trip."""

    def test_round_trip(self, graph_store: GraphStore) -> None:
        e1 = Entity(id="src", name="source", entity_type=EntityType.FILE)
        e2 = Entity(id="tgt", name="target", entity_type=EntityType.FUNCTION)
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        edge = Edge(
            id="edge-1",
            source_id="src",
            target_id="tgt",
            relation=RelationType.IMPORTS,
            weight=0.8,
            metadata={"note": "direct"},
        )
        graph_store.insert_edge(edge)
        result = graph_store.get_edge("edge-1")

        assert result is not None
        assert result.id == edge.id
        assert result.source_id == edge.source_id
        assert result.target_id == edge.target_id
        assert result.relation == edge.relation
        assert result.weight == edge.weight
        assert result.metadata == edge.metadata

    def test_insert_edge_missing_source_raises(self, graph_store: GraphStore) -> None:
        tgt = Entity(id="tgt", name="target", entity_type=EntityType.FILE)
        graph_store.insert_entity(tgt)

        edge = Edge(
            id="bad-edge",
            source_id="nonexistent",
            target_id="tgt",
            relation=RelationType.DEPENDS_ON,
        )
        with pytest.raises(sqlite3.IntegrityError):
            graph_store.insert_edge(edge)

    def test_insert_edge_missing_target_raises(self, graph_store: GraphStore) -> None:
        src = Entity(id="src", name="source", entity_type=EntityType.FILE)
        graph_store.insert_entity(src)

        edge = Edge(
            id="bad-edge",
            source_id="src",
            target_id="nonexistent",
            relation=RelationType.DEPENDS_ON,
        )
        with pytest.raises(sqlite3.IntegrityError):
            graph_store.insert_edge(edge)


class TestListEdges:
    """list_edges with optional source_id / target_id filters."""

    @pytest.fixture(autouse=True)
    def _seed_graph(self, graph_store: GraphStore) -> None:
        """Insert a small graph for edge listing tests."""
        for eid in ("a", "b", "c"):
            graph_store.insert_entity(Entity(id=eid, name=eid, entity_type=EntityType.CONCEPT))
        graph_store.insert_edge(
            Edge(id="ab", source_id="a", target_id="b", relation=RelationType.RELATED_TO)
        )
        graph_store.insert_edge(
            Edge(id="ac", source_id="a", target_id="c", relation=RelationType.DEFINES)
        )
        graph_store.insert_edge(
            Edge(id="bc", source_id="b", target_id="c", relation=RelationType.IMPORTS)
        )

    def test_list_all_edges(self, graph_store: GraphStore) -> None:
        result = graph_store.list_edges()
        assert len(result) == 3

    def test_filter_by_source(self, graph_store: GraphStore) -> None:
        result = graph_store.list_edges(source_id="a")
        assert len(result) == 2
        assert all(e.source_id == "a" for e in result)

    def test_filter_by_target(self, graph_store: GraphStore) -> None:
        result = graph_store.list_edges(target_id="c")
        assert len(result) == 2
        assert all(e.target_id == "c" for e in result)

    def test_filter_by_both(self, graph_store: GraphStore) -> None:
        result = graph_store.list_edges(source_id="a", target_id="c")
        assert len(result) == 1
        assert result[0].id == "ac"


class TestDeleteEdge:
    """delete_edge returns True/False correctly."""

    def test_delete_existing_returns_true(self, graph_store: GraphStore) -> None:
        e1 = Entity(id="src", name="s", entity_type=EntityType.FILE)
        e2 = Entity(id="tgt", name="t", entity_type=EntityType.FILE)
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        edge = Edge(
            id="edge-del",
            source_id="src",
            target_id="tgt",
            relation=RelationType.DEFINES,
        )
        graph_store.insert_edge(edge)

        assert graph_store.delete_edge("edge-del") is True
        assert graph_store.get_edge("edge-del") is None

    def test_delete_nonexistent_returns_false(self, graph_store: GraphStore) -> None:
        assert graph_store.delete_edge("no-such-edge") is False


# ---------------------------------------------------------------------------
# Document operations
# ---------------------------------------------------------------------------


class TestInsertAndGetDocument:
    """insert_document + get_document round-trip."""

    def test_round_trip(self, graph_store: GraphStore) -> None:
        doc = Document(
            id="doc-001",
            title="README",
            content="Hello, world!",
            metadata={"format": "markdown"},
        )
        graph_store.insert_document(doc)
        result = graph_store.get_document("doc-001")

        assert result is not None
        assert result.id == doc.id
        assert result.title == doc.title
        assert result.content == doc.content
        assert result.metadata == doc.metadata

    def test_get_document_nonexistent_returns_none(self, graph_store: GraphStore) -> None:
        assert graph_store.get_document("nope") is None

    def test_insert_duplicate_document_raises(self, graph_store: GraphStore) -> None:
        doc = Document(id="doc-dup", title="A", content="B")
        graph_store.insert_document(doc)
        with pytest.raises(sqlite3.IntegrityError):
            graph_store.insert_document(Document(id="doc-dup", title="C", content="D"))


class TestListDocuments:
    """list_documents returns all documents."""

    def test_list_all(self, graph_store: GraphStore) -> None:
        d1 = Document(id="d1", title="T1", content="C1")
        d2 = Document(id="d2", title="T2", content="C2")
        graph_store.insert_document(d1)
        graph_store.insert_document(d2)

        result = graph_store.list_documents()
        assert len(result) == 2
        ids = {d.id for d in result}
        assert ids == {"d1", "d2"}

    def test_list_documents_empty(self, graph_store: GraphStore) -> None:
        assert graph_store.list_documents() == []


class TestDeleteDocument:
    """delete_document returns True/False correctly."""

    def test_delete_existing_returns_true(self, graph_store: GraphStore) -> None:
        doc = Document(id="del-doc", title="T", content="C")
        graph_store.insert_document(doc)

        assert graph_store.delete_document("del-doc") is True
        assert graph_store.get_document("del-doc") is None

    def test_delete_nonexistent_returns_false(self, graph_store: GraphStore) -> None:
        assert graph_store.delete_document("nope") is False


# ---------------------------------------------------------------------------
# Scoped queries (#221 / #202)
# ---------------------------------------------------------------------------


class TestEntityScopeInsertAndGet:
    """insert_entity persists scope; get_entity round-trips it."""

    def test_insert_entity_persists_scope(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="scoped-ent",
            name="my_func",
            entity_type=EntityType.FUNCTION,
            scope="project:owlbear",
        )
        graph_store.insert_entity(entity)
        result = graph_store.get_entity("scoped-ent")
        assert result is not None
        assert result.scope == "project:owlbear"

    def test_default_scope_is_global(self, graph_store: GraphStore) -> None:
        entity = Entity(id="default-scope", name="x", entity_type=EntityType.FILE)
        graph_store.insert_entity(entity)
        result = graph_store.get_entity("default-scope")
        assert result is not None
        assert result.scope == "global"


class TestListEntitiesScoped:
    """list_entities with scopes parameter."""

    @pytest.fixture(autouse=True)
    def _seed(self, graph_store: GraphStore) -> None:
        graph_store.insert_entity(
            Entity(id="e-g", name="g", entity_type=EntityType.FILE, scope="global")
        )
        graph_store.insert_entity(
            Entity(id="e-p", name="p", entity_type=EntityType.FILE, scope="project:owlbear")
        )
        graph_store.insert_entity(
            Entity(id="e-a", name="a", entity_type=EntityType.FUNCTION, scope="agent:builder")
        )

    def test_scopes_filter_returns_matching(self, graph_store: GraphStore) -> None:
        result = graph_store.list_entities(scopes=["global", "project:owlbear"])
        ids = {e.id for e in result}
        assert ids == {"e-g", "e-p"}

    def test_scopes_none_returns_all(self, graph_store: GraphStore) -> None:
        result = graph_store.list_entities(scopes=None)
        assert len(result) == 3

    def test_scopes_empty_list_returns_none(self, graph_store: GraphStore) -> None:
        result = graph_store.list_entities(scopes=[])
        assert result == []

    def test_scopes_combined_with_entity_type(self, graph_store: GraphStore) -> None:
        result = graph_store.list_entities(entity_type=EntityType.FILE, scopes=["project:owlbear"])
        assert len(result) == 1
        assert result[0].id == "e-p"


class TestEdgeScopeInsertAndGet:
    """insert_edge persists scope; get_edge round-trips it."""

    @pytest.fixture(autouse=True)
    def _seed_entities(self, graph_store: GraphStore) -> None:
        graph_store.insert_entity(Entity(id="src", name="s", entity_type=EntityType.FILE))
        graph_store.insert_entity(Entity(id="tgt", name="t", entity_type=EntityType.FILE))

    def test_insert_edge_persists_scope(self, graph_store: GraphStore) -> None:
        edge = Edge(
            id="scoped-edge",
            source_id="src",
            target_id="tgt",
            relation=RelationType.DEFINES,
            scope="agent:builder",
        )
        graph_store.insert_edge(edge)
        result = graph_store.get_edge("scoped-edge")
        assert result is not None
        assert result.scope == "agent:builder"

    def test_default_edge_scope_is_global(self, graph_store: GraphStore) -> None:
        edge = Edge(
            id="def-edge",
            source_id="src",
            target_id="tgt",
            relation=RelationType.IMPORTS,
        )
        graph_store.insert_edge(edge)
        result = graph_store.get_edge("def-edge")
        assert result is not None
        assert result.scope == "global"


class TestListEdgesScoped:
    """list_edges with scopes parameter."""

    @pytest.fixture(autouse=True)
    def _seed(self, graph_store: GraphStore) -> None:
        for eid in ("a", "b", "c"):
            graph_store.insert_entity(Entity(id=eid, name=eid, entity_type=EntityType.CONCEPT))
        graph_store.insert_edge(
            Edge(
                id="ab",
                source_id="a",
                target_id="b",
                relation=RelationType.RELATED_TO,
                scope="global",
            )
        )
        graph_store.insert_edge(
            Edge(
                id="ac",
                source_id="a",
                target_id="c",
                relation=RelationType.DEFINES,
                scope="project:owlbear",
            )
        )
        graph_store.insert_edge(
            Edge(
                id="bc",
                source_id="b",
                target_id="c",
                relation=RelationType.IMPORTS,
                scope="agent:builder",
            )
        )

    def test_scopes_filter(self, graph_store: GraphStore) -> None:
        result = graph_store.list_edges(scopes=["global"])
        assert len(result) == 1
        assert result[0].id == "ab"

    def test_scopes_none_returns_all(self, graph_store: GraphStore) -> None:
        result = graph_store.list_edges(scopes=None)
        assert len(result) == 3

    def test_scopes_empty_list_returns_none(self, graph_store: GraphStore) -> None:
        result = graph_store.list_edges(scopes=[])
        assert result == []

    def test_scopes_combined_with_source(self, graph_store: GraphStore) -> None:
        result = graph_store.list_edges(source_id="a", scopes=["project:owlbear"])
        assert len(result) == 1
        assert result[0].id == "ac"


class TestDocumentScopeInsertAndGet:
    """insert_document persists scope; get_document round-trips it."""

    def test_insert_document_persists_scope(self, graph_store: GraphStore) -> None:
        doc = Document(
            id="scoped-doc",
            title="Scoped",
            content="Hello",
            scope="project:foo",
        )
        graph_store.insert_document(doc)
        result = graph_store.get_document("scoped-doc")
        assert result is not None
        assert result.scope == "project:foo"

    def test_default_document_scope_is_global(self, graph_store: GraphStore) -> None:
        doc = Document(id="def-doc", title="T", content="C")
        graph_store.insert_document(doc)
        result = graph_store.get_document("def-doc")
        assert result is not None
        assert result.scope == "global"


class TestListDocumentsScoped:
    """list_documents with scopes parameter."""

    @pytest.fixture(autouse=True)
    def _seed(self, graph_store: GraphStore) -> None:
        graph_store.insert_document(Document(id="d-g", title="G", content="global", scope="global"))
        graph_store.insert_document(
            Document(id="d-p", title="P", content="project", scope="project:foo")
        )
        graph_store.insert_document(
            Document(id="d-a", title="A", content="agent", scope="agent:builder")
        )

    def test_scopes_filter(self, graph_store: GraphStore) -> None:
        result = graph_store.list_documents(scopes=["global"])
        assert len(result) == 1
        assert result[0].id == "d-g"

    def test_scopes_none_returns_all(self, graph_store: GraphStore) -> None:
        result = graph_store.list_documents(scopes=None)
        assert len(result) == 3

    def test_scopes_empty_list_returns_none(self, graph_store: GraphStore) -> None:
        result = graph_store.list_documents(scopes=[])
        assert result == []


class TestDeleteScopedData:
    """delete operations work correctly with scoped data."""

    def test_delete_scoped_entity(self, graph_store: GraphStore) -> None:
        entity = Entity(
            id="del-scoped", name="x", entity_type=EntityType.FILE, scope="project:owlbear"
        )
        graph_store.insert_entity(entity)
        assert graph_store.delete_entity("del-scoped") is True
        assert graph_store.get_entity("del-scoped") is None

    def test_delete_scoped_edge(self, graph_store: GraphStore) -> None:
        graph_store.insert_entity(Entity(id="s", name="s", entity_type=EntityType.FILE))
        graph_store.insert_entity(Entity(id="t", name="t", entity_type=EntityType.FILE))
        edge = Edge(
            id="del-scoped-edge",
            source_id="s",
            target_id="t",
            relation=RelationType.DEFINES,
            scope="agent:builder",
        )
        graph_store.insert_edge(edge)
        assert graph_store.delete_edge("del-scoped-edge") is True
        assert graph_store.get_edge("del-scoped-edge") is None

    def test_delete_scoped_document(self, graph_store: GraphStore) -> None:
        doc = Document(id="del-scoped-doc", title="T", content="C", scope="project:foo")
        graph_store.insert_document(doc)
        assert graph_store.delete_document("del-scoped-doc") is True
        assert graph_store.get_document("del-scoped-doc") is None


# ---------------------------------------------------------------------------
# Metadata round-trip
# ---------------------------------------------------------------------------


class TestMetadataRoundTrip:
    """Metadata dicts survive JSON serialization → deserialization."""

    def test_entity_metadata_round_trip(self, graph_store: GraphStore) -> None:
        meta = {"tags": ["a", "b"], "count": 42, "nested": {"key": "val"}}
        entity = Entity(
            id="meta-ent",
            name="rich",
            entity_type=EntityType.PATTERN,
            metadata=meta,
        )
        graph_store.insert_entity(entity)
        result = graph_store.get_entity("meta-ent")

        assert result is not None
        assert result.metadata == meta
        assert isinstance(result.metadata, dict)

    def test_edge_metadata_round_trip(self, graph_store: GraphStore) -> None:
        e1 = Entity(id="ms", name="s", entity_type=EntityType.FILE)
        e2 = Entity(id="mt", name="t", entity_type=EntityType.FILE)
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        meta = {"confidence": 0.95, "source": "auto"}
        edge = Edge(
            id="meta-edge",
            source_id="ms",
            target_id="mt",
            relation=RelationType.RELATED_TO,
            metadata=meta,
        )
        graph_store.insert_edge(edge)
        result = graph_store.get_edge("meta-edge")

        assert result is not None
        assert result.metadata == meta
        assert isinstance(result.metadata, dict)

    def test_document_metadata_round_trip(self, graph_store: GraphStore) -> None:
        meta = {"format": "rst", "version": 2}
        doc = Document(
            id="meta-doc",
            title="Notes",
            content="Some text",
            metadata=meta,
        )
        graph_store.insert_document(doc)
        result = graph_store.get_document("meta-doc")

        assert result is not None
        assert result.metadata == meta
        assert isinstance(result.metadata, dict)


# ---------------------------------------------------------------------------
# source_pipeline filter (#411)
# ---------------------------------------------------------------------------


class TestListEntitiesSourcePipelineFilter:
    """list_entities(source_pipeline=...) filters by metadata provenance."""

    def test_filter_returns_matching_entities(self, graph_store: GraphStore) -> None:
        """Only entities whose metadata.source_pipeline matches are returned."""
        e1 = Entity(
            id="prov-1",
            name="a",
            entity_type=EntityType.CONCEPT,
            metadata={"source_pipeline": "ingest", "source_task": "entity_extraction"},
        )
        e2 = Entity(
            id="prov-2",
            name="b",
            entity_type=EntityType.CONCEPT,
            metadata={"custom": "value"},
        )
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        result = graph_store.list_entities(source_pipeline="ingest")
        assert len(result) == 1
        assert result[0].id == "prov-1"

    def test_none_returns_all(self, graph_store: GraphStore) -> None:
        """source_pipeline=None returns all entities (backward compatible)."""
        e1 = Entity(
            id="all-1",
            name="x",
            entity_type=EntityType.FILE,
            metadata={"source_pipeline": "ingest"},
        )
        e2 = Entity(
            id="all-2",
            name="y",
            entity_type=EntityType.FILE,
        )
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        result = graph_store.list_entities(source_pipeline=None)
        assert len(result) == 2

    def test_filter_with_other_params(self, graph_store: GraphStore) -> None:
        """source_pipeline filter combines with entity_type filter."""
        e1 = Entity(
            id="combo-1",
            name="a",
            entity_type=EntityType.FILE,
            metadata={"source_pipeline": "ingest"},
        )
        e2 = Entity(
            id="combo-2",
            name="b",
            entity_type=EntityType.CONCEPT,
            metadata={"source_pipeline": "ingest"},
        )
        graph_store.insert_entity(e1)
        graph_store.insert_entity(e2)

        result = graph_store.list_entities(entity_type=EntityType.FILE, source_pipeline="ingest")
        assert len(result) == 1
        assert result[0].id == "combo-1"


class TestListEdgesSourcePipelineFilter:
    """list_edges(source_pipeline=...) filters by metadata provenance."""

    @pytest.fixture(autouse=True)
    def _seed_entities(self, graph_store: GraphStore) -> None:
        """Insert entities needed for edge FK constraints."""
        for eid in ("ep1", "ep2", "ep3"):
            graph_store.insert_entity(Entity(id=eid, name=eid, entity_type=EntityType.CONCEPT))

    def test_filter_returns_matching_edges(self, graph_store: GraphStore) -> None:
        """Only edges whose metadata.source_pipeline matches are returned."""
        edge1 = Edge(
            id="pe1",
            source_id="ep1",
            target_id="ep2",
            relation=RelationType.RELATED_TO,
            metadata={"source_pipeline": "ingest", "source_task": "entity_extraction"},
        )
        edge2 = Edge(
            id="pe2",
            source_id="ep2",
            target_id="ep3",
            relation=RelationType.DEFINES,
            metadata={"custom": "thing"},
        )
        graph_store.insert_edge(edge1)
        graph_store.insert_edge(edge2)

        result = graph_store.list_edges(source_pipeline="ingest")
        assert len(result) == 1
        assert result[0].id == "pe1"

    def test_none_returns_all(self, graph_store: GraphStore) -> None:
        """source_pipeline=None returns all edges (backward compatible)."""
        edge1 = Edge(
            id="ae1",
            source_id="ep1",
            target_id="ep2",
            relation=RelationType.RELATED_TO,
            metadata={"source_pipeline": "ingest"},
        )
        edge2 = Edge(
            id="ae2",
            source_id="ep2",
            target_id="ep3",
            relation=RelationType.DEFINES,
        )
        graph_store.insert_edge(edge1)
        graph_store.insert_edge(edge2)

        result = graph_store.list_edges(source_pipeline=None)
        assert len(result) == 2
