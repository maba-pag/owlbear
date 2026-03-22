"""Tests for RefreshOrchestrator — dispatch by source type.

TDD red-phase for task #430 / implementation #384.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.memory.knowledge.ingest import IngestResult
from owlbear.memory.knowledge.models import KnowledgeSource, SourceType
from owlbear.memory.knowledge.refresh import RefreshOrchestrator, RefreshResult

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_NOW = "2026-03-02T12:00:00+00:00"


def _make_source(
    *,
    source_type: SourceType = SourceType.URL_LIST,
    config: dict | None = None,
    enabled: bool = True,
    priority: int = 0,
    source_id: str = "src-1",
) -> KnowledgeSource:
    """Build a test KnowledgeSource."""
    return KnowledgeSource(
        id=source_id,
        name="test-source",
        source_type=source_type,
        config=config or {},
        scope="global",
        enabled=enabled,
        priority=priority,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _ok_result(doc_id: str = "doc-1", *, skipped: bool = False) -> IngestResult:
    return IngestResult(
        document_id=doc_id,
        chunk_count=2,
        entity_count=1,
        edge_count=1,
        status="skipped" if skipped else "indexed",
        skipped=skipped,
    )


def _failed_result(doc_id: str = "doc-f") -> IngestResult:
    return IngestResult(
        document_id=doc_id,
        chunk_count=0,
        entity_count=0,
        edge_count=0,
        status="failed",
    )


def _make_orchestrator(
    *,
    store: MagicMock | None = None,
    pipeline: MagicMock | None = None,
    crawl_handler: AsyncMock | None = None,
    workspace_root: Path | None = None,
) -> RefreshOrchestrator:
    """Build a RefreshOrchestrator with mocked dependencies."""
    return RefreshOrchestrator(
        store=store or MagicMock(),
        pipeline=pipeline or MagicMock(),
        crawl_handler=crawl_handler,
        workspace_root=workspace_root or Path("/workspace"),
    )


# ===========================================================================
# RefreshResult model
# ===========================================================================


class TestRefreshResult:
    """RefreshResult is a frozen BaseModel with expected fields."""

    def test_fields(self) -> None:
        r = RefreshResult(source_id="s1", refreshed=3, skipped=1, failed=0, errors=[])
        assert r.source_id == "s1"
        assert r.refreshed == 3
        assert r.skipped == 1
        assert r.failed == 0
        assert r.errors == []

    def test_frozen(self) -> None:
        r = RefreshResult(source_id="s1", refreshed=0, skipped=0, failed=0, errors=[])
        with pytest.raises(ValidationError, match="frozen"):
            r.source_id = "other"  # type: ignore[misc]


# ===========================================================================
# Constructor
# ===========================================================================


class TestConstructor:
    """RefreshOrchestrator accepts store, pipeline, crawl_handler, workspace_root."""

    def test_accepts_deps(self) -> None:
        orch = _make_orchestrator()
        assert orch is not None

    def test_crawl_handler_optional(self) -> None:
        orch = _make_orchestrator(crawl_handler=None)
        assert orch is not None


# ===========================================================================
# url_list handler
# ===========================================================================


class TestUrlListHandler:
    """refresh() dispatches url_list: calls pipeline.ingest(url) per URL."""

    @pytest.mark.asyncio
    async def test_calls_ingest_per_url(self) -> None:
        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            config={"urls": ["https://a.com", "https://b.com"]},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store)
        result = await orch.refresh(source)

        assert pipeline.ingest.await_count == 2
        pipeline.ingest.assert_any_await("https://a.com")
        pipeline.ingest.assert_any_await("https://b.com")
        assert result.refreshed == 2

    @pytest.mark.asyncio
    async def test_counts_skipped(self) -> None:
        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(side_effect=[_ok_result(), _ok_result(skipped=True)])
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            config={"urls": ["https://a.com", "https://b.com"]},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store)
        result = await orch.refresh(source)

        assert result.refreshed == 1
        assert result.skipped == 1
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_individual_failure_collected(self) -> None:
        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(side_effect=[RuntimeError("boom"), _ok_result("doc-2")])
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            config={"urls": ["https://fail.com", "https://ok.com"]},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store)
        result = await orch.refresh(source)

        assert result.refreshed == 1
        assert result.failed == 1
        assert len(result.errors) == 1
        assert "boom" in result.errors[0]

    @pytest.mark.asyncio
    async def test_returns_refresh_result_with_source_id(self) -> None:
        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(source_id="my-src", config={"urls": ["https://a.com"]})
        orch = _make_orchestrator(pipeline=pipeline, store=store)
        result = await orch.refresh(source)

        assert isinstance(result, RefreshResult)
        assert result.source_id == "my-src"


# ===========================================================================
# crawl handler
# ===========================================================================


class TestCrawlHandler:
    """refresh() dispatches crawl: passes config dict to crawl_handler callback."""

    @pytest.mark.asyncio
    async def test_passes_config_dict_to_handler(self) -> None:
        store = MagicMock()
        store.update = MagicMock()

        ingest_results = [_ok_result("d1"), _ok_result("d2")]
        crawl_handler = AsyncMock(return_value=ingest_results)

        source = _make_source(
            source_type=SourceType.CRAWL,
            config={
                "seed_urls": ["https://example.com"],
                "max_depth": 2,
                "max_pages": 10,
            },
        )

        orch = _make_orchestrator(crawl_handler=crawl_handler, store=store)
        result = await orch.refresh(source)

        crawl_handler.assert_awaited_once_with(source.config)
        assert result.refreshed == 2

    @pytest.mark.asyncio
    async def test_raises_if_crawl_handler_is_none(self) -> None:
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.CRAWL,
            config={"seed_urls": ["https://example.com"]},
        )
        orch = _make_orchestrator(crawl_handler=None, store=store)

        with pytest.raises(ValueError, match="crawl"):
            await orch.refresh(source)

    @pytest.mark.asyncio
    async def test_counts_skipped_crawl_results(self) -> None:
        store = MagicMock()
        store.update = MagicMock()

        ingest_results = [_ok_result("d1"), _ok_result("d2", skipped=True)]
        crawl_handler = AsyncMock(return_value=ingest_results)

        source = _make_source(
            source_type=SourceType.CRAWL,
            config={"seed_urls": ["https://example.com"]},
        )

        orch = _make_orchestrator(crawl_handler=crawl_handler, store=store)
        result = await orch.refresh(source)

        assert result.refreshed == 1
        assert result.skipped == 1


# ===========================================================================
# file_glob handler
# ===========================================================================


class TestFileGlobHandler:
    """refresh() dispatches file_glob: resolves pattern, calls pipeline.ingest per file."""

    @pytest.mark.asyncio
    async def test_resolves_pattern_relative_to_workspace(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "a.md").write_text("a")
        (tmp_path / "docs" / "b.md").write_text("b")

        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "docs/*.md"},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store, workspace_root=tmp_path)
        result = await orch.refresh(source)

        assert pipeline.ingest.await_count == 2
        assert result.refreshed == 2

    @pytest.mark.asyncio
    async def test_resolves_pattern_relative_to_base_dir(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "x.txt").write_text("x")

        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.txt", "base_dir": str(sub)},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store, workspace_root=tmp_path)
        result = await orch.refresh(source)

        assert pipeline.ingest.await_count == 1
        assert result.refreshed == 1

    @pytest.mark.asyncio
    async def test_nonmatching_pattern_returns_empty(self, tmp_path: Path) -> None:
        pipeline = MagicMock()
        pipeline.ingest = AsyncMock()
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.nonexistent"},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store, workspace_root=tmp_path)
        result = await orch.refresh(source)

        pipeline.ingest.assert_not_awaited()
        assert result.refreshed == 0
        assert result.failed == 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_individual_file_failure_collected(self, tmp_path: Path) -> None:
        (tmp_path / "a.md").write_text("a")
        (tmp_path / "b.md").write_text("b")

        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(side_effect=[RuntimeError("disk error"), _ok_result("doc-2")])
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.md"},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store, workspace_root=tmp_path)
        result = await orch.refresh(source)

        assert result.failed == 1
        assert result.refreshed == 1
        assert "disk error" in result.errors[0]


# ===========================================================================
# Source record updates
# ===========================================================================


class TestSourceRecordUpdates:
    """Updates source via store.update() on success / failure."""

    @pytest.mark.asyncio
    async def test_updates_last_refreshed_on_success(self) -> None:
        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(config={"urls": ["https://a.com"]})
        orch = _make_orchestrator(pipeline=pipeline, store=store)
        await orch.refresh(source)

        store.update.assert_called_once()
        updated_source = store.update.call_args[0][0]
        assert updated_source.last_refreshed_at is not None
        assert updated_source.last_error is None

    @pytest.mark.asyncio
    async def test_clears_last_error_on_success(self) -> None:
        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(config={"urls": ["https://a.com"]})
        # Source had a previous error
        source = source.model_copy(update={"last_error": "old error"})
        orch = _make_orchestrator(pipeline=pipeline, store=store)
        await orch.refresh(source)

        updated_source = store.update.call_args[0][0]
        assert updated_source.last_error is None

    @pytest.mark.asyncio
    async def test_sets_last_error_when_all_fail(self) -> None:
        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(side_effect=RuntimeError("fail"))
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            config={"urls": ["https://a.com", "https://b.com"]},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store)
        result = await orch.refresh(source)

        assert result.failed == 2
        updated_source = store.update.call_args[0][0]
        assert updated_source.last_error is not None
        assert "fail" in updated_source.last_error


# ===========================================================================
# Disabled source
# ===========================================================================


class TestDisabledSource:
    """Disabled source passed to refresh() raises ValueError."""

    @pytest.mark.asyncio
    async def test_raises_for_disabled_source(self) -> None:
        source = _make_source(enabled=False)
        orch = _make_orchestrator()

        with pytest.raises(ValueError, match="disabled"):
            await orch.refresh(source)


# ===========================================================================
# refresh_all
# ===========================================================================


class TestRefreshAll:
    """refresh_all() processes all enabled sources ordered by priority."""

    @pytest.mark.asyncio
    async def test_processes_all_enabled_sources(self) -> None:
        s1 = _make_source(source_id="s1", config={"urls": ["https://a.com"]}, priority=1)
        s2 = _make_source(source_id="s2", config={"urls": ["https://b.com"]}, priority=2)

        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.list_enabled = MagicMock(return_value=[s2, s1])  # priority DESC
        store.update = MagicMock()

        orch = _make_orchestrator(pipeline=pipeline, store=store)
        results = await orch.refresh_all()

        assert len(results) == 2
        assert results[0].source_id == "s2"  # Higher priority first
        assert results[1].source_id == "s1"

    @pytest.mark.asyncio
    async def test_passes_scope_to_list_enabled(self) -> None:
        store = MagicMock()
        store.list_enabled = MagicMock(return_value=[])
        store.update = MagicMock()

        orch = _make_orchestrator(store=store)
        await orch.refresh_all(scope="project-x")

        store.list_enabled.assert_called_once_with("project-x")

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_sources(self) -> None:
        store = MagicMock()
        store.list_enabled = MagicMock(return_value=[])
        store.update = MagicMock()

        orch = _make_orchestrator(store=store)
        results = await orch.refresh_all()

        assert results == []

    @pytest.mark.asyncio
    async def test_one_source_failure_doesnt_abort_others(self) -> None:
        s1 = _make_source(
            source_id="s1",
            config={"urls": ["https://fail.com"]},
            priority=2,
        )
        s2 = _make_source(
            source_id="s2",
            config={"urls": ["https://ok.com"]},
            priority=1,
        )

        pipeline = MagicMock()
        # First source → ingest raises, second source → succeeds
        pipeline.ingest = AsyncMock(
            side_effect=[RuntimeError("network error"), _ok_result("doc-2")]
        )
        store = MagicMock()
        store.list_enabled = MagicMock(return_value=[s1, s2])
        store.update = MagicMock()

        orch = _make_orchestrator(pipeline=pipeline, store=store)
        results = await orch.refresh_all()

        assert len(results) == 2
        assert results[0].failed == 1  # s1 failed
        assert results[1].refreshed == 1  # s2 succeeded


# ===========================================================================
# file_glob path sandboxing (#654)
# ===========================================================================


class TestFileGlobSandboxing:
    """_handle_file_glob validates paths with sandbox_path."""

    @pytest.mark.asyncio
    async def test_base_dir_outside_workspace_raises(self, tmp_path: Path) -> None:
        """base_dir resolving outside workspace_root must raise PermissionError."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.txt", "base_dir": str(outside)},
        )
        orch = _make_orchestrator(pipeline=MagicMock(), store=MagicMock(), workspace_root=workspace)

        with pytest.raises(PermissionError, match="outside workspace"):
            await orch.refresh(source)

    @pytest.mark.asyncio
    async def test_base_dir_traversal_raises(self, tmp_path: Path) -> None:
        """base_dir with .. traversal outside workspace must raise PermissionError."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.txt", "base_dir": str(workspace / ".." / "..")},
        )
        orch = _make_orchestrator(pipeline=MagicMock(), store=MagicMock(), workspace_root=workspace)

        with pytest.raises(PermissionError, match="outside workspace"):
            await orch.refresh(source)

    @pytest.mark.asyncio
    async def test_glob_result_outside_workspace_skipped(self, tmp_path: Path) -> None:
        """Glob result resolving outside workspace is skipped (e.g. symlink escape)."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside_path = tmp_path / "outside" / "secret.md"

        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.md"},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store, workspace_root=workspace)
        # Mock glob to return a path outside workspace
        with patch.object(Path, "glob", return_value=[outside_path]):
            result = await orch.refresh(source)

        # outside path should NOT be passed to ingest
        pipeline.ingest.assert_not_awaited()
        assert result.refreshed == 0
        assert result.failed == 1
        assert any("outside workspace" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_valid_base_dir_inside_workspace_works(self, tmp_path: Path) -> None:
        """base_dir inside workspace should work normally."""
        workspace = tmp_path / "workspace"
        sub = workspace / "sub"
        sub.mkdir(parents=True)
        (sub / "a.txt").write_text("a")

        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.txt", "base_dir": str(sub)},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store, workspace_root=workspace)
        result = await orch.refresh(source)

        assert pipeline.ingest.await_count == 1
        assert result.refreshed == 1

    @pytest.mark.asyncio
    async def test_none_base_dir_defaults_to_workspace(self, tmp_path: Path) -> None:
        """base_dir=None defaults to workspace_root (no sandbox check needed)."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "readme.md").write_text("hello")

        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.md"},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store, workspace_root=workspace)
        result = await orch.refresh(source)

        assert pipeline.ingest.await_count == 1
        assert result.refreshed == 1

    @pytest.mark.asyncio
    async def test_only_sandboxed_paths_reach_ingest(self, tmp_path: Path) -> None:
        """Mix of valid and escape paths: only valid ones get ingested."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        good_path = workspace / "good.md"
        good_path.write_text("good")
        bad_path = tmp_path / "outside" / "bad.md"  # outside workspace

        pipeline = MagicMock()
        pipeline.ingest = AsyncMock(return_value=_ok_result())
        store = MagicMock()
        store.update = MagicMock()

        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"pattern": "*.md"},
        )
        orch = _make_orchestrator(pipeline=pipeline, store=store, workspace_root=workspace)
        # Mock glob to return one valid and one outside path
        with patch.object(Path, "glob", return_value=[bad_path, good_path]):
            result = await orch.refresh(source)

        # Only good.md should be ingested
        assert pipeline.ingest.await_count == 1
        call_arg = pipeline.ingest.call_args_list[0][0][0]
        assert "good" in call_arg
        assert result.refreshed == 1
        assert result.failed == 1  # bad.md outside workspace


# ===========================================================================
# cancel= parameter — cooperative cancellation seam (task #880)
# ===========================================================================


class TestFromAC_RefreshCancellation:
    """cancel= signal stops refresh_all and _ingest_items at iteration boundaries."""

    @pytest.mark.asyncio
    async def test_refresh_all_stops_before_next_source_when_cancel_set_between_iterations(
        self,
    ) -> None:
        """refresh_all(cancel=) does not start the next source once cancel is set."""
        cancel = asyncio.Event()
        src_a = _make_source(source_id="src-a", config={"urls": ["https://a.com"]})
        src_b = _make_source(source_id="src-b", config={"urls": ["https://b.com"]})
        store = MagicMock()
        store.list_enabled.return_value = [src_a, src_b]
        store.update = MagicMock()
        pipeline = MagicMock()

        async def ingest_and_cancel(_url: str) -> IngestResult:
            cancel.set()  # set after first item — next source should not start
            return _ok_result()

        pipeline.ingest = AsyncMock(side_effect=ingest_and_cancel)
        orch = _make_orchestrator(store=store, pipeline=pipeline)

        results = await orch.refresh_all(cancel=cancel)

        assert len(results) == 1
        assert results[0].source_id == "src-a"
        assert pipeline.ingest.await_count == 1

    @pytest.mark.asyncio
    async def test_refresh_all_returns_only_results_produced_before_cancellation(
        self,
    ) -> None:
        """refresh_all partial result list reflects only sources completed before cancel."""
        cancel = asyncio.Event()
        sources = [
            _make_source(source_id=f"s{i}", config={"urls": [f"https://{i}.com"]}) for i in range(3)
        ]
        store = MagicMock()
        store.list_enabled.return_value = sources
        store.update = MagicMock()

        call_count = 0
        pipeline = MagicMock()

        async def counted_ingest(_url: str) -> IngestResult:
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # 2 of 3 sources
                cancel.set()
            return _ok_result()

        pipeline.ingest = AsyncMock(side_effect=counted_ingest)
        orch = _make_orchestrator(store=store, pipeline=pipeline)

        results = await orch.refresh_all(cancel=cancel)

        # Two sources completed; cancel set at end of second, third not started
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_ingest_items_stops_before_next_item_when_cancel_set_between_iterations(
        self,
    ) -> None:
        """_ingest_items(cancel=) does not start the next item once cancel is set."""
        cancel = asyncio.Event()
        pipeline = MagicMock()

        async def ingest_and_cancel(_item: str) -> IngestResult:
            cancel.set()
            return _ok_result()

        pipeline.ingest = AsyncMock(side_effect=ingest_and_cancel)
        orch = _make_orchestrator(pipeline=pipeline)

        result = await orch._ingest_items("src-x", ["item-0", "item-1", "item-2"], cancel=cancel)

        assert pipeline.ingest.await_count == 1
        assert result.refreshed == 1

    @pytest.mark.asyncio
    async def test_ingest_items_result_counts_only_work_completed_before_cancel(
        self,
    ) -> None:
        """_ingest_items RefreshResult counts only items processed before cancel fires."""
        cancel = asyncio.Event()
        pipeline = MagicMock()
        seen: list[str] = []

        async def tracking_ingest(item: str) -> IngestResult:
            seen.append(item)
            if len(seen) == 1:
                cancel.set()
            return _ok_result()

        pipeline.ingest = AsyncMock(side_effect=tracking_ingest)
        orch = _make_orchestrator(pipeline=pipeline)

        result = await orch._ingest_items("src-z", ["item-0", "item-1", "item-2"], cancel=cancel)

        assert len(seen) == 1
        assert result.refreshed == 1
        assert result.skipped == 0
        assert result.failed == 0
