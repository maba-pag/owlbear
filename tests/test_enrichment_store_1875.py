"""Tests for EnrichmentStore — queue state machine (task #1875).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/stores/enrichment.py

AC coverage:
  AC1  — enqueue_chunks: PENDING transition, count, idempotency, ValueError on empty
  AC2  — discard_chunks: removes PENDING/FAILED; leaves IN_PROGRESS; idempotent
  AC3  — claim_batch: batch_size, batch_id, claim timestamp, max_retries persisted per-item
  AC4  — claim_batch: stale IN_PROGRESS (>600s) reclaimed to PENDING; fresh untouched
  AC5  — mark_failed: increments attempts, PENDING retry or FAILED (revivable via enqueue_chunks); LookupError guards
  AC6  — stats: counts per state (pending, in_progress, completed, failed)
  AC7  — ensure_tables: creates enrich_queue and enrich_batches idempotently
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear_knowledge.protocols.enrichment import (
    EnrichmentBatch,
    EnrichmentDiscardResult,
    EnrichmentParams,
    EnrichmentState,
    EnrichmentStats,
)
from owlbear_knowledge.stores.enrichment import EnrichmentStore  # greenfield — ImportError expected


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db() -> sqlite3.Connection:
    """In-memory SQLite connection shared within a test."""
    return sqlite3.connect(":memory:")


@pytest.fixture()
def store(db: sqlite3.Connection) -> EnrichmentStore:
    """Fully initialised EnrichmentStore backed by in-memory SQLite."""
    s = EnrichmentStore(db=db)
    s.ensure_tables()
    return s


# ---------------------------------------------------------------------------
# TestFromAC_EnrichmentStore
# ---------------------------------------------------------------------------


class TestFromAC_EnrichmentStore:
    # ------------------------------------------------------------------
    # AC1 — enqueue_chunks
    # ------------------------------------------------------------------

    def test_enqueue_returns_count_of_new_items(self, store: EnrichmentStore) -> None:
        count = store.enqueue_chunks(("c1", "c2", "c3"), "src-1")
        assert count == 3

    def test_enqueue_transitions_chunks_to_pending_state(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        stats = store.stats()
        assert stats.pending == 1

    def test_enqueue_idempotent_for_pending_chunks(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1", "c2"), "src-1")
        count2 = store.enqueue_chunks(("c1", "c2"), "src-1")
        assert count2 == 0

    def test_enqueue_partial_dedup_counts_only_newly_enqueued(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1", "c2"), "src-1")
        count2 = store.enqueue_chunks(("c1", "c2", "c3"), "src-1")
        assert count2 == 1

    def test_enqueue_does_not_reenqueue_in_progress_chunks(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        params = EnrichmentParams(batch_size=1, max_retries=3)
        store.claim_batch(params)
        count = store.enqueue_chunks(("c1",), "src-1")
        assert count == 0

    def test_enqueue_does_not_reenqueue_completed_chunks(
        self, store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        # Manually set COMPLETED — submit_extractions is in #1876 scope
        store.enqueue_chunks(("c1",), "src-1")
        db.execute("UPDATE enrich_queue SET state = 'completed' WHERE chunk_id = 'c1'")
        db.commit()
        count = store.enqueue_chunks(("c1",), "src-1")
        assert count == 0

    def test_enqueue_raises_value_error_on_empty_chunk_ids(self, store: EnrichmentStore) -> None:
        with pytest.raises(ValueError):
            store.enqueue_chunks((), "src-1")

    # ------------------------------------------------------------------
    # AC2 — discard_chunks
    # ------------------------------------------------------------------

    def test_discard_removes_pending_items(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1", "c2"), "src-1")
        result = store.discard_chunks(("c1",))
        assert isinstance(result, EnrichmentDiscardResult)
        assert result.queue_items_removed == 1
        assert "c1" in result.discarded_chunk_ids

    def test_discard_removes_failed_items(self, store: EnrichmentStore) -> None:
        # Reach FAILED via claim + mark_failed with max_retries=1
        store.enqueue_chunks(("c1",), "src-1")
        params = EnrichmentParams(batch_size=1, max_retries=1)
        store.claim_batch(params)
        store.mark_failed("c1", "fatal")  # attempts=1 >= max_retries=1 → FAILED
        result = store.discard_chunks(("c1",))
        assert result.queue_items_removed == 1

    def test_discard_leaves_in_progress_untouched(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        params = EnrichmentParams(batch_size=1, max_retries=3)
        store.claim_batch(params)  # c1 → IN_PROGRESS
        result = store.discard_chunks(("c1",))
        assert result.queue_items_removed == 0
        # IN_PROGRESS count must still be 1
        assert store.stats().in_progress == 1

    def test_discard_absent_chunks_silently_ignored(self, store: EnrichmentStore) -> None:
        result = store.discard_chunks(("ghost-1", "ghost-2"))
        assert result.queue_items_removed == 0

    def test_discard_idempotent(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        store.discard_chunks(("c1",))
        result2 = store.discard_chunks(("c1",))
        assert result2.queue_items_removed == 0

    def test_discard_mixed_states_removes_only_pending_and_failed(
        self, store: EnrichmentStore
    ) -> None:
        # c_in_progress: claim → IN_PROGRESS
        store.enqueue_chunks(("c_in_progress",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))

        # c_pending: enqueued but not claimed
        store.enqueue_chunks(("c_pending",), "src-1")

        # c_failed: claim → mark_failed with max_retries=1 → FAILED
        store.enqueue_chunks(("c_failed",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))
        store.mark_failed("c_failed", "err")

        result = store.discard_chunks(("c_in_progress", "c_pending", "c_failed"))
        # IN_PROGRESS untouched → only PENDING + FAILED removed
        assert result.queue_items_removed == 2
        assert store.stats().in_progress == 1

    # ------------------------------------------------------------------
    # AC3 — claim_batch
    # ------------------------------------------------------------------

    def test_claim_batch_transitions_pending_to_in_progress(
        self, store: EnrichmentStore
    ) -> None:
        store.enqueue_chunks(("c1", "c2"), "src-1")
        params = EnrichmentParams(batch_size=2, max_retries=3)
        batch = store.claim_batch(params)
        assert isinstance(batch, EnrichmentBatch)
        assert len(batch.items) == 2
        for item in batch.items:
            assert item.state == EnrichmentState.IN_PROGRESS

    def test_claim_batch_assigns_batch_id(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        batch = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        assert batch.batch_id
        assert isinstance(batch.batch_id, str)

    def test_claim_batch_assigns_unique_batch_id_per_call(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1", "c2"), "src-1")
        batch1 = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        batch2 = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        assert batch1.batch_id != batch2.batch_id

    def test_claim_batch_assigns_claim_timestamp_to_items(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        batch = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        for item in batch.items:
            assert item.started_at is not None

    def test_claim_batch_respects_batch_size_limit(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1", "c2", "c3", "c4", "c5"), "src-1")
        batch = store.claim_batch(EnrichmentParams(batch_size=2, max_retries=3))
        assert len(batch.items) == 2

    def test_claim_batch_returns_fewer_when_queue_smaller_than_batch_size(
        self, store: EnrichmentStore
    ) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        batch = store.claim_batch(EnrichmentParams(batch_size=10, max_retries=3))
        assert len(batch.items) == 1

    def test_claim_batch_empty_queue_returns_empty_batch(self, store: EnrichmentStore) -> None:
        batch = store.claim_batch(EnrichmentParams(batch_size=10, max_retries=3))
        assert len(batch.items) == 0

    def test_claim_batch_claimed_items_not_visible_to_second_claim(
        self, store: EnrichmentStore
    ) -> None:
        store.enqueue_chunks(("c1", "c2"), "src-1")
        batch1 = store.claim_batch(EnrichmentParams(batch_size=2, max_retries=3))
        batch2 = store.claim_batch(EnrichmentParams(batch_size=2, max_retries=3))
        claimed_ids = {item.chunk_id for item in batch1.items}
        for item in batch2.items:
            assert item.chunk_id not in claimed_ids

    def test_claim_batch_max_retries_persisted_governs_mark_failed_threshold(
        self, store: EnrichmentStore
    ) -> None:
        """Per-item max_retries persisted at claim time determines FAILED transition."""
        store.enqueue_chunks(("c1",), "src-1")
        # Claim with max_retries=1 — first failure should be permanent
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))
        result = store.mark_failed("c1", "err")
        assert result.state == EnrichmentState.FAILED

    # ------------------------------------------------------------------
    # AC4 — claim_batch: stale IN_PROGRESS reclaim
    # ------------------------------------------------------------------

    def test_claim_batch_reclaims_stale_in_progress_to_pending(
        self, store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        # Backdate started_at to 701 seconds ago to simulate stale claim
        db.execute(
            "UPDATE enrich_queue SET started_at = datetime('now', '-701 seconds')"
            " WHERE chunk_id = 'c1'"
        )
        db.commit()
        # Next claim_batch must reclaim stale item
        batch = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        chunk_ids = {item.chunk_id for item in batch.items}
        assert "c1" in chunk_ids

    def test_claim_batch_does_not_reclaim_fresh_in_progress(
        self, store: EnrichmentStore
    ) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        # c1 freshly claimed; second call must not return it
        batch2 = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        chunk_ids = {item.chunk_id for item in batch2.items}
        assert "c1" not in chunk_ids

    # ------------------------------------------------------------------
    # AC5 — mark_failed
    # ------------------------------------------------------------------

    def test_mark_failed_returns_to_pending_below_max_retries(
        self, store: EnrichmentStore
    ) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        result = store.mark_failed("c1", "transient error")
        assert result.state == EnrichmentState.PENDING
        assert result.chunk_id == "c1"

    def test_mark_failed_increments_attempts_counter(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        result = store.mark_failed("c1", "err")
        assert result.attempts == 1

    def test_mark_failed_transitions_to_failed_when_attempts_reach_max_retries(
        self, store: EnrichmentStore
    ) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))
        result = store.mark_failed("c1", "fatal")  # attempts=1 >= max_retries=1
        assert result.state == EnrichmentState.FAILED

    def test_mark_failed_uses_per_item_max_retries_from_claim_time(
        self, store: EnrichmentStore
    ) -> None:
        """max_retries stored per-item at claim time — governs retry vs permanent failure."""
        store.enqueue_chunks(("c1",), "src-1")
        params = EnrichmentParams(batch_size=1, max_retries=2)
        store.claim_batch(params)
        # First failure: attempts=1 < max_retries=2 → PENDING
        r1 = store.mark_failed("c1", "err1")
        assert r1.state == EnrichmentState.PENDING
        # Re-claim and fail again: attempts=2 >= max_retries=2 → FAILED
        store.claim_batch(params)
        r2 = store.mark_failed("c1", "err2")
        assert r2.state == EnrichmentState.FAILED

    def test_mark_failed_raises_lookup_error_if_chunk_is_pending_not_in_progress(
        self, store: EnrichmentStore
    ) -> None:
        store.enqueue_chunks(("c1",), "src-1")  # c1 is PENDING
        with pytest.raises(LookupError):
            store.mark_failed("c1", "error")

    def test_mark_failed_raises_lookup_error_if_chunk_not_found(
        self, store: EnrichmentStore
    ) -> None:
        with pytest.raises(LookupError):
            store.mark_failed("nonexistent-chunk", "error")

    # ------------------------------------------------------------------
    # AC6 — stats
    # ------------------------------------------------------------------

    def test_stats_returns_enrichment_stats_instance(self, store: EnrichmentStore) -> None:
        assert isinstance(store.stats(), EnrichmentStats)

    def test_stats_zero_counts_on_empty_queue(self, store: EnrichmentStore) -> None:
        s = store.stats()
        assert s.pending == 0
        assert s.in_progress == 0
        assert s.completed == 0
        assert s.failed == 0

    def test_stats_counts_pending(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1", "c2"), "src-1")
        assert store.stats().pending == 2

    def test_stats_counts_in_progress(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1", "c2", "c3"), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=2, max_retries=3))
        assert store.stats().in_progress == 2

    def test_stats_counts_failed(self, store: EnrichmentStore) -> None:
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))
        store.mark_failed("c1", "err")  # → FAILED
        assert store.stats().failed == 1

    def test_stats_counts_completed(
        self, store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        # COMPLETED transition belongs to submit_extractions (#1876); set via SQL for stats test
        store.enqueue_chunks(("c1",), "src-1")
        db.execute("UPDATE enrich_queue SET state = 'completed' WHERE chunk_id = 'c1'")
        db.commit()
        assert store.stats().completed == 1

    # ------------------------------------------------------------------
    # AC7 — ensure_tables
    # ------------------------------------------------------------------

    def test_ensure_tables_creates_enrich_queue_table(
        self, db: sqlite3.Connection
    ) -> None:
        s = EnrichmentStore(db=db)
        s.ensure_tables()
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "enrich_queue" in tables

    def test_ensure_tables_creates_enrich_batches_table(
        self, db: sqlite3.Connection
    ) -> None:
        s = EnrichmentStore(db=db)
        s.ensure_tables()
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "enrich_batches" in tables

    def test_ensure_tables_is_idempotent(self, db: sqlite3.Connection) -> None:
        s = EnrichmentStore(db=db)
        s.ensure_tables()
        s.ensure_tables()  # must not raise

    # ------------------------------------------------------------------
    # AC1 x AC5 — FAILED item re-enqueue boundary (retry-cycle addition)
    # Resolves reviewer finding: cross-method contract between AC1 and AC5
    # was not independently verifiable. Architect re-review confirmed:
    # enqueue_chunks MAY revive FAILED items to PENDING.
    # ------------------------------------------------------------------

    def test_enqueue_revives_failed_item_to_pending_and_returns_count_one(
        self, store: EnrichmentStore
    ) -> None:
        """FAILED items revived to PENDING by enqueue_chunks; count reflects revival."""
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))
        store.mark_failed("c1", "fatal error")  # attempts=1 >= max_retries=1 → FAILED
        assert store.stats().failed == 1

        count = store.enqueue_chunks(("c1",), "src-1")

        assert count == 1
        assert store.stats().pending == 1
        assert store.stats().failed == 0

    def test_enqueue_preserves_attempts_count_on_failed_item_revival(
        self, store: EnrichmentStore
    ) -> None:
        """Reviving a FAILED item preserves its attempts count (not reset to 0)."""
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))
        store.mark_failed("c1", "fatal error")  # attempts=1, state=FAILED
        store.enqueue_chunks(("c1",), "src-1")  # revive → PENDING

        # Claim to read the item's stored attempts value
        batch = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        assert len(batch.items) == 1
        item = batch.items[0]
        assert item.attempts == 1  # preserved, not reset to 0

    def test_enqueue_clears_last_error_on_failed_item_revival(
        self, store: EnrichmentStore
    ) -> None:
        """Reviving a FAILED item clears last_error (AC1: 'last_error cleared')."""
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=1))
        store.mark_failed("c1", "the error message")  # attempts=1, state=FAILED
        store.enqueue_chunks(("c1",), "src-1")  # revive → PENDING

        # Claim to read the item's stored last_error value
        batch = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        assert len(batch.items) == 1
        item = batch.items[0]
        assert item.last_error is None  # cleared on revival

    # ------------------------------------------------------------------
    # AC4 — stale reclaim boundary (retry-cycle addition #2)
    # Resolves reviewer finding: AC4 says "strictly >600s" but tests used 701s
    # and fresh only, leaving the exact boundary unspecified.  Architect
    # re-review (Re-review #2) chose strict >600s and prescribed 601s/599s
    # as the non-flaky proof shape (exact 600s is wall-clock-unreliable in
    # SQLite).  Builder must also change `<=` to `<` in claim_batch.
    # ------------------------------------------------------------------

    def test_claim_batch_reclaims_item_strictly_more_than_600s_old(
        self, store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """An item 601s old (strictly >600s) IS reclaimed to PENDING (AC4)."""
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        # Backdate started_at to exactly 601 seconds ago
        db.execute(
            "UPDATE enrich_queue SET started_at = datetime('now', '-601 seconds')"
            " WHERE chunk_id = 'c1'"
        )
        db.commit()
        batch = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        chunk_ids = {item.chunk_id for item in batch.items}
        assert "c1" in chunk_ids, "item aged 601s must be reclaimed (strictly >600s TTL)"

    def test_claim_batch_does_not_reclaim_item_599s_old(
        self, store: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """An item 599s old (not yet >600s) is NOT reclaimed (AC4 strict > boundary)."""
        store.enqueue_chunks(("c1",), "src-1")
        store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        # Backdate started_at to 599 seconds ago — still within TTL
        db.execute(
            "UPDATE enrich_queue SET started_at = datetime('now', '-599 seconds')"
            " WHERE chunk_id = 'c1'"
        )
        db.commit()
        batch = store.claim_batch(EnrichmentParams(batch_size=1, max_retries=3))
        chunk_ids = {item.chunk_id for item in batch.items}
        assert "c1" not in chunk_ids, "item aged 599s must NOT be reclaimed (within 600s TTL)"
