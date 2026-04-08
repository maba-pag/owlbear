"""RED-phase tests for knowledge engine foundation (#107).

Tests the contract for: init_db, GraphStore, KnowledgeSourceStore, StatusStore,
compute_content_hash, models (Entity, Edge, Document, KnowledgeSource), and
protocol types (SparseVector, HybridEmbedding, Embedding).

All tests import from owlbear_knowledge (not v1 paths) and use :memory: SQLite.
All tests fail in RED phase — implementation not yet extracted from v1.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from owlbear_knowledge import GraphStore, KnowledgeSourceStore, StatusStore, init_db
from owlbear_knowledge.models import (
    Document,
    Edge,
    Entity,
    EntityType,
    KnowledgeSource,
    RelationType,
    SourceType,
)
from owlbear_knowledge.protocol import Embedding, HybridEmbedding, SparseVector
from owlbear_knowledge.status_store import DocumentStatus, compute_content_hash

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_entity(name: str = "test-entity", scope: str = "global", **kwargs: object) -> Entity:
    return Entity(name=name, entity_type=EntityType.CONCEPT, scope=scope, **kwargs)  # type: ignore[arg-type]


def _make_edge(source_id: str, target_id: str, scope: str = "global") -> Edge:
    return Edge(
        source_id=source_id, target_id=target_id, relation=RelationType.RELATED_TO, scope=scope
    )


def _make_document(title: str = "test-doc", scope: str = "global") -> Document:
    return Document(title=title, content="test content body", scope=scope)


def _make_source(name: str = "test-source", scope: str = "global") -> KnowledgeSource:
    return KnowledgeSource(
        name=name,
        source_type=SourceType.URL_LIST,
        scope=scope,
        created_at=_now(),
        updated_at=_now(),
    )


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


class TestFromAC_InitDb:  # noqa: N801
    """init_db creates all tables and is idempotent."""

    def test_init_db_creates_tables_in_memory_no_error(self) -> None:
        conn = sqlite3.connect(":memory:")
        init_db(conn)  # must not raise
        # Verify at least one core table exists
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'"
        ).fetchone()
        assert row is not None

    def test_init_db_idempotent_no_error_on_second_call(self) -> None:
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        init_db(conn)  # must not raise

    def test_init_db_idempotent_schema_version_equals_8(self) -> None:
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 8


# ---------------------------------------------------------------------------
# GraphStore — entities
# ---------------------------------------------------------------------------


class TestFromAC_GraphStoreEntities:  # noqa: N801
    """GraphStore entity CRUD: insert, get, list, list_for_document, delete with cascade."""

    def test_insert_get_entity_round_trip(self) -> None:
        store = GraphStore(_make_db())
        entity = _make_entity(name="concept-A")
        store.insert_entity(entity)
        result = store.get_entity(entity.id)
        assert result is not None
        assert result.id == entity.id
        assert result.name == "concept-A"
        assert result.entity_type == EntityType.CONCEPT

    def test_get_entity_missing_returns_none(self) -> None:
        store = GraphStore(_make_db())
        assert store.get_entity("nonexistent-id") is None

    def test_list_entities_returns_all_inserted(self) -> None:
        store = GraphStore(_make_db())
        e1 = _make_entity(name="e1")
        e2 = _make_entity(name="e2")
        store.insert_entity(e1)
        store.insert_entity(e2)
        results = store.list_entities()
        ids = {e.id for e in results}
        assert e1.id in ids
        assert e2.id in ids

    def test_list_entities_filter_by_type(self) -> None:
        store = GraphStore(_make_db())
        file_e = Entity(name="f", entity_type=EntityType.FILE)
        concept_e = Entity(name="c", entity_type=EntityType.CONCEPT)
        store.insert_entity(file_e)
        store.insert_entity(concept_e)
        files = store.list_entities(entity_type=EntityType.FILE)
        assert all(e.entity_type == EntityType.FILE for e in files)
        assert any(e.id == file_e.id for e in files)
        assert not any(e.id == concept_e.id for e in files)

    def test_list_entities_filter_by_scope(self) -> None:
        store = GraphStore(_make_db())
        global_e = _make_entity(name="global-e", scope="global")
        local_e = _make_entity(name="local-e", scope="local")
        store.insert_entity(global_e)
        store.insert_entity(local_e)
        results = store.list_entities(scopes=["local"])
        ids = {e.id for e in results}
        assert local_e.id in ids
        assert global_e.id not in ids

    def test_list_entities_for_document_returns_linked(self) -> None:
        store = GraphStore(_make_db())
        doc_id = "doc-xyz-123"
        linked = Entity(name="linked", entity_type=EntityType.CONCEPT, document_id=doc_id)
        unlinked = Entity(name="unlinked", entity_type=EntityType.CONCEPT)
        store.insert_entity(linked)
        store.insert_entity(unlinked)
        results = store.list_entities_for_document(doc_id)
        ids = {e.id for e in results}
        assert linked.id in ids
        assert unlinked.id not in ids

    def test_delete_entity_returns_true_and_removes_it(self) -> None:
        store = GraphStore(_make_db())
        entity = _make_entity()
        store.insert_entity(entity)
        assert store.delete_entity(entity.id) is True
        assert store.get_entity(entity.id) is None

    def test_delete_entity_missing_returns_false(self) -> None:
        store = GraphStore(_make_db())
        assert store.delete_entity("nonexistent-id") is False

    def test_delete_entity_cascades_edges(self) -> None:
        store = GraphStore(_make_db())
        e1 = _make_entity(name="e1")
        e2 = _make_entity(name="e2")
        store.insert_entity(e1)
        store.insert_entity(e2)
        edge = _make_edge(source_id=e1.id, target_id=e2.id)
        store.insert_edge(edge)
        store.delete_entity(e1.id)
        assert store.get_edge(edge.id) is None


# ---------------------------------------------------------------------------
# GraphStore — edges
# ---------------------------------------------------------------------------


class TestFromAC_GraphStoreEdges:  # noqa: N801
    """GraphStore edge CRUD: insert, get, list (with filters), delete."""

    def test_insert_get_edge_round_trip(self) -> None:
        store = GraphStore(_make_db())
        e1 = _make_entity(name="src")
        e2 = _make_entity(name="tgt")
        store.insert_entity(e1)
        store.insert_entity(e2)
        edge = _make_edge(source_id=e1.id, target_id=e2.id)
        store.insert_edge(edge)
        result = store.get_edge(edge.id)
        assert result is not None
        assert result.id == edge.id
        assert result.source_id == e1.id
        assert result.target_id == e2.id
        assert result.relation == RelationType.RELATED_TO

    def test_get_edge_missing_returns_none(self) -> None:
        store = GraphStore(_make_db())
        assert store.get_edge("nonexistent-edge-id") is None

    def test_list_edges_filter_by_source_id(self) -> None:
        store = GraphStore(_make_db())
        e1, e2, e3 = _make_entity("e1"), _make_entity("e2"), _make_entity("e3")
        for e in (e1, e2, e3):
            store.insert_entity(e)
        edge_1_2 = _make_edge(source_id=e1.id, target_id=e2.id)
        edge_1_3 = _make_edge(source_id=e1.id, target_id=e3.id)
        edge_2_3 = _make_edge(source_id=e2.id, target_id=e3.id)
        for ed in (edge_1_2, edge_1_3, edge_2_3):
            store.insert_edge(ed)
        results = store.list_edges(source_id=e1.id)
        ids = {ed.id for ed in results}
        assert edge_1_2.id in ids
        assert edge_1_3.id in ids
        assert edge_2_3.id not in ids

    def test_list_edges_filter_by_target_id(self) -> None:
        store = GraphStore(_make_db())
        e1, e2, e3 = _make_entity("e1"), _make_entity("e2"), _make_entity("e3")
        for e in (e1, e2, e3):
            store.insert_entity(e)
        edge_1_3 = _make_edge(source_id=e1.id, target_id=e3.id)
        edge_2_3 = _make_edge(source_id=e2.id, target_id=e3.id)
        edge_1_2 = _make_edge(source_id=e1.id, target_id=e2.id)
        for ed in (edge_1_3, edge_2_3, edge_1_2):
            store.insert_edge(ed)
        results = store.list_edges(target_id=e3.id)
        ids = {ed.id for ed in results}
        assert edge_1_3.id in ids
        assert edge_2_3.id in ids
        assert edge_1_2.id not in ids

    def test_list_edges_filter_by_scope(self) -> None:
        store = GraphStore(_make_db())
        e1 = _make_entity("e1")
        e2 = _make_entity("e2")
        store.insert_entity(e1)
        store.insert_entity(e2)
        edge_global = Edge(
            source_id=e1.id, target_id=e2.id, relation=RelationType.IMPORTS, scope="global"
        )
        edge_local = Edge(
            source_id=e1.id, target_id=e2.id, relation=RelationType.IMPORTS, scope="local"
        )
        store.insert_edge(edge_global)
        store.insert_edge(edge_local)
        results = store.list_edges(scopes=["local"])
        ids = {ed.id for ed in results}
        assert edge_local.id in ids
        assert edge_global.id not in ids

    def test_delete_edge_returns_true_and_removes_it(self) -> None:
        store = GraphStore(_make_db())
        e1 = _make_entity("e1")
        e2 = _make_entity("e2")
        store.insert_entity(e1)
        store.insert_entity(e2)
        edge = _make_edge(source_id=e1.id, target_id=e2.id)
        store.insert_edge(edge)
        assert store.delete_edge(edge.id) is True
        assert store.get_edge(edge.id) is None

    def test_delete_edge_missing_returns_false(self) -> None:
        store = GraphStore(_make_db())
        assert store.delete_edge("nonexistent-edge-id") is False


# ---------------------------------------------------------------------------
# GraphStore — documents
# ---------------------------------------------------------------------------


class TestFromAC_GraphStoreDocuments:  # noqa: N801
    """GraphStore document CRUD: insert, get, list (with scope filter), delete."""

    def test_insert_get_document_round_trip(self) -> None:
        store = GraphStore(_make_db())
        doc = _make_document(title="My Document")
        store.insert_document(doc)
        result = store.get_document(doc.id)
        assert result is not None
        assert result.id == doc.id
        assert result.title == "My Document"
        assert result.content == "test content body"

    def test_get_document_missing_returns_none(self) -> None:
        store = GraphStore(_make_db())
        assert store.get_document("nonexistent-doc-id") is None

    def test_list_documents_respects_scope_filter(self) -> None:
        store = GraphStore(_make_db())
        d_global = _make_document(title="global-doc", scope="global")
        d_local = _make_document(title="local-doc", scope="local")
        store.insert_document(d_global)
        store.insert_document(d_local)
        results = store.list_documents(scopes=["local"])
        ids = {d.id for d in results}
        assert d_local.id in ids
        assert d_global.id not in ids

    def test_delete_document_returns_true_and_removes(self) -> None:
        store = GraphStore(_make_db())
        doc = _make_document()
        store.insert_document(doc)
        assert store.delete_document(doc.id) is True
        assert store.get_document(doc.id) is None

    def test_delete_document_missing_returns_false(self) -> None:
        store = GraphStore(_make_db())
        assert store.delete_document("nonexistent-doc-id") is False


# ---------------------------------------------------------------------------
# GraphStore — merge and BFS traversal
# ---------------------------------------------------------------------------


class TestFromAC_GraphStoreMergeTraversal:  # noqa: N801
    """GraphStore merge_entities and get_neighbors (BFS) with depth/node limits."""

    def test_merge_entities_redirects_edges_deletes_duplicates_returns_count(self) -> None:
        store = GraphStore(_make_db())
        canonical = _make_entity(name="canonical")
        dup1 = _make_entity(name="dup1")
        dup2 = _make_entity(name="dup2")
        other = _make_entity(name="other")
        for e in (canonical, dup1, dup2, other):
            store.insert_entity(e)
        edge_to_dup1 = _make_edge(source_id=other.id, target_id=dup1.id)
        edge_to_dup2 = _make_edge(source_id=other.id, target_id=dup2.id)
        store.insert_edge(edge_to_dup1)
        store.insert_edge(edge_to_dup2)
        count = store.merge_entities(canonical.id, [dup1.id, dup2.id], {})
        assert count == 2
        assert store.get_entity(dup1.id) is None
        assert store.get_entity(dup2.id) is None
        assert store.get_entity(canonical.id) is not None

    def test_merge_entities_edges_redirected_to_canonical(self) -> None:
        """AC: merge_entities 'redirects edges' — both target and source edges point to canonical after merge."""
        store = GraphStore(_make_db())
        canonical = _make_entity(name="canonical")
        dup1 = _make_entity(name="dup1")
        dup2 = _make_entity(name="dup2")
        other = _make_entity(name="other")
        for e in (canonical, dup1, dup2, other):
            store.insert_entity(e)
        # Edge where dup1 is the target (incoming edge to dup1)
        incoming = _make_edge(source_id=other.id, target_id=dup1.id)
        # Edge where dup2 is the source (outgoing edge from dup2)
        outgoing = _make_edge(source_id=dup2.id, target_id=other.id)
        store.insert_edge(incoming)
        store.insert_edge(outgoing)

        store.merge_entities(canonical.id, [dup1.id, dup2.id], {})

        # Target redirect: edge that pointed TO dup1 must now point TO canonical
        target_edges = store.list_edges(target_id=canonical.id)
        assert len(target_edges) == 1, "incoming edge to dup1 must be redirected to canonical"
        assert target_edges[0].source_id == other.id

        # Source redirect: edge that originated FROM dup2 must now originate FROM canonical
        source_edges = store.list_edges(source_id=canonical.id)
        assert len(source_edges) == 1, "outgoing edge from dup2 must be redirected to canonical"
        assert source_edges[0].target_id == other.id

        # No edges remain pointing to or from the duplicates
        assert store.list_edges(target_id=dup1.id) == []
        assert store.list_edges(source_id=dup2.id) == []

    def test_get_neighbors_bfs_returns_direct_neighbors_with_edges(self) -> None:
        store = GraphStore(_make_db())
        center = _make_entity(name="center")
        n1 = _make_entity(name="n1")
        n2 = _make_entity(name="n2")
        for e in (center, n1, n2):
            store.insert_entity(e)
        edge1 = _make_edge(source_id=center.id, target_id=n1.id)
        edge2 = _make_edge(source_id=center.id, target_id=n2.id)
        store.insert_edge(edge1)
        store.insert_edge(edge2)
        results = store.get_neighbors(center.id, max_depth=1)
        entity_ids = {e.id for e, _ in results}
        assert n1.id in entity_ids
        assert n2.id in entity_ids
        assert center.id not in entity_ids
        # Each result is a (Entity, Edge) tuple
        for entity, edge in results:
            assert entity.id in {n1.id, n2.id}
            assert edge.id in {edge1.id, edge2.id}

    def test_get_neighbors_returns_empty_for_nonexistent_entity(self) -> None:
        store = GraphStore(_make_db())
        assert store.get_neighbors("nonexistent-entity-id") == []

    def test_get_neighbors_respects_max_depth(self) -> None:
        store = GraphStore(_make_db())
        center = _make_entity(name="center")
        hop1 = _make_entity(name="hop1")
        hop2 = _make_entity(name="hop2")
        for e in (center, hop1, hop2):
            store.insert_entity(e)
        store.insert_edge(_make_edge(source_id=center.id, target_id=hop1.id))
        store.insert_edge(_make_edge(source_id=hop1.id, target_id=hop2.id))
        # max_depth=1 should only reach hop1, not hop2
        results = store.get_neighbors(center.id, max_depth=1)
        entity_ids = {e.id for e, _ in results}
        assert hop1.id in entity_ids
        assert hop2.id not in entity_ids

    def test_get_neighbors_respects_max_nodes_limit(self) -> None:
        store = GraphStore(_make_db())
        center = _make_entity(name="center")
        store.insert_entity(center)
        neighbors = [_make_entity(name=f"n{i}") for i in range(5)]
        for n in neighbors:
            store.insert_entity(n)
            store.insert_edge(_make_edge(source_id=center.id, target_id=n.id))
        results = store.get_neighbors(center.id, max_depth=1, max_nodes=3)
        assert len(results) <= 3


# ---------------------------------------------------------------------------
# KnowledgeSourceStore
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeSourceStore:  # noqa: N801
    """KnowledgeSourceStore full CRUD + scope filtering."""

    def test_create_and_get_by_id(self) -> None:
        store = KnowledgeSourceStore(_make_db())
        source = _make_source(name="my-source")
        store.create(source)
        result = store.get(source.id)
        assert result is not None
        assert result.id == source.id
        assert result.name == "my-source"

    def test_get_missing_returns_none(self) -> None:
        store = KnowledgeSourceStore(_make_db())
        assert store.get("nonexistent-source-id") is None

    def test_list_all_returns_all_inserted(self) -> None:
        store = KnowledgeSourceStore(_make_db())
        s1 = _make_source("src-a")
        s2 = _make_source("src-b")
        store.create(s1)
        store.create(s2)
        results = store.list_all()
        ids = {s.id for s in results}
        assert s1.id in ids
        assert s2.id in ids

    def test_list_all_scope_filter_returns_only_matching(self) -> None:
        store = KnowledgeSourceStore(_make_db())
        global_s = _make_source("gs", scope="global")
        local_s = _make_source("ls", scope="local")
        store.create(global_s)
        store.create(local_s)
        results = store.list_all(scope="local")
        ids = {s.id for s in results}
        assert local_s.id in ids
        assert global_s.id not in ids

    def test_update_changes_persisted(self) -> None:
        store = KnowledgeSourceStore(_make_db())
        source = _make_source("original-name")
        store.create(source)
        updated = KnowledgeSource(
            id=source.id,
            name="updated-name",
            source_type=SourceType.URL_LIST,
            scope=source.scope,
            created_at=source.created_at,
            updated_at=_now(),
        )
        store.update(updated)
        result = store.get(source.id)
        assert result is not None
        assert result.name == "updated-name"

    def test_delete_returns_true_and_removes(self) -> None:
        store = KnowledgeSourceStore(_make_db())
        source = _make_source()
        store.create(source)
        assert store.delete(source.id) is True
        assert store.get(source.id) is None

    def test_delete_missing_returns_false(self) -> None:
        store = KnowledgeSourceStore(_make_db())
        assert store.delete("nonexistent-source-id") is False


# ---------------------------------------------------------------------------
# StatusStore
# ---------------------------------------------------------------------------


class TestFromAC_StatusStore:  # noqa: N801
    """StatusStore: set_status, find_status_by_source, check_content_changed, update_content_hash."""

    def test_set_status_and_find_status_by_source_round_trip(self) -> None:
        store = StatusStore(_make_db())
        store.set_status("doc-001", "ingested", source="http://example.com/doc1")
        result = store.find_status_by_source("http://example.com/doc1")
        assert result is not None
        assert result.document_id == "doc-001"
        assert result.status == "ingested"

    def test_find_status_by_source_missing_returns_none(self) -> None:
        store = StatusStore(_make_db())
        assert store.find_status_by_source("http://missing.example.com") is None

    def test_check_content_changed_detects_hash_delta(self) -> None:
        store = StatusStore(_make_db())
        source = "http://example.com/delta"
        store.set_status("doc-002", "ingested", source=source)
        store.update_content_hash("doc-002", "original content")
        changed, doc_id = store.check_content_changed(source, "different content entirely")
        assert changed is True
        assert doc_id == "doc-002"

    def test_check_content_changed_returns_false_for_same_content(self) -> None:
        store = StatusStore(_make_db())
        source = "http://example.com/same"
        content = "identical content here"
        store.set_status("doc-003", "ingested", source=source)
        store.update_content_hash("doc-003", content)
        changed, doc_id = store.check_content_changed(source, content)
        assert changed is False
        assert doc_id == "doc-003"

    def test_update_content_hash_persists_non_none_hash(self) -> None:
        store = StatusStore(_make_db())
        store.set_status("doc-004", "ingested", source="http://example.com/hash")
        store.update_content_hash("doc-004", "some hashed content")
        result = store.find_status_by_source("http://example.com/hash")
        assert result is not None
        assert result.content_hash is not None
        # SHA-256 produces 64 hex characters
        assert len(result.content_hash) == 64

    def test_document_status_is_a_known_type(self) -> None:
        # DocumentStatus is importable and has expected fields
        ds = DocumentStatus(document_id="d", content_hash=None, status="pending")
        assert ds.document_id == "d"
        assert ds.status == "pending"
        assert ds.content_hash is None


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


class TestFromAC_ComputeContentHash:  # noqa: N801
    """compute_content_hash strips whitespace and returns stable SHA-256 hex."""

    def test_strips_whitespace_before_hashing(self) -> None:
        assert compute_content_hash("  hello  ") == compute_content_hash("hello")

    def test_different_content_produces_different_hash(self) -> None:
        assert compute_content_hash("abc") != compute_content_hash("xyz")

    def test_returns_64_char_lowercase_hex_string(self) -> None:
        result = compute_content_hash("test content")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# Models — frozen + validation
# ---------------------------------------------------------------------------


class TestFromAC_Models:  # noqa: N801
    """Entity, Edge, Document, KnowledgeSource are frozen Pydantic models with enum validation."""

    def test_entity_is_frozen(self) -> None:
        entity = Entity(name="x", entity_type=EntityType.CONCEPT)
        with pytest.raises((TypeError, ValidationError)):
            entity.name = "mutated"  # type: ignore[misc]

    def test_edge_is_frozen(self) -> None:
        edge = Edge(source_id="a", target_id="b", relation=RelationType.RELATED_TO)
        with pytest.raises((TypeError, ValidationError)):
            edge.weight = 999.0  # type: ignore[misc]

    def test_document_is_frozen(self) -> None:
        doc = Document(title="t", content="c")
        with pytest.raises((TypeError, ValidationError)):
            doc.title = "mutated"  # type: ignore[misc]

    def test_knowledge_source_is_frozen(self) -> None:
        source = KnowledgeSource(
            name="s",
            source_type=SourceType.URL_LIST,
            created_at=_now(),
            updated_at=_now(),
        )
        with pytest.raises((TypeError, ValidationError)):
            source.name = "mutated"  # type: ignore[misc]

    def test_entity_valid_entity_type_constructs(self) -> None:
        entity = Entity(name="f", entity_type=EntityType.FILE)
        assert entity.entity_type == EntityType.FILE

    def test_entity_invalid_entity_type_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            Entity(name="x", entity_type="not_a_valid_type")  # type: ignore[arg-type]

    def test_edge_valid_relation_type_constructs(self) -> None:
        edge = Edge(source_id="a", target_id="b", relation=RelationType.DEFINES)
        assert edge.relation == RelationType.DEFINES

    def test_edge_invalid_relation_type_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            Edge(source_id="a", target_id="b", relation="not_a_valid_relation")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Protocol types
# ---------------------------------------------------------------------------


class TestFromAC_ProtocolTypes:  # noqa: N801
    """SparseVector, HybridEmbedding, and Embedding alias from owlbear_knowledge.protocol."""

    def test_sparse_vector_instantiates_with_valid_data(self) -> None:
        sv = SparseVector(indices=[0, 1, 2], values=[0.1, 0.2, 0.3])
        assert sv.indices == [0, 1, 2]
        assert sv.values == [0.1, 0.2, 0.3]

    def test_hybrid_embedding_instantiates_with_dense_only(self) -> None:
        he = HybridEmbedding(dense=[0.1, 0.2, 0.3])
        assert he.dense == [0.1, 0.2, 0.3]
        assert he.sparse is None
        assert he.colbert is None

    def test_hybrid_embedding_instantiates_with_all_fields(self) -> None:
        sv = SparseVector(indices=[1], values=[0.5])
        he = HybridEmbedding(dense=[0.1, 0.2], sparse=sv, colbert=[[0.1, 0.2]])
        assert he.sparse is not None
        assert he.sparse.indices == [1]
        assert he.colbert is not None
        assert he.colbert == [[0.1, 0.2]]

    def test_embedding_alias_accepts_list_of_float(self) -> None:
        emb: Embedding = [0.1, 0.2, 0.3]
        assert isinstance(emb, list)

    def test_embedding_alias_accepts_hybrid_embedding(self) -> None:
        emb: Embedding = HybridEmbedding(dense=[0.1, 0.2])
        assert isinstance(emb, HybridEmbedding)


# ---------------------------------------------------------------------------
# __init__.py re-exports
# ---------------------------------------------------------------------------


class TestFromAC_PublicExports:  # noqa: N801
    """GraphStore, KnowledgeSourceStore, StatusStore, init_db importable from owlbear_knowledge."""

    def test_graph_store_importable_from_owlbear_knowledge(self) -> None:
        from owlbear_knowledge import GraphStore as GraphStore_  # noqa: PLC0415

        assert GraphStore_ is not None

    def test_knowledge_source_store_importable_from_owlbear_knowledge(self) -> None:
        from owlbear_knowledge import KnowledgeSourceStore as KnowledgeSourceStore_  # noqa: PLC0415

        assert KnowledgeSourceStore_ is not None

    def test_status_store_importable_from_owlbear_knowledge(self) -> None:
        from owlbear_knowledge import StatusStore as StatusStore_  # noqa: PLC0415

        assert StatusStore_ is not None

    def test_init_db_importable_from_owlbear_knowledge(self) -> None:
        from owlbear_knowledge import init_db as idb  # noqa: PLC0415

        assert idb is not None


# ---------------------------------------------------------------------------
# pyproject.toml manifest (AC: pydantic>=2.10.0 as sole dependency)
# ---------------------------------------------------------------------------


class TestFromAC_PackageManifest:  # noqa: N801
    """pyproject.toml must declare pydantic>=2.10.0 as the sole runtime dependency."""

    def _load_pyproject(self) -> dict:
        import pathlib
        import tomllib

        path = pathlib.Path(__file__).parent.parent / "serve" / "knowledge" / "pyproject.toml"
        with path.open("rb") as f:
            return tomllib.load(f)

    def test_pydantic_declared_as_dependency(self) -> None:
        """packages/knowledge/pyproject.toml must list pydantic as a runtime dep."""
        data = self._load_pyproject()
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        pydantic_deps = [d for d in deps if d.lower().startswith("pydantic")]
        assert pydantic_deps, (
            "pydantic not found in [project].dependencies of packages/knowledge/pyproject.toml"
        )

    def test_pydantic_version_constraint_gte_2_10_0(self) -> None:
        """Declared pydantic dependency must specify >=2.10.0."""
        data = self._load_pyproject()
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        pydantic_deps = [d for d in deps if d.lower().startswith("pydantic")]
        assert pydantic_deps, "pydantic not declared — run test_pydantic_declared_as_dependency first"
        assert any(">=2.10.0" in d for d in pydantic_deps), (
            f"Expected pydantic>=2.10.0 in dependencies, found: {pydantic_deps}"
        )

    def test_pydantic_is_sole_runtime_dependency(self) -> None:
        """pydantic must be the ONLY entry in [project].dependencies."""
        data = self._load_pyproject()
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        assert len(deps) == 1, (
            f"Expected exactly 1 runtime dependency (pydantic), found {len(deps)}: {deps}"
        )


# ---------------------------------------------------------------------------
# Builder-discovered tests
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Edge cases and migration paths discovered during implementation."""

    def test_init_db_migrates_v1_schema_to_v8(self) -> None:
        """Full migration path v1 -> v8: all migration helpers and dispatch branches run."""
        conn = sqlite3.connect(":memory:")
        # Create a minimal v1 schema (no scope columns, no chunks/document_status)
        conn.execute(
            "CREATE TABLE documents ("
            "id TEXT PRIMARY KEY, title TEXT, content TEXT, metadata TEXT, created_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE entities ("
            "id TEXT PRIMARY KEY, name TEXT, entity_type TEXT,"
            " description TEXT, metadata TEXT, created_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE edges ("
            "id TEXT PRIMARY KEY, source_id TEXT, target_id TEXT,"
            " relation TEXT, weight REAL, metadata TEXT, created_at TEXT)"
        )
        conn.execute("CREATE TABLE schema_version (version INTEGER, applied_at TEXT)")
        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (1, '2024-01-01T00:00:00+00:00')"
        )
        conn.commit()

        init_db(conn)

        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 8

        # Verify that migration-added tables now exist
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "chunks" in tables
        assert "document_status" in tables
        assert "knowledge_sources" in tables
        assert "bookmarks" in tables
        assert "consolidations" in tables

    def test_list_entities_with_empty_scopes_returns_empty(self) -> None:
        """list_entities with scopes=[] short-circuits to return empty list."""
        store = GraphStore(_make_db())
        store.insert_entity(_make_entity(name="e1"))
        assert store.list_entities(scopes=[]) == []

    def test_list_edges_with_empty_scopes_returns_empty(self) -> None:
        """list_edges with scopes=[] short-circuits to return empty list."""
        store = GraphStore(_make_db())
        e1, e2 = _make_entity("e1"), _make_entity("e2")
        store.insert_entity(e1)
        store.insert_entity(e2)
        store.insert_edge(_make_edge(source_id=e1.id, target_id=e2.id))
        assert store.list_edges(scopes=[]) == []

    def test_list_documents_with_empty_scopes_returns_empty(self) -> None:
        """list_documents with scopes=[] short-circuits to return empty list."""
        store = GraphStore(_make_db())
        store.insert_document(_make_document())
        assert store.list_documents(scopes=[]) == []

    def test_status_store_set_status_update_path(self) -> None:
        """set_status on existing doc_id follows UPDATE path (not INSERT)."""
        store = StatusStore(_make_db())
        store.set_status("doc-x", "pending", source="http://x.com")
        store.set_status("doc-x", "ingested")  # triggers UPDATE path
        result = store.find_status_by_source("http://x.com")
        assert result is not None
        assert result.status == "ingested"

    def test_check_content_changed_new_source_returns_true_none(self) -> None:
        """check_content_changed on unknown source returns (True, None)."""
        store = StatusStore(_make_db())
        changed, doc_id = store.check_content_changed("http://new.example.com", "content")
        assert changed is True
        assert doc_id is None
