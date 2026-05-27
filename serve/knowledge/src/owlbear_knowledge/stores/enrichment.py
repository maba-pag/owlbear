"""SQLite-backed Enrichment queue state-machine store."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from itertools import combinations
from uuid import uuid4

from owlbear_knowledge.protocols.common import RelationType
from owlbear_knowledge.protocols.enrichment import (
    EnrichmentBatch,
    EnrichmentDiscardResult,
    EnrichmentParams,
    EnrichmentPurgeResult,
    EnrichmentQueueItem,
    EnrichmentResetResult,
    EnrichmentState,
    EnrichmentStats,
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    SuggestedEdge,
)
from owlbear_knowledge.protocols.enrichment import (
    EnrichmentStore as EnrichmentStoreProtocol,
)
from owlbear_knowledge.protocols.graph import (
    EdgeInput,
    EntityInput,
    EvidenceClaimType,
    EvidenceInput,
    GraphStore,
)


class EnrichmentStore(EnrichmentStoreProtocol):
    """SQLite-backed queue state machine for enrichment work items."""

    _CLAIM_TTL_SECONDS = 600
    _MIN_SHARED_CHUNKS_FOR_SUGGESTION = 2

    def __init__(self, *, db: sqlite3.Connection, graph: GraphStore | None = None) -> None:
        self._db = db
        self._db.row_factory = sqlite3.Row
        self._graph = graph

    def ensure_tables(self) -> None:
        """Create Enrichment-owned tables if they do not yet exist."""
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS enrich_queue (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL UNIQUE,
                source_id TEXT NOT NULL,
                state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                last_error TEXT,
                batch_id TEXT,
                enqueued_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS enrich_batches (
                batch_id TEXT PRIMARY KEY,
                claimed_at TEXT NOT NULL,
                item_count INTEGER NOT NULL
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS enrich_extractions (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                batch_id TEXT,
                entity_count INTEGER NOT NULL,
                edge_count INTEGER NOT NULL,
                submitted_at TEXT NOT NULL
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_enrich_extractions_source_id "
            "ON enrich_extractions(source_id)"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_enrich_extractions_chunk_id "
            "ON enrich_extractions(chunk_id)"
        )
        self._db.commit()

    def enqueue_chunks(self, chunk_ids: tuple[str, ...], source_id: str) -> int:
        """Enqueue chunks for enrichment processing."""
        if not chunk_ids:
            msg = "chunk_ids cannot be empty"
            raise ValueError(msg)

        now_iso = self._now_iso()
        enqueued = 0

        with self._db:
            for chunk_id in chunk_ids:
                row = self._db.execute(
                    "SELECT state FROM enrich_queue WHERE chunk_id = ?",
                    (chunk_id,),
                ).fetchone()

                if row is None:
                    self._db.execute(
                        """
                        INSERT INTO enrich_queue (
                            id, chunk_id, source_id, state, attempts, max_retries,
                            last_error, batch_id, enqueued_at, started_at, completed_at
                        ) VALUES (?, ?, ?, ?, 0, 3, NULL, NULL, ?, NULL, NULL)
                        """,
                        (
                            str(uuid4()),
                            chunk_id,
                            source_id,
                            EnrichmentState.PENDING.value,
                            now_iso,
                        ),
                    )
                    enqueued += 1
                    continue

                state = EnrichmentState(str(row["state"]))
                if state in {EnrichmentState.IN_PROGRESS, EnrichmentState.COMPLETED}:
                    continue

                if state == EnrichmentState.FAILED:
                    self._db.execute(
                        """
                        UPDATE enrich_queue
                        SET state = ?, batch_id = NULL, started_at = NULL,
                            completed_at = NULL, last_error = NULL
                        WHERE chunk_id = ?
                        """,
                        (EnrichmentState.PENDING.value, chunk_id),
                    )
                    enqueued += 1

        return enqueued

    def discard_chunks(self, chunk_ids: tuple[str, ...]) -> EnrichmentDiscardResult:
        """Discard PENDING and FAILED queue entries for selected chunks."""
        if not chunk_ids:
            return EnrichmentDiscardResult(discarded_chunk_ids=(), queue_items_removed=0)

        removable_states = {EnrichmentState.PENDING.value, EnrichmentState.FAILED.value}
        removed_ids: list[str] = []

        with self._db:
            for chunk_id in chunk_ids:
                row = self._db.execute(
                    "SELECT state FROM enrich_queue WHERE chunk_id = ?",
                    (chunk_id,),
                ).fetchone()
                if row is None or str(row["state"]) not in removable_states:
                    continue
                self._db.execute("DELETE FROM enrich_queue WHERE chunk_id = ?", (chunk_id,))
                removed_ids.append(chunk_id)

        discarded = tuple(removed_ids)
        return EnrichmentDiscardResult(
            discarded_chunk_ids=discarded,
            queue_items_removed=len(discarded),
        )

    def reset_failed(
        self,
        chunk_ids: tuple[str, ...] | None = None,
        limit: int = 100,
        scopes: tuple[str, ...] | None = None,
    ) -> EnrichmentResetResult:
        """Reset failed queue items to pending so they can be claimed again.

        Reconciliation note:
          - ``enrich_queue`` is this store's canonical state source.
          - When a legacy ``chunks`` table exists, matching rows are synced
            best-effort to keep mixed-schema deployments consistent.
        """
        normalized_chunk_ids = tuple(
            chunk_id.strip() for chunk_id in (chunk_ids or ()) if chunk_id.strip()
        )
        normalized_scopes = tuple(scope.strip() for scope in (scopes or ()) if scope.strip())
        normalized_limit = self._normalize_reset_limit(limit)

        reset_count = 0
        with self._db:
            if normalized_chunk_ids:
                rows = self._db.execute(
                    """
                    SELECT chunk_id
                    FROM enrich_queue
                    WHERE state = ?
                      AND chunk_id IN (SELECT value FROM json_each(?))
                    ORDER BY chunk_id
                    """,
                    (EnrichmentState.FAILED.value, json.dumps(normalized_chunk_ids)),
                ).fetchall()
            else:
                rows = self._select_failed_for_bulk_reset(
                    limit=normalized_limit,
                    scopes=normalized_scopes,
                )

            reset_chunk_ids = tuple(str(row["chunk_id"]) for row in rows)
            if reset_chunk_ids:
                reset_count = max(
                    self._db.execute(
                        """
                        UPDATE enrich_queue
                        SET state = ?, attempts = 0, last_error = NULL,
                            batch_id = NULL, started_at = NULL, completed_at = NULL
                        WHERE state = ?
                          AND chunk_id IN (SELECT value FROM json_each(?))
                        """,
                        (
                            EnrichmentState.PENDING.value,
                            EnrichmentState.FAILED.value,
                            json.dumps(reset_chunk_ids),
                        ),
                    ).rowcount,
                    0,
                )
                self._sync_legacy_chunk_state(reset_chunk_ids)

            remaining_row = self._db.execute(
                "SELECT COUNT(*) FROM enrich_queue WHERE state = ?",
                (EnrichmentState.FAILED.value,),
            ).fetchone()

        remaining_failed = int(remaining_row[0] if remaining_row is not None else 0)
        return EnrichmentResetResult(reset=reset_count, remaining_failed=remaining_failed)

    def claim_batch(self, params: EnrichmentParams) -> EnrichmentBatch:
        """Claim up to batch_size queue items for processing."""
        batch_id = str(uuid4())
        now_iso = self._now_iso()

        self._db.execute("BEGIN IMMEDIATE")
        try:
            self._db.execute(
                """
                UPDATE enrich_queue
                SET state = ?, batch_id = NULL, started_at = NULL
                WHERE state = ?
                  AND started_at IS NOT NULL
                                    AND started_at < datetime('now', ?)
                """,
                (
                    EnrichmentState.PENDING.value,
                    EnrichmentState.IN_PROGRESS.value,
                    f"-{self._CLAIM_TTL_SECONDS} seconds",
                ),
            )

            rows = self._db.execute(
                """
                SELECT chunk_id
                FROM enrich_queue
                WHERE state = ?
                ORDER BY enqueued_at, chunk_id
                LIMIT ?
                """,
                (EnrichmentState.PENDING.value, params.batch_size),
            ).fetchall()
            chunk_ids = tuple(str(row["chunk_id"]) for row in rows)

            if not chunk_ids:
                self._db.commit()
                return EnrichmentBatch(items=(), batch_id=batch_id)

            self._db.executemany(
                """
                UPDATE enrich_queue
                SET state = ?, batch_id = ?, started_at = ?, max_retries = ?
                WHERE chunk_id = ?
                """,
                [
                    (
                        EnrichmentState.IN_PROGRESS.value,
                        batch_id,
                        now_iso,
                        params.max_retries,
                        chunk_id,
                    )
                    for chunk_id in chunk_ids
                ],
            )
            self._db.execute(
                """
                INSERT INTO enrich_batches (batch_id, claimed_at, item_count)
                VALUES (?, ?, ?)
                """,
                (batch_id, now_iso, len(chunk_ids)),
            )
            claimed_rows = self._db.execute(
                """
                SELECT id, chunk_id, source_id, state, attempts, last_error,
                       enqueued_at, started_at, completed_at
                FROM enrich_queue
                WHERE batch_id = ?
                ORDER BY enqueued_at, chunk_id
                """,
                (batch_id,),
            ).fetchall()
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        items = tuple(self._row_to_queue_item(row) for row in claimed_rows)
        return EnrichmentBatch(items=items, batch_id=batch_id)

    def mark_failed(self, chunk_id: str, error: str) -> EnrichmentQueueItem:
        """Mark an in-progress queue item as failed and apply retry policy."""
        with self._db:
            row = self._db.execute(
                """
                SELECT id, chunk_id, source_id, state, attempts, max_retries,
                       last_error, enqueued_at, started_at, completed_at
                FROM enrich_queue
                WHERE chunk_id = ? AND state = ?
                """,
                (chunk_id, EnrichmentState.IN_PROGRESS.value),
            ).fetchone()
            if row is None:
                msg = f"chunk {chunk_id!r} is not in progress"
                raise LookupError(msg)

            attempts = int(row["attempts"]) + 1
            max_retries = int(row["max_retries"])
            next_state = (
                EnrichmentState.FAILED
                if attempts >= max_retries
                else EnrichmentState.PENDING
            )
            started_at = None if next_state == EnrichmentState.PENDING else str(row["started_at"])

            self._db.execute(
                """
                UPDATE enrich_queue
                SET attempts = ?, state = ?, last_error = ?, started_at = ?, batch_id = NULL
                WHERE chunk_id = ?
                """,
                (attempts, next_state.value, error, started_at, chunk_id),
            )
            updated = self._db.execute(
                """
                SELECT id, chunk_id, source_id, state, attempts, last_error,
                       enqueued_at, started_at, completed_at
                FROM enrich_queue
                WHERE chunk_id = ?
                """,
                (chunk_id,),
            ).fetchone()

        if updated is None:  # pragma: no cover
            msg = f"chunk {chunk_id!r} not found after update"
            raise LookupError(msg)

        return self._row_to_queue_item(updated)

    def submit_extractions(
        self,
        chunk_id: str,
        entities: tuple[ExtractedEntity, ...],
        relations: tuple[ExtractedRelation, ...],
    ) -> ExtractionResult:
        """Resolve extracted entities/relations, create evidence, and complete queue item."""
        row = self._db.execute(
            """
            SELECT source_id, batch_id
            FROM enrich_queue
            WHERE chunk_id = ? AND state = ?
            """,
            (chunk_id, EnrichmentState.IN_PROGRESS.value),
        ).fetchone()
        if row is None:
            msg = f"chunk {chunk_id!r} is not in progress"
            raise LookupError(msg)

        graph = self._require_graph()
        local_ref_to_entity_id: dict[str, str] = {}
        entity_ids: list[str] = []
        edge_ids: list[str] = []
        evidence_ids: list[str] = []

        for entity in entities:
            entity_record = graph.upsert_entity(
                EntityInput(
                    name=entity.name,
                    entity_type=entity.entity_type,
                    description=entity.description,
                    metadata=entity.metadata,
                )
            )
            entity_ids.append(entity_record.id)
            local_ref_to_entity_id[entity.local_ref] = entity_record.id

        resolved_relations: list[tuple[ExtractedRelation, str, str]] = []
        for relation in relations:
            source_entity_id = local_ref_to_entity_id.get(relation.source_ref)
            target_entity_id = local_ref_to_entity_id.get(relation.target_ref)
            if source_entity_id is None or target_entity_id is None:
                msg = (
                    "relation reference must match submitted entity local_ref values"
                )
                raise ValueError(msg)
            resolved_relations.append((relation, source_entity_id, target_entity_id))

        for relation, source_entity_id, target_entity_id in resolved_relations:
            edge_record = graph.upsert_edge(
                EdgeInput(
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    relation_type=relation.relation_type,
                    weight=relation.weight,
                    metadata=relation.metadata,
                )
            )
            edge_ids.append(edge_record.id)

        for entity, entity_id in zip(entities, entity_ids, strict=False):
            evidence_record = graph.add_evidence(
                EvidenceInput(
                    chunk_id=chunk_id,
                    claim_type=EvidenceClaimType.ENTITY,
                    entity_id=entity_id,
                    confidence=entity.confidence,
                    metadata=entity.metadata,
                )
            )
            evidence_ids.append(evidence_record.id)

        for relation, edge_id in zip(relations, edge_ids, strict=False):
            evidence_record = graph.add_evidence(
                EvidenceInput(
                    chunk_id=chunk_id,
                    claim_type=EvidenceClaimType.EDGE,
                    edge_id=edge_id,
                    confidence=relation.confidence,
                    metadata=relation.metadata,
                )
            )
            evidence_ids.append(evidence_record.id)

        completed_at = self._now_iso()
        with self._db:
            self._db.execute(
                """
                INSERT INTO enrich_extractions (
                    id, chunk_id, source_id, batch_id, entity_count, edge_count, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    chunk_id,
                    str(row["source_id"]),
                    None if row["batch_id"] is None else str(row["batch_id"]),
                    len(entity_ids),
                    len(edge_ids),
                    completed_at,
                ),
            )
            self._db.execute(
                """
                UPDATE enrich_queue
                SET state = ?, completed_at = ?, batch_id = NULL
                WHERE chunk_id = ?
                """,
                (EnrichmentState.COMPLETED.value, completed_at, chunk_id),
            )

        return ExtractionResult(
            chunk_id=chunk_id,
            entity_ids=tuple(entity_ids),
            edge_ids=tuple(edge_ids),
            evidence_ids=tuple(evidence_ids),
        )

    def suggest_intra_doc_edges(self, document_id: str) -> tuple[SuggestedEdge, ...]:
        """Return co-occurrence suggestions for entities in a document's chunks."""
        chunk_rows = self._db.execute(
            "SELECT id FROM content_chunks WHERE document_id = ? ORDER BY chunk_index, id",
            (document_id,),
        ).fetchall()
        if not chunk_rows:
            msg = f"unknown document_id: {document_id!r}"
            raise LookupError(msg)

        chunk_ids = tuple(str(row["id"]) for row in chunk_rows)
        evidence_rows = self._db.execute(
            """
            SELECT chunk_id, entity_id
            FROM graph_evidence
            WHERE claim_type = ?
              AND entity_id IS NOT NULL
              AND chunk_id IN (SELECT value FROM json_each(?))
            """,
            (EvidenceClaimType.ENTITY.value, json.dumps(chunk_ids)),
        ).fetchall()

        entities_by_chunk: dict[str, set[str]] = {chunk_id: set() for chunk_id in chunk_ids}
        for row in evidence_rows:
            entities_by_chunk[str(row["chunk_id"])].add(str(row["entity_id"]))

        pair_counts: dict[tuple[str, str], int] = {}
        for entity_ids in entities_by_chunk.values():
            for source_id, target_id in combinations(sorted(entity_ids), 2):
                pair = (source_id, target_id)
                pair_counts[pair] = pair_counts.get(pair, 0) + 1

        total_chunks = len(chunk_ids)
        suggestions: list[SuggestedEdge] = []
        for (source_id, target_id), shared_chunks in sorted(pair_counts.items()):
            if shared_chunks < self._MIN_SHARED_CHUNKS_FOR_SUGGESTION:
                continue
            suggestions.append(
                SuggestedEdge(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relation_type=RelationType.RELATED_TO,
                    confidence=shared_chunks / total_chunks,
                    reason=(
                        f"co-occurred in {shared_chunks} of {total_chunks} chunks"
                    ),
                )
            )

        return tuple(suggestions)

    def purge_source(self, source_id: str) -> EnrichmentPurgeResult:
        """Delete source-owned queue and extraction rows from Enrichment tables."""
        with self._db:
            queue_deleted = self._db.execute(
                "DELETE FROM enrich_queue WHERE source_id = ?",
                (source_id,),
            ).rowcount
            extractions_deleted = self._db.execute(
                "DELETE FROM enrich_extractions WHERE source_id = ?",
                (source_id,),
            ).rowcount

        return EnrichmentPurgeResult(
            source_id=source_id,
            queue_items_removed=max(queue_deleted, 0),
            extractions_removed=max(extractions_deleted, 0),
        )

    def stats(self) -> EnrichmentStats:
        """Return queue item counts per state."""
        rows = self._db.execute(
            """
            SELECT state, COUNT(*) AS count
            FROM enrich_queue
            GROUP BY state
            """
        ).fetchall()
        counts = {str(row["state"]): int(row["count"]) for row in rows}
        return EnrichmentStats(
            pending=counts.get(EnrichmentState.PENDING.value, 0),
            in_progress=counts.get(EnrichmentState.IN_PROGRESS.value, 0),
            completed=counts.get(EnrichmentState.COMPLETED.value, 0),
            failed=counts.get(EnrichmentState.FAILED.value, 0),
        )

    def _select_failed_for_bulk_reset(
        self,
        *,
        limit: int,
        scopes: tuple[str, ...],
    ) -> tuple[sqlite3.Row, ...]:
        base_query = """
            SELECT q.chunk_id
            FROM enrich_queue AS q
            WHERE q.state = ?
            ORDER BY q.enqueued_at, q.chunk_id
            LIMIT ?
            """
        base_params: tuple[object, ...] = (EnrichmentState.FAILED.value, limit)

        joins: list[str] = []
        predicates = ["q.state = ?"]
        params: list[object] = [EnrichmentState.FAILED.value]

        if self._table_exists("source_registry"):
            joins.append("JOIN source_registry AS s ON s.id = q.source_id")
            predicates.append("s.state = 'active'")
            predicates.append("COALESCE(s.enrich, 0) = 1")

        if scopes and self._table_exists("content_chunks"):
            joins.append("JOIN content_chunks AS c ON c.id = q.chunk_id")
            predicates.append(
                "COALESCE(c.scope, 'global') IN (SELECT value FROM json_each(?))"
            )
            params.append(json.dumps(scopes))

        if not joins and not scopes:
            return tuple(self._db.execute(base_query, base_params).fetchall())

        query = "\n".join(
            [
                "SELECT q.chunk_id",
                "FROM enrich_queue AS q",
                *joins,
                f"WHERE {' AND '.join(predicates)}",
                "ORDER BY q.enqueued_at, q.chunk_id",
                "LIMIT ?",
            ]
        )
        params.append(limit)

        try:
            return tuple(self._db.execute(query, tuple(params)).fetchall())
        except sqlite3.Error:
            # Optional joins may be unavailable in mixed-schema deployments.
            return tuple(self._db.execute(base_query, base_params).fetchall())

    def _sync_legacy_chunk_state(self, chunk_ids: tuple[str, ...]) -> None:
        if not chunk_ids or not self._table_exists("chunks"):
            return

        try:
            self._db.execute(
                """
                UPDATE chunks
                SET enrichment_state = 'pending',
                    claimed_at = NULL,
                    claimed_by = NULL,
                    claim_token = NULL,
                    enrichment_error = NULL,
                    enrichment_attempts = 0,
                    last_enrichment_error_at = NULL
                WHERE enrichment_state = 'failed'
                  AND id IN (SELECT value FROM json_each(?))
                """,
                (json.dumps(chunk_ids),),
            )
        except sqlite3.Error:
            # Keep queue reset functional even when legacy table shape differs.
            return

    def _table_exists(self, table_name: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _normalize_reset_limit(limit: int) -> int:
        if isinstance(limit, bool) or not isinstance(limit, int):
            return 100
        return max(limit, 1)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=UTC).replace(tzinfo=None, microsecond=0).isoformat(sep=" ")

    @staticmethod
    def _parse_optional_datetime(raw: object) -> datetime | None:
        if raw is None:
            return None
        return datetime.fromisoformat(str(raw))

    def _row_to_queue_item(self, row: sqlite3.Row) -> EnrichmentQueueItem:
        return EnrichmentQueueItem(
            id=str(row["id"]),
            chunk_id=str(row["chunk_id"]),
            source_id=str(row["source_id"]),
            state=EnrichmentState(str(row["state"])),
            attempts=int(row["attempts"]),
            last_error=None if row["last_error"] is None else str(row["last_error"]),
            enqueued_at=datetime.fromisoformat(str(row["enqueued_at"])),
            started_at=self._parse_optional_datetime(row["started_at"]),
            completed_at=self._parse_optional_datetime(row["completed_at"]),
        )

    def _require_graph(self) -> GraphStore:
        if self._graph is None:
            msg = "graph store is required for extraction operations"
            raise RuntimeError(msg)
        return self._graph
