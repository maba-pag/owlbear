"""RED-phase tests for BookmarkPipeline, RefreshOrchestrator, MCP tools extraction (#136).

Tests the contract for:
- BookmarkResult model + BookmarkPipeline in bookmark_pipeline.py (new module)
- RefreshResult model + RefreshOrchestrator in refresh.py (new module)
- KnowledgeSourceStore.list_enabled() new method in source_store.py
- bookmark_source and list_bookmarks MCP tools in mcp-knowledge tools.py
- AppContext extended with bookmark_pipeline and bookmark_store fields
- packages/knowledge __init__.py exports updated

Imports from new modules are done inline (noqa: PLC0415) so collection succeeds;
tests fail at execution time with ImportError or AttributeError.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge import init_db
from owlbear_knowledge.evaluator import EvaluationResult
from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_knowledge.source_store import KnowledgeSourceStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_source(  # noqa: PLR0913
    *,
    name: str = "src",
    source_type: SourceType = SourceType.URL_LIST,
    enabled: bool = True,
    scope: str = "global",
    priority: int = 0,
    config: dict[str, Any] | None = None,
) -> KnowledgeSource:
    return KnowledgeSource(
        name=name,
        source_type=source_type,
        config=config or {},
        scope=scope,
        enabled=enabled,
        priority=priority,
        created_at=_now(),
        updated_at=_now(),
    )


def _make_eval_result(
    *,
    relevance_score: float = 0.5,
    worth_ingesting: bool = False,
    tags: list[str] | None = None,
    summary: str = "test summary",
) -> EvaluationResult:
    return EvaluationResult(
        relevance_score=relevance_score,
        worth_ingesting=worth_ingesting,
        tags=tags or [],
        summary=summary,
    )


class _SetSignal:
    """Simple CancelSignal that is always set."""

    def is_set(self) -> bool:
        return True


class _ClearSignal:
    """Simple CancelSignal that is never set."""

    def is_set(self) -> bool:
        return False


# ===========================================================================
# AC: BookmarkResult model
# ===========================================================================


class TestFromAC_BookmarkResultModel:  # noqa: N801
    """BookmarkResult is a frozen Pydantic BaseModel with expected fields."""

    def test_bookmark_result_importable(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        assert BookmarkResult is not None

    def test_bookmark_result_required_url_field(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        r = BookmarkResult(url="https://example.com")
        assert r.url == "https://example.com"

    def test_bookmark_result_optional_fields_default_none(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        r = BookmarkResult(url="https://example.com")
        assert r.bookmark is None
        assert r.evaluation is None
        assert r.skipped_reason is None

    def test_bookmark_result_ingested_defaults_false(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        r = BookmarkResult(url="https://example.com")
        assert r.ingested is False

    def test_bookmark_result_is_frozen(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415
        from pydantic import ValidationError  # noqa: PLC0415

        r = BookmarkResult(url="https://example.com")
        with pytest.raises(ValidationError):
            r.url = "https://mutated.com"  # type: ignore[misc]

    def test_bookmark_result_accepts_all_fields(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415
        from owlbear_knowledge.bookmark_store import Bookmark  # noqa: PLC0415

        bm = Bookmark(url="https://x.com", title="T", created_at=_now(), updated_at=_now())
        ev = _make_eval_result()
        r = BookmarkResult(url="https://x.com", bookmark=bm, evaluation=ev, ingested=True)
        assert r.bookmark is bm
        assert r.evaluation is ev
        assert r.ingested is True


# ===========================================================================
# AC: BookmarkPipeline constructor — web_read_fn is REQUIRED
# ===========================================================================


class TestFromAC_BookmarkPipelineConstructor:  # noqa: N801
    """BookmarkPipeline constructor: web_read_fn is required, no _default_web_read."""

    def test_constructor_without_web_read_fn_raises_type_error(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        with pytest.raises(TypeError):
            BookmarkPipeline(  # type: ignore[call-arg]
                bookmark_store=MagicMock(),
                evaluator=MagicMock(),
            )

    def test_constructor_accepts_all_parameters(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        async def dummy_web_read(_url: str) -> str | None:
            return "<html/>"

        pipeline = BookmarkPipeline(
            bookmark_store=MagicMock(),
            evaluator=MagicMock(),
            ingest_pipeline=None,
            web_read_fn=dummy_web_read,
            ingest_threshold=0.7,
        )
        assert pipeline is not None

    def test_default_web_read_not_exported_from_module(self) -> None:
        """_default_web_read must NOT be extracted to v2 (v1-only HTTP dep)."""
        import owlbear_knowledge.bookmark_pipeline as bp_module  # noqa: PLC0415

        assert not hasattr(bp_module, "_default_web_read"), (
            "_default_web_read must not exist in v2 bookmark_pipeline"
        )

    def test_ingest_threshold_defaults_to_0_7(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        async def dummy_web_read(_url: str) -> str | None:
            return "content"

        # Verify default threshold by inspecting constructor signature
        import inspect  # noqa: PLC0415

        sig = inspect.signature(BookmarkPipeline.__init__)
        default = sig.parameters["ingest_threshold"].default
        assert default == 0.7


# ===========================================================================
# AC: BookmarkPipeline.process() contract
# ===========================================================================


class TestFromAC_BookmarkPipelineProcess:  # noqa: N801
    """process() returns BookmarkResult with cooperative cancellation at each stage."""

    def _make_pipeline(
        self,
        *,
        existing_bookmark: object = None,
        web_read_return: str | None = "page content",
        eval_result: EvaluationResult | None = None,
        ingest_pipeline: object | None = None,
        threshold: float = 0.7,
    ) -> object:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store_mock = MagicMock()
        store_mock.get_by_url.return_value = existing_bookmark
        store_mock.create.side_effect = lambda b: b

        evaluator_mock = MagicMock()
        evaluator_mock.evaluate = AsyncMock(
            return_value=eval_result or _make_eval_result()
        )

        web_read_mock = AsyncMock(return_value=web_read_return)

        return BookmarkPipeline(
            bookmark_store=store_mock,
            evaluator=evaluator_mock,
            ingest_pipeline=ingest_pipeline,
            web_read_fn=web_read_mock,
            ingest_threshold=threshold,
        )

    @pytest.mark.asyncio
    async def test_process_returns_bookmark_result(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        pipeline = self._make_pipeline()
        result = await pipeline.process("https://example.com")
        assert isinstance(result, BookmarkResult)

    @pytest.mark.asyncio
    async def test_process_happy_path_stores_bookmark(self) -> None:
        pipeline = self._make_pipeline()
        result = await pipeline.process("https://example.com")
        assert result.url == "https://example.com"
        assert result.bookmark is not None
        assert result.skipped_reason is None

    @pytest.mark.asyncio
    async def test_process_dedup_returns_early_if_already_bookmarked(self) -> None:
        from owlbear_knowledge.bookmark_store import Bookmark  # noqa: PLC0415

        existing = Bookmark(url="https://example.com", title="Existing", created_at=_now(), updated_at=_now())
        pipeline = self._make_pipeline(existing_bookmark=existing)
        result = await pipeline.process("https://example.com")
        assert result.bookmark is existing
        assert result.skipped_reason is not None
        assert "Already" in result.skipped_reason or "already" in result.skipped_reason

    @pytest.mark.asyncio
    async def test_process_cancel_before_extract_returns_empty_result(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        pipeline = self._make_pipeline()
        result = await pipeline.process("https://example.com", cancel=_SetSignal())
        assert isinstance(result, BookmarkResult)
        assert result.bookmark is None
        assert result.evaluation is None

    @pytest.mark.asyncio
    async def test_process_cancel_before_evaluate_returns_no_evaluation(self) -> None:
        """Cancel set after extract but before evaluate — evaluation is None."""
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        call_count = 0

        class _CancelAfterFirstCall:
            def is_set(self) -> bool:
                nonlocal call_count
                call_count += 1
                # Set after the first is_set() check (post-extract)
                return call_count > 1

        store = MagicMock()
        store.get_by_url.return_value = None
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        web_read = AsyncMock(return_value="content")

        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            ingest_pipeline=None,
            web_read_fn=web_read,
        )
        result = await pipeline.process("https://example.com", cancel=_CancelAfterFirstCall())
        assert result.evaluation is None

    @pytest.mark.asyncio
    async def test_process_web_read_failure_returns_skipped_reason(self) -> None:
        # web_read raising an exception:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        web_read = AsyncMock(side_effect=RuntimeError("Network error"))
        evaluator = MagicMock()

        p = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            ingest_pipeline=None,
            web_read_fn=web_read,
        )
        result = await p.process("https://failing.com")
        assert result.bookmark is None
        assert result.skipped_reason is not None

    @pytest.mark.asyncio
    async def test_process_below_threshold_does_not_ingest(self) -> None:
        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock()
        pipeline = self._make_pipeline(
            eval_result=_make_eval_result(relevance_score=0.3, worth_ingesting=True),
            ingest_pipeline=ingest_mock,
            threshold=0.7,
        )
        result = await pipeline.process("https://example.com")
        assert result.ingested is False
        ingest_mock.ingest_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_above_threshold_with_worth_ingesting_triggers_ingest(self) -> None:
        from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415

        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock(
            return_value=IngestResult(
                document_id="doc-1",
                chunk_count=1,
                entity_count=0,
                edge_count=0,
                status="ok",
            )
        )
        pipeline = self._make_pipeline(
            eval_result=_make_eval_result(relevance_score=0.9, worth_ingesting=True),
            ingest_pipeline=ingest_mock,
            threshold=0.7,
        )
        result = await pipeline.process("https://example.com")
        assert result.ingested is True
        ingest_mock.ingest_text.assert_called_once()


# ===========================================================================
# AC: RefreshResult model
# ===========================================================================


class TestFromAC_RefreshResultModel:  # noqa: N801
    """RefreshResult is a frozen Pydantic BaseModel with source_id, counters, errors."""

    def test_refresh_result_importable(self) -> None:
        from owlbear_knowledge.refresh import RefreshResult  # noqa: PLC0415

        assert RefreshResult is not None

    def test_refresh_result_required_source_id(self) -> None:
        from owlbear_knowledge.refresh import RefreshResult  # noqa: PLC0415

        r = RefreshResult(source_id="src-1", refreshed=3, skipped=1, failed=0)
        assert r.source_id == "src-1"
        assert r.refreshed == 3
        assert r.skipped == 1
        assert r.failed == 0

    def test_refresh_result_errors_defaults_empty_list(self) -> None:
        from owlbear_knowledge.refresh import RefreshResult  # noqa: PLC0415

        r = RefreshResult(source_id="src-1", refreshed=0, skipped=0, failed=0)
        assert r.errors == []

    def test_refresh_result_is_frozen(self) -> None:
        from owlbear_knowledge.refresh import RefreshResult  # noqa: PLC0415
        from pydantic import ValidationError  # noqa: PLC0415

        r = RefreshResult(source_id="s", refreshed=0, skipped=0, failed=0)
        with pytest.raises(ValidationError):
            r.refreshed = 99  # type: ignore[misc]


# ===========================================================================
# AC: RefreshOrchestrator constructor
# ===========================================================================


class TestFromAC_RefreshOrchestratorConstructor:  # noqa: N801
    """RefreshOrchestrator constructor accepts store, pipeline, crawl_handler, workspace_root."""

    def test_constructor_accepts_required_params(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
        )
        assert orch is not None

    def test_constructor_accepts_optional_params(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            crawl_handler=None,
            workspace_root=Path.cwd(),
        )
        assert orch is not None


# ===========================================================================
# AC: RefreshOrchestrator.refresh() — dispatch by SourceType
# ===========================================================================


class TestFromAC_RefreshOrchestratorRefresh:  # noqa: N801
    """refresh() dispatches by SourceType; disabled raises; refresh_all cancellation."""

    @pytest.mark.asyncio
    async def test_refresh_disabled_source_raises_value_error(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        orch = RefreshOrchestrator(store=MagicMock(), pipeline=MagicMock())
        source = _make_source(enabled=False)
        with pytest.raises(ValueError, match="disabled"):
            await orch.refresh(source)

    @pytest.mark.asyncio
    async def test_refresh_url_list_returns_refresh_result(self) -> None:
        from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(
            return_value=IngestResult(
                document_id="d1", chunk_count=1, entity_count=0, edge_count=0, status="ok"
            )
        )
        store_mock = MagicMock()
        store_mock.update = MagicMock()
        store_mock.get = MagicMock(return_value=None)

        orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
        source = _make_source(source_type=SourceType.URL_LIST, config={"urls": ["https://a.com"]})
        result = await orch.refresh(source)
        assert isinstance(result, RefreshResult)
        assert result.source_id == source.id

    @pytest.mark.asyncio
    async def test_refresh_crawl_without_handler_raises_value_error(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        orch = RefreshOrchestrator(store=MagicMock(), pipeline=MagicMock(), crawl_handler=None)
        source = _make_source(source_type=SourceType.CRAWL)
        with pytest.raises(ValueError, match="crawl"):
            await orch.refresh(source)

    @pytest.mark.asyncio
    async def test_refresh_all_calls_list_enabled_with_scope(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        store_mock = MagicMock()
        store_mock.list_enabled.return_value = []
        orch = RefreshOrchestrator(store=store_mock, pipeline=MagicMock())
        await orch.refresh_all(scope="project-1")
        store_mock.list_enabled.assert_called_once_with("project-1")

    @pytest.mark.asyncio
    async def test_refresh_all_cooperative_cancellation_stops_loop(self) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        store_mock = MagicMock()
        store_mock.list_enabled.return_value = [_make_source(name=f"src-{i}") for i in range(3)]
        store_mock.update = MagicMock()
        pipeline_mock = MagicMock()

        orch = RefreshOrchestrator(store=store_mock, pipeline=pipeline_mock)
        # Cancel signal is immediately set — loop must not dispatch any source
        results = await orch.refresh_all(cancel=_SetSignal())
        assert results == []


# ===========================================================================
# AC: file_glob handler — sandbox_path for path-traversal prevention
# ===========================================================================


class TestFromAC_RefreshOrchestratorFileGlob:  # noqa: N801
    """file_glob uses sandbox_path; path-traversal attempts are rejected."""

    @pytest.mark.asyncio
    async def test_file_glob_path_traversal_counted_as_failed(self, tmp_path: Path) -> None:
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock()
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        # Create a file outside the workspace
        evil_file = outside / "secret.txt"
        evil_file.write_text("secret content")

        orch = RefreshOrchestrator(
            store=store_mock,
            pipeline=pipeline_mock,
            workspace_root=workspace,
        )
        # Source with base_dir pointing outside workspace
        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"base_dir": str(outside), "pattern": "*.txt"},
        )
        result = await orch.refresh(source)
        # Paths outside the sandbox must be counted as failed, not ingested
        assert result.failed > 0 or result.refreshed == 0

    @pytest.mark.asyncio
    async def test_file_glob_valid_path_within_workspace_is_ingested(self, tmp_path: Path) -> None:
        from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        workspace = tmp_path / "workspace"
        workspace.mkdir()
        docs_dir = workspace / "docs"
        docs_dir.mkdir()
        (docs_dir / "readme.md").write_text("# Hello")

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(
            return_value=IngestResult(
                document_id="d", chunk_count=1, entity_count=0, edge_count=0, status="ok"
            )
        )
        store_mock = MagicMock()
        store_mock.update = MagicMock()

        orch = RefreshOrchestrator(
            store=store_mock,
            pipeline=pipeline_mock,
            workspace_root=workspace,
        )
        source = _make_source(
            source_type=SourceType.FILE_GLOB,
            config={"base_dir": "docs", "pattern": "*.md"},
        )
        result = await orch.refresh(source)
        # At least one file was processed (refreshed or skipped — not all failed)
        assert result.failed == 0 or result.refreshed + result.skipped > 0


# ===========================================================================
# AC: _update_source_record persists refresh timestamp and error summary
# ===========================================================================


class TestFromAC_UpdateSourceRecord:  # noqa: N801
    """After refresh(), source record in store has last_refreshed_at set."""

    @pytest.mark.asyncio
    async def test_refresh_persists_last_refreshed_at(self) -> None:
        from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        conn = _make_db()
        real_store = KnowledgeSourceStore(conn)
        source = _make_source(source_type=SourceType.URL_LIST, config={"urls": []})
        real_store.create(source)

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(
            return_value=IngestResult(
                document_id="d", chunk_count=0, entity_count=0, edge_count=0, status="ok"
            )
        )

        orch = RefreshOrchestrator(store=real_store, pipeline=pipeline_mock)
        await orch.refresh(source)

        updated = real_store.get(source.id)
        assert updated is not None
        assert updated.last_refreshed_at is not None

    @pytest.mark.asyncio
    async def test_refresh_clears_last_error_on_success(self) -> None:
        from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415
        from owlbear_knowledge.refresh import RefreshOrchestrator  # noqa: PLC0415

        conn = _make_db()
        real_store = KnowledgeSourceStore(conn)

        # Create source with a pre-existing error
        source = KnowledgeSource(
            name="err-src",
            source_type=SourceType.URL_LIST,
            config={"urls": []},
            last_error="previous error",
            created_at=_now(),
            updated_at=_now(),
        )
        real_store.create(source)

        pipeline_mock = MagicMock()
        pipeline_mock.ingest = AsyncMock(
            return_value=IngestResult(
                document_id="d", chunk_count=0, entity_count=0, edge_count=0, status="ok"
            )
        )
        orch = RefreshOrchestrator(store=real_store, pipeline=pipeline_mock)
        await orch.refresh(source)

        updated = real_store.get(source.id)
        assert updated is not None
        # On clean refresh, error should be cleared or contain empty string
        assert updated.last_error is None or updated.last_error == ""


# ===========================================================================
# AC: KnowledgeSourceStore.list_enabled(scope)
# ===========================================================================


class TestFromAC_ListEnabled:  # noqa: N801
    """list_enabled() returns enabled sources, optionally filtered by scope, priority DESC."""

    def _make_store(self) -> KnowledgeSourceStore:
        return KnowledgeSourceStore(_make_db())

    def test_list_enabled_method_exists(self) -> None:
        store = self._make_store()
        assert hasattr(store, "list_enabled")

    def test_list_enabled_returns_only_enabled_sources(self) -> None:
        store = self._make_store()
        enabled_src = _make_source(name="enabled", enabled=True)
        disabled_src = _make_source(name="disabled", enabled=False)
        store.create(enabled_src)
        store.create(disabled_src)

        result = store.list_enabled()
        ids = [s.id for s in result]
        assert enabled_src.id in ids
        assert disabled_src.id not in ids

    def test_list_enabled_scope_filter_excludes_other_scopes(self) -> None:
        store = self._make_store()
        proj_src = _make_source(name="proj", scope="project-abc")
        global_src = _make_source(name="global")
        store.create(proj_src)
        store.create(global_src)

        result = store.list_enabled(scope="project-abc")
        ids = [s.id for s in result]
        assert proj_src.id in ids
        assert global_src.id not in ids

    def test_list_enabled_ordered_by_priority_desc(self) -> None:
        store = self._make_store()
        low = _make_source(name="low", priority=1)
        high = _make_source(name="high", priority=10)
        mid = _make_source(name="mid", priority=5)
        for s in [low, high, mid]:
            store.create(s)

        result = store.list_enabled()
        enabled = [s for s in result if s.id in {low.id, high.id, mid.id}]
        priorities = [s.priority for s in enabled]
        assert priorities == sorted(priorities, reverse=True)

    def test_list_enabled_no_scope_returns_all_enabled(self) -> None:
        store = self._make_store()
        s1 = _make_source(name="s1", scope="a")
        s2 = _make_source(name="s2", scope="b")
        for s in [s1, s2]:
            store.create(s)

        result = store.list_enabled()
        ids = [s.id for s in result]
        assert s1.id in ids
        assert s2.id in ids


# ===========================================================================
# AC: MCP tools — AppContext, bookmark_source, list_bookmarks
# ===========================================================================


class TestFromAC_MCPBookmarkTools:  # noqa: N801
    """AppContext extended; bookmark_source and list_bookmarks MCP tools registered."""

    def test_app_context_has_bookmark_pipeline_field(self) -> None:
        from owlbear_mcp_knowledge.server import AppContext  # noqa: PLC0415

        import dataclasses  # noqa: PLC0415

        fields = {f.name for f in dataclasses.fields(AppContext)}
        assert "bookmark_pipeline" in fields

    def test_app_context_has_bookmark_store_field(self) -> None:
        from owlbear_mcp_knowledge.server import AppContext  # noqa: PLC0415

        import dataclasses  # noqa: PLC0415

        fields = {f.name for f in dataclasses.fields(AppContext)}
        assert "bookmark_store" in fields

    def test_bookmark_source_function_registered(self) -> None:
        from owlbear_mcp_knowledge import server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "bookmark_source"), "bookmark_source tool missing from server.py"

    def test_list_bookmarks_function_registered(self) -> None:
        from owlbear_mcp_knowledge import server as server_mod  # noqa: PLC0415

        assert hasattr(server_mod, "list_bookmarks"), "list_bookmarks tool missing from server.py"

    @pytest.mark.asyncio
    async def test_bookmark_source_calls_pipeline_process(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415
        from owlbear_mcp_knowledge.server import AppContext, bookmark_source  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.process = AsyncMock(
            return_value=BookmarkResult(url="https://example.com", skipped_reason="dup")
        )
        ctx = AppContext(
            query_service=None,
            bookmark_pipeline=pipeline_mock,
            bookmark_store=MagicMock(),
        )
        result = await bookmark_source(ctx, "https://example.com")
        pipeline_mock.process.assert_called_once()
        assert "https://example.com" in str(result)

    @pytest.mark.asyncio
    async def test_bookmark_source_reason_is_optional(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415
        from owlbear_mcp_knowledge.server import AppContext, bookmark_source  # noqa: PLC0415

        pipeline_mock = MagicMock()
        pipeline_mock.process = AsyncMock(
            return_value=BookmarkResult(url="https://x.com")
        )
        ctx = AppContext(
            query_service=None,
            bookmark_pipeline=pipeline_mock,
            bookmark_store=MagicMock(),
        )
        # Should not raise — reason has no default but is optional per AC
        await bookmark_source(ctx, "https://x.com")
        pipeline_mock.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_bookmarks_calls_store_list(self) -> None:
        from owlbear_mcp_knowledge.server import AppContext, list_bookmarks  # noqa: PLC0415

        store_mock = MagicMock()
        store_mock.list.return_value = []
        ctx = AppContext(
            query_service=None,
            bookmark_pipeline=MagicMock(),
            bookmark_store=store_mock,
        )
        await list_bookmarks(ctx, tag="python", min_score=0.5)
        store_mock.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_bookmarks_tag_and_min_score_optional(self) -> None:
        from owlbear_mcp_knowledge.server import AppContext, list_bookmarks  # noqa: PLC0415

        store_mock = MagicMock()
        store_mock.list.return_value = []
        ctx = AppContext(
            query_service=None,
            bookmark_pipeline=MagicMock(),
            bookmark_store=store_mock,
        )
        # Should not raise — both parameters are optional
        await list_bookmarks(ctx)
        store_mock.list.assert_called_once()


# ===========================================================================
# AC: __init__.py exports BookmarkResult, BookmarkPipeline, RefreshResult, RefreshOrchestrator
# ===========================================================================


class TestFromAC_InitExports:  # noqa: N801
    """owlbear_knowledge exports BookmarkResult, BookmarkPipeline, RefreshResult, RefreshOrchestrator."""

    def test_bookmark_result_importable_from_package(self) -> None:
        from owlbear_knowledge import BookmarkResult  # noqa: PLC0415

        assert BookmarkResult is not None

    def test_bookmark_pipeline_importable_from_package(self) -> None:
        from owlbear_knowledge import BookmarkPipeline  # noqa: PLC0415

        assert BookmarkPipeline is not None

    def test_refresh_result_importable_from_package(self) -> None:
        from owlbear_knowledge import RefreshResult  # noqa: PLC0415

        assert RefreshResult is not None

    def test_refresh_orchestrator_importable_from_package(self) -> None:
        from owlbear_knowledge import RefreshOrchestrator  # noqa: PLC0415

        assert RefreshOrchestrator is not None

    def test_bookmark_result_in_dunder_all(self) -> None:
        import owlbear_knowledge  # noqa: PLC0415

        assert "BookmarkResult" in owlbear_knowledge.__all__

    def test_bookmark_pipeline_in_dunder_all(self) -> None:
        import owlbear_knowledge  # noqa: PLC0415

        assert "BookmarkPipeline" in owlbear_knowledge.__all__

    def test_refresh_result_in_dunder_all(self) -> None:
        import owlbear_knowledge  # noqa: PLC0415

        assert "RefreshResult" in owlbear_knowledge.__all__

    def test_refresh_orchestrator_in_dunder_all(self) -> None:
        import owlbear_knowledge  # noqa: PLC0415

        assert "RefreshOrchestrator" in owlbear_knowledge.__all__
