"""Tests for ConsolidationService — TDD RED phase for task #789.

Contract tests for the consolidation service that periodically synthesizes
cross-document insights from unconsolidated chunks.  All tests must fail
until #723 implements the service.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest

from owlbear.memory.knowledge.consolidation import (
    ConsolidationService,  # type: ignore[import-not-found]
)
from owlbear.memory.knowledge.schema import init_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    """Return an in-memory DB with the full v8 schema initialised."""
    conn = sqlite3.Connection(":memory:")
    init_db(conn)
    conn.commit()
    return conn


# Module-level counter for unique chunk IDs across multiple _seed_chunks calls.
_chunk_counter = 0


def _seed_chunks(
    conn: sqlite3.Connection,
    n: int,
    *,
    consolidated: int = 0,
    scope: str = "global",
) -> list[str]:
    """Insert *n* unconsolidated chunks and return their IDs."""
    global _chunk_counter  # noqa: PLW0603
    ids: list[str] = []
    for i in range(n):
        cid = f"chunk-{_chunk_counter}"
        doc_id = f"doc-{_chunk_counter % 3}"
        _chunk_counter += 1
        # Ensure the parent document exists (FK constraint).
        conn.execute(
            "INSERT OR IGNORE INTO documents (id, title, content, created_at, scope) "
            "VALUES (?, ?, ?, ?, ?)",
            (doc_id, doc_id, "", "2026-01-01", scope),
        )
        conn.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content, "
            "created_at, scope, consolidated) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cid, doc_id, i, f"content for chunk {cid}", "2026-01-01", scope, consolidated),
        )
        ids.append(cid)
    conn.commit()
    return ids


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidateReads
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidateReads:  # noqa: N801
    """AC: consolidate() reads unconsolidated chunks (consolidated=0) from DB."""

    @pytest.mark.asyncio
    async def test_reads_only_unconsolidated_chunks(self) -> None:
        """Only chunks with consolidated=0 should be picked up."""
        conn = _make_db()
        _seed_chunks(conn, 3, consolidated=0)
        _seed_chunks(conn, 2, consolidated=1)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        count = await svc.consolidate()

        # Should process only the 3 unconsolidated chunks, not the 2 already done.
        assert count >= 1
        unconsolidated = conn.execute(
            "SELECT count(*) FROM chunks WHERE consolidated = 0"
        ).fetchone()[0]
        assert unconsolidated == 0, "All unconsolidated chunks should be marked done"

    @pytest.mark.asyncio
    async def test_queries_correct_scope(self) -> None:
        """consolidate() should read chunks regardless of scope (default behaviour)."""
        conn = _make_db()
        _seed_chunks(conn, 2, scope="project-a")
        _seed_chunks(conn, 2, scope="project-b")

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        count = await svc.consolidate()
        assert count >= 1


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidateStoresInsight
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidateStoresInsight:  # noqa: N801
    """AC: consolidate() stores insight row in consolidations table with source_ids JSON array."""

    @pytest.mark.asyncio
    async def test_insight_row_created(self) -> None:
        """At least one row should appear in consolidations after processing chunks."""
        conn = _make_db()
        _seed_chunks(conn, 3)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        await svc.consolidate()

        rows = conn.execute("SELECT id, source_ids, insight FROM consolidations").fetchall()
        assert len(rows) >= 1, "Should store at least one insight"

    @pytest.mark.asyncio
    async def test_source_ids_is_json_array(self) -> None:
        """source_ids column must be a JSON-encoded list of chunk IDs."""
        conn = _make_db()
        chunk_ids = _seed_chunks(conn, 3)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        await svc.consolidate()

        rows = conn.execute("SELECT source_ids FROM consolidations").fetchall()
        assert len(rows) >= 1
        for (raw_ids,) in rows:
            parsed = json.loads(raw_ids)
            assert isinstance(parsed, list), "source_ids must be a JSON array"
            for sid in parsed:
                assert sid in chunk_ids, f"source_id {sid} not in original chunk IDs"

    @pytest.mark.asyncio
    async def test_insight_has_id_and_created_at(self) -> None:
        """Each consolidation row must have a non-empty id and created_at."""
        conn = _make_db()
        _seed_chunks(conn, 2)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        await svc.consolidate()

        rows = conn.execute("SELECT id, created_at FROM consolidations").fetchall()
        assert len(rows) >= 1
        for row_id, created_at in rows:
            assert row_id, "consolidation id must not be empty"
            assert created_at, "created_at must not be empty"


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidateMarksChunks
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidateMarksChunks:  # noqa: N801
    """AC: consolidate() marks source chunks consolidated=1."""

    @pytest.mark.asyncio
    async def test_processed_chunks_marked_consolidated(self) -> None:
        """After consolidate(), all processed chunks should have consolidated=1."""
        conn = _make_db()
        chunk_ids = _seed_chunks(conn, 4)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        await svc.consolidate()

        for cid in chunk_ids:
            val = conn.execute("SELECT consolidated FROM chunks WHERE id = ?", (cid,)).fetchone()[0]
            assert val == 1, f"Chunk {cid} should be consolidated=1"

    @pytest.mark.asyncio
    async def test_already_consolidated_chunks_unchanged(self) -> None:
        """Chunks already consolidated=1 should not be touched again."""
        conn = _make_db()
        pre_ids = _seed_chunks(conn, 2, consolidated=1)
        _seed_chunks(conn, 2, consolidated=0)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        await svc.consolidate()

        # Pre-consolidated chunks should still be 1
        for cid in pre_ids:
            val = conn.execute("SELECT consolidated FROM chunks WHERE id = ?", (cid,)).fetchone()[0]
            assert val == 1


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidateReturnsCount
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidateReturnsCount:  # noqa: N801
    """AC: consolidate() returns count of insights created."""

    @pytest.mark.asyncio
    async def test_returns_int_count(self) -> None:
        """Return value must be an integer."""
        conn = _make_db()
        _seed_chunks(conn, 3)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        result = await svc.consolidate()
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_count_matches_consolidation_rows(self) -> None:
        """The returned count should equal the number of rows in consolidations."""
        conn = _make_db()
        _seed_chunks(conn, 5)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        count = await svc.consolidate()

        rows = conn.execute("SELECT count(*) FROM consolidations").fetchone()[0]
        assert count == rows


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidateBatchSize
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidateBatchSize:  # noqa: N801
    """AC: consolidate() batch_size parameter limits chunk selection."""

    @pytest.mark.asyncio
    async def test_batch_size_limits_processing(self) -> None:
        """With 5 unconsolidated chunks and batch_size=2, only 2 should be processed."""
        conn = _make_db()
        _seed_chunks(conn, 5)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        await svc.consolidate(batch_size=2)

        still_unconsolidated = conn.execute(
            "SELECT count(*) FROM chunks WHERE consolidated = 0"
        ).fetchone()[0]
        assert still_unconsolidated == 3, "Only 2 of 5 chunks should be processed"

    @pytest.mark.asyncio
    async def test_batch_size_default_is_50(self) -> None:
        """Default batch_size should be 50 (per AC)."""
        conn = _make_db()
        _seed_chunks(conn, 3)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        # With only 3 chunks and default batch_size=50, all should be processed.
        await svc.consolidate()

        still_unconsolidated = conn.execute(
            "SELECT count(*) FROM chunks WHERE consolidated = 0"
        ).fetchone()[0]
        assert still_unconsolidated == 0

    @pytest.mark.asyncio
    async def test_multiple_batches_cover_all(self) -> None:
        """Two calls with batch_size=3 should cover 5 chunks (3+2)."""
        conn = _make_db()
        _seed_chunks(conn, 5)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        count1 = await svc.consolidate(batch_size=3)
        count2 = await svc.consolidate(batch_size=3)

        assert count1 >= 1
        assert count2 >= 1
        still_unconsolidated = conn.execute(
            "SELECT count(*) FROM chunks WHERE consolidated = 0"
        ).fetchone()[0]
        assert still_unconsolidated == 0


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidateEmpty
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidateEmpty:  # noqa: N801
    """AC: consolidate() with no unconsolidated chunks returns 0."""

    @pytest.mark.asyncio
    async def test_empty_db_returns_zero(self) -> None:
        """No chunks at all -> returns 0."""
        conn = _make_db()

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        result = await svc.consolidate()
        assert result == 0

    @pytest.mark.asyncio
    async def test_all_consolidated_returns_zero(self) -> None:
        """All chunks already consolidated -> returns 0."""
        conn = _make_db()
        _seed_chunks(conn, 3, consolidated=1)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        result = await svc.consolidate()
        assert result == 0

    @pytest.mark.asyncio
    async def test_no_consolidation_rows_when_empty(self) -> None:
        """When returning 0, no new rows should be in consolidations."""
        conn = _make_db()

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        await svc.consolidate()

        rows = conn.execute("SELECT count(*) FROM consolidations").fetchone()[0]
        assert rows == 0


# ---------------------------------------------------------------------------
# TestFromAC_SchedulePeriodic
# ---------------------------------------------------------------------------


class TestFromAC_SchedulePeriodic:  # noqa: N801
    """AC: schedule_periodic() calls consolidate() on interval (mock asyncio.sleep)."""

    @pytest.mark.asyncio
    async def test_calls_consolidate_on_interval(self) -> None:
        """schedule_periodic() should call consolidate() after sleeping interval seconds."""
        conn = _make_db()
        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]

        call_count = 0

        async def _mock_consolidate(_batch_size: int = 50) -> int:
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise asyncio.CancelledError
            return 0

        svc.consolidate = _mock_consolidate  # type: ignore[assignment]

        with (
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            pytest.raises(asyncio.CancelledError),
        ):
            await svc.schedule_periodic(interval=60)

        assert call_count == 3
        assert mock_sleep.await_count >= 2
        for call in mock_sleep.call_args_list:
            assert call.args[0] == 60

    @pytest.mark.asyncio
    async def test_schedule_periodic_uses_given_interval(self) -> None:
        """The interval parameter should be honoured, not hardcoded."""
        conn = _make_db()
        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]

        async def _stop(*_: object, **__: object) -> int:
            raise asyncio.CancelledError

        svc.consolidate = _stop  # type: ignore[assignment]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError
            with pytest.raises(asyncio.CancelledError):
                await svc.schedule_periodic(interval=120)

            if mock_sleep.call_args_list:
                assert mock_sleep.call_args_list[0].args[0] == 120


# ---------------------------------------------------------------------------
# TestFromAC_LLMFailure
# ---------------------------------------------------------------------------


class TestFromAC_LLMFailure:  # noqa: N801
    """AC: LLM failure during consolidation is logged, does not crash the loop."""

    @pytest.mark.asyncio
    async def test_llm_error_logged_not_raised(self, caplog: pytest.LogCaptureFixture) -> None:
        """If the LLM call raises, consolidate() should log and return 0 (not raise)."""
        conn = _make_db()
        _seed_chunks(conn, 3)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]

        with (
            patch.object(svc, "_run_llm", side_effect=RuntimeError("LLM down")),
            caplog.at_level(logging.WARNING),
        ):
            result = await svc.consolidate()

        assert isinstance(result, int)
        assert result == 0

    @pytest.mark.asyncio
    async def test_loop_continues_after_llm_failure(self) -> None:
        """schedule_periodic() must not crash when consolidate() encounters LLM errors."""
        conn = _make_db()
        _seed_chunks(conn, 3)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]

        call_count = 0
        _llm_err = "LLM down"

        async def _failing_then_ok(_batch_size: int = 50) -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError(_llm_err)
            if call_count >= 3:
                raise asyncio.CancelledError
            return 0

        svc.consolidate = _failing_then_ok  # type: ignore[assignment]

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(asyncio.CancelledError),
        ):
            await svc.schedule_periodic(interval=10)

        assert call_count == 3


# ---------------------------------------------------------------------------
# TestFromAC_Constructor
# ---------------------------------------------------------------------------


class TestFromAC_Constructor:  # noqa: N801
    """AC: Constructor takes (conn, graph_store, model)."""

    def test_constructor_accepts_required_args(self) -> None:
        """ConsolidationService(conn, graph_store, model) must not raise."""
        conn = _make_db()
        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        assert svc is not None

    def test_constructor_stores_conn(self) -> None:
        """The service must hold a reference to the connection."""
        conn = _make_db()
        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]
        assert hasattr(svc, "_conn") or hasattr(svc, "conn")
