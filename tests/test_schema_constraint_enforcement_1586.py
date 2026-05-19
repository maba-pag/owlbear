"""Failing tests (RED phase) for task #1586: Knowledge schema constraint enforcement.

All tests must FAIL until the builder implements _migrate_v12_to_v13 and bumps
_SCHEMA_VERSION to 13.

AC coverage:
- AC-1: _SCHEMA_VERSION = 13; init_db() calls PRAGMA foreign_keys = ON;
        _apply_migrations dispatch includes (13, _migrate_v12_to_v13).
- AC-2: _migrate_v12_to_v13 (a) deletes entities with NULL document_id,
        (b) deletes edges with NULL document_id or orphaned refs,
        (c) rebuilds tables with NOT NULL constraint,
        (d) updates schema_version to 13.
- AC-3: Post-migration db — store_chunks, store_extractions, delete_document_data
        all succeed without IntegrityError.
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear_knowledge.chunker import Chunk
from owlbear_knowledge.document_store import DocumentStore
from owlbear_knowledge.extractor import ExtractionResult
from owlbear_knowledge.graph_store import GraphStore
from owlbear_knowledge.models import Edge, Entity, EntityType, RelationType
from owlbear_knowledge.schema import _SCHEMA_VERSION, _apply_migrations, init_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_v12_legacy_conn() -> sqlite3.Connection:
    """Return an in-memory DB in the state of a database migrated through v11→v12.

    entities.document_id and edges.document_id are nullable TEXT, matching the
    ALTER TABLE ADD COLUMN state produced by v3 and v11 migrations respectively.
    schema_version = 12.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE documents (
            id TEXT PRIMARY KEY, title TEXT, content TEXT, metadata TEXT,
            created_at TEXT, scope TEXT DEFAULT 'global', source_id TEXT
        );
        CREATE TABLE entities (
            id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, description TEXT,
            metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global',
            document_id TEXT,
            chunk_id TEXT, importance REAL DEFAULT 0.5
        );
        CREATE TABLE edges (
            id TEXT PRIMARY KEY,
            source_id TEXT REFERENCES entities(id),
            target_id TEXT REFERENCES entities(id),
            relation TEXT,
            document_id TEXT,
            weight REAL, metadata TEXT, created_at TEXT, scope TEXT DEFAULT 'global'
        );
        CREATE TABLE chunks (
            id TEXT PRIMARY KEY, document_id TEXT REFERENCES documents(id),
            chunk_index INTEGER, content TEXT, metadata TEXT, created_at TEXT,
            scope TEXT DEFAULT 'global', consolidated INTEGER DEFAULT 0,
            enrichment_state TEXT DEFAULT 'pending', claimed_at TEXT
        );
        CREATE TABLE document_status (
            document_id TEXT PRIMARY KEY, status TEXT, source TEXT, error TEXT,
            created_at TEXT, updated_at TEXT,
            scope TEXT DEFAULT 'global', content_hash TEXT
        );
        CREATE TABLE schema_version (version INTEGER, applied_at TEXT);
        INSERT INTO schema_version (version, applied_at) VALUES (12, '2025-01-01T00:00:00');
        """
    )
    return conn


def _require_migrate_v12_to_v13():
    """Return _migrate_v12_to_v13 or pytest.fail if not yet implemented."""
    from owlbear_knowledge import schema as _schema  # noqa: PLC0415

    fn = getattr(_schema, "_migrate_v12_to_v13", None)
    if fn is None:
        pytest.fail("_migrate_v12_to_v13 is not implemented in owlbear_knowledge.schema — builder must add it.")
    return fn


class _NullVectorStore:
    """Stub vector store that no-ops all calls."""

    def store_embedding(self, **kwargs) -> None:  # noqa: ANN003
        pass

    def delete_embedding(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass


class _NullEmbedder:
    """Stub embedder that returns zero vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 3] * len(texts)


def _make_document_store(conn: sqlite3.Connection) -> DocumentStore:
    """Return a DocumentStore backed by the given connection."""
    return DocumentStore(conn, GraphStore(conn), _NullVectorStore(), _NullEmbedder())


def _make_migrated_conn() -> sqlite3.Connection:
    """Return a v12 legacy db with _migrate_v12_to_v13 applied."""
    migrate = _require_migrate_v12_to_v13()
    conn = _make_v12_legacy_conn()
    migrate(conn)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# TestFromAC_SchemaVersion — AC-1
# ---------------------------------------------------------------------------


class TestFromAC_SchemaVersion:
    """Contract tests derived from AC-1."""

    def test_schema_version_constant_is_13(self) -> None:
        """_SCHEMA_VERSION constant must be at the current terminal version (14 after #1651)."""
        assert _SCHEMA_VERSION == 14

    def test_fresh_db_schema_version_is_13_after_init_db(self) -> None:
        """init_db() on a new connection writes schema_version = 14 to the table."""
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 14

    def test_init_db_enables_foreign_keys_and_reaches_v13(self) -> None:
        """init_db() enables PRAGMA foreign_keys = ON and reaches current schema version."""
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        ver = conn.execute("SELECT version FROM schema_version").fetchone()[0]
        assert fk == 1
        assert ver == 14  # updated to 14 by #1651

    def test_apply_migrations_dispatches_v12_to_v13(self) -> None:
        """_apply_migrations(conn, 12) migrates a v12 db to the terminal schema version (14)."""
        conn = _make_v12_legacy_conn()
        _apply_migrations(conn, 12)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None, "schema_version table must contain a row"
        assert row[0] == 14


# ---------------------------------------------------------------------------
# TestFromAC_MigrationV12ToV13 — AC-2
# ---------------------------------------------------------------------------


class TestFromAC_MigrationV12ToV13:
    """Contract tests for the _migrate_v12_to_v13 function derived from AC-2."""

    def test_migration_updates_schema_version_to_13(self) -> None:
        """(AC-2d) Migration updates the schema_version row to 13."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        migrate(conn)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        assert row is not None
        assert row[0] == 13

    def test_migration_deletes_entities_with_null_document_id(self) -> None:
        """(AC-2a) Entities with document_id IS NULL are removed by the migration."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e_null', 'Orphan', 'concept', NULL)"
        )
        conn.commit()
        migrate(conn)
        row = conn.execute("SELECT id FROM entities WHERE id = 'e_null'").fetchone()
        assert row is None, "Entity with NULL document_id must be deleted by migration"

    def test_migration_preserves_entities_with_non_null_document_id(self) -> None:
        """(AC-2a) Entities with a valid document_id are not deleted."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e_valid', 'Valid', 'concept', 'doc-1')"
        )
        conn.commit()
        migrate(conn)
        row = conn.execute("SELECT id FROM entities WHERE id = 'e_valid'").fetchone()
        assert row is not None, "Entity with valid document_id must be preserved"

    def test_migration_preserves_entities_with_empty_string_document_id(self) -> None:
        """Boundary: empty string '' is NOT NULL — entity must be preserved."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e_empty', 'EmptyDoc', 'concept', '')"
        )
        conn.commit()
        migrate(conn)
        row = conn.execute("SELECT id FROM entities WHERE id = 'e_empty'").fetchone()
        assert row is not None, "Entity with empty-string document_id must be preserved (NULL != '')"

    def test_migration_deletes_edges_with_null_document_id(self) -> None:
        """(AC-2b) Edges with document_id IS NULL are deleted."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e1', 'E1', 'concept', 'doc-1')"
        )
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e2', 'E2', 'concept', 'doc-1')"
        )
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id)"
            " VALUES ('edge_null', 'e1', 'e2', 'related_to', NULL)"
        )
        conn.commit()
        migrate(conn)
        row = conn.execute("SELECT id FROM edges WHERE id = 'edge_null'").fetchone()
        assert row is None, "Edge with NULL document_id must be deleted by migration"

    def test_migration_deletes_transitively_orphaned_edges(self) -> None:
        """(AC-2b) Edges whose source_id refs a NULL-document entity are also removed."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        # Entity with NULL document_id — will be deleted in step (a)
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e_null', 'NullParent', 'concept', NULL)"
        )
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id)"
            " VALUES ('e_valid', 'ValidChild', 'concept', 'doc-1')"
        )
        # Edge has a valid document_id but source_id references the doomed entity
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id)"
            " VALUES ('edge_orphan', 'e_null', 'e_valid', 'related_to', 'doc-1')"
        )
        conn.commit()
        migrate(conn)
        row = conn.execute("SELECT id FROM edges WHERE id = 'edge_orphan'").fetchone()
        assert row is None, "Edge referencing a deleted entity must be removed as transitively orphaned"

    def test_migration_deletes_edges_orphaned_via_target_id(self) -> None:
        """(AC-2b) Edges orphaned via target_id (not just source_id) are also removed."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id)"
            " VALUES ('e_valid', 'ValidSource', 'concept', 'doc-1')"
        )
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e_null', 'NullTarget', 'concept', NULL)"
        )
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id)"
            " VALUES ('edge_orphan_target', 'e_valid', 'e_null', 'related_to', 'doc-1')"
        )
        conn.commit()
        migrate(conn)
        row = conn.execute("SELECT id FROM edges WHERE id = 'edge_orphan_target'").fetchone()
        assert row is None, "Edge orphaned via target_id must be removed by the migration"

    def test_migration_preserves_valid_edges(self) -> None:
        """(AC-2b/c) Edges with valid entity refs and non-null document_id are preserved."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e1', 'Ent1', 'concept', 'doc-1')"
        )
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e2', 'Ent2', 'concept', 'doc-1')"
        )
        conn.execute(
            "INSERT INTO edges (id, source_id, target_id, relation, document_id)"
            " VALUES ('edge_valid', 'e1', 'e2', 'related_to', 'doc-1')"
        )
        conn.commit()
        migrate(conn)
        row = conn.execute("SELECT id FROM edges WHERE id = 'edge_valid'").fetchone()
        assert row is not None, "Edge with valid refs and non-null document_id must be preserved"

    def test_migration_enforces_not_null_on_entities_document_id(self) -> None:
        """(AC-2c) After migration, inserting an entity with NULL document_id raises IntegrityError."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        conn.execute("PRAGMA foreign_keys = OFF")
        migrate(conn)
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e_bad', 'Bad', 'concept', NULL)"
            )

    def test_migration_enforces_not_null_on_edges_document_id(self) -> None:
        """(AC-2c) After migration, inserting an edge with NULL document_id raises IntegrityError."""
        migrate = _require_migrate_v12_to_v13()
        conn = _make_v12_legacy_conn()
        conn.execute("PRAGMA foreign_keys = OFF")
        migrate(conn)
        conn.execute(
            "INSERT INTO entities (id, name, entity_type, document_id) VALUES ('e1', 'E1', 'concept', 'doc-1')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO edges (id, source_id, target_id, relation, document_id)"
                " VALUES ('edge_bad', 'e1', 'e1', 'related_to', NULL)"
            )


# ---------------------------------------------------------------------------
# TestFromAC_WritePathsPostMigration — AC-3
# ---------------------------------------------------------------------------


class TestFromAC_WritePathsPostMigration:
    """Smoke tests for write paths on a v12→v13 migrated database (AC-3)."""

    def test_store_chunks_succeeds_with_valid_document_id_on_migrated_db(self) -> None:
        """(AC-3) store_chunks() with a valid document_id completes without IntegrityError."""
        conn = _make_migrated_conn()
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at)"
            " VALUES ('doc-1', 'Test', '', '{}', '2025-01-01')"
        )
        conn.commit()
        store = _make_document_store(conn)
        chunk_ids = store.store_chunks("doc-1", [Chunk(text="Hello world", index=0)])
        assert len(chunk_ids) == 1

    def test_store_extractions_entity_and_edge_succeed_on_migrated_db(self) -> None:
        """(AC-3) store_extractions() with ≥1 entity and ≥1 edge completes without error."""
        conn = _make_migrated_conn()
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at)"
            " VALUES ('doc-1', 'Doc', '', '{}', '2025-01-01')"
        )
        conn.commit()
        store = _make_document_store(conn)
        entity = Entity(
            id="ent-1",
            name="Alpha",
            entity_type=EntityType.CONCEPT,
            document_id="doc-1",
        )
        edge = Edge(
            id="edg-1",
            source_id="ent-1",
            target_id="ent-1",
            relation=RelationType.RELATED_TO,
        )
        result = ExtractionResult(entities=[entity], edges=[edge])
        entity_count, edge_count = store.store_extractions([result], document_id="doc-1")
        assert entity_count >= 1
        assert edge_count >= 1

    def test_store_extractions_rejects_blank_document_id_for_graph_rows(self) -> None:
        """store_extractions() refuses to persist entity/edge rows without document provenance."""
        conn = _make_migrated_conn()
        store = _make_document_store(conn)
        entity = Entity(
            id="ent-blank-doc",
            name="Alpha",
            entity_type=EntityType.CONCEPT,
        )

        with pytest.raises(ValueError, match="document_id is required"):
            store.store_extractions([ExtractionResult(entities=[entity], edges=[])])

        assert conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 0

    def test_store_extractions_allows_empty_results_without_document_id(self) -> None:
        """Empty extraction results can still be stored as a no-op without document provenance."""
        conn = _make_migrated_conn()
        store = _make_document_store(conn)

        assert store.store_extractions([ExtractionResult(entities=[], edges=[])]) == (0, 0)

    def test_delete_document_data_removes_all_rows_without_fk_violation(self) -> None:
        """(AC-3) delete_document_data() removes all associated rows without FK violation."""
        conn = _make_migrated_conn()
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at)"
            " VALUES ('doc-1', 'Doc', '', '{}', '2025-01-01')"
        )
        conn.commit()
        store = _make_document_store(conn)
        store.store_chunks("doc-1", [Chunk(text="content", index=0)])
        entity = Entity(
            id="ent-1",
            name="Alpha",
            entity_type=EntityType.CONCEPT,
            document_id="doc-1",
        )
        edge = Edge(
            id="edg-1",
            source_id="ent-1",
            target_id="ent-1",
            relation=RelationType.RELATED_TO,
        )
        store.store_extractions([ExtractionResult(entities=[entity], edges=[edge])], document_id="doc-1")
        store.delete_document_data("doc-1")
        assert conn.execute("SELECT COUNT(*) FROM chunks WHERE document_id='doc-1'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM entities WHERE document_id='doc-1'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM edges WHERE document_id='doc-1'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM documents WHERE id='doc-1'").fetchone()[0] == 0

    def test_delete_document_data_removes_edges_by_document_id(self) -> None:
        """delete_document_data() removes edges whose provenance document is deleted."""
        conn = _make_migrated_conn()
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at)"
            " VALUES ('doc-1', 'Deleted Doc', '', '{}', '2025-01-01')"
        )
        conn.execute(
            "INSERT INTO documents (id, title, content, metadata, created_at)"
            " VALUES ('doc-2', 'Endpoint Doc', '', '{}', '2025-01-01')"
        )
        conn.commit()
        graph = GraphStore(conn)
        store = _make_document_store(conn)
        graph.insert_entity(Entity(id="ent-a", name="Alpha", entity_type=EntityType.CONCEPT, document_id="doc-2"))
        graph.insert_entity(Entity(id="ent-b", name="Beta", entity_type=EntityType.CONCEPT, document_id="doc-2"))
        graph.insert_edge(
            Edge(id="edge-doc-1", source_id="ent-a", target_id="ent-b", relation=RelationType.RELATED_TO),
            document_id="doc-1",
        )

        store.delete_document_data("doc-1")

        assert conn.execute("SELECT id FROM documents ORDER BY id").fetchall() == [("doc-2",)]
        assert conn.execute("SELECT id FROM entities ORDER BY id").fetchall() == [("ent-a",), ("ent-b",)]
        assert conn.execute("SELECT id FROM edges").fetchall() == []
