"""Tests for EnrichmentStore.reset_failed() Protocol method (task #1902).

Tests the contract defined in:
  serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py

Target implementation:
  serve/knowledge/src/owlbear_knowledge/stores/enrichment.py

AC coverage:
  AC1 — EnrichmentResetResult BoundaryModel with fields reset:int=0, remaining_failed:int=0
  AC2 — Protocol defines reset_failed with correct signature; Raises: Never
  AC3 — chunk_ids provided: exclusive filter, limit/scopes ignored, FAILED→PENDING
  AC4 — chunk_ids=None: bulk path, limit caps reset count, selection implementation-defined
  AC5 — error tracking state (last_error, claim fields) cleared on transition
  AC6 — remaining_failed counts items still FAILED after the operation
  AC7 — idempotent: already-pending or no matching FAILED → reset=0, remaining_failed=current
  AC8 — SQLite EnrichmentStore implements reset_failed (reconciles dual-table state)
  AC9 — EnrichmentResetResult exported from protocols package __init__
"""

from __future__ import annotations

import sqlite3

import pytest

from owlbear_knowledge.protocols.enrichment import (
    EnrichmentParams,
    EnrichmentResetResult,  # AC1 — ImportError expected until added
)
from owlbear_knowledge.stores.enrichment import EnrichmentStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db() -> sqlite3.Connection:
    """In-memory SQLite connection shared within a test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture()
def store(db: sqlite3.Connection) -> EnrichmentStore:
    """Fully initialised EnrichmentStore backed by in-memory SQLite."""
    s = EnrichmentStore(db=db)
    s.ensure_tables()
    return s


def _drive_to_failed(store: EnrichmentStore, chunk_id: str, source_id: str = "src-1") -> None:
    """Drive a chunk to FAILED state: enqueue → claim (max_retries=1) → mark_failed."""
    store.enqueue_chunks((chunk_id,), source_id)
    store.claim_batch(EnrichmentParams(batch_size=10, max_retries=1))
    store.mark_failed(chunk_id, "test error")


# ---------------------------------------------------------------------------
# TestFromAC_EnrichmentResetResult — AC1, AC9
# ---------------------------------------------------------------------------


class TestEnrichmentResetResult:
    """EnrichmentResetResult BoundaryModel definition and export checks."""

    # AC1 — type importable from protocols.enrichment

    def test_importable_from_protocols_enrichment(self) -> None:
        from owlbear_knowledge.protocols.enrichment import EnrichmentResetResult  # noqa: F401

        assert EnrichmentResetResult is not None

    def test_default_reset_field_is_zero(self) -> None:
        result = EnrichmentResetResult()
        assert result.reset == 0

    def test_default_remaining_failed_field_is_zero(self) -> None:
        result = EnrichmentResetResult()
        assert result.remaining_failed == 0

    def test_fields_accept_explicit_values(self) -> None:
        result = EnrichmentResetResult(reset=5, remaining_failed=3)
        assert result.reset == 5
        assert result.remaining_failed == 3

    # AC9 — type re-exported from the protocols package __init__

    def test_importable_from_protocols_package(self) -> None:
        from owlbear_knowledge.protocols import EnrichmentResetResult  # noqa: F401

        assert EnrichmentResetResult is not None

    def test_same_class_from_both_import_paths(self) -> None:
        from owlbear_knowledge.protocols import (
            EnrichmentResetResult as FromPackage,
        )
        from owlbear_knowledge.protocols.enrichment import (
            EnrichmentResetResult as FromModule,
        )

        assert FromModule is FromPackage


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedSignature — AC2
# ---------------------------------------------------------------------------


class TestResetFailedSignature:
    """Protocol method signature: correct name, return type, 'Raises: Never'."""

    def test_store_has_reset_failed_method(self, store: EnrichmentStore) -> None:
        assert hasattr(store, "reset_failed")
        assert callable(store.reset_failed)

    def test_returns_enrichment_reset_result(self, store: EnrichmentStore) -> None:
        result = store.reset_failed()
        assert isinstance(result, EnrichmentResetResult)

    def test_callable_with_no_arguments(self, store: EnrichmentStore) -> None:
        """AC2: all parameters have defaults — zero-arg call must work."""
        result = store.reset_failed()
        assert result.reset == 0

    def test_callable_with_all_parameters(self, store: EnrichmentStore) -> None:
        """AC2: full signature reset_failed(chunk_ids, limit, scopes) is accepted."""
        result = store.reset_failed(chunk_ids=None, limit=50, scopes=None)
        assert isinstance(result, EnrichmentResetResult)

    def test_never_raises_on_empty_queue(self, store: EnrichmentStore) -> None:
        """AC2 Raises: Never — empty queue returns result, not exception."""
        result = store.reset_failed(chunk_ids=("nonexistent",), limit=100, scopes=None)
        assert isinstance(result, EnrichmentResetResult)


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedChunkIdsPath — AC3
# ---------------------------------------------------------------------------


class TestResetFailedChunkIdsPath:
    """chunk_ids provided: exclusive filter, limit/scopes ignored, FAILED→PENDING."""

    def test_failed_chunk_transitions_to_pending(self, store: EnrichmentStore) -> None:
        """AC3: matching FAILED item transitions to PENDING."""
        _drive_to_failed(store, "c1")
        result = store.reset_failed(chunk_ids=("c1",))
        assert result.reset == 1
        stats = store.stats()
        assert stats.pending == 1
        assert stats.failed == 0

    def test_reset_count_matches_matching_failed_chunks(self, store: EnrichmentStore) -> None:
        """AC3: reset count equals the number of actually-failed chunks provided."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")
        result = store.reset_failed(chunk_ids=("c1", "c2"))
        assert result.reset == 2

    def test_resets_only_specified_chunks(self, store: EnrichmentStore) -> None:
        """AC3: exclusive filter — unspecified FAILED chunks are not touched."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")
        store.reset_failed(chunk_ids=("c1",))
        stats = store.stats()
        assert stats.pending == 1  # c1 reset
        assert stats.failed == 1  # c2 still FAILED

    def test_limit_ignored_when_chunk_ids_provided(self, store: EnrichmentStore) -> None:
        """AC3: limit parameter has no effect when chunk_ids is given."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")
        # limit=1 would stop after 1 in bulk path; must be ignored here
        result = store.reset_failed(chunk_ids=("c1", "c2"), limit=1)
        assert result.reset == 2

    def test_scopes_ignored_when_chunk_ids_provided(self, store: EnrichmentStore) -> None:
        """AC3: scopes parameter has no effect when chunk_ids is given."""
        _drive_to_failed(store, "c1")
        # scopes points to a scope that doesn't exist — irrelevant for chunk_ids path
        result = store.reset_failed(chunk_ids=("c1",), scopes=("nonexistent-scope",))
        assert result.reset == 1

    def test_non_failed_chunks_not_counted(self, store: EnrichmentStore) -> None:
        """AC3: PENDING chunk provided in chunk_ids → reset=0, nothing changed."""
        store.enqueue_chunks(("c1",), "src-1")  # c1 is PENDING, not FAILED
        result = store.reset_failed(chunk_ids=("c1",))
        assert result.reset == 0


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedBulkPath — AC4
# ---------------------------------------------------------------------------


class TestResetFailedBulkPath:
    """chunk_ids=None bulk path: limit caps count, remaining_failed accurate."""

    def test_bulk_resets_all_failed_items_by_default(self, store: EnrichmentStore) -> None:
        """AC4: with no limit constraint, all FAILED items are reset."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")
        result = store.reset_failed(chunk_ids=None, limit=100)
        assert result.reset == 2
        assert store.stats().failed == 0

    def test_bulk_limit_caps_reset_count(self, store: EnrichmentStore) -> None:
        """AC4: limit=1 resets at most 1 FAILED item."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")
        _drive_to_failed(store, "c3")
        result = store.reset_failed(chunk_ids=None, limit=1)
        assert result.reset == 1

    def test_bulk_limit_two_resets_two(self, store: EnrichmentStore) -> None:
        """AC4: limit=2 with 3 FAILED resets exactly 2."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")
        _drive_to_failed(store, "c3")
        result = store.reset_failed(chunk_ids=None, limit=2)
        assert result.reset == 2

    def test_bulk_remaining_reflects_uncapped_items(self, store: EnrichmentStore) -> None:
        """AC4+AC6: after limited reset, remaining_failed shows unreset count."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")
        result = store.reset_failed(chunk_ids=None, limit=1)
        assert result.reset == 1
        assert result.remaining_failed == 1

    def test_bulk_default_limit_is_100(self, store: EnrichmentStore) -> None:
        """AC2+AC4: default limit is 100 — calling with no args resets up to 100."""
        for i in range(5):
            _drive_to_failed(store, f"c{i}")
        result = store.reset_failed()  # uses default limit=100
        assert result.reset == 5


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedErrorClearing — AC5
# ---------------------------------------------------------------------------


class TestResetFailedErrorClearing:
    """Error tracking state cleared on FAILED→PENDING transition."""

    def test_last_error_cleared_in_queue(self, store: EnrichmentStore, db: sqlite3.Connection) -> None:
        """AC5: last_error column is NULL after reset_failed."""
        _drive_to_failed(store, "c1")
        # Confirm last_error is set before reset
        before = db.execute("SELECT last_error FROM enrich_queue WHERE chunk_id = 'c1'").fetchone()
        assert before is not None  # sanity: row exists
        assert before[0] is not None  # sanity: error was recorded

        store.reset_failed(chunk_ids=("c1",))

        after = db.execute("SELECT last_error FROM enrich_queue WHERE chunk_id = 'c1'").fetchone()
        assert after is not None
        assert after[0] is None

    def test_claim_fields_cleared_after_reset(self, store: EnrichmentStore, db: sqlite3.Connection) -> None:
        """AC5: batch_id and started_at (claim fields) are NULL after reset."""
        _drive_to_failed(store, "c1")
        store.reset_failed(chunk_ids=("c1",))

        row = db.execute("SELECT batch_id, started_at FROM enrich_queue WHERE chunk_id = 'c1'").fetchone()
        assert row is not None
        assert row[0] is None  # batch_id
        assert row[1] is None  # started_at

    def test_reset_chunk_claimable_in_next_batch(self, store: EnrichmentStore) -> None:
        """AC5: after reset, chunk appears in next claim_batch (PENDING state)."""
        _drive_to_failed(store, "c1")
        store.reset_failed(chunk_ids=("c1",))
        batch = store.claim_batch(EnrichmentParams(batch_size=5, max_retries=3))
        claimed = {item.chunk_id for item in batch.items}
        assert "c1" in claimed


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedRemainingFailed — AC6
# ---------------------------------------------------------------------------


class TestResetFailedRemainingFailed:
    """remaining_failed counts items still FAILED after the operation."""

    def test_remaining_zero_when_all_reset(self, store: EnrichmentStore) -> None:
        """AC6: all FAILED items reset → remaining_failed = 0."""
        _drive_to_failed(store, "c1")
        result = store.reset_failed(chunk_ids=("c1",))
        assert result.remaining_failed == 0

    def test_remaining_counts_items_not_covered(self, store: EnrichmentStore) -> None:
        """AC6: items not in chunk_ids remain FAILED and are counted."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")
        result = store.reset_failed(chunk_ids=("c1",))  # c2 stays FAILED
        assert result.remaining_failed == 1

    def test_remaining_zero_when_no_failed_items(self, store: EnrichmentStore) -> None:
        """AC6: no FAILED items at all → remaining_failed = 0."""
        store.enqueue_chunks(("c1",), "src-1")  # PENDING only
        result = store.reset_failed()
        assert result.remaining_failed == 0

    def test_remaining_reflects_failed_after_bulk_limit(self, store: EnrichmentStore) -> None:
        """AC6: after limited bulk reset, remaining_failed is accurate."""
        for i in range(4):
            _drive_to_failed(store, f"c{i}")
        result = store.reset_failed(chunk_ids=None, limit=2)
        # 2 reset, 2 remain
        assert result.reset == 2
        assert result.remaining_failed == 2


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedIdempotency — AC7
# ---------------------------------------------------------------------------


class TestResetFailedIdempotency:
    """Idempotent: already-pending or no matching FAILED → reset=0, no error."""

    def test_already_pending_chunk_ids_reset_zero(self, store: EnrichmentStore) -> None:
        """AC7: chunk in PENDING state provided in chunk_ids → reset=0."""
        store.enqueue_chunks(("c1",), "src-1")
        result = store.reset_failed(chunk_ids=("c1",))
        assert result.reset == 0

    def test_nonexistent_chunk_id_reset_zero(self, store: EnrichmentStore) -> None:
        """AC7: chunk that doesn't exist at all → reset=0, no error."""
        result = store.reset_failed(chunk_ids=("does-not-exist",))
        assert result.reset == 0

    def test_second_call_same_chunk_ids_is_zero(self, store: EnrichmentStore) -> None:
        """AC7: calling reset_failed twice on same chunk_ids is idempotent."""
        _drive_to_failed(store, "c1")
        store.reset_failed(chunk_ids=("c1",))  # first call: resets
        result2 = store.reset_failed(chunk_ids=("c1",))  # second: no-op
        assert result2.reset == 0

    def test_remaining_failed_still_accurate_on_noop(self, store: EnrichmentStore) -> None:
        """AC7: remaining_failed reflects current count even on no-op."""
        _drive_to_failed(store, "c2")  # c2 is FAILED, untouched
        store.enqueue_chunks(("c1",), "src-1")  # c1 is PENDING
        result = store.reset_failed(chunk_ids=("c1",))
        assert result.reset == 0
        assert result.remaining_failed == 1  # c2 still FAILED

    def test_bulk_empty_queue_never_raises(self, store: EnrichmentStore) -> None:
        """AC7: no FAILED items in bulk path → returns zeros, no exception."""
        result = store.reset_failed(chunk_ids=None, limit=100, scopes=None)
        assert result.reset == 0
        assert result.remaining_failed == 0

    def test_bulk_only_pending_queue_reset_zero(self, store: EnrichmentStore) -> None:
        """AC7: queue has only PENDING items in bulk path → reset=0."""
        store.enqueue_chunks(("c1", "c2"), "src-1")
        result = store.reset_failed(chunk_ids=None)
        assert result.reset == 0
        assert result.remaining_failed == 0


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedAttemptsClearing — AC5 (retry-cycle gap fill)
# ---------------------------------------------------------------------------


class TestResetFailedAttemptsClearing:
    """AC5: attempts counter is reset to 0 on FAILED→PENDING transition."""

    def test_attempts_reset_to_zero_chunk_ids_path(self, store: EnrichmentStore, db: sqlite3.Connection) -> None:
        """AC5: attempts column is 0 in enrich_queue after chunk_ids reset."""
        _drive_to_failed(store, "c1")
        before = db.execute("SELECT attempts FROM enrich_queue WHERE chunk_id = 'c1'").fetchone()
        assert before is not None
        assert before[0] > 0  # mark_failed recorded at least one attempt

        store.reset_failed(chunk_ids=("c1",))

        after = db.execute("SELECT attempts FROM enrich_queue WHERE chunk_id = 'c1'").fetchone()
        assert after is not None
        assert after[0] == 0

    def test_attempts_reset_to_zero_bulk_path(self, store: EnrichmentStore, db: sqlite3.Connection) -> None:
        """AC5: attempts column is 0 in enrich_queue after bulk reset."""
        _drive_to_failed(store, "c1")
        _drive_to_failed(store, "c2")

        store.reset_failed(chunk_ids=None, limit=2)

        for chunk_id in ("c1", "c2"):
            row = db.execute(
                "SELECT attempts FROM enrich_queue WHERE chunk_id = ?",
                (chunk_id,),
            ).fetchone()
            assert row is not None
            assert row[0] == 0


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedBulkSourceScope — AC4 (retry-cycle gap fill)
# ---------------------------------------------------------------------------


class TestResetFailedBulkSourceScope:
    """AC4: bulk path excludes disabled/non-enrich sources and honours scopes filter."""

    @pytest.fixture()
    def store_with_source_registry(self, db: sqlite3.Connection) -> EnrichmentStore:
        """EnrichmentStore backed by a db with a source_registry table."""
        s = EnrichmentStore(db=db)
        s.ensure_tables()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS source_registry (
                id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                enrich INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        db.executemany(
            "INSERT INTO source_registry (id, state, enrich) VALUES (?, ?, ?)",
            [
                ("src-active-enrich", "active", 1),
                ("src-active-noenrich", "active", 0),
                ("src-inactive-enrich", "inactive", 1),
            ],
        )
        db.commit()
        return s

    @pytest.fixture()
    def store_with_content_chunks(self, db: sqlite3.Connection) -> EnrichmentStore:
        """EnrichmentStore backed by a db with a content_chunks table (for scope filtering)."""
        s = EnrichmentStore(db=db)
        s.ensure_tables()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS content_chunks (
                id TEXT PRIMARY KEY,
                scope TEXT
            )
            """
        )
        db.executemany(
            "INSERT INTO content_chunks (id, scope) VALUES (?, ?)",
            [
                ("c-scope-a", "scope-a"),
                ("c-scope-b", "scope-b"),
            ],
        )
        db.commit()
        return s

    def test_bulk_excludes_inactive_source(self, store_with_source_registry: EnrichmentStore) -> None:
        """AC4: FAILED item from inactive source is not reset in bulk path."""
        s = store_with_source_registry
        _drive_to_failed(s, "c-active", "src-active-enrich")
        _drive_to_failed(s, "c-inactive", "src-inactive-enrich")

        result = s.reset_failed(chunk_ids=None)

        assert result.reset == 1
        stats = s.stats()
        assert stats.pending == 1  # c-active reset
        assert stats.failed == 1  # c-inactive still FAILED

    def test_bulk_excludes_non_enrich_source(self, store_with_source_registry: EnrichmentStore) -> None:
        """AC4: FAILED item from active but non-enrich source is not reset."""
        s = store_with_source_registry
        _drive_to_failed(s, "c-enrich", "src-active-enrich")
        _drive_to_failed(s, "c-noenrich", "src-active-noenrich")

        result = s.reset_failed(chunk_ids=None)

        assert result.reset == 1
        stats = s.stats()
        assert stats.pending == 1  # c-enrich reset
        assert stats.failed == 1  # c-noenrich still FAILED

    def test_bulk_resets_only_active_enrich_source(self, store_with_source_registry: EnrichmentStore) -> None:
        """AC4: with all three source variants only the active+enrich item is reset."""
        s = store_with_source_registry
        _drive_to_failed(s, "c1", "src-active-enrich")
        _drive_to_failed(s, "c2", "src-active-noenrich")
        _drive_to_failed(s, "c3", "src-inactive-enrich")

        result = s.reset_failed(chunk_ids=None)

        assert result.reset == 1
        assert result.remaining_failed == 2

    def test_bulk_scope_filter_limits_to_matching_chunks(self, store_with_content_chunks: EnrichmentStore) -> None:
        """AC4: scopes filter resets only chunks whose document scope matches."""
        s = store_with_content_chunks
        _drive_to_failed(s, "c-scope-a")
        _drive_to_failed(s, "c-scope-b")

        result = s.reset_failed(chunk_ids=None, scopes=("scope-a",))

        assert result.reset == 1
        stats = s.stats()
        assert stats.pending == 1  # c-scope-a reset
        assert stats.failed == 1  # c-scope-b still FAILED

    def test_bulk_scope_filter_ignores_non_matching_scope(self, store_with_content_chunks: EnrichmentStore) -> None:
        """AC4: scopes filter that matches nothing resets nothing."""
        s = store_with_content_chunks
        _drive_to_failed(s, "c-scope-a")
        _drive_to_failed(s, "c-scope-b")

        result = s.reset_failed(chunk_ids=None, scopes=("scope-c",))

        assert result.reset == 0
        assert result.remaining_failed == 2


# ---------------------------------------------------------------------------
# TestFromAC_ResetFailedLegacyChunks — AC5, AC8 (retry-cycle gap fill)
# ---------------------------------------------------------------------------


class TestResetFailedLegacyChunks:
    """AC5, AC8: mixed-schema reset_failed clears legacy chunks table state."""

    @pytest.fixture()
    def store_with_legacy_chunks(self, db: sqlite3.Connection) -> EnrichmentStore:
        """EnrichmentStore with a legacy chunks table present in the same db."""
        s = EnrichmentStore(db=db)
        s.ensure_tables()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                enrichment_state TEXT NOT NULL DEFAULT 'pending',
                claimed_at TEXT,
                claimed_by TEXT,
                claim_token TEXT,
                enrichment_error TEXT,
                enrichment_attempts INTEGER NOT NULL DEFAULT 0,
                last_enrichment_error_at TEXT
            )
            """
        )
        db.commit()
        return s

    def test_legacy_enrichment_state_reset_to_pending(
        self, store_with_legacy_chunks: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """AC5/AC8: chunks.enrichment_state is set to 'pending' after reset_failed."""
        db.execute(
            "INSERT INTO chunks (id, enrichment_state, enrichment_error, enrichment_attempts)"
            " VALUES ('c1', 'failed', 'boom', 3)"
        )
        db.commit()
        _drive_to_failed(store_with_legacy_chunks, "c1")

        store_with_legacy_chunks.reset_failed(chunk_ids=("c1",))

        row = db.execute("SELECT enrichment_state FROM chunks WHERE id = 'c1'").fetchone()
        assert row is not None
        assert row[0] == "pending"

    def test_legacy_error_and_claim_fields_cleared(
        self, store_with_legacy_chunks: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """AC5/AC8: enrichment_error and all claim fields are NULL after reset."""
        db.execute(
            """
            INSERT INTO chunks
              (id, enrichment_state, enrichment_error,
               claimed_at, claimed_by, claim_token, enrichment_attempts)
            VALUES ('c1', 'failed', 'old error', '2025-01-01', 'agent-x', 'tok-abc', 2)
            """
        )
        db.commit()
        _drive_to_failed(store_with_legacy_chunks, "c1")

        store_with_legacy_chunks.reset_failed(chunk_ids=("c1",))

        row = db.execute(
            """
            SELECT enrichment_error, claimed_at, claimed_by, claim_token,
                   enrichment_attempts
            FROM chunks WHERE id = 'c1'
            """
        ).fetchone()
        assert row is not None
        assert row[0] is None  # enrichment_error
        assert row[1] is None  # claimed_at
        assert row[2] is None  # claimed_by
        assert row[3] is None  # claim_token
        assert row[4] == 0  # enrichment_attempts

    def test_legacy_attempts_reset_to_zero(
        self, store_with_legacy_chunks: EnrichmentStore, db: sqlite3.Connection
    ) -> None:
        """AC5/AC8: enrichment_attempts in legacy chunks table is 0 after reset."""
        db.execute("INSERT INTO chunks (id, enrichment_state, enrichment_attempts) VALUES ('c1', 'failed', 5)")
        db.commit()
        _drive_to_failed(store_with_legacy_chunks, "c1")

        store_with_legacy_chunks.reset_failed(chunk_ids=("c1",))

        row = db.execute("SELECT enrichment_attempts FROM chunks WHERE id = 'c1'").fetchone()
        assert row is not None
        assert row[0] == 0
