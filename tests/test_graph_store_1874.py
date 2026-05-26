"""Tests for SqliteGraphStore — evidence, aliases & traversal (task #1874).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/graph.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/stores/graph.py

AC coverage:
  AC1 — add_evidence: links chunk to entity/edge; idempotent; returns EvidenceRecord
  AC2 — claims_for_chunk: returns ChunkClaims; empty for unknown chunk_id
  AC3 — invalidate_evidence_by_chunks: hard-delete; orphan cascade; idempotent
  AC4 — add_alias: canonical storage; find_entities resolution; LookupError/ValueError
  AC5 — traverse: multi-hop; max_hops; relation_types filter; limit; LookupError
  AC6 — stats: returns GraphStats reflecting current graph_* table counts
  AC7 — ensure_tables: creates graph_evidence + graph_aliases; idempotent
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear_knowledge.protocols.common import EntityType, RelationType, canonicalize_name
from owlbear_knowledge.protocols.graph import (
    AdjacencyQuery,
    ChunkClaims,
    EdgeInput,
    EntityAliasInput,
    EntityAliasRecord,
    EntityInput,
    EntityQuery,
    EvidenceClaimType,
    EvidenceInput,
    EvidenceInvalidationResult,
    EvidenceRecord,
    GraphStats,
    TraversalQuery,
    TraversalResult,
)
from owlbear_knowledge.stores.graph import SqliteGraphStore


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


def _entity_evidence(
    chunk_id: str,
    entity_id: str,
    confidence: float = 1.0,
) -> EvidenceInput:
    return EvidenceInput(
        chunk_id=chunk_id,
        claim_type=EvidenceClaimType.ENTITY,
        entity_id=entity_id,
        confidence=confidence,
    )


def _edge_evidence(
    chunk_id: str,
    edge_id: str,
    confidence: float = 1.0,
) -> EvidenceInput:
    return EvidenceInput(
        chunk_id=chunk_id,
        claim_type=EvidenceClaimType.EDGE,
        edge_id=edge_id,
        confidence=confidence,
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
    return store.upsert_entity(_mk_entity(name="Alpha", entity_type=EntityType.CONCEPT))


@pytest.fixture()
def entity_b(store: SqliteGraphStore):
    return store.upsert_entity(_mk_entity(name="Beta", entity_type=EntityType.TECHNOLOGY))


@pytest.fixture()
def edge_ab(store: SqliteGraphStore, entity_a, entity_b):
    return store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))


# ---------------------------------------------------------------------------
# TestFromAC_AddEvidence — AC1
# ---------------------------------------------------------------------------


class TestFromAC_AddEvidence:
    """AC1: add_evidence links chunk to entity/edge; idempotent; returns EvidenceRecord."""

    # ------------------------------------------------------------------ happy

    def test_add_entity_evidence_returns_evidence_record(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC1 happy: entity claim → EvidenceRecord with correct fields."""
        result = store.add_evidence(_entity_evidence("chunk-1", entity_a.id))
        assert isinstance(result, EvidenceRecord)
        assert result.chunk_id == "chunk-1"
        assert result.claim_type == EvidenceClaimType.ENTITY
        assert result.entity_id == entity_a.id
        assert result.edge_id is None

    def test_add_edge_evidence_returns_evidence_record(
        self, store: SqliteGraphStore, edge_ab
    ) -> None:
        """AC1 happy: edge claim → EvidenceRecord with correct fields."""
        result = store.add_evidence(_edge_evidence("chunk-2", edge_ab.id))
        assert isinstance(result, EvidenceRecord)
        assert result.chunk_id == "chunk-2"
        assert result.claim_type == EvidenceClaimType.EDGE
        assert result.edge_id == edge_ab.id
        assert result.entity_id is None

    def test_add_evidence_idempotent_returns_same_id(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC1 edge: same (chunk_id, claim_type, target_id) → same evidence_id on repeat call."""
        ev1 = store.add_evidence(_entity_evidence("chunk-idem", entity_a.id))
        ev2 = store.add_evidence(_entity_evidence("chunk-idem", entity_a.id))
        assert ev1.id == ev2.id

    # ------------------------------------------------------------------ boundary

    def test_add_evidence_confidence_zero_accepted(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC1 boundary: confidence=0.0 is valid lower bound."""
        result = store.add_evidence(
            _entity_evidence("chunk-conf0", entity_a.id, confidence=0.0)
        )
        assert result.confidence == 0.0

    def test_add_evidence_confidence_one_accepted(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC1 boundary: confidence=1.0 is valid upper bound."""
        result = store.add_evidence(
            _entity_evidence("chunk-conf1", entity_a.id, confidence=1.0)
        )
        assert result.confidence == 1.0


# ---------------------------------------------------------------------------
# TestFromAC_ClaimsForChunk — AC2
# ---------------------------------------------------------------------------


class TestFromAC_ClaimsForChunk:
    """AC2: claims_for_chunk returns ChunkClaims; empty for unknown chunk_id."""

    # ------------------------------------------------------------------ happy

    def test_claims_for_chunk_returns_chunk_claims_instance(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC2 happy: claims_for_chunk returns a ChunkClaims instance."""
        store.add_evidence(_entity_evidence("chunk-a", entity_a.id))
        result = store.claims_for_chunk("chunk-a")
        assert isinstance(result, ChunkClaims)
        assert result.chunk_id == "chunk-a"

    def test_claims_for_chunk_includes_entity_id(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC2 happy: entity_ids contains the entity linked by the chunk."""
        store.add_evidence(_entity_evidence("chunk-ent", entity_a.id))
        result = store.claims_for_chunk("chunk-ent")
        assert entity_a.id in result.entity_ids

    def test_claims_for_chunk_includes_evidence_ids(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC2 happy: evidence_ids contains the evidence record ID."""
        ev = store.add_evidence(_entity_evidence("chunk-evid", entity_a.id))
        result = store.claims_for_chunk("chunk-evid")
        assert ev.id in result.evidence_ids

    def test_claims_for_chunk_empty_for_unknown_chunk(
        self, store: SqliteGraphStore
    ) -> None:
        """AC2 happy: empty ChunkClaims for an unknown chunk_id."""
        result = store.claims_for_chunk("nonexistent-chunk")
        assert isinstance(result, ChunkClaims)
        assert result.chunk_id == "nonexistent-chunk"
        assert result.entity_ids == ()
        assert result.edge_ids == ()
        assert result.evidence_ids == ()

    def test_claims_for_chunk_includes_edge_id(
        self, store: SqliteGraphStore, edge_ab
    ) -> None:
        """AC2 edge: edge_ids populated when chunk claims an edge."""
        store.add_evidence(_edge_evidence("chunk-edge", edge_ab.id))
        result = store.claims_for_chunk("chunk-edge")
        assert edge_ab.id in result.edge_ids

    def test_claims_for_chunk_mixed_entity_and_edge_claims(
        self, store: SqliteGraphStore, entity_a, edge_ab
    ) -> None:
        """AC2 edge: chunk with both entity and edge claims — both present in ChunkClaims."""
        store.add_evidence(_entity_evidence("chunk-mixed", entity_a.id))
        store.add_evidence(_edge_evidence("chunk-mixed", edge_ab.id))
        result = store.claims_for_chunk("chunk-mixed")
        assert entity_a.id in result.entity_ids
        assert edge_ab.id in result.edge_ids


# ---------------------------------------------------------------------------
# TestFromAC_InvalidateEvidenceByChunks — AC3
# ---------------------------------------------------------------------------


class TestFromAC_InvalidateEvidenceByChunks:
    """AC3: invalidate_evidence_by_chunks hard-deletes; orphan cascade; idempotent."""

    # ------------------------------------------------------------------ happy

    def test_invalidate_returns_evidence_invalidation_result(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC3 happy: returns EvidenceInvalidationResult."""
        store.add_evidence(_entity_evidence("chunk-r", entity_a.id))
        result = store.invalidate_evidence_by_chunks(("chunk-r",))
        assert isinstance(result, EvidenceInvalidationResult)

    def test_invalidate_reports_invalidated_evidence_ids(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC3 happy: invalidated_evidence_ids contains the deleted evidence record ID."""
        ev = store.add_evidence(_entity_evidence("chunk-del-ev", entity_a.id))
        result = store.invalidate_evidence_by_chunks(("chunk-del-ev",))
        assert ev.id in result.invalidated_evidence_ids

    def test_invalidate_orphans_entity_with_no_remaining_evidence(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC3 happy: entity with zero remaining evidence appears in orphaned_entity_ids."""
        store.add_evidence(_entity_evidence("chunk-orphan-ent", entity_a.id))
        result = store.invalidate_evidence_by_chunks(("chunk-orphan-ent",))
        assert entity_a.id in result.orphaned_entity_ids

    def test_invalidate_orphaned_entity_is_deleted_from_graph(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC3 happy: orphaned entity is hard-deleted — get_entity returns None after."""
        store.add_evidence(_entity_evidence("chunk-del-ent", entity_a.id))
        store.invalidate_evidence_by_chunks(("chunk-del-ent",))
        assert store.get_entity(entity_a.id) is None

    def test_invalidate_orphans_edge_with_no_remaining_evidence(
        self, store: SqliteGraphStore, entity_a, entity_b, edge_ab
    ) -> None:
        """AC3 happy: edge with zero remaining evidence appears in orphaned_edge_ids."""
        store.add_evidence(_entity_evidence("chunk-keep-a", entity_a.id))
        store.add_evidence(_entity_evidence("chunk-keep-b", entity_b.id))
        store.add_evidence(_edge_evidence("chunk-del-edge", edge_ab.id))
        result = store.invalidate_evidence_by_chunks(("chunk-del-edge",))
        assert edge_ab.id in result.orphaned_edge_ids

    # ------------------------------------------------------------------ cascade

    def test_invalidate_cascades_aliases_of_orphaned_entity(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC3 cascade: aliases of orphaned entity are deleted."""
        store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name="Alpha Alias"))
        store.add_evidence(_entity_evidence("chunk-alias-casc", entity_a.id))
        store.invalidate_evidence_by_chunks(("chunk-alias-casc",))
        # entity_a is orphaned; alias should be gone
        found = store.find_entities(EntityQuery(name="Alpha Alias"))
        assert found == ()

    def test_invalidate_cascades_edges_referencing_orphaned_entity(
        self, store: SqliteGraphStore, entity_a, entity_b, edge_ab
    ) -> None:
        """AC3 cascade: edges referencing an orphaned entity are also deleted."""
        store.add_evidence(_entity_evidence("chunk-ent-b-keep", entity_b.id))
        store.add_evidence(_entity_evidence("chunk-ent-a-del", entity_a.id))
        store.invalidate_evidence_by_chunks(("chunk-ent-a-del",))
        # entity_a is orphaned → edge_ab should be gone
        adj = store.get_adjacent(AdjacencyQuery(entity_id=entity_b.id))
        assert all(e.id != edge_ab.id for e in adj)

    # ------------------------------------------------------------------ edge

    def test_invalidate_entity_not_orphaned_when_other_evidence_remains(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC3 edge: entity with evidence from two chunks; invalidate one → entity survives."""
        store.add_evidence(_entity_evidence("chunk-keep-1", entity_a.id))
        store.add_evidence(_entity_evidence("chunk-keep-2", entity_a.id))
        result = store.invalidate_evidence_by_chunks(("chunk-keep-1",))
        assert entity_a.id not in result.orphaned_entity_ids
        assert store.get_entity(entity_a.id) is not None

    def test_invalidate_idempotent_for_absent_chunk_ids(
        self, store: SqliteGraphStore
    ) -> None:
        """AC3 edge: absent chunk_ids are silently ignored — returns empty result."""
        result = store.invalidate_evidence_by_chunks(("no-such-chunk-xyz",))
        assert isinstance(result, EvidenceInvalidationResult)
        assert result.invalidated_evidence_ids == ()

    def test_invalidate_empty_chunk_ids_is_no_op(
        self, store: SqliteGraphStore
    ) -> None:
        """AC3 edge: empty chunk_ids tuple → no-op result with all empty tuples."""
        result = store.invalidate_evidence_by_chunks(())
        assert isinstance(result, EvidenceInvalidationResult)
        assert result.invalidated_evidence_ids == ()
        assert result.orphaned_entity_ids == ()
        assert result.orphaned_edge_ids == ()


# ---------------------------------------------------------------------------
# TestFromAC_AddAlias — AC4
# ---------------------------------------------------------------------------


class TestFromAC_AddAlias:
    """AC4: add_alias canonical storage; find_entities resolution; LookupError/ValueError."""

    # ------------------------------------------------------------------ happy

    def test_add_alias_returns_entity_alias_record(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC4 happy: add_alias returns EntityAliasRecord with correct entity_id."""
        result = store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name="A-alias"))
        assert isinstance(result, EntityAliasRecord)
        assert result.entity_id == entity_a.id

    def test_add_alias_stores_canonical_form(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC4 happy: canonical_alias stored equals canonicalize_name(alias_name)."""
        raw = "  Alpha-ALIAS!  "
        result = store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name=raw))
        assert result.canonical_alias == canonicalize_name(raw)

    def test_add_alias_find_entities_resolves_alias_transparently(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC4 happy: find_entities finds the entity by its alias name."""
        store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name="Alpha Prime"))
        results = store.find_entities(EntityQuery(name="Alpha Prime"))
        assert len(results) >= 1
        assert any(r.id == entity_a.id for r in results)

    def test_add_alias_idempotent_for_same_entity_and_alias(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC4 happy: duplicate (entity_id, canonical_alias) is idempotent — same record ID."""
        r1 = store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name="Alias-X"))
        r2 = store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name="Alias-X"))
        assert r1.id == r2.id

    # ------------------------------------------------------------------ error

    def test_add_alias_raises_lookup_error_for_missing_entity(
        self, store: SqliteGraphStore
    ) -> None:
        """AC4 error: LookupError if entity_id does not exist."""
        with pytest.raises(LookupError):
            store.add_alias(
                EntityAliasInput(entity_id="nonexistent-entity-id", alias_name="Orphan-Alias")
            )

    def test_add_alias_raises_value_error_for_empty_alias_after_canonicalization(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC4 error: ValueError if alias_name is empty after canonicalization."""
        # "..." → strips trailing punctuation → empty string
        with pytest.raises(ValueError):
            store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name="..."))

    def test_add_alias_raises_value_error_if_conflicts_with_different_entity_canonical_name(
        self, store: SqliteGraphStore, entity_a, entity_b  # noqa: ARG002
    ) -> None:
        """AC4 error: ValueError if alias canonical form equals another entity's canonical_name."""
        # entity_b must exist in the DB so the store can detect the canonical_name conflict
        # entity_b canonical_name == canonicalize_name("Beta") == "beta"
        with pytest.raises(ValueError):
            store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name="Beta"))


# ---------------------------------------------------------------------------
# TestFromAC_Traverse — AC5
# ---------------------------------------------------------------------------


class TestFromAC_Traverse:
    """AC5: traverse — multi-hop; max_hops; relation_types filter; limit; LookupError."""

    # ------------------------------------------------------------------ happy

    def test_traverse_single_hop_returns_traversal_result(
        self, store: SqliteGraphStore, entity_a, edge_ab  # noqa: ARG002
    ) -> None:
        """AC5 happy: single-hop traversal returns TraversalResult."""
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=1))
        assert isinstance(result, TraversalResult)

    def test_traverse_includes_directly_connected_entity(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC5 happy: directly connected entity appears in traversal entities."""
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=1))
        entity_ids = {e.id for e in result.entities}
        assert entity_b.id in entity_ids

    def test_traverse_includes_directly_connected_edge(
        self, store: SqliteGraphStore, entity_a, edge_ab
    ) -> None:
        """AC5 happy: connecting edge appears in traversal edges."""
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=1))
        edge_ids = {e.id for e in result.edges}
        assert edge_ab.id in edge_ids

    def test_traverse_multi_hop_reaches_distant_entity(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC5 happy: two-hop traversal reaches entity two hops from seed."""
        entity_c = store.upsert_entity(_mk_entity("Gamma", entity_type=EntityType.CONCEPT))
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))
        store.upsert_edge(_mk_edge(entity_b.id, entity_c.id))
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=2))
        entity_ids = {e.id for e in result.entities}
        assert entity_c.id in entity_ids

    def test_traverse_max_hops_one_does_not_reach_two_hop_entity(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC5 happy: max_hops=1 stops before entity two hops away."""
        entity_c = store.upsert_entity(_mk_entity("Gamma-Hop2", entity_type=EntityType.CONCEPT))
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id))
        store.upsert_edge(_mk_edge(entity_b.id, entity_c.id))
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=1))
        entity_ids = {e.id for e in result.entities}
        assert entity_c.id not in entity_ids

    def test_traverse_relation_types_filter_excludes_unmatched_edges(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC5 happy: relation_types filter omits edges not in the filter set."""
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id, RelationType.REFERENCES))
        entity_c = store.upsert_entity(_mk_entity("Gamma-RT", entity_type=EntityType.CONCEPT))
        store.upsert_edge(_mk_edge(entity_a.id, entity_c.id, RelationType.DEPENDS_ON))
        result = store.traverse(
            TraversalQuery(
                entity_id=entity_a.id,
                max_hops=1,
                relation_types=(RelationType.REFERENCES,),
            )
        )
        # All returned edges must match the filter
        for edge in result.edges:
            assert edge.relation_type == RelationType.REFERENCES
        # entity_c is only reachable via DEPENDS_ON → must not appear
        entity_ids = {e.id for e in result.entities}
        assert entity_c.id not in entity_ids

    def test_traverse_total_size_respects_limit(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC5 boundary: total result size (entities + edges) <= query.limit."""
        for i in range(10):
            nbr = store.upsert_entity(_mk_entity(f"LimitNode-{i}", entity_type=EntityType.CONCEPT))
            store.upsert_edge(_mk_edge(entity_a.id, nbr.id))
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=1, limit=5))
        assert len(result.entities) + len(result.edges) <= 5

    def test_traverse_no_duplicate_entities_in_result(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC5 happy: no duplicate entities even when multiple paths lead to same entity."""
        entity_c = store.upsert_entity(_mk_entity("Gamma-Dup", entity_type=EntityType.CONCEPT))
        # Two paths from entity_a to entity_b (direct + via entity_c)
        store.upsert_edge(_mk_edge(entity_a.id, entity_b.id, RelationType.REFERENCES))
        store.upsert_edge(_mk_edge(entity_a.id, entity_c.id, RelationType.REFERENCES))
        store.upsert_edge(_mk_edge(entity_c.id, entity_b.id, RelationType.REFERENCES))
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=2))
        entity_ids = [e.id for e in result.entities]
        assert len(entity_ids) == len(set(entity_ids))

    def test_traverse_no_duplicate_edges_in_result(
        self, store: SqliteGraphStore, entity_a, edge_ab  # noqa: ARG002
    ) -> None:
        """AC5 happy: no duplicate edges in result."""
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=2))
        edge_ids = [e.id for e in result.edges]
        assert len(edge_ids) == len(set(edge_ids))

    # ------------------------------------------------------------------ error

    def test_traverse_raises_lookup_error_for_nonexistent_seed(
        self, store: SqliteGraphStore
    ) -> None:
        """AC5 error: LookupError if seed entity_id does not exist."""
        with pytest.raises(LookupError):
            store.traverse(TraversalQuery(entity_id="nonexistent-seed-entity-id"))

    # ------------------------------------------------------------------ edge

    def test_traverse_seed_with_no_edges_returns_no_edges(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC5 edge: seed entity has no edges — traversal result contains no edges."""
        result = store.traverse(TraversalQuery(entity_id=entity_a.id, max_hops=1))
        assert result.edges == ()


# ---------------------------------------------------------------------------
# TestFromAC_Stats — AC6
# ---------------------------------------------------------------------------


class TestFromAC_Stats:
    """AC6: stats returns GraphStats reflecting current graph_* table counts."""

    def test_stats_returns_graph_stats_instance(self, store: SqliteGraphStore) -> None:
        """AC6 happy: stats() returns a GraphStats instance."""
        result = store.stats()
        assert isinstance(result, GraphStats)

    def test_stats_empty_store_all_zero_counts(self, store: SqliteGraphStore) -> None:
        """AC6 happy: empty store → all counts are zero."""
        result = store.stats()
        assert result.entities == 0
        assert result.edges == 0
        assert result.evidence_claims == 0
        assert result.aliases == 0

    def test_stats_reflects_entity_count(self, store: SqliteGraphStore) -> None:
        """AC6 happy: entities count reflects upserted entities."""
        store.upsert_entity(_mk_entity("StatsEnt1"))
        store.upsert_entity(_mk_entity("StatsEnt2"))
        result = store.stats()
        assert result.entities >= 2

    def test_stats_reflects_edge_count(self, store: SqliteGraphStore) -> None:
        """AC6 happy: edges count reflects upserted edges."""
        a = store.upsert_entity(_mk_entity("StatsEdgeA"))
        b = store.upsert_entity(_mk_entity("StatsEdgeB"))
        store.upsert_edge(_mk_edge(a.id, b.id))
        result = store.stats()
        assert result.edges >= 1

    def test_stats_reflects_evidence_count(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC6 happy: evidence_claims count reflects added evidence records."""
        store.add_evidence(_entity_evidence("chunk-stat-ev", entity_a.id))
        result = store.stats()
        assert result.evidence_claims >= 1

    def test_stats_reflects_alias_count(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC6 happy: aliases count reflects added alias records."""
        store.add_alias(EntityAliasInput(entity_id=entity_a.id, alias_name="Stat-Alias"))
        result = store.stats()
        assert result.aliases >= 1


# ---------------------------------------------------------------------------
# TestFromAC_EnsureTablesExtended — AC7
# ---------------------------------------------------------------------------


class TestFromAC_EnsureTablesExtended:
    """AC7: ensure_tables creates graph_evidence + graph_aliases; idempotent."""

    def test_ensure_tables_creates_graph_evidence_table(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7 happy: graph_evidence table exists after ensure_tables."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_evidence'"
        ).fetchone()
        assert row is not None, "graph_evidence table was not created by ensure_tables"

    def test_ensure_tables_creates_graph_aliases_table(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7 happy: graph_aliases table exists after ensure_tables."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='graph_aliases'"
        ).fetchone()
        assert row is not None, "graph_aliases table was not created by ensure_tables"

    def test_ensure_tables_idempotent_creates_all_tables_on_second_call(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7 happy: calling ensure_tables twice does not raise and new tables still exist."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        store.ensure_tables()  # must not raise
        tables = {
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "graph_evidence" in tables
        assert "graph_aliases" in tables

    def test_ensure_tables_graph_evidence_has_index_on_chunk_id(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7 edge: graph_evidence has an explicit index on chunk_id column."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        indexes = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='graph_evidence'"
        ).fetchall()
        chunk_id_indexed = False
        for (idx_name,) in indexes:
            cols = db.execute(f'PRAGMA index_info("{idx_name}")').fetchall()
            if any(col[2] == "chunk_id" for col in cols):
                chunk_id_indexed = True
                break
        assert chunk_id_indexed, (
            f"No index on chunk_id found in graph_evidence. "
            f"Indexes: {[r[0] for r in indexes]}"
        )

    def test_ensure_tables_graph_aliases_unique_constraint_rejects_duplicate(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7 edge: graph_aliases UNIQUE(entity_id, canonical_alias) rejects duplicate rows."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        db.execute("PRAGMA foreign_keys = OFF")
        now = "2026-01-01T00:00:00+00:00"
        db.execute(
            "INSERT INTO graph_aliases (id, entity_id, alias_name, canonical_alias, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            ("id1", "ent1", "alias-one", "alias-one", now),
        )
        db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO graph_aliases (id, entity_id, alias_name, canonical_alias, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                ("id2", "ent1", "alias-one", "alias-one", now),  # same entity_id + canonical_alias
            )


# ---------------------------------------------------------------------------
# Retry-gap tests — reviewer round 1 findings
# ---------------------------------------------------------------------------

# Finding #1 — AC1: XOR validator contract and update-branch proof


class TestFromAC_AddEvidence_XorAndUpdate:
    """AC1 retry gaps: XOR model_validator rejection and confidence-update on repeat call."""

    # ------------------------------------------------------------------ error: XOR violations

    def test_evidence_input_entity_claim_with_edge_id_raises_value_error(self) -> None:
        """AC1 error: ENTITY claim_type with edge_id set violates XOR — ValueError at construction."""
        with pytest.raises(ValueError, match="ENTITY"):
            EvidenceInput(
                chunk_id="chunk-x",
                claim_type=EvidenceClaimType.ENTITY,
                edge_id="some-edge-id",  # XOR violation: entity claim must not have edge_id
            )

    def test_evidence_input_edge_claim_with_entity_id_raises_value_error(self) -> None:
        """AC1 error: EDGE claim_type with entity_id set violates XOR — ValueError at construction."""
        with pytest.raises(ValueError, match="EDGE"):
            EvidenceInput(
                chunk_id="chunk-x",
                claim_type=EvidenceClaimType.EDGE,
                entity_id="some-entity-id",  # XOR violation: edge claim must not have entity_id
            )

    def test_evidence_input_entity_claim_without_entity_id_raises_value_error(self) -> None:
        """AC1 error: ENTITY claim_type with no entity_id raises ValueError (XOR unmet)."""
        with pytest.raises(ValueError, match="ENTITY"):
            EvidenceInput(
                chunk_id="chunk-x",
                claim_type=EvidenceClaimType.ENTITY,
                # entity_id omitted — XOR violation
            )

    def test_evidence_input_edge_claim_without_edge_id_raises_value_error(self) -> None:
        """AC1 error: EDGE claim_type with no edge_id raises ValueError (XOR unmet)."""
        with pytest.raises(ValueError, match="EDGE"):
            EvidenceInput(
                chunk_id="chunk-x",
                claim_type=EvidenceClaimType.EDGE,
                # edge_id omitted — XOR violation
            )

    # ------------------------------------------------------------------ update branch

    def test_add_evidence_repeat_call_updates_confidence_mutable_field(
        self, store: SqliteGraphStore, entity_a
    ) -> None:
        """AC1: repeated add_evidence with same identity but different confidence updates the record.

        The existing idempotency test proves the ID is reused but never observes changed
        state. An implementation that ignores the new confidence on update would still pass
        the existing test; this test catches that regression.
        """
        first = store.add_evidence(
            EvidenceInput(
                chunk_id="chunk-upd",
                claim_type=EvidenceClaimType.ENTITY,
                entity_id=entity_a.id,
                confidence=0.3,
            )
        )
        updated = store.add_evidence(
            EvidenceInput(
                chunk_id="chunk-upd",
                claim_type=EvidenceClaimType.ENTITY,
                entity_id=entity_a.id,
                confidence=0.9,  # different confidence on same identity
            )
        )
        assert updated.id == first.id, "same identity must yield the same evidence ID"
        assert updated.confidence == pytest.approx(0.9), (
            "confidence must be updated when add_evidence is called again with same identity"
        )


# Finding #2 — AC6: exact counts in isolated fixtures


class TestFromAC_Stats_ExactCounts:
    """AC6 retry gaps: exact count assertions for each graph_* table in isolated stores.

    The original suite uses >= assertions. An implementation that overcounts rows
    (e.g. emits duplicates via a JOIN) would still pass those assertions but fails here.
    """

    def test_stats_exact_entity_count(self, db: sqlite3.Connection) -> None:
        """AC6: after inserting exactly 2 entities, entities == 2 (not >= 2)."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        store.upsert_entity(_mk_entity("ExactEnt1"))
        store.upsert_entity(_mk_entity("ExactEnt2"))
        result = store.stats()
        assert result.entities == 2, (
            f"expected exactly 2 entities, got {result.entities}"
        )

    def test_stats_exact_edge_count(self, db: sqlite3.Connection) -> None:
        """AC6: after inserting exactly 1 edge, edges == 1 (not >= 1)."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        a = store.upsert_entity(_mk_entity("ExactEdgeA"))
        b = store.upsert_entity(_mk_entity("ExactEdgeB"))
        store.upsert_edge(_mk_edge(a.id, b.id))
        result = store.stats()
        assert result.edges == 1, (
            f"expected exactly 1 edge, got {result.edges}"
        )

    def test_stats_exact_evidence_count(self, db: sqlite3.Connection) -> None:
        """AC6: after inserting exactly 1 evidence record, evidence_claims == 1 (not >= 1)."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        ent = store.upsert_entity(_mk_entity("ExactEvEnt"))
        store.add_evidence(_entity_evidence("chunk-exact-ev", ent.id))
        result = store.stats()
        assert result.evidence_claims == 1, (
            f"expected exactly 1 evidence_claim, got {result.evidence_claims}"
        )

    def test_stats_exact_alias_count(self, db: sqlite3.Connection) -> None:
        """AC6: after adding exactly 1 alias, aliases == 1 (not >= 1)."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        ent = store.upsert_entity(_mk_entity("ExactAliasEnt"))
        store.add_alias(EntityAliasInput(entity_id=ent.id, alias_name="ExactAlias"))
        result = store.stats()
        assert result.aliases == 1, (
            f"expected exactly 1 alias, got {result.aliases}"
        )


# Finding #3 — AC7: missing index and FK coverage


class TestFromAC_EnsureTablesExtended_IndexAndFK:
    """AC7 retry gaps: indexes on graph_evidence entity_id/edge_id, graph_aliases
    canonical_alias, and FK declarations for both new tables.

    The original suite covers only the chunk_id index and alias uniqueness.
    """

    def test_ensure_tables_graph_evidence_has_index_on_entity_id(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_evidence has an explicit index on entity_id column."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        indexes = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='graph_evidence'"
        ).fetchall()
        entity_id_indexed = False
        for (idx_name,) in indexes:
            cols = db.execute(f'PRAGMA index_info("{idx_name}")').fetchall()  # noqa: S608
            if any(col[2] == "entity_id" for col in cols):
                entity_id_indexed = True
                break
        assert entity_id_indexed, (
            f"No index on entity_id found in graph_evidence. "
            f"Indexes: {[r[0] for r in indexes]}"
        )

    def test_ensure_tables_graph_evidence_has_index_on_edge_id(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_evidence has an explicit index on edge_id column."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        indexes = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='graph_evidence'"
        ).fetchall()
        edge_id_indexed = False
        for (idx_name,) in indexes:
            cols = db.execute(f'PRAGMA index_info("{idx_name}")').fetchall()  # noqa: S608
            if any(col[2] == "edge_id" for col in cols):
                edge_id_indexed = True
                break
        assert edge_id_indexed, (
            f"No index on edge_id found in graph_evidence. "
            f"Indexes: {[r[0] for r in indexes]}"
        )

    def test_ensure_tables_graph_aliases_has_index_on_canonical_alias(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_aliases has an explicit index on canonical_alias column."""
        store = SqliteGraphStore(db)
        store.ensure_tables()
        indexes = db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='graph_aliases'"
        ).fetchall()
        canonical_alias_indexed = False
        for (idx_name,) in indexes:
            cols = db.execute(f'PRAGMA index_info("{idx_name}")').fetchall()  # noqa: S608
            if any(col[2] == "canonical_alias" for col in cols):
                canonical_alias_indexed = True
                break
        assert canonical_alias_indexed, (
            f"No index on canonical_alias found in graph_aliases. "
            f"Indexes: {[r[0] for r in indexes]}"
        )

    def test_ensure_tables_graph_evidence_fk_entity_id_references_graph_entities(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_evidence.entity_id declares FK referencing graph_entities.

        Uses PRAGMA foreign_key_list to verify the declared FK — mirrors the
        pattern established in test_graph_store_1873.py for graph_edges FKs.
        """
        SqliteGraphStore(db).ensure_tables()
        fk_rows = db.execute("PRAGMA foreign_key_list(graph_evidence)").fetchall()
        found = any(fk[3] == "entity_id" and fk[2] == "graph_entities" for fk in fk_rows)
        assert found, "graph_evidence must declare FK: entity_id → graph_entities"

    def test_ensure_tables_graph_evidence_fk_edge_id_references_graph_edges(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_evidence.edge_id declares FK referencing graph_edges."""
        SqliteGraphStore(db).ensure_tables()
        fk_rows = db.execute("PRAGMA foreign_key_list(graph_evidence)").fetchall()
        found = any(fk[3] == "edge_id" and fk[2] == "graph_edges" for fk in fk_rows)
        assert found, "graph_evidence must declare FK: edge_id → graph_edges"

    def test_ensure_tables_graph_aliases_fk_entity_id_references_graph_entities(
        self, db: sqlite3.Connection
    ) -> None:
        """AC7: graph_aliases.entity_id declares FK referencing graph_entities."""
        SqliteGraphStore(db).ensure_tables()
        fk_rows = db.execute("PRAGMA foreign_key_list(graph_aliases)").fetchall()
        found = any(fk[3] == "entity_id" and fk[2] == "graph_entities" for fk in fk_rows)
        assert found, "graph_aliases must declare FK: entity_id → graph_entities"


# ---------------------------------------------------------------------------
# Retry-gap tests — reviewer round 2 finding
# ---------------------------------------------------------------------------

# Finding #1 (round 2) — AC2: chunk-scoped exclusivity


class TestFromAC_ClaimsForChunk_Exclusivity:
    """AC2 retry gap (cycle 3): claims_for_chunk must exclude IDs linked via other chunks.

    The prior tests prove that expected IDs appear for a known chunk and that an unknown
    chunk returns empty. They do not prove isolation — a regression that leaked IDs from
    another chunk's evidence would still pass the prior suite.

    Architect refined AC2: 'IDs linked via other chunks are excluded.'
    """

    def test_claims_for_chunk_excludes_entity_ids_from_other_chunk(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC2: entity_id linked only via chunk-B must not appear in claims_for_chunk('chunk-A')."""
        store.add_evidence(_entity_evidence("chunk-A", entity_a.id))
        store.add_evidence(_entity_evidence("chunk-B", entity_b.id))
        result = store.claims_for_chunk("chunk-A")
        assert entity_b.id not in result.entity_ids, (
            "entity linked only via chunk-B must not appear in claims for chunk-A"
        )

    def test_claims_for_chunk_excludes_edge_ids_from_other_chunk(
        self, store: SqliteGraphStore, entity_a, entity_b, edge_ab
    ) -> None:
        """AC2: edge_id linked only via chunk-B must not appear in claims_for_chunk('chunk-A')."""
        store.add_evidence(_entity_evidence("chunk-A", entity_a.id))
        store.add_evidence(_edge_evidence("chunk-B", edge_ab.id))
        # entity_b must have evidence so it is not orphaned during this test
        store.add_evidence(_entity_evidence("chunk-B", entity_b.id))
        result = store.claims_for_chunk("chunk-A")
        assert edge_ab.id not in result.edge_ids, (
            "edge linked only via chunk-B must not appear in claims for chunk-A"
        )

    def test_claims_for_chunk_excludes_evidence_ids_from_other_chunk(
        self, store: SqliteGraphStore, entity_a, entity_b
    ) -> None:
        """AC2: evidence record from chunk-B must not appear in claims_for_chunk('chunk-A')."""
        store.add_evidence(_entity_evidence("chunk-A", entity_a.id))
        ev_b = store.add_evidence(_entity_evidence("chunk-B", entity_b.id))
        result = store.claims_for_chunk("chunk-A")
        assert ev_b.id not in result.evidence_ids, (
            "evidence record from chunk-B must not appear in claims for chunk-A"
        )
