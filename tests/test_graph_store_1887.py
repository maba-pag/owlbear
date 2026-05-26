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

import sqlite3

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

    def test_chunk_ids_for_entity_returns_chunk_id_for_known_entity(
        self, store: SqliteGraphStore
    ) -> None:
        """AC2 — Returns chunk_ids from evidence claims referencing entity_id."""
        entity = store.upsert_entity(_mk_entity())
        store.add_evidence(_entity_evidence(chunk_id="chunk-abc", entity_id=entity.id))

        result = store.chunk_ids_for_entity(entity.id)

        assert "chunk-abc" in result

    def test_chunk_ids_for_entity_returns_tuple_of_strings(
        self, store: SqliteGraphStore
    ) -> None:
        """AC3 — SqliteGraphStore returns a tuple[str, ...] from graph_evidence query."""
        entity = store.upsert_entity(_mk_entity(name="String Check"))
        store.add_evidence(_entity_evidence(chunk_id="chunk-xyz", entity_id=entity.id))

        result = store.chunk_ids_for_entity(entity.id)

        assert isinstance(result, tuple)
        assert all(isinstance(c, str) for c in result)

    def test_chunk_ids_for_entity_empty_tuple_for_unknown_entity(
        self, store: SqliteGraphStore
    ) -> None:
        """AC4 — Returns empty tuple (not raises) for entity_id with no evidence."""
        result = store.chunk_ids_for_entity("nonexistent-entity-id-00000000")

        assert result == ()
