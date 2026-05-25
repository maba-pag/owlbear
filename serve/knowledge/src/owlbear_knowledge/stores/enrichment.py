"""SQLite-backed Enrichment queue state-machine store."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from owlbear_knowledge.protocols.enrichment import (
    EnrichmentBatch,
    EnrichmentDiscardResult,
    EnrichmentParams,
    EnrichmentQueueItem,
    EnrichmentState,
    EnrichmentStats,
)
from owlbear_knowledge.protocols.enrichment import (
    EnrichmentStore as EnrichmentStoreProtocol,
)


class EnrichmentStore(EnrichmentStoreProtocol):
    """SQLite-backed queue state machine for enrichment work items."""

    _CLAIM_TTL_SECONDS = 600

    def __init__(self, *, db: sqlite3.Connection) -> None:
        self._db = db
        self._db.row_factory = sqlite3.Row

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
                  AND started_at <= datetime('now', ?)
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
