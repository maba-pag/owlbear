"""Tests for SqliteGraphStore — entities & edges (task #1873).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/graph.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/stores/graph.py

AC coverage:
  AC1  — upsert_entity: canonicalization, identity key, returns EntityRecord, ValueError on empty name
  AC2  — upsert_entity idempotency: same ID; metadata shallow-merge (CP25)
  AC3  — upsert_edge: identity key, ValueError on missing entities, ValueError on SAME_AS
  AC4  — get_entity: returns EntityRecord or None; alias_names empty when no aliases
  AC5  — find_entities: canonical name/type filters; alias resolution; limit; graceful degradation
  AC6  — get_adjacent: direction filtering; relation_types filter; empty for unknown entity
  AC7  — Table DDL: graph_entities + graph_edges; ensure_tables() idempotent
  AC8  — SqliteGraphStore is synchronous; constructor accepts sqlite3.Connection
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

import pytest

from owlbear_knowledge.protocols.common import EntityType, RelationType, canonicalize_name
from owlbear_knowledge.protocols.graph import (
    AdjacencyQuery,
    EdgeInput,
    EntityInput,
    EntityQuery,
    TraversalDirection,
)
from owlbear_knowledge.stores.graph import SqliteGraphStore  # greenfield — ImportError expected


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_entity(
    name: str = "Test Entity",
    entity_type: EntityType = EntityType.CONCEPT,
    **kwargs: object,
) -> EntityInput:
    return EntityInput(name=name, entity_type=entity_type, **kwargs)


def _mk_edge(
    src: str,
    tgt: str,
    relation_type: RelationType = RelationType.REFERENCES,
) -> EdgeInput:
    return EdgeInput(
        source_entity_id=src,
        target_entity_id=tgt,
        relation_type=relation_type,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


@pytest.fixture()
def store(db: sqlite3.Connection) -> SqliteGraphStore:
    s = SqliteGraphStore(db)
    s.ensure_tables()
    return s


@pytest.fixture()
def entity_a(store: SqliteGraphStore):
    """Upserted entity for edge/adjacency tests."""
    return store.upsert_entity(_mk_entity(name="Alpha", entity_type=EntityType.CONCEPT))


@pytest.fixture()
def entity_b(store: SqliteGraphStore):
    """Second upserted entity for edge/adjacency tests."""
    return store.upsert_entity(_mk_entity(name="Beta", entity_type=EntityType.TECHNOLOGY))


# ---------------------------------------------------------------------------
# TestFromAC_GraphStore
# ---------------------------------------------------------------------------


class TestFromAC_GraphStore:
    """AC-derived tests for SqliteGraphStore contract (AC1-AC8)."""

    # ------------------------------------------------------------------ AC1
    # upsert_entity → EntityRecord; canonical identity; ValueError on empty

    def test_upsert_entity_new_returns_entity_record(
        self, store: SqliteGraphStore
    ) -> None:
        """AC1: upsert_entity returns an EntityRecord for a new entity."""
        from owlbear_knowledge.protocols.graph import EntityRecord

        result = store.upsert_entity(_mk_entity("Python"))
        assert isinstance(result, EntityRecord)

    def test_upsert_entity_record_has_non_empty_id(self, store: SqliteGraphStore) -> None:
        """AC1: returned EntityRecord has a non-empty stable ID."""
        result = store.upsert_entity(_mk_entity("Python"))
        assert result.id
        assert len(result.id) > 0

    def test_upsert_entity_canonical_name_stored(self, store: SqliteGraphStore) -> None:
        """AC1: canonical_name in record equals canonicalize_name(name)."""
        raw = "  Python Language!  "
        result = store.upsert_entity(_mk_entity(raw))
        assert result.canonical_name == canonicalize_name(raw)

    def test_upsert_entity_entity_type_preserved(self, store: SqliteGraphStore) -> None:
        """AC1: entity_type is preserved in returned EntityRecord."""
        result = store.upsert_entity(_mk_entity("Go Lang", entity_type=EntityType.TECHNOLOGY))
        assert result.entity_type == EntityType.TECHNOLOGY

    def test_upsert_entity_empty_string_raises_value_error(
        self, store: SqliteGraphStore
    ) -> None:
        """AC1: ValueError when name is empty string after canonicalization."""
        with pytest.raises(ValueError):
            store.upsert_entity(_mk_entity(""))

    def test_upsert_entity_whitespace_only_name_raises_value_error(
        self, store: SqliteGraphStore
    ) -> None:
        """AC1: ValueError when name is whitespace-only (canonicalizes to empty)."""
        with pytest.raises(ValueError):
            store.upsert_entity(_mk_entity("   "))

    def test_upsert_entity_punctuation_only_name_raises_value_error(
        self, store: SqliteGraphStore
    ) -> None:
        """AC1 boundary: ValueError when name is punctuation-only (canonicalizes to empty)."""
        with pytest.raises(ValueError):
            store.upsert_entity(_mk_entity("..."))

    # ------------------------------------------------------------------ AC2
    # Idempotency: same ID on repeat; metadata shallow-merge (CP25)

    def test_upsert_entity_same_identity_returns_same_id(
        self, store: SqliteGraphStore
    ) -> None:
        """AC2: two upserts with same (canonical_name, entity_type) yield same ID."""
        e1 = store.upsert_entity(_mk_entity("Rust", entity_type=EntityType.TECHNOLOGY))
        e2 = store.upsert_entity(_mk_entity("Rust", entity_type=EntityType.TECHNOLOGY))
        assert e1.id == e2.id

    def test_upsert_entity_case_variant_same_identity(
        self, store: SqliteGraphStore
    ) -> None:
        """AC2: case variants that canonicalize to the same name yield same ID."""
        e1 = store.upsert_entity(_mk_entity("RUST", entity_type=EntityType.TECHNOLOGY))
        e2 = store.upsert_entity(_mk_entity("rust", entity_type=EntityType.TECHNOLOGY))
        assert e1.id == e2.id

    def test_upsert_entity_metadata_shallow_merged_adds_new_key(
        self, store: SqliteGraphStore
    ) -> None:
        """AC2: on update, metadata new keys are added to existing metadata (CP25)."""
        store.upsert_entity(_mk_entity("Rust", metadata={"lang": "systems"}))
        result = store.upsert_entity(_mk_entity("Rust", metadata={"version": "1.75"}))
        assert result.metadata.get("lang") == "systems"
        assert result.metadata.get("version") == "1.75"

    def test_upsert_entity_metadata_shallow_merged_overrides_existing_key(
        self, store: SqliteGraphStore
    ) -> None:
        """AC2: on update, existing metadata keys are overridden by new values (CP25 shallow merge)."""
        store.upsert_entity(_mk_entity("Rust", metadata={"version": "1.70"}))
        result = store.upsert_entity(_mk_entity("Rust", metadata={"version": "1.75"}))
        assert result.metadata["version"] == "1.75"

    # ------------------------------------------------------------------ AC3
    # upsert_edge → EdgeRecord; ValueError on missing src/tgt; ValueError on SAME_AS

    def test_upsert_edge_new_returns_edge_record(
        self,
        store: SqliteGraphStore,
        entity_a,
        entity_b,
    ) -> None:
        """AC3: upsert_edge returns an EdgeRecord for a new edge."""
        from owlbear_knowledge.protocols.graph import EdgeRecord

        result = store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))
        assert isinstance(result, EdgeRecord)

    def test_upsert_edge_missing_source_raises_value_error(
        self, store: SqliteGraphStore, entity_b
    ) -> None:
        """AC3: ValueError when source entity does not exist."""
        with pytest.raises(ValueError):
            store.upsert_edge(_mk_edge("nonexistent-id", entity_b.id))

    def test_upsert_edge_missing_target_raises_value_error(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC3: ValueError when target entity does not exist."""
        with pytest.raises(ValueError):
            store.upsert_edge(_mk_edge(entity_a.id, "nonexistent-id"))

    def test_upsert_edge_same_as_raises_value_error(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC3: ValueError if relation_type is SAME_AS (bypasses Pydantic to test store guard)."""
        # model_construct bypasses Pydantic validation — tests store-level guard
        bad_edge = EdgeInput.model_construct(
            source_entity_id=entity_a.id,
            target_entity_id=entity_b.id,
            relation_type="same_as",
            weight=1.0,
            metadata={},
        )
        with pytest.raises(ValueError):
            store.upsert_edge(bad_edge)

    def test_upsert_edge_identity_key_prevents_duplicates(
        self,
        store: SqliteGraphStore,
        entity_a,
        entity_b,
    ) -> None:
        """AC3: two upserts with same (src, tgt, relation_type) return same edge ID."""
        e1 = store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))
        e2 = store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))
        assert e1.id == e2.id

    # ------------------------------------------------------------------ AC4
    # get_entity: returns EntityRecord or None; alias_names empty when no aliases

    def test_get_entity_returns_entity_record(self, store: SqliteGraphStore) -> None:
        """AC4: get_entity returns EntityRecord for a known entity_id."""
        from owlbear_knowledge.protocols.graph import EntityRecord

        created = store.upsert_entity(_mk_entity("Django"))
        result = store.get_entity(created.id)
        assert isinstance(result, EntityRecord)
        assert result.id == created.id

    def test_get_entity_alias_names_empty_tuple_when_no_aliases(
        self, store: SqliteGraphStore
    ) -> None:
        """AC4: alias_names is empty tuple when no aliases exist for entity."""
        created = store.upsert_entity(_mk_entity("Flask"))
        result = store.get_entity(created.id)
        assert result is not None
        assert result.alias_names == ()

    def test_get_entity_returns_none_for_unknown_id(
        self, store: SqliteGraphStore
    ) -> None:
        """AC4: get_entity returns None for an unknown entity_id."""
        result = store.get_entity("00000000-0000-0000-0000-000000000000")
        assert result is None

    # ------------------------------------------------------------------ AC5
    # find_entities: filters; alias resolution; limit; graceful degradation

    def test_find_entities_by_canonical_name(self, store: SqliteGraphStore) -> None:
        """AC5: find_entities returns entity matching canonical name."""
        store.upsert_entity(_mk_entity("FastAPI"))
        results = store.find_entities(EntityQuery(name="fastapi"))
        assert len(results) >= 1
        assert any(r.canonical_name == "fastapi" for r in results)

    def test_find_entities_name_match_is_case_insensitive(
        self, store: SqliteGraphStore
    ) -> None:
        """AC5: name lookup is canonical (case-insensitive)."""
        store.upsert_entity(_mk_entity("FastAPI"))
        results = store.find_entities(EntityQuery(name="FASTAPI"))
        assert len(results) >= 1

    def test_find_entities_by_entity_type(self, store: SqliteGraphStore) -> None:
        """AC5: find_entities filters by entity_type."""
        store.upsert_entity(_mk_entity("Kafka", entity_type=EntityType.TECHNOLOGY))
        store.upsert_entity(_mk_entity("AWS", entity_type=EntityType.ORGANIZATION))
        results = store.find_entities(EntityQuery(entity_type=EntityType.TECHNOLOGY))
        types = {r.entity_type for r in results}
        assert EntityType.TECHNOLOGY in types
        assert EntityType.ORGANIZATION not in types

    def test_find_entities_by_name_and_type(self, store: SqliteGraphStore) -> None:
        """AC5: find_entities with both name and entity_type filters."""
        store.upsert_entity(_mk_entity("Redis", entity_type=EntityType.TECHNOLOGY))
        store.upsert_entity(_mk_entity("Redis Foundation", entity_type=EntityType.ORGANIZATION))
        results = store.find_entities(
            EntityQuery(name="redis", entity_type=EntityType.TECHNOLOGY)
        )
        assert len(results) == 1
        assert results[0].entity_type == EntityType.TECHNOLOGY

    def test_find_entities_returns_empty_tuple_on_no_match(
        self, store: SqliteGraphStore
    ) -> None:
        """AC5: returns empty tuple when no entities match."""
        results = store.find_entities(EntityQuery(name="xyzzy-not-found-42"))
        assert results == ()

    def test_find_entities_respects_limit(self, store: SqliteGraphStore) -> None:
        """AC5 boundary: find_entities respects query.limit."""
        for i in range(5):
            store.upsert_entity(_mk_entity(f"Entity {i}", entity_type=EntityType.CONCEPT))
        results = store.find_entities(EntityQuery(entity_type=EntityType.CONCEPT, limit=2))
        assert len(results) <= 2

    def test_find_entities_works_without_aliases_table(
        self, store: SqliteGraphStore
    ) -> None:
        """AC5 graceful degradation: find_entities works when graph_aliases table is absent."""
        # Default store fixture only creates graph_entities + graph_edges (AC7 scope).
        # Verify canonical-name search works without graph_aliases.
        store.upsert_entity(_mk_entity("Celery", entity_type=EntityType.TOOL))
        results = store.find_entities(EntityQuery(name="celery"))
        assert len(results) == 1

    def test_find_entities_includes_alias_match_when_aliases_table_exists(
        self, store: SqliteGraphStore, db: sqlite3.Connection
    ) -> None:
        """AC5: when graph_aliases table exists, find_entities resolves aliases."""
        entity = store.upsert_entity(_mk_entity("PostgreSQL", entity_type=EntityType.TECHNOLOGY))
        # Manually create graph_aliases table (managed by task #1874) and insert alias row
        db.execute(
            """CREATE TABLE IF NOT EXISTS graph_aliases (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                alias_name TEXT NOT NULL,
                canonical_alias TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        now = datetime.now(tz=UTC).isoformat()
        alias_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO graph_aliases VALUES (?, ?, ?, ?, ?)",
            (alias_id, entity.id, "Postgres", canonicalize_name("Postgres"), now),
        )
        db.commit()
        results = store.find_entities(EntityQuery(name="postgres"))
        assert any(r.id == entity.id for r in results)

    # ------------------------------------------------------------------ AC6
    # get_adjacent: direction / relation_type filter; empty for unknown entity

    def test_get_adjacent_returns_outgoing_edges(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC6: OUTGOING returns edges where queried entity is the source."""
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id, RelationType.DEPENDS_ON))
        results = store.get_adjacent(
            AdjacencyQuery(entity_id=entity_a.id, direction=TraversalDirection.OUTGOING)
        )
        assert len(results) == 1
        assert results[0].source_entity_id == entity_a.id

    def test_get_adjacent_returns_incoming_edges(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC6: INCOMING returns edges where queried entity is the target."""
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id, RelationType.DEPENDS_ON))
        results = store.get_adjacent(
            AdjacencyQuery(entity_id=entity_b.id, direction=TraversalDirection.INCOMING)
        )
        assert len(results) == 1
        assert results[0].target_entity_id == entity_b.id

    def test_get_adjacent_both_directions_includes_all_edges(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC6: BOTH direction returns edges regardless of source/target role."""
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id, RelationType.DEPENDS_ON))
        out = store.get_adjacent(
            AdjacencyQuery(entity_id=entity_a.id, direction=TraversalDirection.BOTH)
        )
        inc = store.get_adjacent(
            AdjacencyQuery(entity_id=entity_b.id, direction=TraversalDirection.BOTH)
        )
        assert len(out) >= 1
        assert len(inc) >= 1

    def test_get_adjacent_filters_by_relation_type(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC6: relation_types filter excludes non-matching edges."""
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id, RelationType.DEPENDS_ON))
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id, RelationType.MENTIONS))
        results = store.get_adjacent(
            AdjacencyQuery(
                entity_id=entity_a.id,
                direction=TraversalDirection.OUTGOING,
                relation_types=(RelationType.DEPENDS_ON,),
            )
        )
        assert all(r.relation_type == RelationType.DEPENDS_ON for r in results)

    def test_get_adjacent_returns_empty_tuple_for_unknown_entity(
        self, store: SqliteGraphStore
    ) -> None:
        """AC6: empty tuple returned for unknown entity_id — does not raise."""
        results = store.get_adjacent(
            AdjacencyQuery(
                entity_id="00000000-0000-0000-0000-000000000000",
                direction=TraversalDirection.BOTH,
            )
        )
        assert results == ()

    def test_get_adjacent_outgoing_excludes_incoming_only_edges(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC6: OUTGOING for entity_b is empty when only entity_a→entity_b edge exists."""
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))
        results = store.get_adjacent(
            AdjacencyQuery(entity_id=entity_b.id, direction=TraversalDirection.OUTGOING)
        )
        assert results == ()

    # ------------------------------------------------------------------ AC7
    # Table DDL: graph_entities + graph_edges; ensure_tables() idempotent

    def test_ensure_tables_creates_graph_entities_table(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: ensure_tables() creates graph_entities table."""
        s = SqliteGraphStore(db)
        s.ensure_tables()
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='graph_entities'"
        )
        assert cursor.fetchone() is not None

    def test_ensure_tables_creates_graph_edges_table(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: ensure_tables() creates graph_edges table."""
        s = SqliteGraphStore(db)
        s.ensure_tables()
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='graph_edges'"
        )
        assert cursor.fetchone() is not None

    def test_ensure_tables_is_idempotent(self, db: sqlite3.Connection) -> None:
        """AC7: calling ensure_tables() twice does not raise."""
        s = SqliteGraphStore(db)
        s.ensure_tables()
        s.ensure_tables()  # must not raise

    def test_graph_entities_has_unique_constraint_on_canonical_name_and_type(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7 boundary: graph_entities enforces UNIQUE (canonical_name, entity_type)."""
        SqliteGraphStore(db).ensure_tables()
        cursor = db.execute("PRAGMA index_list(graph_entities)")
        indexes = cursor.fetchall()
        has_unique = any("unique" in str(idx).lower() or idx[2] == 1 for idx in indexes)
        assert has_unique

    # ------------------------------------------------------------------ AC8
    # Synchronous; constructor accepts sqlite3.Connection

    def test_constructor_accepts_sqlite_connection(self, db: sqlite3.Connection) -> None:
        """AC8: SqliteGraphStore constructor accepts sqlite3.Connection."""
        s = SqliteGraphStore(db)
        assert s is not None

    def test_upsert_entity_is_synchronous(self, store: SqliteGraphStore) -> None:
        """AC8: upsert_entity is synchronous — calling without await returns a value."""
        import inspect

        result = store.upsert_entity(_mk_entity("SyncCheck"))
        assert not inspect.isawaitable(result), "upsert_entity must be synchronous"

    def test_upsert_edge_is_synchronous(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC8: upsert_edge is synchronous — calling without await returns a value."""
        import inspect

        result = store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))
        assert not inspect.isawaitable(result), "upsert_edge must be synchronous"

    # ---- Retry-gap tests (reviewer round 1) --------------------------------

    # AC1+AC2 gap: prove entity_type is part of the identity key

    def test_upsert_entity_same_name_different_type_yields_distinct_ids(
        self, store: SqliteGraphStore
    ) -> None:
        """AC1+AC2: same canonical name under two different entity_types produces distinct IDs.

        Proves that entity_type is a required component of the identity key; an
        implementation that used only canonical_name would produce the same ID for
        both calls and fail this assertion.
        """
        e_concept = store.upsert_entity(_mk_entity("Python", entity_type=EntityType.CONCEPT))
        e_tech = store.upsert_entity(_mk_entity("Python", entity_type=EntityType.TECHNOLOGY))
        assert e_concept.id != e_tech.id

    # AC4 gap: get_entity must hydrate alias_names from graph_aliases

    def test_get_entity_returns_alias_names_when_aliases_exist(
        self, store: SqliteGraphStore, db: sqlite3.Connection
    ) -> None:
        """AC4: get_entity populates alias_names when graph_aliases table exists and has rows.

        Distinct from the AC5 alias-search path: this verifies that get_entity itself
        reads and returns current alias_names, not just that aliases are searchable.
        """
        entity = store.upsert_entity(
            _mk_entity("PostgreSQL", entity_type=EntityType.TECHNOLOGY)
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_aliases (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                alias_name TEXT NOT NULL,
                canonical_alias TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        now = datetime.now(tz=UTC).isoformat()
        alias_id = str(uuid.uuid4())
        db.execute(
            "INSERT INTO graph_aliases VALUES (?, ?, ?, ?, ?)",
            (alias_id, entity.id, "Postgres", canonicalize_name("Postgres"), now),
        )
        db.commit()

        result = store.get_entity(entity.id)
        assert result is not None
        assert "Postgres" in result.alias_names

    # AC7 gap: graph_edges composite uniqueness and FK declarations

    def test_graph_edges_has_unique_constraint_on_composite_key(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_edges enforces UNIQUE(source_entity_id, target_entity_id, relation_type).

        Uses PRAGMA index_list to confirm a unique index exists on graph_edges.
        """
        SqliteGraphStore(db).ensure_tables()
        cursor = db.execute("PRAGMA index_list(graph_edges)")
        indexes = cursor.fetchall()
        has_unique = any(idx[2] == 1 for idx in indexes)
        assert has_unique, "graph_edges must declare a UNIQUE composite index"

    def test_graph_edges_declares_foreign_keys_to_graph_entities(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_edges FK constraints reference graph_entities for source and target.

        Uses PRAGMA foreign_key_list to inspect declared FK constraints.
        """
        SqliteGraphStore(db).ensure_tables()
        cursor = db.execute("PRAGMA foreign_key_list(graph_edges)")
        fks = cursor.fetchall()
        referenced_tables = {fk[2] for fk in fks}
        assert "graph_entities" in referenced_tables, (
            "graph_edges must declare FOREIGN KEY constraints referencing graph_entities"
        )

    # AC8 gap: BEGIN IMMEDIATE must be used explicitly in both upsert paths

    def test_upsert_entity_executes_begin_immediate_transaction(
        self, db: sqlite3.Connection
    ) -> None:
        """AC8: upsert_entity issues BEGIN IMMEDIATE, not the weaker BEGIN/BEGIN DEFERRED.

        Uses sqlite3.Connection.set_trace_callback to record every SQL statement
        issued during the upsert. If the implementation uses BEGIN or BEGIN DEFERRED,
        the assertion fails.
        """
        executed_sql: list[str] = []
        s = SqliteGraphStore(db)
        s.ensure_tables()
        db.set_trace_callback(executed_sql.append)
        try:
            s.upsert_entity(_mk_entity("TxnTest"))
        finally:
            db.set_trace_callback(None)
        assert any("BEGIN IMMEDIATE" in sql for sql in executed_sql), (
            "upsert_entity must use BEGIN IMMEDIATE, not BEGIN or BEGIN DEFERRED"
        )

    def test_upsert_edge_executes_begin_immediate_transaction(
        self, db: sqlite3.Connection
    ) -> None:
        """AC8: upsert_edge issues BEGIN IMMEDIATE, not the weaker BEGIN/BEGIN DEFERRED.

        Uses sqlite3.Connection.set_trace_callback to record every SQL statement
        issued during the upsert. If the implementation uses BEGIN or BEGIN DEFERRED,
        the assertion fails.
        """
        s_setup = SqliteGraphStore(db)
        s_setup.ensure_tables()
        e_a = s_setup.upsert_entity(_mk_entity("Alpha", entity_type=EntityType.CONCEPT))
        e_b = s_setup.upsert_entity(_mk_entity("Beta", entity_type=EntityType.TECHNOLOGY))

        executed_sql: list[str] = []
        db.set_trace_callback(executed_sql.append)
        try:
            s_setup.upsert_edge(_mk_edge(e_a.id, e_b.id))
        finally:
            db.set_trace_callback(None)
        assert any("BEGIN IMMEDIATE" in sql for sql in executed_sql), (
            "upsert_edge must use BEGIN IMMEDIATE, not BEGIN or BEGIN DEFERRED"
        )

    # ---- Retry-gap tests (reviewer round 2) --------------------------------

    # AC3 gap: prove the UPDATE half of upsert_edge — weight, metadata, updated_at

    def test_upsert_edge_update_replaces_weight_metadata_and_advances_updated_at(
        self,
        store: SqliteGraphStore,
        entity_a,
        entity_b,
    ) -> None:
        """AC3: second upsert with same edge identity replaces weight and metadata; updated_at > created_at.

        The existing idempotency test proves the ID is reused but never observes
        changed state. An implementation that returns the same EdgeRecord while
        ignoring the new weight or metadata would pass the old test but fail here.
        """
        import time

        first = store.upsert_edge(
            EdgeInput(
                source_entity_id=entity_a.id,
                target_entity_id=entity_b.id,
                relation_type=RelationType.REFERENCES,
                weight=0.5,
                metadata={"priority": "low"},
            )
        )
        time.sleep(0.001)  # ensure clock advances so updated_at > created_at
        updated = store.upsert_edge(
            EdgeInput(
                source_entity_id=entity_a.id,
                target_entity_id=entity_b.id,
                relation_type=RelationType.REFERENCES,
                weight=0.9,
                metadata={"priority": "high"},
            )
        )

        assert updated.id == first.id, "same identity must yield same edge ID on update"
        assert updated.weight == pytest.approx(0.9), "weight must be replaced from new EdgeInput"
        assert updated.metadata.get("priority") == "high", (
            "metadata must be replaced from new EdgeInput"
        )
        assert updated.updated_at > updated.created_at, (
            "updated_at must advance beyond created_at on update"
        )

    # AC7 gap: graph_entities UNIQUE index must cover exactly (canonical_name, entity_type)

    def test_graph_entities_unique_index_covers_exactly_canonical_name_and_entity_type(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_entities UNIQUE constraint covers exactly (canonical_name, entity_type).

        The prior test only asserts that some unique index exists. An impl with a
        unique index on only canonical_name, or one that adds extra columns, would
        pass the old test but fail here.
        """
        SqliteGraphStore(db).ensure_tables()
        idx_rows = db.execute("PRAGMA index_list(graph_entities)").fetchall()
        unique_indexes = [row for row in idx_rows if row[2] == 1]

        found = False
        for idx in unique_indexes:
            info_rows = db.execute(f"PRAGMA index_info({idx[1]})").fetchall()  # noqa: S608
            covered = {row[2] for row in info_rows}
            if covered == {"canonical_name", "entity_type"}:
                found = True
                break
        assert found, (
            "graph_entities must have a UNIQUE index covering exactly "
            "(canonical_name, entity_type)"
        )

    # AC8 gap: graph_edges UNIQUE index must cover exactly the three-column composite key
    # and both FK declarations must exist (not just one)

    def test_graph_edges_unique_index_covers_exactly_source_target_and_relation_type(
        self, db: sqlite3.Connection
    ) -> None:
        """AC8: graph_edges UNIQUE constraint covers exactly (source_entity_id, target_entity_id, relation_type).

        The prior test only asserts that some unique index exists. An impl missing
        one of the three columns, or carrying an extra column, would pass the old
        test but fail here.
        """
        SqliteGraphStore(db).ensure_tables()
        idx_rows = db.execute("PRAGMA index_list(graph_edges)").fetchall()
        unique_indexes = [row for row in idx_rows if row[2] == 1]
        expected = {"source_entity_id", "target_entity_id", "relation_type"}

        found = False
        for idx in unique_indexes:
            info_rows = db.execute(f"PRAGMA index_info({idx[1]})").fetchall()  # noqa: S608
            covered = {row[2] for row in info_rows}
            if covered == expected:
                found = True
                break
        assert found, (
            f"graph_edges must have a UNIQUE index covering exactly {expected}"
        )

    def test_graph_edges_source_entity_id_fk_references_graph_entities(
        self, db: sqlite3.Connection
    ) -> None:
        """AC8: FK source_entity_id → graph_entities.id must be explicitly declared.

        The prior FK test checks only that at least one FK references graph_entities;
        an impl with only the target FK (or no FK at all) could pass the old test.
        """
        SqliteGraphStore(db).ensure_tables()
        # PRAGMA foreign_key_list columns: (id, seq, table, from, to, ...)
        fk_rows = db.execute("PRAGMA foreign_key_list(graph_edges)").fetchall()
        found = any(fk[3] == "source_entity_id" and fk[2] == "graph_entities" for fk in fk_rows)
        assert found, "graph_edges must declare FK: source_entity_id → graph_entities"

    def test_graph_edges_target_entity_id_fk_references_graph_entities(
        self, db: sqlite3.Connection
    ) -> None:
        """AC8: FK target_entity_id → graph_entities.id must be explicitly declared.

        An impl with only the source_entity_id FK (missing the target FK) would
        pass the old test but fail here.
        """
        SqliteGraphStore(db).ensure_tables()
        fk_rows = db.execute("PRAGMA foreign_key_list(graph_edges)").fetchall()
        found = any(fk[3] == "target_entity_id" and fk[2] == "graph_entities" for fk in fk_rows)
        assert found, "graph_edges must declare FK: target_entity_id → graph_entities"
