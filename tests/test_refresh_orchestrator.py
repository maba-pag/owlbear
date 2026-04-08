"""RED-phase tests for RefreshOrchestrator and RefreshResult (#554).

Tests the contract for:
- RefreshResult model in refresh.py (new module)
- CrawlHandler type alias in refresh.py
- RefreshOrchestrator class: constructor, refresh(), refresh_all()
- Handler dispatch: url_list, crawl, file_glob
- _update_source_record: persists outcome via store.update
- CancelSignal integration (between items & between sources)
- IngestResult status counting (ok → refreshed, skipped → skipped, failed → failed)

All imports from owlbear_knowledge.refresh are inline (noqa: PLC0415) so
collection succeeds; tests fail at execution time with ImportError.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.ingest import IngestResult
from owlbear_knowledge.intake import IntakeResult
from owlbear_knowledge.models import KnowledgeSource, SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_source(  # noqa: PLR0913
    *,
    name: str = "src",
    source_type: SourceType = SourceType.URL_LIST,
    enabled: bool = True,
    priority: int = 0,
    config: dict[str, Any] | None = None,
    scope: str = "global",
) -> KnowledgeSource:
    return KnowledgeSource(
        name=name,
        source_type=source_type,
        enabled=enabled,
        priority=priority,
        config=config or {},
        scope=scope,
        created_at=_now(),
        updated_at=_now(),
    )


def _ok_ingest_result(doc_id: str = "doc-1") -> IngestResult:
    return IngestResult(
        document_id=doc_id,
        chunk_count=1,
        entity_count=0,
        edge_count=0,
        status="ok",
    )


def _skipped_ingest_result() -> IngestResult:
    return IngestResult(
        document_id="doc-skip",
        chunk_count=0,
        entity_count=0,
        edge_count=0,
        status="skipped",
    )


def _failed_ingest_result() -> IngestResult:
    return IngestResult(
        document_id="doc-fail",
        chunk_count=0,
        entity_count=0,
        edge_count=0,
        status="failed",
    )


def _make_intake_result(source: str = "https://example.com") -> IntakeResult:
    return IntakeResult(
        content="hello",
        source=source,
        metadata={"source_type": "url", "fetched_at": _now()},
    )


class _SetSignal:
    """CancelSignal that is always set (immediately cancels any loop)."""

    def is_set(self) -> bool:
        return True


class _ClearSignal:
    """CancelSignal that is never set."""

    def is_set(self) -> bool:
        return False


# ===========================================================================
# AC: RefreshResult model — frozen, all fields, correct types and defaults
# ===========================================================================


class TestFromAC_RefreshResultModel:  # noqa: N801
    """RefreshResult is a frozen Pydantic BaseModel with source_id, counters, errors."""

    def test_importable(self) -> None:
        from owlbear_knowledge.refresh import RefreshResult  # noqa: PLC0415

        assert RefreshResult is not None

    def test_all_fields_with_correct_types(self) -> None:
        from owlbear_knowledge.refresh import RefreshResult  # noqa: PLC0415

        r = RefreshResult(source_id="s1", refreshed=3, skipped=1, failed=2, errors=["err"])
        assert r.source_id == "s1"
        assert r.refreshed == 3
        assert r.skipped == 1
        assert r.failed == 2
        assert r.errors == ["err"]

    def test_errors_defaults_to_empty_list(self) -> None:
        from owlbear_knowledge.refresh import RefreshResult  # noqa: PLC0415

        r = RefreshResult(source_id="s1", refreshed=0, skipped=0, failed=0)
        assert r.errors == []

    def test_frozen_raises_on_mutation(self) -> None:
        from owlbear_knowledge.refresh import RefreshResult  # noqa: PLC0415
        from pydantic import ValidationError  # noqa: PLC0415

        r = RefreshResult(source_id="s1", refreshed=0, skipped=0, failed=0)
        with pytest.raises((ValidationError, TypeError)):
            r.refreshed = 99  # type: ignore[misc]


# ===========================================================================
# AC: RefreshOrchestrator constructor
# ===========================================================================


class TestFromAC_RefreshOrchestratorConstructor:  # noqa: N801
    """Constructor accepts store, pipeline, optional workspace_root."""

    def test_required_params_only(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        orch = RefreshOrchestrator(store=MagicMock(), pipeline=MagicMock())
        assert orch is not None

    def test_workspace_root_none_is_valid(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        # workspace_root=None is valid; the implementation defaults to Path.cwd()
        orch = RefreshOrchestrator(
            store=MagicMock(), pipeline=MagicMock(), workspace_root=None
        )
        assert orch is not None


# ===========================================================================
# AC: refresh() raises ValueError for disabled source
# ===========================================================================


class TestFromAC_RefreshDisabledSource:  # noqa: N801
    """refresh() raises ValueError when source.enabled is False."""

    @pytest.mark.asyncio
    async def test_disabled_source_raises_value_error(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        orch = RefreshOrchestrator(store=MagicMock(), pipeline=MagicMock())
        source = _make_source(enabled=False)
        with pytest.raises(ValueError, match="disabled"):
            await orch.refresh(source)


# ===========================================================================
# AC: refresh() dispatches by SourceType
# ===========================================================================


class TestFromAC_RefreshDispatch:  # noqa: N801
    """refresh() returns RefreshResult for each SourceType dispatch path."""

    @pytest.mark.asyncio
    async def test_url_list_dispatch_returns_refresh_result(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://example.com"]},
            )
            result = await orch.refresh(source)

        assert isinstance(result, RefreshResult)
        assert result.source_id == source.id

    @pytest.mark.asyncio
    async def test_file_glob_dispatch_returns_refresh_result(self, tmp_path: Path) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult  # noqa: PLC0415

        (tmp_path / "file.txt").write_text("hello")
        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(return_value=_make_intake_result("file.txt")),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
            )
            result = await orch.refresh(source)

        assert isinstance(result, RefreshResult)


# ===========================================================================
# AC: refresh_all() — list_all + filter enabled, priority desc, cancel
# ===========================================================================


class TestFromAC_RefreshAll:  # noqa: N801
    """refresh_all() calls list_all(), filters enabled, sorts by priority desc, respects cancel."""

    @pytest.mark.asyncio
    async def test_calls_list_all_not_list_enabled(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        store_mock = MagicMock()
        store_mock.list_all.return_value = []
        orch = RefreshOrchestrator(store=store_mock, pipeline=MagicMock())
        await orch.refresh_all(scope="proj")

        store_mock.list_all.assert_called_once()
        # Verify scope was forwarded (positional or keyword)
        call_args = store_mock.list_all.call_args
        passed = list(call_args.args) + list(call_args.kwargs.values())
        assert "proj" in passed
        # Must NOT call the stale list_enabled method
        store_mock.list_enabled.assert_not_called()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_filters_enabled_sources_only(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        enabled_src = _make_source(name="enabled", enabled=True)
        disabled_src = _make_source(name="disabled", enabled=False)

        store_mock = MagicMock()
        store_mock.list_all.return_value = [enabled_src, disabled_src]
        store_mock.update = MagicMock()

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            results = await orch.refresh_all()

        result_ids = {r.source_id for r in results}
        assert enabled_src.id in result_ids
        assert disabled_src.id not in result_ids

    @pytest.mark.asyncio
    async def test_iterates_by_priority_descending(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        src_p1 = _make_source(name="low", priority=1)
        src_p3 = _make_source(name="high", priority=3)
        src_p2 = _make_source(name="mid", priority=2)

        store_mock = MagicMock()
        store_mock.list_all.return_value = [src_p1, src_p3, src_p2]
        store_mock.update = MagicMock()

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            results = await orch.refresh_all()

        result_ids = [r.source_id for r in results]
        assert result_ids == [src_p3.id, src_p2.id, src_p1.id]

    @pytest.mark.asyncio
    async def test_stops_on_cancel_before_all_sources(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        sources = [
            _make_source(
                name=f"src-{i}",
                source_type=SourceType.URL_LIST,
                config={"urls": []},
            )
            for i in range(3)
        ]
        store_mock = MagicMock()
        store_mock.list_all.return_value = sources
        store_mock.update = MagicMock()

        orch = RefreshOrchestrator(store=store_mock, pipeline=MagicMock())
        results = await orch.refresh_all(cancel=_SetSignal())

        assert len(results) < 3

    @pytest.mark.asyncio
    async def test_empty_source_list_returns_empty_list(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        store_mock = MagicMock()
        store_mock.list_all.return_value = []
        orch = RefreshOrchestrator(store=store_mock, pipeline=MagicMock())
        results = await orch.refresh_all()
        assert results == []


# ===========================================================================
# AC: url_list handler
# ===========================================================================


class TestFromAC_UrlListHandler:  # noqa: N801
    """url_list reads config[urls], calls intake.read_url per URL, passes to pipeline.ingest."""

    @pytest.mark.asyncio
    async def test_calls_read_url_for_each_configured_url(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ) as mock_read:
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com", "https://b.com"]},
            )
            await orch.refresh(source)

        assert mock_read.call_count == 2

    @pytest.mark.asyncio
    async def test_calls_pipeline_ingest_per_url(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com", "https://b.com", "https://c.com"]},
            )
            result = await orch.refresh(source)

        assert pipeline_mock.ingest.call_count == 3
        assert result.refreshed == 3

    @pytest.mark.asyncio
    async def test_per_url_exception_counted_as_failed_not_raised(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(side_effect=RuntimeError("network error"))
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com"]},
            )
            result = await orch.refresh(source)  # must not raise

        assert result.failed == 1
        assert result.refreshed == 0


# ===========================================================================
# AC: file_glob handler — resolves pattern, validates with sandbox_path
# ===========================================================================


class TestFromAC_FileGlobHandler:  # noqa: N801
    """file_glob resolves pattern, validates paths, ingests matching files."""

    @pytest.mark.asyncio
    async def test_ingests_matching_files(self, tmp_path: Path) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult  # noqa: PLC0415

        (tmp_path / "doc1.md").write_text("content 1")
        (tmp_path / "doc2.md").write_text("content 2")
        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.md"},
            )
            result = await orch.refresh(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 2

    @pytest.mark.asyncio
    async def test_sandbox_permission_error_counted_as_failed_not_raised(
        self, tmp_path: Path
    ) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        (tmp_path / "test.txt").write_text("content")
        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock()
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(side_effect=PermissionError("escape attempt")),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
            )
            result = await orch.refresh(source)  # must not raise PermissionError

        assert result.failed == 1
        assert result.refreshed == 0

    @pytest.mark.asyncio
    async def test_uses_base_dir_from_config(self, tmp_path: Path) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        subdir = tmp_path / "docs"
        subdir.mkdir()
        (subdir / "readme.txt").write_text("hello")
        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt", "base_dir": str(subdir)},
            )
            result = await orch.refresh(source)

        assert result.refreshed == 1


# ===========================================================================
# AC: _update_source_record — store.update with last_refreshed_at and last_error
# ===========================================================================


class TestFromAC_UpdateSourceRecord:  # noqa: N801
    """_update_source_record persists refresh outcome via store.update."""

    @pytest.mark.asyncio
    async def test_calls_store_update_after_refresh(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com"]},
            )
            await orch.refresh(source)

        store_mock.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_last_refreshed_at_on_update(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com"]},
            )
            await orch.refresh(source)

        updated_source: KnowledgeSource = store_mock.update.call_args[0][0]
        assert updated_source.last_refreshed_at is not None

    @pytest.mark.asyncio
    async def test_clears_last_error_on_successful_refresh(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com"]},
            )
            await orch.refresh(source)

        updated_source: KnowledgeSource = store_mock.update.call_args[0][0]
        # success run — last_error should be None
        assert updated_source.last_error is None


# ===========================================================================
# AC: CancelSignal checked between items and between sources
# ===========================================================================


class TestFromAC_CancelSignal:  # noqa: N801
    """CancelSignal is checked between items in loop and between sources in refresh_all."""

    @pytest.mark.asyncio
    async def test_cancel_between_items_stops_url_list_loop(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com", "https://b.com", "https://c.com"]},
            )
            result = await orch.refresh(source, cancel=_SetSignal())

        # Cancel always set — loop stops before processing all 3 URLs
        total_processed = result.refreshed + result.skipped + result.failed
        assert total_processed < 3

    @pytest.mark.asyncio
    async def test_cancel_between_sources_stops_refresh_all(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        sources = [
            _make_source(
                name=f"src-{i}",
                source_type=SourceType.URL_LIST,
                config={"urls": []},
            )
            for i in range(3)
        ]
        store_mock = MagicMock()
        store_mock.list_all.return_value = sources
        store_mock.update = MagicMock()

        orch = RefreshOrchestrator(store=store_mock, pipeline=MagicMock())
        results = await orch.refresh_all(cancel=_SetSignal())

        # Cancel always set — should not process all 3 sources
        assert len(results) < 3


# ===========================================================================
# AC: IngestResult.status drives refreshed/skipped/failed counters
# ===========================================================================


class TestFromAC_IngestResultCounting:  # noqa: N801
    """ok → refreshed, skipped → skipped (not refreshed), failed → failed."""

    @pytest.mark.asyncio
    async def test_ok_status_counted_as_refreshed(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com"]},
            )
            result = await orch.refresh(source)

        assert result.refreshed == 1
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_skipped_status_counted_as_skipped_not_refreshed(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_skipped_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com"]},
            )
            result = await orch.refresh(source)

        assert result.skipped == 1
        assert result.refreshed == 0

    @pytest.mark.asyncio
    async def test_failed_status_counted_as_failed(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_failed_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_url",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
            source = _make_source(
                source_type=SourceType.URL_LIST,
                config={"urls": ["https://a.com"]},
            )
            result = await orch.refresh(source)

        assert result.failed == 1
        assert result.refreshed == 0


# ===========================================================================
# RETRY ADDITIONS — tests for reviewer-cited coverage gaps
# (lines 105-106, 136-137, 189-192, 213-214, 228, 236-239)
# ===========================================================================


class TestFromAC_UnsupportedSourceType:  # noqa: N801
    """refresh() raises ValueError for a SourceType not handled by any dispatch branch."""

    @pytest.mark.asyncio
    async def test_unsupported_source_type_raises_value_error(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        store_mock = MagicMock()
        # Create a source-like object with an unrecognised source_type
        source = MagicMock(spec=KnowledgeSource)
        source.enabled = True
        source.source_type = "totally_unsupported"  # does not match any SourceType enum value

        orch = RefreshOrchestrator(store=store_mock, pipeline=MagicMock())
        with pytest.raises(ValueError, match="Unsupported source type"):
            await orch.refresh(source)


class TestFromAC_RefreshAllExceptionHandling:  # noqa: N801
    """refresh_all() catches exceptions from individual source refreshes and continues."""

    @pytest.mark.asyncio
    async def test_continues_processing_after_source_refresh_raises(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        # Source that will raise ValueError (unsupported type — gets past enabled filter)
        bad_source = MagicMock(spec=KnowledgeSource)
        bad_source.enabled = True
        bad_source.priority = 1
        bad_source.source_type = "unsupported_type"
        bad_source.id = "bad-src-id"

        # Good source with empty URL list — will succeed
        good_source = _make_source(
            name="good",
            source_type=SourceType.URL_LIST,
            config={"urls": []},
            priority=0,
        )

        store_mock = MagicMock()
        store_mock.list_all.return_value = [bad_source, good_source]
        store_mock.update = MagicMock()

        orch = RefreshOrchestrator(store=store_mock, pipeline=MagicMock())
        results = await orch.refresh_all()

        # bad_source exception is swallowed; only good_source appears in results
        assert len(results) == 1
        assert results[0].source_id == good_source.id


class TestFromAC_SandboxPathPermissionError:  # noqa: N801
    """_handle_file_glob returns failed=1 when sandbox_path() itself raises PermissionError."""

    @pytest.mark.asyncio
    async def test_sandbox_path_permission_error_counted_as_failed_not_raised(
        self, tmp_path: Path
    ) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        # Patch sandbox_path *in the refresh module* — this triggers lines 189-192
        with patch(
            "owlbear_knowledge.refresh.sandbox_path",
            side_effect=PermissionError("path escape attempt"),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
            )
            result = await orch.refresh(source)  # must not raise PermissionError

        assert result.failed == 1
        assert result.refreshed == 0
        assert len(result.errors) == 1
        assert "path escape attempt" in result.errors[0]


class TestFromAC_FileGlobPerFileHandling:  # noqa: N801
    """_handle_file_glob per-file cancel, skipped counting, and exception counting."""

    @pytest.mark.asyncio
    async def test_cancel_stops_per_file_loop_in_file_glob(self, tmp_path: Path) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        for i in range(3):
            (tmp_path / f"file{i}.txt").write_text(f"content {i}")

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_ok_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
            )
            result = await orch.refresh(source, cancel=_SetSignal())

        # Cancel always set — loop stops before processing all 3 files
        total_processed = result.refreshed + result.skipped + result.failed
        assert total_processed < 3

    @pytest.mark.asyncio
    async def test_file_glob_skipped_status_counted_as_skipped(self, tmp_path: Path) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        (tmp_path / "file.txt").write_text("content")
        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_skipped_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
            )
            result = await orch.refresh(source)

        assert result.skipped == 1
        assert result.refreshed == 0

    @pytest.mark.asyncio
    async def test_file_glob_per_file_exception_counted_as_failed_not_raised(
        self, tmp_path: Path
    ) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        (tmp_path / "file.txt").write_text("content")
        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(side_effect=RuntimeError("ingest failure"))
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
            )
            result = await orch.refresh(source)  # must not raise

        assert result.failed == 1
        assert result.refreshed == 0

    @pytest.mark.asyncio
    async def test_file_glob_failed_ingest_status_counted_as_failed(self, tmp_path: Path) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        (tmp_path / "file.txt").write_text("content")
        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(return_value=_failed_ingest_result())
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        with patch(
            "owlbear_knowledge.intake.read_file",
            new=AsyncMock(return_value=_make_intake_result()),
        ):
            orch = RefreshOrchestrator(
                store=store_mock, pipeline=pipeline_mock, workspace_root=tmp_path
            )
            source = _make_source(
                source_type=SourceType.FILE_GLOB,
                config={"pattern": "*.txt"},
            )
            result = await orch.refresh(source)

        assert result.failed == 1
        assert result.refreshed == 0
