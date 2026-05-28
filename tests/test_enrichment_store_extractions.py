"""Tests for EnrichmentStore — extractions & purge (task #1876).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/stores/enrichment.py

AC coverage:
  AC1  — submit_extractions: entity resolution, edge resolution, evidence creation,
          state transition to COMPLETED, ExtractionResult shape
  AC2  — submit_extractions: LookupError if chunk_id not in IN_PROGRESS state
  AC3  — submit_extractions: ValueError if relation source_ref or target_ref not in
          submitted entities batch
  AC4  — suggest_intra_doc_edges: co-occurrence ≥2 distinct chunks, confidence =
          shared_chunks/total_chunks, relation_type RELATED_TO, tuple return type
  AC5  — suggest_intra_doc_edges: LookupError if document_id has no chunks
  AC6  — purge_source: deletes enrich_queue and enrich_extractions rows by source_id;
          idempotent; EnrichmentPurgeResult shape with correct counts; unknown source → zeros
  AC7  — ensure_tables: creates enrich_extractions (id, chunk_id, source_id, batch_id,
          entity_count, edge_count, submitted_at) with indexes on source_id and chunk_id;
          idempotent alongside enrich_queue and enrich_batches
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from owlbear_knowledge.protocols.common import EntityType, RelationType
from owlbear_knowledge.protocols.enrichment import (
    EnrichmentParams,
    EnrichmentPurgeResult,
    EnrichmentState,
    ExtractionResult,
    ExtractedEntity,
    ExtractedRelation,
)
from owlbear_knowledge.protocols.graph import (
    EdgeRecord,
    EntityRecord,
    EvidenceClaimType,
    EvidenceRecord,
)
from owlbear_knowledge.stores.enrichment import EnrichmentStore  # graph kwarg not yet accepted


# ---------------------------------------------------------------------------
# Record builders
# ---------------------------------------------------------------------------


def _now_dt() -> datetime:
    return datetime.now(tz=UTC).replace(tzinfo=None, microsecond=0)


def _entity_record(entity_id: str, name: str = "test-entity") -> EntityRecord:
    now = _now_dt()
    return EntityRecord(
        id=entity_id,
        name=name,
        canonical_name=name.lower(),
        entity_type=EntityType.CONCEPT,
        description="",
        alias_names=(),
        metadata={},
        created_at=now,
        updated_at=now,
    )


def _edge_record(edge_id: str, source_id: str, target_id: str) -> EdgeRecord:
    now = _now_dt()
    return EdgeRecord(
        id=edge_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relation_type=RelationType.RELATED_TO,
        weight=1.0,
        metadata={},
        created_at=now,
        updated_at=now,
    )


def _evidence_record(
    ev_id: str,
    chunk_id: str,
    claim_type: EvidenceClaimType,
    *,
    entity_id: str | None = None,
    edge_id: str | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        id=ev_id,
        chunk_id=chunk_id,
        claim_type=claim_type,
        entity_id=entity_id,
        edge_id=edge_id,
        confidence=1.0,
        metadata={},
        created_at=_now_dt(),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture()
def mock_graph() -> MagicMock:
    """MagicMock GraphStore with predictable return values."""
    g = MagicMock()
    # Default entity upsert: return entity "eid-1" for first call, "eid-2" for second
    g.upsert_entity.side_effect = [
        _entity_record("eid-1", "alpha"),
        _entity_record("eid-2", "beta"),
        _entity_record("eid-3", "gamma"),
    ]
    # Default edge upsert returns one edge
    g.upsert_edge.return_value = _edge_record("edgeid-1", "eid-1", "eid-2")
    # Default evidence returns unique IDs
    g.add_evidence.side_effect = [
        _evidence_record("evid-1", "chunk-1", EvidenceClaimType.ENTITY, entity_id="eid-1"),
        _evidence_record("evid-2", "chunk-1", EvidenceClaimType.ENTITY, entity_id="eid-2"),
        _evidence_record("evid-3", "chunk-1", EvidenceClaimType.EDGE, edge_id="edgeid-1"),
    ]
    return g


@pytest.fixture()
def store(db: sqlite3.Connection, mock_graph: MagicMock) -> EnrichmentStore:
    """Fully-initialised EnrichmentStore with GraphStore DI. Fails in RED (graph kwarg missing)."""
    s = EnrichmentStore(db=db, graph=mock_graph)
    s.ensure_tables()
    return s


@pytest.fixture()
def initialised_db(db: sqlite3.Connection, mock_graph: MagicMock) -> sqlite3.Connection:
    """db connection with all EnrichmentStore tables created. Fails in RED (graph kwarg missing)."""
    s = EnrichmentStore(db=db, graph=mock_graph)
    s.ensure_tables()
    return db


def _claim_chunk(store: EnrichmentStore, chunk_id: str, source_id: str = "src-1") -> None:
    """Enqueue then claim one chunk so it's IN_PROGRESS."""
    store.enqueue_chunks((chunk_id,), source_id)
    store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))


def _setup_suggest_tables(conn: sqlite3.Connection) -> None:
    """Create content_chunks and graph_evidence tables for suggest tests."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS content_chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL DEFAULT '',
            content_hash TEXT NOT NULL DEFAULT '',
            scope TEXT NOT NULL DEFAULT '',
            uri TEXT,
            section_path_json TEXT NOT NULL DEFAULT '[]',
            trusted INTEGER NOT NULL DEFAULT 1,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS graph_evidence (
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
    conn.commit()


def _insert_chunk(conn: sqlite3.Connection, chunk_id: str, document_id: str) -> None:
    now = datetime.now(tz=UTC).isoformat()
    conn.execute(
        """
        INSERT INTO content_chunks
            (id, document_id, source_id, chunk_index, text, content_hash, scope,
             uri, section_path_json, trusted, metadata_json, created_at, updated_at)
        VALUES (?, ?, 'src-1', 0, 'text', 'hash', 'source', NULL, '[]', 1, '{}', ?, ?)
        """,
        (chunk_id, document_id, now, now),
    )
    conn.commit()


def _insert_entity_evidence(conn: sqlite3.Connection, ev_id: str, chunk_id: str, entity_id: str) -> None:
    now = datetime.now(tz=UTC).isoformat()
    conn.execute(
        """
        INSERT INTO graph_evidence (id, chunk_id, claim_type, entity_id, edge_id, confidence, metadata_json, created_at)
        VALUES (?, ?, 'entity', ?, NULL, 1.0, '{}', ?)
        """,
        (ev_id, chunk_id, entity_id, now),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# TestFromAC_SubmitExtractions  (AC1, AC2, AC3)
# ---------------------------------------------------------------------------


class TestSubmitExtractions:
    # ------------------------------------------------------------------
    # AC1 — happy path: entity resolution and ExtractionResult shape
    # ------------------------------------------------------------------

    def test_returns_extraction_result_with_correct_chunk_id(self, store: EnrichmentStore) -> None:
        """submit_extractions returns ExtractionResult with the submitted chunk_id."""
        _claim_chunk(store, "chunk-a")
        entity = ExtractedEntity(
            local_ref="e1",
            name="Alpha",
            entity_type=EntityType.CONCEPT,
        )
        result = store.submit_extractions("chunk-a", (entity,), ())
        assert isinstance(result, ExtractionResult)
        assert result.chunk_id == "chunk-a"

    def test_entity_ids_populated_with_one_id_per_entity(self, store: EnrichmentStore) -> None:
        """submit_extractions entity_ids tuple has one ID per submitted entity."""
        _claim_chunk(store, "chunk-a")
        entities = (
            ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),
            ExtractedEntity(local_ref="e2", name="Beta", entity_type=EntityType.PERSON),
        )
        result = store.submit_extractions("chunk-a", entities, ())
        assert len(result.entity_ids) == 2

    def test_upsert_entity_called_once_per_entity(self, store: EnrichmentStore, mock_graph: MagicMock) -> None:
        """Graph.upsert_entity is called exactly once per extracted entity."""
        _claim_chunk(store, "chunk-a")
        entities = (
            ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),
            ExtractedEntity(local_ref="e2", name="Beta", entity_type=EntityType.PERSON),
        )
        store.submit_extractions("chunk-a", entities, ())
        assert mock_graph.upsert_entity.call_count == 2

    def test_edge_ids_populated_with_one_id_per_relation(self, store: EnrichmentStore) -> None:
        """submit_extractions edge_ids tuple has one ID per submitted relation."""
        _claim_chunk(store, "chunk-a")
        entities = (
            ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),
            ExtractedEntity(local_ref="e2", name="Beta", entity_type=EntityType.CONCEPT),
        )
        relation = ExtractedRelation(
            source_ref="e1",
            target_ref="e2",
            relation_type=RelationType.RELATED_TO,
        )
        result = store.submit_extractions("chunk-a", entities, (relation,))
        assert len(result.edge_ids) == 1

    def test_upsert_edge_called_with_resolved_entity_ids(self, store: EnrichmentStore, mock_graph: MagicMock) -> None:
        """Graph.upsert_edge receives resolved persistent entity IDs, not local_refs."""
        _claim_chunk(store, "chunk-a")
        entities = (
            ExtractedEntity(local_ref="local-src", name="Alpha", entity_type=EntityType.CONCEPT),
            ExtractedEntity(local_ref="local-tgt", name="Beta", entity_type=EntityType.CONCEPT),
        )
        relation = ExtractedRelation(
            source_ref="local-src",
            target_ref="local-tgt",
            relation_type=RelationType.DEPENDS_ON,
        )
        store.submit_extractions("chunk-a", entities, (relation,))
        assert mock_graph.upsert_edge.call_count == 1
        edge_input = mock_graph.upsert_edge.call_args[0][0]
        # Must use persistent IDs from upsert_entity, not the local_ref strings
        assert edge_input.source_entity_id == "eid-1"
        assert edge_input.target_entity_id == "eid-2"

    def test_add_evidence_called_for_each_entity_as_entity_claim(
        self, store: EnrichmentStore, mock_graph: MagicMock
    ) -> None:
        """Graph.add_evidence is called with ENTITY claim for each entity."""
        _claim_chunk(store, "chunk-a")
        entities = (
            ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),
            ExtractedEntity(local_ref="e2", name="Beta", entity_type=EntityType.CONCEPT),
        )
        store.submit_extractions("chunk-a", entities, ())
        entity_calls = [
            c for c in mock_graph.add_evidence.call_args_list if c[0][0].claim_type == EvidenceClaimType.ENTITY
        ]
        assert len(entity_calls) == 2

    def test_add_evidence_called_for_each_edge_as_edge_claim(
        self, store: EnrichmentStore, mock_graph: MagicMock
    ) -> None:
        """Graph.add_evidence is called with EDGE claim for each edge."""
        _claim_chunk(store, "chunk-a")
        entities = (
            ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),
            ExtractedEntity(local_ref="e2", name="Beta", entity_type=EntityType.CONCEPT),
        )
        relation = ExtractedRelation(source_ref="e1", target_ref="e2", relation_type=RelationType.RELATED_TO)
        store.submit_extractions("chunk-a", entities, (relation,))
        edge_calls = [c for c in mock_graph.add_evidence.call_args_list if c[0][0].claim_type == EvidenceClaimType.EDGE]
        assert len(edge_calls) == 1

    def test_evidence_ids_populated_with_all_evidence_records(self, store: EnrichmentStore) -> None:
        """evidence_ids tuple contains IDs for entity + edge evidence combined."""
        _claim_chunk(store, "chunk-a")
        entities = (
            ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),
            ExtractedEntity(local_ref="e2", name="Beta", entity_type=EntityType.CONCEPT),
        )
        relation = ExtractedRelation(source_ref="e1", target_ref="e2", relation_type=RelationType.RELATED_TO)
        result = store.submit_extractions("chunk-a", entities, (relation,))
        # 2 entity evidence + 1 edge evidence = 3
        assert len(result.evidence_ids) == 3

    def test_queue_item_transitions_to_completed_with_timestamp(
        self, store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """Queue item state becomes COMPLETED and completed_at is set after submit."""
        _claim_chunk(store, "chunk-a")
        entity = ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT)
        store.submit_extractions("chunk-a", (entity,), ())
        row = db.execute("SELECT state, completed_at FROM enrich_queue WHERE chunk_id = ?", ("chunk-a",)).fetchone()
        assert row["state"] == EnrichmentState.COMPLETED.value
        assert row["completed_at"] is not None

    def test_submit_empty_entities_and_relations_completes_item(
        self, store: EnrichmentStore, db: sqlite3.Connection, mock_graph: MagicMock
    ) -> None:
        """submit_extractions with no entities or relations still completes the queue item."""
        mock_graph.upsert_entity.side_effect = []
        mock_graph.add_evidence.side_effect = []
        _claim_chunk(store, "chunk-a")
        result = store.submit_extractions("chunk-a", (), ())
        assert isinstance(result, ExtractionResult)
        assert result.entity_ids == ()
        assert result.edge_ids == ()
        row = db.execute("SELECT state FROM enrich_queue WHERE chunk_id = ?", ("chunk-a",)).fetchone()
        assert row["state"] == EnrichmentState.COMPLETED.value

    def test_state_transition_step4_occurs_only_after_graph_steps(
        self, store: EnrichmentStore, db: sqlite3.Connection, mock_graph: MagicMock
    ) -> None:
        """Queue stays IN_PROGRESS if graph call raises; step 4 not applied on failure."""
        mock_graph.upsert_entity.side_effect = RuntimeError("graph down")
        _claim_chunk(store, "chunk-a")
        entity = ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT)
        with pytest.raises(RuntimeError):
            store.submit_extractions("chunk-a", (entity,), ())
        row = db.execute("SELECT state FROM enrich_queue WHERE chunk_id = ?", ("chunk-a",)).fetchone()
        assert row["state"] != EnrichmentState.COMPLETED.value

    # ------------------------------------------------------------------
    # AC2 — LookupError if chunk not IN_PROGRESS
    # ------------------------------------------------------------------

    def test_raises_lookup_error_if_chunk_not_in_queue(self, store: EnrichmentStore) -> None:
        """LookupError raised when chunk_id does not exist in enrich_queue at all."""
        entity = ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT)
        with pytest.raises(LookupError):
            store.submit_extractions("no-such-chunk", (entity,), ())

    def test_raises_lookup_error_if_chunk_is_pending(self, store: EnrichmentStore) -> None:
        """LookupError raised when chunk_id is in PENDING state (not yet claimed)."""
        store.enqueue_chunks(("chunk-pending",), "src-1")
        entity = ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT)
        with pytest.raises(LookupError):
            store.submit_extractions("chunk-pending", (entity,), ())

    def test_raises_lookup_error_if_chunk_is_completed(self, store: EnrichmentStore, db: sqlite3.Connection) -> None:
        """LookupError raised when chunk_id is already COMPLETED."""
        store.enqueue_chunks(("chunk-done",), "src-1")
        db.execute("UPDATE enrich_queue SET state = 'completed' WHERE chunk_id = 'chunk-done'")
        db.commit()
        entity = ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT)
        with pytest.raises(LookupError):
            store.submit_extractions("chunk-done", (entity,), ())

    def test_raises_lookup_error_if_chunk_is_failed(self, store: EnrichmentStore) -> None:
        """LookupError raised when chunk_id is in FAILED state."""
        store.enqueue_chunks(("chunk-fail",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))
        store.mark_failed("chunk-fail", "permanent error")  # 1 attempt >= max_retries 1 → FAILED
        entity = ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT)
        with pytest.raises(LookupError):
            store.submit_extractions("chunk-fail", (entity,), ())

    # ------------------------------------------------------------------
    # AC3 — ValueError if relation refs unresolved
    # ------------------------------------------------------------------

    def test_raises_value_error_if_source_ref_not_in_entities(self, store: EnrichmentStore) -> None:
        """ValueError raised when a relation source_ref is not among submitted entities."""
        _claim_chunk(store, "chunk-a")
        entities = (ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),)
        relation = ExtractedRelation(
            source_ref="UNKNOWN-ref",
            target_ref="e1",
            relation_type=RelationType.RELATED_TO,
        )
        with pytest.raises(ValueError):
            store.submit_extractions("chunk-a", entities, (relation,))

    def test_raises_value_error_if_target_ref_not_in_entities(self, store: EnrichmentStore) -> None:
        """ValueError raised when a relation target_ref is not among submitted entities."""
        _claim_chunk(store, "chunk-a")
        entities = (ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),)
        relation = ExtractedRelation(
            source_ref="e1",
            target_ref="UNKNOWN-ref",
            relation_type=RelationType.RELATED_TO,
        )
        with pytest.raises(ValueError):
            store.submit_extractions("chunk-a", entities, (relation,))

    def test_raises_value_error_if_both_refs_unresolved(self, store: EnrichmentStore) -> None:
        """ValueError raised when both source_ref and target_ref are unresolved."""
        _claim_chunk(store, "chunk-a")
        entities = (ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),)
        relation = ExtractedRelation(
            source_ref="no-src",
            target_ref="no-tgt",
            relation_type=RelationType.RELATED_TO,
        )
        with pytest.raises(ValueError):
            store.submit_extractions("chunk-a", entities, (relation,))

    def test_value_error_raised_before_graph_calls_for_unresolved_ref(
        self, store: EnrichmentStore, mock_graph: MagicMock
    ) -> None:
        """ValueError for unresolved ref must be raised without calling Graph.upsert_edge."""
        # Reset side_effect so entity upserts work
        mock_graph.upsert_entity.side_effect = [_entity_record("eid-1", "alpha")]
        _claim_chunk(store, "chunk-a")
        entities = (ExtractedEntity(local_ref="e1", name="Alpha", entity_type=EntityType.CONCEPT),)
        relation = ExtractedRelation(
            source_ref="e1",
            target_ref="MISSING",
            relation_type=RelationType.RELATED_TO,
        )
        with pytest.raises(ValueError):
            store.submit_extractions("chunk-a", entities, (relation,))
        mock_graph.upsert_edge.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_SuggestIntraDocEdges  (AC4, AC5)
# ---------------------------------------------------------------------------


class TestSuggestIntraDocEdges:
    @pytest.fixture()
    def suggest_store(self, db: sqlite3.Connection, mock_graph: MagicMock) -> EnrichmentStore:
        """Store with both enrich tables and content/graph evidence tables set up."""
        _setup_suggest_tables(db)
        s = EnrichmentStore(db=db, graph=mock_graph)
        s.ensure_tables()
        return s

    # ------------------------------------------------------------------
    # AC4 — happy paths
    # ------------------------------------------------------------------

    def test_returns_tuple_of_suggested_edges(self, suggest_store: EnrichmentStore, db: sqlite3.Connection) -> None:
        """suggest_intra_doc_edges returns a tuple."""
        _insert_chunk(db, "c1", "doc-1")
        _insert_chunk(db, "c2", "doc-1")
        _insert_entity_evidence(db, "ev1", "c1", "ent-A")
        _insert_entity_evidence(db, "ev2", "c2", "ent-A")
        _insert_entity_evidence(db, "ev3", "c1", "ent-B")
        _insert_entity_evidence(db, "ev4", "c2", "ent-B")
        result = suggest_store.suggest_intra_doc_edges("doc-1")
        assert isinstance(result, tuple)

    def test_entity_pair_co_occurring_in_two_chunks_produces_suggestion(
        self, suggest_store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """Two entities in ≥2 chunks yield one SuggestedEdge between them."""
        _insert_chunk(db, "c1", "doc-1")
        _insert_chunk(db, "c2", "doc-1")
        _insert_entity_evidence(db, "ev1", "c1", "ent-A")
        _insert_entity_evidence(db, "ev2", "c2", "ent-A")
        _insert_entity_evidence(db, "ev3", "c1", "ent-B")
        _insert_entity_evidence(db, "ev4", "c2", "ent-B")
        result = suggest_store.suggest_intra_doc_edges("doc-1")
        entity_pair = {result[0].source_entity_id, result[0].target_entity_id}
        assert entity_pair == {"ent-A", "ent-B"}

    def test_suggested_edge_has_related_to_relation_type(
        self, suggest_store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """SuggestedEdge relation_type is RELATED_TO."""
        _insert_chunk(db, "c1", "doc-1")
        _insert_chunk(db, "c2", "doc-1")
        _insert_entity_evidence(db, "ev1", "c1", "ent-A")
        _insert_entity_evidence(db, "ev2", "c2", "ent-A")
        _insert_entity_evidence(db, "ev3", "c1", "ent-B")
        _insert_entity_evidence(db, "ev4", "c2", "ent-B")
        result = suggest_store.suggest_intra_doc_edges("doc-1")
        assert len(result) >= 1
        assert result[0].relation_type == RelationType.RELATED_TO

    def test_confidence_equals_shared_chunks_over_total_chunks(
        self, suggest_store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """Confidence = shared_chunks / total_chunks for the co-occurring entity pair."""
        # 4 total chunks; entities A and B share 2 of them
        _insert_chunk(db, "c1", "doc-1")
        _insert_chunk(db, "c2", "doc-1")
        _insert_chunk(db, "c3", "doc-1")
        _insert_chunk(db, "c4", "doc-1")
        # A and B appear in c1 and c2 (2 shared out of 4 total)
        _insert_entity_evidence(db, "ev1", "c1", "ent-A")
        _insert_entity_evidence(db, "ev2", "c1", "ent-B")
        _insert_entity_evidence(db, "ev3", "c2", "ent-A")
        _insert_entity_evidence(db, "ev4", "c2", "ent-B")
        result = suggest_store.suggest_intra_doc_edges("doc-1")
        assert len(result) >= 1
        assert abs(result[0].confidence - (2 / 4)) < 1e-6

    def test_entity_pair_co_occurring_in_only_one_chunk_not_suggested(
        self, suggest_store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """Entity pair sharing only 1 chunk is below the ≥2 threshold — not returned."""
        _insert_chunk(db, "c1", "doc-1")
        _insert_chunk(db, "c2", "doc-1")
        # A and B only share c1
        _insert_entity_evidence(db, "ev1", "c1", "ent-A")
        _insert_entity_evidence(db, "ev2", "c1", "ent-B")
        _insert_entity_evidence(db, "ev3", "c2", "ent-A")  # only A in c2
        result = suggest_store.suggest_intra_doc_edges("doc-1")
        pairs = [frozenset({e.source_entity_id, e.target_entity_id}) for e in result]
        assert frozenset({"ent-A", "ent-B"}) not in pairs

    def test_no_suggestions_when_no_entity_evidence_in_document(
        self, suggest_store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """Empty tuple returned when document chunks have no entity evidence."""
        _insert_chunk(db, "c1", "doc-1")
        _insert_chunk(db, "c2", "doc-1")
        # No graph_evidence rows for these chunks
        result = suggest_store.suggest_intra_doc_edges("doc-1")
        assert result == ()

    def test_suggest_does_not_write_to_graph(
        self, suggest_store: EnrichmentStore, db: sqlite3.Connection, mock_graph: MagicMock
    ) -> None:
        """suggest_intra_doc_edges is read-only — no Graph write methods called."""
        _insert_chunk(db, "c1", "doc-1")
        _insert_chunk(db, "c2", "doc-1")
        _insert_entity_evidence(db, "ev1", "c1", "ent-A")
        _insert_entity_evidence(db, "ev2", "c2", "ent-A")
        _insert_entity_evidence(db, "ev3", "c1", "ent-B")
        _insert_entity_evidence(db, "ev4", "c2", "ent-B")
        suggest_store.suggest_intra_doc_edges("doc-1")
        mock_graph.upsert_entity.assert_not_called()
        mock_graph.upsert_edge.assert_not_called()
        mock_graph.add_evidence.assert_not_called()

    # ------------------------------------------------------------------
    # AC4 — adversarial: cross-document scoping
    # ------------------------------------------------------------------

    def test_suggest_scopes_confidence_to_requested_document_only(
        self, suggest_store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """Confidence is computed using only the requested document's chunk count.

        doc-1 has 2 chunks with ent-A and ent-B in both → shared=2, total=2, confidence=1.0.
        doc-2 also contributes 2 chunks with the same entities. An unscoped implementation
        would count 4 total chunks and produce confidence=0.5 instead of 1.0.
        """
        _insert_chunk(db, "c1", "doc-1")
        _insert_chunk(db, "c2", "doc-1")
        _insert_entity_evidence(db, "ev1", "c1", "ent-A")
        _insert_entity_evidence(db, "ev2", "c2", "ent-A")
        _insert_entity_evidence(db, "ev3", "c1", "ent-B")
        _insert_entity_evidence(db, "ev4", "c2", "ent-B")
        # doc-2: same entities, 2 additional chunks — must not inflate doc-1 total
        _insert_chunk(db, "c3", "doc-2")
        _insert_chunk(db, "c4", "doc-2")
        _insert_entity_evidence(db, "ev5", "c3", "ent-A")
        _insert_entity_evidence(db, "ev6", "c4", "ent-A")
        _insert_entity_evidence(db, "ev7", "c3", "ent-B")
        _insert_entity_evidence(db, "ev8", "c4", "ent-B")
        result = suggest_store.suggest_intra_doc_edges("doc-1")
        assert len(result) == 1
        # Unscoped regression: 2/4 = 0.5; correctly scoped: 2/2 = 1.0
        assert abs(result[0].confidence - 1.0) < 1e-6

    def test_suggest_does_not_include_entity_pairs_from_other_documents(
        self, suggest_store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """Entity pairs that co-occur only in a different document are not returned.

        doc-1 has one entity with no co-occurring partner (no pair should form).
        doc-2 has entities C and D co-occurring in 2 chunks (would satisfy the threshold).
        Calling suggest_intra_doc_edges("doc-1") must return an empty tuple,
        not doc-2's C-D pair.
        """
        # doc-1: single entity, no pair possible
        _insert_chunk(db, "d1c1", "doc-1")
        _insert_chunk(db, "d1c2", "doc-1")
        _insert_entity_evidence(db, "d1ev1", "d1c1", "ent-A-solo")
        _insert_entity_evidence(db, "d1ev2", "d1c2", "ent-A-solo")
        # doc-2: C and D co-occur in 2 chunks — meets ≥2 threshold
        _insert_chunk(db, "d2c1", "doc-2")
        _insert_chunk(db, "d2c2", "doc-2")
        _insert_entity_evidence(db, "d2ev1", "d2c1", "ent-C")
        _insert_entity_evidence(db, "d2ev2", "d2c2", "ent-C")
        _insert_entity_evidence(db, "d2ev3", "d2c1", "ent-D")
        _insert_entity_evidence(db, "d2ev4", "d2c2", "ent-D")
        result = suggest_store.suggest_intra_doc_edges("doc-1")
        pairs = [frozenset({e.source_entity_id, e.target_entity_id}) for e in result]
        assert frozenset({"ent-C", "ent-D"}) not in pairs
        assert result == ()

    # ------------------------------------------------------------------
    # AC5 — LookupError for unknown document
    # ------------------------------------------------------------------

    def test_raises_lookup_error_for_document_with_no_chunks(self, suggest_store: EnrichmentStore) -> None:
        """LookupError raised if document_id has no rows in content_chunks."""
        with pytest.raises(LookupError):
            suggest_store.suggest_intra_doc_edges("no-such-doc")

    def test_raises_lookup_error_not_empty_tuple_for_unknown_document(self, suggest_store: EnrichmentStore) -> None:
        """Confirm the raised exception is exactly LookupError, not a subclass or silent return."""
        exc: LookupError | None = None
        try:
            suggest_store.suggest_intra_doc_edges("ghost-document")
        except LookupError as e:
            exc = e
        assert exc is not None, "Expected LookupError was not raised"


# ---------------------------------------------------------------------------
# TestFromAC_PurgeSource  (AC6)
# ---------------------------------------------------------------------------


class TestPurgeSource:
    def test_returns_enrichment_purge_result(self, store: EnrichmentStore) -> None:
        """purge_source returns an EnrichmentPurgeResult instance."""
        result = store.purge_source("src-unknown")
        assert isinstance(result, EnrichmentPurgeResult)

    def test_result_source_id_matches_input(self, store: EnrichmentStore) -> None:
        """EnrichmentPurgeResult.source_id reflects the requested source_id."""
        result = store.purge_source("src-xyz")
        assert result.source_id == "src-xyz"

    def test_purge_removes_enqueue_queue_items_for_source(self, store: EnrichmentStore, db: sqlite3.Connection) -> None:
        """purge_source deletes enrich_queue rows with matching source_id."""
        store.enqueue_chunks(("c1", "c2"), "src-A")
        store.enqueue_chunks(("c3",), "src-B")
        result = store.purge_source("src-A")
        assert result.queue_items_removed == 2
        remaining = db.execute("SELECT COUNT(*) AS n FROM enrich_queue WHERE source_id = 'src-A'").fetchone()["n"]
        assert remaining == 0

    def test_purge_does_not_remove_other_source_queue_items(
        self, store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """purge_source leaves enrich_queue rows from other sources untouched."""
        store.enqueue_chunks(("c1",), "src-A")
        store.enqueue_chunks(("c2",), "src-B")
        store.purge_source("src-A")
        remaining = db.execute("SELECT COUNT(*) AS n FROM enrich_queue WHERE source_id = 'src-B'").fetchone()["n"]
        assert remaining == 1

    def test_purge_removes_enrich_extractions_for_source(self, store: EnrichmentStore, db: sqlite3.Connection) -> None:
        """purge_source deletes enrich_extractions rows with matching source_id."""
        now = datetime.now(tz=UTC).isoformat()
        db.execute(
            """
            INSERT INTO enrich_extractions
                (id, chunk_id, source_id, batch_id, entity_count, edge_count, submitted_at)
            VALUES ('ex1', 'c1', 'src-A', 'b1', 2, 1, ?)
            """,
            (now,),
        )
        db.commit()
        result = store.purge_source("src-A")
        assert result.extractions_removed == 1
        remaining = db.execute("SELECT COUNT(*) AS n FROM enrich_extractions WHERE source_id = 'src-A'").fetchone()["n"]
        assert remaining == 0

    def test_purge_returns_zero_counts_for_unknown_source(self, store: EnrichmentStore) -> None:
        """purge_source with unknown source_id returns zeros — never raises."""
        result = store.purge_source("nonexistent-src")
        assert result.queue_items_removed == 0
        assert result.extractions_removed == 0

    def test_purge_is_idempotent(self, store: EnrichmentStore) -> None:
        """Second purge_source call for same source returns zeros — idempotent."""
        store.enqueue_chunks(("c1",), "src-A")
        store.purge_source("src-A")
        result2 = store.purge_source("src-A")
        assert result2.queue_items_removed == 0
        assert result2.extractions_removed == 0


# ---------------------------------------------------------------------------
# TestFromAC_EnsureTables  (AC7)
# ---------------------------------------------------------------------------


class TestEnsureTables:
    def test_enrich_extractions_table_is_created(self, initialised_db: sqlite3.Connection) -> None:
        """ensure_tables creates the enrich_extractions table."""
        row = initialised_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='enrich_extractions'"
        ).fetchone()
        assert row is not None

    def test_enrich_extractions_has_required_columns(self, initialised_db: sqlite3.Connection) -> None:
        """enrich_extractions has all required columns per AC7."""
        pragma = initialised_db.execute("PRAGMA table_info(enrich_extractions)").fetchall()
        col_names = {row["name"] for row in pragma}
        required = {"id", "chunk_id", "source_id", "batch_id", "entity_count", "edge_count", "submitted_at"}
        assert required.issubset(col_names)

    def test_index_on_source_id_exists(self, initialised_db: sqlite3.Connection) -> None:
        """enrich_extractions has an index on source_id."""
        indexes = initialised_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='enrich_extractions'"
        ).fetchall()
        index_names = {row["name"] for row in indexes}
        has_source_idx = any("source_id" in name for name in index_names)
        assert has_source_idx, f"No source_id index found in {index_names}"

    def test_index_on_chunk_id_exists(self, initialised_db: sqlite3.Connection) -> None:
        """enrich_extractions has an index on chunk_id."""
        indexes = initialised_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='enrich_extractions'"
        ).fetchall()
        index_names = {row["name"] for row in indexes}
        has_chunk_idx = any("chunk_id" in name for name in index_names)
        assert has_chunk_idx, f"No chunk_id index found in {index_names}"

    def test_ensure_tables_is_idempotent(self, store: EnrichmentStore) -> None:
        """Calling ensure_tables twice does not raise."""
        store.ensure_tables()  # second call

    def test_enrich_queue_table_still_present_after_ensure_tables(self, initialised_db: sqlite3.Connection) -> None:
        """ensure_tables leaves existing enrich_queue table intact."""
        row = initialised_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='enrich_queue'"
        ).fetchone()
        assert row is not None

    def test_enrich_batches_table_still_present_after_ensure_tables(self, initialised_db: sqlite3.Connection) -> None:
        """ensure_tables leaves existing enrich_batches table intact."""
        row = initialised_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='enrich_batches'"
        ).fetchone()
        assert row is not None

    # ------------------------------------------------------------------
    # AC7 — column-level index verification (stronger than name-match)
    # ------------------------------------------------------------------

    def test_source_id_index_covers_source_id_column(self, initialised_db: sqlite3.Connection) -> None:
        """At least one index on enrich_extractions physically covers the source_id column.

        Reads the CREATE INDEX DDL from sqlite_master to verify the actual indexed column,
        not just the index name. A miswired index whose name contains 'source_id' but
        indexes a different column would pass the name-based check but fail here.
        """
        ddls = initialised_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='enrich_extractions'"
        ).fetchall()
        # DDL looks like: CREATE INDEX ... ON enrich_extractions(source_id)
        # Check the column list explicitly, not just the index name.
        column_lists = []
        for row in ddls:
            sql = row["sql"] or ""
            # Extract the part between ON enrich_extractions( and )
            if "ON enrich_extractions(" in sql:
                col_part = sql.split("ON enrich_extractions(", 1)[1].rstrip(")")
                column_lists.append(col_part)
        assert any("source_id" in cols for cols in column_lists), (
            f"No index DDL on enrich_extractions covers source_id column; DDLs: {[r['sql'] for r in ddls]}"
        )

    def test_chunk_id_index_covers_chunk_id_column(self, initialised_db: sqlite3.Connection) -> None:
        """At least one index on enrich_extractions physically covers the chunk_id column.

        Reads the CREATE INDEX DDL from sqlite_master to verify the actual indexed column,
        not just the index name. A miswired index whose name contains 'chunk_id' but
        indexes a different column would pass the name-based check but fail here.
        """
        ddls = initialised_db.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='enrich_extractions'"
        ).fetchall()
        # DDL looks like: CREATE INDEX ... ON enrich_extractions(chunk_id)
        column_lists = []
        for row in ddls:
            sql = row["sql"] or ""
            if "ON enrich_extractions(" in sql:
                col_part = sql.split("ON enrich_extractions(", 1)[1].rstrip(")")
                column_lists.append(col_part)
        assert any("chunk_id" in cols for cols in column_lists), (
            f"No index DDL on enrich_extractions covers chunk_id column; DDLs: {[r['sql'] for r in ddls]}"
        )
