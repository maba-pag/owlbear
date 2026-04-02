"""Tests for ConsolidationService — LLM callable injection (#523).

Updated from #138 stub tests to use the new llm_fn-injected constructor.
Covers: constructor w/ llm_fn, consolidate() DB+LLM flow, exception
handling, schedule_periodic(), and the ConsolidationInsight schema.
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from owlbear_knowledge.consolidation import ConsolidationInsight, ConsolidationService
from owlbear_knowledge.schema import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with the full v8 schema."""
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _insert_chunk(conn: sqlite3.Connection, chunk_id: str, content: str) -> None:
    """Insert a single unconsolidated chunk row into the chunks table."""
    conn.execute(
        "INSERT INTO chunks (id, content) VALUES (?, ?)",
        (chunk_id, content),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidationService
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidationService:  # noqa: N801
    """AC: ConsolidationService(conn, llm_fn) constructor and consolidate() for #523."""

    # -- Constructor --

    def test_constructor_requires_llm_fn(self) -> None:
        """ConsolidationService(conn) without llm_fn raises TypeError."""
        conn = sqlite3.connect(":memory:")
        with pytest.raises(TypeError):
            ConsolidationService(conn)  # type: ignore[call-arg]

    def test_constructor_accepts_llm_fn_keyword(self) -> None:
        """ConsolidationService(conn, llm_fn=<async callable>) instantiates correctly."""
        conn = sqlite3.connect(":memory:")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        assert svc is not None

    # -- consolidate(): no rows --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_returns_zero_when_no_chunks(self) -> None:
        """consolidate() returns 0 when no unconsolidated chunks exist."""
        conn = _make_db()
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        result = await svc.consolidate()
        assert result == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_no_llm_call_when_no_chunks(self) -> None:
        """consolidate() does NOT call llm_fn when no unconsolidated chunks exist."""
        conn = _make_db()
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        llm_fn.assert_not_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_ignores_already_consolidated_chunks(self) -> None:
        """consolidate() ignores chunks with consolidated=1 and returns 0."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "already done")
        conn.execute("UPDATE chunks SET consolidated = 1 WHERE id = 'c1'")
        conn.commit()
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        result = await svc.consolidate()
        assert result == 0
        llm_fn.assert_not_awaited()

    # -- consolidate(): prompt format --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_prompt_format_single_chunk(self) -> None:
        """Prompt passed to llm_fn contains 'Chunk 1: {content}'."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "hello world")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        prompt: str = llm_fn.call_args[0][0]
        assert "Chunk 1: hello world" in prompt

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_prompt_multiple_chunks_joined_by_double_newline(self) -> None:
        """Multiple chunks are numbered and joined with double newlines."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "first chunk")
        _insert_chunk(conn, "c2", "second chunk")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        prompt: str = llm_fn.call_args[0][0]
        assert "Chunk 1: first chunk" in prompt
        assert "Chunk 2: second chunk" in prompt
        assert "\n\n" in prompt

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_respects_batch_size(self) -> None:
        """consolidate(batch_size=1) processes at most 1 chunk even when 2 exist."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "first")
        _insert_chunk(conn, "c2", "second")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate(batch_size=1)
        prompt: str = llm_fn.call_args[0][0]
        assert "Chunk 2" not in prompt

    # -- consolidate(): success — return value and DB state --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_returns_one_on_success(self) -> None:
        """consolidate() returns 1 after successfully processing a batch."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "content")
        llm_fn: AsyncMock = AsyncMock(return_value="synthesized insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        result = await svc.consolidate()
        assert result == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_inserts_one_consolidations_row(self) -> None:
        """consolidate() inserts exactly one row into the consolidations table."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "content")
        llm_fn: AsyncMock = AsyncMock(return_value="the insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        rows = conn.execute("SELECT * FROM consolidations").fetchall()
        assert len(rows) == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidation_row_insight_equals_llm_output(self) -> None:
        """The inserted consolidation row's insight equals the llm_fn return value."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "content")
        llm_fn: AsyncMock = AsyncMock(return_value="expected insight text")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        row = conn.execute("SELECT insight FROM consolidations").fetchone()
        assert row is not None
        assert row[0] == "expected insight text"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidation_row_source_ids_is_json_array(self) -> None:
        """The consolidation row's source_ids is a JSON array containing the chunk ID."""
        conn = _make_db()
        _insert_chunk(conn, "chunk-abc", "content")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        row = conn.execute("SELECT source_ids FROM consolidations").fetchone()
        assert row is not None
        source_ids = json.loads(row[0])
        assert isinstance(source_ids, list)
        assert "chunk-abc" in source_ids

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidation_row_id_is_uuid4_format(self) -> None:
        """The consolidation row's id is a UUID4 string."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "content")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        row = conn.execute("SELECT id FROM consolidations").fetchone()
        assert row is not None
        uuid4_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        )
        assert uuid4_pattern.match(row[0]), f"Not a valid UUID4: {row[0]!r}"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidation_row_created_at_is_set(self) -> None:
        """The consolidation row's created_at is a non-empty UTC ISO timestamp."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "content")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        row = conn.execute("SELECT created_at FROM consolidations").fetchone()
        assert row is not None
        assert row[0]  # non-empty

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_marks_processed_chunks_consolidated(self) -> None:
        """consolidate() sets consolidated=1 on all processed chunk rows."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "content")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        await svc.consolidate()
        row = conn.execute("SELECT consolidated FROM chunks WHERE id = 'c1'").fetchone()
        assert row is not None
        assert row[0] == 1

    # -- consolidate(): exception handling --

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_llm_exception_returns_zero(self) -> None:
        """When llm_fn raises, consolidate() returns 0 without propagating the error."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "content")
        llm_fn: AsyncMock = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        result = await svc.consolidate()
        assert result == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_consolidate_llm_exception_logs_warning_with_exc_info(self) -> None:
        """When llm_fn raises, logger.warning is called with exc_info=True."""
        conn = _make_db()
        _insert_chunk(conn, "c1", "content")
        llm_fn: AsyncMock = AsyncMock(side_effect=ValueError("bad response"))
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        with patch("owlbear_knowledge.consolidation.logger") as mock_logger:
            await svc.consolidate()
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs.get("exc_info") is True


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidationService_SchedulePeriodic
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidationService_SchedulePeriodic:  # noqa: N801
    """AC: schedule_periodic(interval=3600) async loop for #523."""

    def test_schedule_periodic_method_exists(self) -> None:
        """ConsolidationService has a schedule_periodic(interval) method."""
        conn = sqlite3.connect(":memory:")
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        assert hasattr(svc, "schedule_periodic")
        assert callable(svc.schedule_periodic)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_periodic_reraises_cancelled_error(self) -> None:
        """schedule_periodic() re-raises asyncio.CancelledError."""
        conn = _make_db()
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        with (
            patch("asyncio.sleep", new_callable=AsyncMock, side_effect=asyncio.CancelledError),
            pytest.raises(asyncio.CancelledError),
        ):
            await svc.schedule_periodic(interval=0)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_periodic_calls_consolidate(self) -> None:
        """schedule_periodic() calls consolidate() at least once before terminating."""
        conn = _make_db()
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        consolidate_calls: list[int] = []

        async def mock_consolidate(**_: object) -> int:
            consolidate_calls.append(1)
            raise asyncio.CancelledError  # terminate after first call

        svc.consolidate = mock_consolidate  # type: ignore[method-assign]
        with pytest.raises(asyncio.CancelledError):
            await svc.schedule_periodic(interval=0)
        assert len(consolidate_calls) >= 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_periodic_catches_non_cancelled_exceptions(self) -> None:
        """schedule_periodic() catches non-CancelledError from consolidate() and continues."""
        conn = _make_db()
        llm_fn: AsyncMock = AsyncMock(return_value="insight")
        svc = ConsolidationService(conn, llm_fn=llm_fn)
        call_count = 0

        err_msg = "transient error"

        async def mock_consolidate(**_: object) -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError(err_msg)
            raise asyncio.CancelledError  # terminate on second call

        svc.consolidate = mock_consolidate  # type: ignore[method-assign]
        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            pytest.raises(asyncio.CancelledError),
        ):
            await svc.schedule_periodic(interval=0)
        assert call_count == 2  # first raised RuntimeError (caught), second CancelledError


# ---------------------------------------------------------------------------
# TestFromAC_ConsolidationInsight
# ---------------------------------------------------------------------------


class TestFromAC_ConsolidationInsight:  # noqa: N801
    """AC: ConsolidationInsight model validation and frozen constraint."""

    def test_instantiates_with_required_fields(self) -> None:
        """ConsolidationInsight validates all required fields when provided."""
        insight = ConsolidationInsight(
            id="ins-1",
            source_ids=["src-1", "src-2"],
            insight="Entities share common scope",
            created_at="2026-03-29T00:00:00Z",
        )
        assert insight.id == "ins-1"
        assert insight.source_ids == ["src-1", "src-2"]
        assert insight.insight == "Entities share common scope"
        assert insight.created_at == "2026-03-29T00:00:00Z"

    def test_id_field_is_required(self) -> None:
        """Missing id field raises ValidationError."""
        with pytest.raises(ValidationError):
            ConsolidationInsight(
                source_ids=["src-1"],
                insight="some insight",
                created_at="2026-01-01",
            )

    def test_source_ids_field_is_required(self) -> None:
        """Missing source_ids field raises ValidationError."""
        with pytest.raises(ValidationError):
            ConsolidationInsight(
                id="ins-1",
                insight="some insight",
                created_at="2026-01-01",
            )

    def test_insight_field_is_required(self) -> None:
        """Missing insight field raises ValidationError."""
        with pytest.raises(ValidationError):
            ConsolidationInsight(
                id="ins-1",
                source_ids=["src-1"],
                created_at="2026-01-01",
            )

    def test_created_at_field_is_required(self) -> None:
        """Missing created_at field raises ValidationError."""
        with pytest.raises(ValidationError):
            ConsolidationInsight(
                id="ins-1",
                source_ids=["src-1"],
                insight="some insight",
            )

    def test_source_ids_is_list_of_str(self) -> None:
        """source_ids accepts a list of strings."""
        insight = ConsolidationInsight(
            id="ins-1",
            source_ids=["a", "b", "c"],
            insight="multi-source",
            created_at="2026-03-29",
        )
        assert isinstance(insight.source_ids, list)
        assert all(isinstance(s, str) for s in insight.source_ids)

    def test_is_frozen_cannot_mutate_id(self) -> None:
        """ConsolidationInsight is frozen — mutating id raises an error."""
        insight = ConsolidationInsight(
            id="ins-1",
            source_ids=["src-1"],
            insight="immutable",
            created_at="2026-03-29",
        )
        with pytest.raises((TypeError, ValidationError)):
            insight.id = "ins-99"  # type: ignore[misc]

    def test_is_frozen_cannot_mutate_insight(self) -> None:
        """ConsolidationInsight is frozen — mutating insight raises an error."""
        insight = ConsolidationInsight(
            id="ins-1",
            source_ids=["src-1"],
            insight="original",
            created_at="2026-03-29",
        )
        with pytest.raises((TypeError, ValidationError)):
            insight.insight = "modified"  # type: ignore[misc]
