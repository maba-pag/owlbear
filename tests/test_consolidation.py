"""Tests for ConsolidationService — TDD RED phase for tasks #789 and #723.

Contract tests for the consolidation service that periodically synthesizes
cross-document insights from unconsolidated chunks, plus config, bootstrap,
and export tests for the remaining #723 AC lines.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestFromAC_ConsolidateReads:
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


class TestFromAC_ConsolidateStoresInsight:
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


class TestFromAC_ConsolidateMarksChunks:
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


class TestFromAC_ConsolidateReturnsCount:
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


class TestFromAC_ConsolidateBatchSize:
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


class TestFromAC_ConsolidateEmpty:
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


class TestFromAC_SchedulePeriodic:
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


class TestFromAC_LLMFailure:
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
    async def test_llm_failure_warning_includes_exc_info(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """WARNING log for LLM failure must include exc_info for debuggability.

        AC: "LLM failure during consolidation is logged" requires the exception
        details to be captured in the log record (exc_info=True), not just a
        plain message.  Removing the exc_info would make failures invisible.
        """
        conn = _make_db()
        _seed_chunks(conn, 2)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]

        with (
            patch.object(svc, "_run_llm", side_effect=RuntimeError("LLM down")),
            caplog.at_level(logging.WARNING, logger="owlbear.memory.knowledge.consolidation"),
        ):
            await svc.consolidate()

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_records, "At least one WARNING must be emitted on LLM failure"
        # exc_info must be set so the exception traceback is captured in logs
        assert any(r.exc_info for r in warning_records), (
            "WARNING record must include exc_info=True so the exception cause is captured"
        )

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


class TestFromAC_Constructor:
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


# ---------------------------------------------------------------------------
# TestFromAC_ConfigConsolidationEnabled  (#723 AC5)
# ---------------------------------------------------------------------------


class TestFromAC_ConfigConsolidationEnabled:
    """AC: consolidation_enabled: bool = False added to OwlBearSettings."""

    def test_default_is_false(self, default_settings: object) -> None:
        """consolidation_enabled must default to False (feature-flagged off)."""
        from owlbear.config import OwlBearSettings

        settings: OwlBearSettings = default_settings  # type: ignore[assignment]
        assert settings.consolidation_enabled is False

    def test_env_override_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_CONSOLIDATION_ENABLED=true should enable the feature."""
        from owlbear.config import OwlBearSettings

        monkeypatch.setenv("OWLBEAR_CONSOLIDATION_ENABLED", "true")
        settings = OwlBearSettings()
        assert settings.consolidation_enabled is True

    def test_env_override_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_CONSOLIDATION_ENABLED=false should keep it disabled."""
        from owlbear.config import OwlBearSettings

        monkeypatch.setenv("OWLBEAR_CONSOLIDATION_ENABLED", "false")
        settings = OwlBearSettings()
        assert settings.consolidation_enabled is False


# ---------------------------------------------------------------------------
# TestFromAC_ConfigConsolidationInterval  (#723 AC6)
# ---------------------------------------------------------------------------


class TestFromAC_ConfigConsolidationInterval:
    """AC: consolidation_interval: int = 1800 added to OwlBearSettings."""

    def test_default_is_1800(self, default_settings: object) -> None:
        """consolidation_interval must default to 1800 seconds (30 min)."""
        from owlbear.config import OwlBearSettings

        settings: OwlBearSettings = default_settings  # type: ignore[assignment]
        assert settings.consolidation_interval == 1800

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_CONSOLIDATION_INTERVAL=900 should change the interval."""
        from owlbear.config import OwlBearSettings

        monkeypatch.setenv("OWLBEAR_CONSOLIDATION_INTERVAL", "900")
        settings = OwlBearSettings()
        assert settings.consolidation_interval == 900

    def test_is_int_type(self, default_settings: object) -> None:
        """The field must be an integer, not a float or string."""
        from owlbear.config import OwlBearSettings

        settings: OwlBearSettings = default_settings  # type: ignore[assignment]
        assert isinstance(settings.consolidation_interval, int)


# ---------------------------------------------------------------------------
# TestFromAC_BootstrapWiring  (#723 AC7)
# ---------------------------------------------------------------------------


class TestFromAC_BootstrapWiring:
    """AC: Bootstrap constructs ConsolidationService in _build_knowledge_toolset when enabled."""

    def test_accepts_consolidation_enabled_kwarg(self, tmp_path: object) -> None:
        """_build_knowledge_toolset must accept a consolidation_enabled keyword argument."""
        from owlbear.bootstrap.knowledge import (
            _build_knowledge_toolset,
        )

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            from owlbear.bootstrap.knowledge import _build_knowledge_infra

            infra = _build_knowledge_infra(tmp_path)  # type: ignore[arg-type]
            assert infra is not None

            # Must accept consolidation_enabled without TypeError
            result = _build_knowledge_toolset(
                tmp_path,  # type: ignore[arg-type]
                infra,
                consolidation_enabled=True,
                consolidation_interval=1800,
            )

        assert result is not None

    def test_returns_consolidation_service_when_enabled(self, tmp_path: object) -> None:
        """When consolidation_enabled=True, return tuple includes ConsolidationService."""
        from owlbear.bootstrap.knowledge import (
            _build_knowledge_toolset,
        )

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            from owlbear.bootstrap.knowledge import _build_knowledge_infra

            infra = _build_knowledge_infra(tmp_path)  # type: ignore[arg-type]
            assert infra is not None

            result = _build_knowledge_toolset(
                tmp_path,  # type: ignore[arg-type]
                infra,
                consolidation_enabled=True,
                consolidation_interval=1800,
            )

        assert result is not None
        # Return tuple should be extended to 4 elements with ConsolidationService
        assert len(result) >= 4, (  # type: ignore[arg-type]
            "_build_knowledge_toolset should return ConsolidationService as 4th element"
        )
        consolidation_svc = result[3]  # type: ignore[index]
        assert type(consolidation_svc).__name__ == "ConsolidationService"

    def test_no_consolidation_service_when_disabled(self, tmp_path: object) -> None:
        """When consolidation_enabled=False, no ConsolidationService returned."""
        from owlbear.bootstrap.knowledge import (
            _build_knowledge_toolset,
        )

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            from owlbear.bootstrap.knowledge import _build_knowledge_infra

            infra = _build_knowledge_infra(tmp_path)  # type: ignore[arg-type]
            assert infra is not None

            # Must accept consolidation_enabled=False without TypeError
            result = _build_knowledge_toolset(
                tmp_path,  # type: ignore[arg-type]
                infra,
                consolidation_enabled=False,
            )

        assert result is not None
        # When disabled: return tuple should be extended to 4 elements
        # with None as the 4th (ConsolidationService slot).
        assert len(result) >= 4, (  # type: ignore[arg-type]
            "_build_knowledge_toolset should return 4-tuple even when disabled"
        )
        assert result[3] is None  # type: ignore[index]


# ---------------------------------------------------------------------------
# TestFromAC_Export  (#723 AC8)
# ---------------------------------------------------------------------------


class TestFromAC_Export:
    """AC: ConsolidationService exported from owlbear.memory.knowledge.__init__."""

    def test_importable_from_package(self) -> None:
        """ConsolidationService must be importable from owlbear.memory.knowledge.consolidation."""
        from owlbear.memory.knowledge.consolidation import ConsolidationService

        assert ConsolidationService is not None

    def test_in_all(self) -> None:
        """ConsolidationService was removed from __all__ in the public-API trim (#839).

        It remains importable (test_importable_from_package covers that).
        """
        import owlbear.memory.knowledge as pkg

        assert "ConsolidationService" not in pkg.__all__


# ---------------------------------------------------------------------------
# TestFromAC_WireSurfacesConsolidation  (#723 AC7 — wiring gap)
# ---------------------------------------------------------------------------


class TestFromAC_WireSurfacesConsolidation:
    """AC7: _wire_knowledge_toolsets must surface ConsolidationService (not discard it)."""

    def test_returns_3_tuple(self, tmp_path: object) -> None:
        """Return value must include ConsolidationService slot (3-tuple, not 2-tuple)."""
        from owlbear.bootstrap.toolsets import _wire_knowledge_toolsets
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(consolidation_enabled=True, approval_policy=[])
        raw: list[object] = []
        summary: list[object] = []
        cleanup: list[object] = []

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            import owlbear.bootstrap as _pkg

            result = _wire_knowledge_toolsets(
                raw,
                settings,
                tmp_path,  # type: ignore[arg-type]
                None,
                None,
                cleanup,
                summary,
                _pkg,
            )

        assert len(result) == 3, (  # type: ignore[arg-type]
            "_wire_knowledge_toolsets should return 3-tuple "
            "(knowledge_service, ingest_pipeline, consolidation_svc)"
        )

    def test_consolidation_service_when_enabled(self, tmp_path: object) -> None:
        """When consolidation_enabled=True, third element is ConsolidationService."""
        from owlbear.bootstrap.toolsets import _wire_knowledge_toolsets
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(consolidation_enabled=True, approval_policy=[])
        raw: list[object] = []
        summary: list[object] = []
        cleanup: list[object] = []

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            import owlbear.bootstrap as _pkg

            result = _wire_knowledge_toolsets(
                raw,
                settings,
                tmp_path,  # type: ignore[arg-type]
                None,
                None,
                cleanup,
                summary,
                _pkg,
            )

        consolidation_svc = result[2]  # type: ignore[index]
        assert type(consolidation_svc).__name__ == "ConsolidationService"

    def test_none_when_disabled(self, tmp_path: object) -> None:
        """When consolidation_enabled=False, third element is None."""
        from owlbear.bootstrap.toolsets import _wire_knowledge_toolsets
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(consolidation_enabled=False, approval_policy=[])
        raw: list[object] = []
        summary: list[object] = []
        cleanup: list[object] = []

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            import owlbear.bootstrap as _pkg

            result = _wire_knowledge_toolsets(
                raw,
                settings,
                tmp_path,  # type: ignore[arg-type]
                None,
                None,
                cleanup,
                summary,
                _pkg,
            )

        assert len(result) == 3  # type: ignore[arg-type]
        assert result[2] is None  # type: ignore[index]


# ---------------------------------------------------------------------------
# TestFromAC_BuildToolsetsReturnsConsolidation  (#723 AC7 — wiring gap)
# ---------------------------------------------------------------------------


class TestFromAC_BuildToolsetsReturnsConsolidation:
    """AC7: build_toolsets must include ConsolidationService in its return value."""

    def test_returns_4_tuple(self, tmp_path: object) -> None:
        """build_toolsets should return a 4-tuple including ConsolidationService slot."""
        from owlbear.bootstrap import build_toolsets
        from owlbear.channels.base import ChannelPlugin
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookRegistry

        settings = OwlBearSettings(consolidation_enabled=True, approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            result = build_toolsets(settings, tmp_path, hooks, channel)  # type: ignore[arg-type]

        assert len(result) == 4, (
            "build_toolsets should return 4-tuple "
            "(toolsets, knowledge_service, ingest_pipeline, consolidation_svc)"
        )

    def test_consolidation_service_when_enabled(self, tmp_path: object) -> None:
        """When consolidation_enabled=True, 4th element is ConsolidationService."""
        from owlbear.bootstrap import build_toolsets
        from owlbear.channels.base import ChannelPlugin
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookRegistry

        settings = OwlBearSettings(consolidation_enabled=True, approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            result = build_toolsets(settings, tmp_path, hooks, channel)  # type: ignore[arg-type]

        consolidation_svc = result[3]  # type: ignore[index]
        assert type(consolidation_svc).__name__ == "ConsolidationService"

    def test_none_when_disabled(self, tmp_path: object) -> None:
        """When consolidation_enabled=False, 4th element is None."""
        from owlbear.bootstrap import build_toolsets
        from owlbear.channels.base import ChannelPlugin
        from owlbear.config import OwlBearSettings
        from owlbear.core.hooks import HookRegistry

        settings = OwlBearSettings(consolidation_enabled=False, approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            result = build_toolsets(settings, tmp_path, hooks, channel)  # type: ignore[arg-type]

        assert len(result) == 4  # type: ignore[arg-type]
        assert result[3] is None  # type: ignore[index]


# ---------------------------------------------------------------------------
# TestFromAC_DaemonStartsConsolidationTimer  (#723 AC7 — daemon gap)
# ---------------------------------------------------------------------------


class TestFromAC_DaemonStartsConsolidationTimer:
    """AC7: Daemon starts schedule_periodic when ConsolidationService is provided."""

    @pytest.mark.asyncio
    async def test_run_daemon_accepts_consolidation_svc(self, tmp_path: object) -> None:
        """run_daemon must accept a consolidation_svc keyword argument."""
        from owlbear.daemon import run_daemon

        mock_channel = AsyncMock()
        mock_channel.receive = AsyncMock(return_value=None)  # EOF immediately
        mock_channel.name = "test"
        mock_agent = AsyncMock()
        mock_agent.hooks = MagicMock()
        mock_agent.hooks.emit = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = tmp_path / "session.jsonl"  # type: ignore[union-attr]
        mock_agent.session.load = MagicMock(return_value=[])

        mock_svc = MagicMock()
        mock_svc.schedule_periodic = AsyncMock()

        # Must accept consolidation_svc without TypeError
        await run_daemon(
            channel=mock_channel,
            agent=mock_agent,
            config_dir=tmp_path,  # type: ignore[arg-type]
            consolidation_svc=mock_svc,
        )

    @pytest.mark.asyncio
    async def test_schedule_periodic_called(self, tmp_path: object) -> None:
        """When consolidation_svc is provided, schedule_periodic must be started."""
        from owlbear.daemon import run_daemon

        mock_channel = AsyncMock()
        mock_channel.receive = AsyncMock(return_value=None)  # EOF immediately
        mock_channel.name = "test"
        mock_agent = AsyncMock()
        mock_agent.hooks = MagicMock()
        mock_agent.hooks.emit = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = tmp_path / "session.jsonl"  # type: ignore[union-attr]
        mock_agent.session.load = MagicMock(return_value=[])

        mock_svc = MagicMock()
        # Make schedule_periodic a never-ending async that we can detect
        mock_svc.schedule_periodic = AsyncMock(side_effect=asyncio.CancelledError)

        settings = MagicMock()
        settings.consolidation_interval = 900
        settings.autonomous_mode = False
        settings.heartbeat_enabled = False

        await run_daemon(
            channel=mock_channel,
            agent=mock_agent,
            config_dir=tmp_path,  # type: ignore[arg-type]
            consolidation_svc=mock_svc,
            settings=settings,
        )

        mock_svc.schedule_periodic.assert_called()

    @pytest.mark.asyncio
    async def test_schedule_periodic_receives_interval(self, tmp_path: object) -> None:
        """schedule_periodic must be called with interval=consolidation_interval from settings."""
        from owlbear.daemon import run_daemon

        mock_channel = AsyncMock()
        mock_channel.receive = AsyncMock(return_value=None)
        mock_channel.name = "test"
        mock_agent = AsyncMock()
        mock_agent.hooks = MagicMock()
        mock_agent.hooks.emit = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = tmp_path / "session.jsonl"  # type: ignore[union-attr]
        mock_agent.session.load = MagicMock(return_value=[])

        mock_svc = MagicMock()
        mock_svc.schedule_periodic = AsyncMock(side_effect=asyncio.CancelledError)

        settings = MagicMock()
        settings.consolidation_interval = 900
        settings.autonomous_mode = False
        settings.heartbeat_enabled = False

        await run_daemon(
            channel=mock_channel,
            agent=mock_agent,
            config_dir=tmp_path,  # type: ignore[arg-type]
            consolidation_svc=mock_svc,
            settings=settings,
        )

        # Verify the interval was passed correctly
        call_kwargs = mock_svc.schedule_periodic.call_args
        assert call_kwargs is not None
        # Check interval=900 was passed
        if call_kwargs.kwargs:
            assert call_kwargs.kwargs.get("interval") == 900
        else:
            assert call_kwargs.args[0] == 900


# ---------------------------------------------------------------------------
# TestFromAC_PydanticAILLMMocking — AC: LLM mocked via PydanticAI test utilities
# ---------------------------------------------------------------------------


class TestFromAC_PydanticAILLMMocking:
    """Verify ConsolidationService LLM calls use PydanticAI so tests can inject
    TestModel / FunctionModel rather than patching ``_run_llm`` directly.

    AC: LLM mocked via PydanticAI test utilities.

    All three tests are RED — the current ``_run_llm`` placeholder stub must be
    replaced with a real PydanticAI Agent before any of them can pass.
    """

    @pytest.mark.asyncio
    async def test_consolidate_insight_text_driven_by_pydantic_ai_test_model(self) -> None:
        """When TestModel is injected, stored insight reflects model output.

        ConsolidationService must use a PydanticAI Agent internally so that
        injecting ``TestModel(custom_output_text=...)`` controls the stored
        insight text.  The current hardcoded stub ignores ``self._model``.
        """
        from pydantic_ai.models.test import TestModel

        conn = _make_db()
        _seed_chunks(conn, 3)
        sentinel = "PYDANTIC_AI_SENTINEL_789test"
        svc = ConsolidationService(
            conn=conn,
            graph_store=None,
            model=TestModel(custom_output_text=sentinel),  # type: ignore[arg-type]
        )
        count = await svc.consolidate()

        assert count == 1
        row = conn.execute("SELECT insight FROM consolidations").fetchone()
        assert row is not None
        assert sentinel in row[0], (
            f"Insight must be driven by PydanticAI TestModel output; got: {row[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_consolidate_function_model_callback_invoked_for_llm(self) -> None:
        """FunctionModel callback must be called when the LLM step executes.

        A PydanticAI Agent backed by FunctionModel will invoke the callback each
        time the agent runs.  The current stub never calls ``self._model``, so
        this test remains RED until the stub is replaced.
        """
        from pydantic_ai.models.function import FunctionModel

        conn = _make_db()
        _seed_chunks(conn, 2)
        calls: list[object] = []

        def capture_model(messages: object, _info: object) -> str:
            calls.append(messages)
            return "captured pydantic insight"

        svc = ConsolidationService(
            conn=conn,
            graph_store=None,
            model=FunctionModel(capture_model),  # type: ignore[arg-type]
        )
        await svc.consolidate()

        assert calls, (
            "FunctionModel callback was never invoked — "
            "_run_llm must use a PydanticAI Agent to enable test-model injection"
        )

    @pytest.mark.asyncio
    async def test_consolidate_does_not_use_placeholder_stub_text(self) -> None:
        """consolidate() must not store the hardcoded placeholder string.

        The current ``_run_llm`` stub returns a fixed
        ``'Consolidated insight from N chunks.'`` string.  When driven by a real
        PydanticAI Agent (or TestModel), the stored insight must come from the
        model, not the stub.
        """
        from pydantic_ai.models.test import TestModel

        conn = _make_db()
        _seed_chunks(conn, 2)
        custom_output = "UNIQUE_PYDANTIC_OUTPUT_xz99"
        svc = ConsolidationService(
            conn=conn,
            graph_store=None,
            model=TestModel(custom_output_text=custom_output),  # type: ignore[arg-type]
        )
        await svc.consolidate()

        row = conn.execute("SELECT insight FROM consolidations").fetchone()
        assert row is not None
        # The hardcoded placeholder text must not appear once the service is
        # properly wired to a PydanticAI Agent.
        assert "Consolidated insight from" not in row[0], (
            "ConsolidationService must use PydanticAI Agent, not the placeholder stub"
        )


# ---------------------------------------------------------------------------
# TestBuilderDiscovered — exception paths and optional branches in bootstrap
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-added tests covering exception paths in _build_knowledge_infra.

    Covers _build_knowledge_infra and _build_knowledge_toolset exception paths
    that are exercised by the wiring changes introduced in task #789.
    """

    def test_build_knowledge_infra_returns_none_on_failure(self, tmp_path: object) -> None:
        """_build_knowledge_infra returns None instead of raising when setup fails."""
        import sqlite3 as _sqlite3

        from owlbear.bootstrap.knowledge import _build_knowledge_infra

        with patch.object(_sqlite3, "connect", side_effect=RuntimeError("DB error")):
            result = _build_knowledge_infra(tmp_path)  # type: ignore[arg-type]

        assert result is None

    def test_build_knowledge_toolset_returns_none_on_failure(self, tmp_path: object) -> None:
        """_build_knowledge_toolset returns None instead of raising when setup fails."""
        from owlbear.bootstrap.knowledge import (
            _build_knowledge_infra,
            _build_knowledge_toolset,
        )

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path)  # type: ignore[arg-type]
            assert infra is not None

            with patch(
                "owlbear.memory.knowledge.document_store.DocumentStore.__init__",
                side_effect=RuntimeError("Store init failed"),
            ):
                result = _build_knowledge_toolset(
                    tmp_path,  # type: ignore[arg-type]
                    infra,
                )

        assert result is None

    def test_build_knowledge_toolset_inter_doc_graph_building(self, tmp_path: object) -> None:
        """_build_knowledge_toolset with inter_doc_graph_building=True covers enricher path."""
        from owlbear.bootstrap.knowledge import (
            _build_knowledge_infra,
            _build_knowledge_toolset,
        )

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.inter_doc_graph_builder.InterDocGraphBuilder.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.enrichment.GraphEnricher.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path)  # type: ignore[arg-type]
            assert infra is not None
            result = _build_knowledge_toolset(
                tmp_path,  # type: ignore[arg-type]
                infra,
                inter_doc_graph_building=True,
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_failure_emits_warning_log(self, caplog: pytest.LogCaptureFixture) -> None:
        """consolidate() must emit a WARNING log when _run_llm raises.

        Strengthens TestFromAC_LLMFailure::test_llm_error_logged_not_raised, which
        verifies the return value but does not assert the log record.  Removing the
        logger.warning() call in consolidation.py must break this test.
        """
        conn = _make_db()
        _seed_chunks(conn, 2)

        svc = ConsolidationService(conn=conn, graph_store=None, model="test")  # type: ignore[arg-type]

        with (
            patch.object(svc, "_run_llm", side_effect=RuntimeError("LLM down")),
            caplog.at_level(logging.WARNING),
        ):
            await svc.consolidate()

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_records, "consolidate() must emit at least one WARNING when LLM call fails"
        msgs = [r.getMessage().lower() for r in warning_records]
        assert any("llm" in m or "consolidation" in m for m in msgs), (
            f"WARNING message should mention LLM or consolidation, got: {msgs}"
        )
