"""Smoke tests for GraphStore.chunk_ids_for_entity (task #1887).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/graph.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/stores/graph.py

AC coverage (smoke — one test per AC line):
  AC1 — GraphStore protocol defines chunk_ids_for_entity(entity_id: str) -> tuple[str, ...]
         with four-section docstring
  AC2 — Returns distinct chunk_ids referencing entity_id; empty tuple for unknown; never raises
  AC3 — SqliteGraphStore queries SELECT DISTINCT chunk_id WHERE entity_id = ?; returns tuple[str, ...]
  AC4 — Returns empty tuple (not raises) when entity_id has no evidence records
"""

from __future__ import annotations

import inspect
import sqlite3
import uuid
from typing import get_type_hints

import pytest

from owlbear_knowledge.protocols.common import EntityType
from owlbear_knowledge.protocols.graph import (
    EntityInput,
    EvidenceClaimType,
    EvidenceInput,
    GraphStore,
)
from owlbear_knowledge.stores.graph import SqliteGraphStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_entity(name: str = "Smoke Entity", entity_type: EntityType = EntityType.CONCEPT) -> EntityInput:
    return EntityInput(name=name, entity_type=entity_type)


def _entity_evidence(chunk_id: str, entity_id: str) -> EvidenceInput:
    return EvidenceInput(
        chunk_id=chunk_id,
        claim_type=EvidenceClaimType.ENTITY,
        entity_id=entity_id,
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_ChunkIdsForEntity:
    """Smoke tests for GraphStore.chunk_ids_for_entity — one per AC line."""

    def test_protocol_defines_chunk_ids_for_entity(self) -> None:
        """AC1 — GraphStore protocol has a chunk_ids_for_entity method."""
        assert callable(getattr(GraphStore, "chunk_ids_for_entity", None)), (
            "GraphStore protocol must define chunk_ids_for_entity"
        )

    def test_protocol_chunk_ids_for_entity_signature(self) -> None:
        """AC1 — Protocol method has exact signature (self, entity_id: str) -> tuple[str, ...]."""
        sig = inspect.signature(GraphStore.chunk_ids_for_entity)
        hints = get_type_hints(GraphStore.chunk_ids_for_entity)

        assert "entity_id" in sig.parameters, "entity_id parameter must exist"
        assert hints.get("entity_id") is str, "entity_id must be annotated as str"
        assert hints.get("return") == tuple[str, ...], "return annotation must be tuple[str, ...]"

    def test_protocol_chunk_ids_for_entity_docstring_sections(self) -> None:
        """AC1 — Protocol method docstring contains all four required sections."""
        doc = GraphStore.chunk_ids_for_entity.__doc__ or ""
        for section in ("Guarantees", "Non-guarantees", "Side effects", "Raises"):
            assert section in doc, f"chunk_ids_for_entity docstring must contain '{section}' section"

    def test_chunk_ids_for_entity_returns_chunk_id_for_known_entity(self, store: SqliteGraphStore) -> None:
        """AC2 — Returns chunk_ids from evidence claims referencing entity_id."""
        entity = store.upsert_entity(_mk_entity())
        store.add_evidence(_entity_evidence(chunk_id="chunk-abc", entity_id=entity.id))

        result = store.chunk_ids_for_entity(entity.id)

        assert "chunk-abc" in result

    def test_chunk_ids_for_entity_returns_tuple_of_strings(self, store: SqliteGraphStore) -> None:
        """AC3 — SqliteGraphStore returns a tuple[str, ...] from graph_evidence query."""
        entity = store.upsert_entity(_mk_entity(name="String Check"))
        store.add_evidence(_entity_evidence(chunk_id="chunk-xyz", entity_id=entity.id))

        result = store.chunk_ids_for_entity(entity.id)

        assert isinstance(result, tuple)
        assert all(isinstance(c, str) for c in result)

    def test_chunk_ids_for_entity_distinct_deduplicates_repeated_rows(
        self, db: sqlite3.Connection, store: SqliteGraphStore
    ) -> None:
        """AC2/AC3 — SELECT DISTINCT suppresses duplicate chunk_id rows for same entity."""
        entity = store.upsert_entity(_mk_entity(name="Dup DISTINCT"))

        # Recreate graph_evidence without UNIQUE constraint to allow identical rows
        db.execute("ALTER TABLE graph_evidence RENAME TO _ge_bak")
        db.execute(
            """
            CREATE TABLE graph_evidence (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL,
                claim_type TEXT NOT NULL,
                entity_id TEXT,
                edge_id TEXT,
                confidence REAL NOT NULL DEFAULT 1.0,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute("INSERT INTO graph_evidence SELECT * FROM _ge_bak")
        db.execute("DROP TABLE _ge_bak")

        # Insert two rows with the same chunk_id and entity_id — bypasses UNIQUE
        for _ in range(2):
            db.execute(
                "INSERT INTO graph_evidence "
                "(id, chunk_id, claim_type, entity_id, edge_id, confidence, metadata_json, created_at) "
                "VALUES (?, 'chunk-dup', 'entity', ?, NULL, 1.0, '{}', datetime('now'))",
                (str(uuid.uuid4()), entity.id),
            )

        result = store.chunk_ids_for_entity(entity.id)

        assert result == ("chunk-dup",), f"SELECT DISTINCT must collapse duplicate chunk_id rows; got {result!r}"

    def test_protocol_chunk_ids_for_entity_exact_params(self) -> None:
        """AC1 — Protocol method has EXACTLY one parameter beyond self; no extra or missing params."""
        sig = inspect.signature(GraphStore.chunk_ids_for_entity)
        hints = get_type_hints(GraphStore.chunk_ids_for_entity)

        non_self_params = [k for k in sig.parameters if k != "self"]
        assert non_self_params == ["entity_id"], (
            f"chunk_ids_for_entity must have exactly one parameter beyond self (entity_id); got {non_self_params!r}"
        )
        assert hints.get("entity_id") is str, "entity_id must be annotated as str"
        assert hints.get("return") == tuple[str, ...], "return annotation must be tuple[str, ...]"

    def test_chunk_ids_for_entity_exact_set_multi_entity(self, store: SqliteGraphStore) -> None:
        """AC2 — Returns exact entity-scoped set; excludes chunks belonging only to other entities.

        Fixture: two entities share chunk-shared; each has one exclusive chunk.
        Proves WHERE entity_id = ? is load-bearing and result is the complete set.
        """
        entity_a = store.upsert_entity(_mk_entity(name="Entity A"))
        entity_b = store.upsert_entity(_mk_entity(name="Entity B"))

        # Entity A: chunk-a1 (exclusive) + chunk-shared (overlapping)
        store.add_evidence(_entity_evidence(chunk_id="chunk-a1", entity_id=entity_a.id))
        store.add_evidence(_entity_evidence(chunk_id="chunk-shared", entity_id=entity_a.id))

        # Entity B: chunk-b1 (exclusive) + chunk-shared (overlapping)
        store.add_evidence(_entity_evidence(chunk_id="chunk-b1", entity_id=entity_b.id))
        store.add_evidence(_entity_evidence(chunk_id="chunk-shared", entity_id=entity_b.id))

        result_a = store.chunk_ids_for_entity(entity_a.id)
        result_b = store.chunk_ids_for_entity(entity_b.id)

        assert set(result_a) == {"chunk-a1", "chunk-shared"}, (
            f"Entity A must return exactly {{chunk-a1, chunk-shared}}; got {set(result_a)!r}"
        )
        assert set(result_b) == {"chunk-b1", "chunk-shared"}, (
            f"Entity B must return exactly {{chunk-b1, chunk-shared}}; got {set(result_b)!r}"
        )

    def test_chunk_ids_for_entity_empty_tuple_for_unknown_entity(self, store: SqliteGraphStore) -> None:
        """AC4 — Returns empty tuple (not raises) for entity_id with no evidence."""
        result = store.chunk_ids_for_entity("nonexistent-entity-id-00000000")

        assert result == ()
