"""RED-phase tests for BookmarkPipeline orchestrator (#552).

Tests the contract for bookmark_pipeline.py (new module):
- BookmarkResult model: frozen, all five fields, types, defaults
- BookmarkPipeline constructor: all params, optional web_read_fn (None default)
- process() dedup: returns early when BookmarkStore.get_by_url finds existing
- process() extraction failure: broad exception -> skipped_reason, no evaluation
- process() evaluation: SourceEvaluator.evaluate called with content + project_context
- process() conditional ingest: 4-condition gate (pipeline, content, score, worth)
- process() bookmark creation: title from summary[:120], tags, score, reason, scope, document_id
- process() cancel signal: checked between stages, returns partial results
- process() no web_read_fn: graceful degradation (no extraction, empty content path)

Imports from bookmark_pipeline are done inline (noqa: PLC0415) so collection
succeeds; tests fail at execution time with ImportError as expected (RED phase).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear_knowledge.evaluator import EvaluationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _make_eval_result(
    *,
    relevance_score: float = 0.8,
    worth_ingesting: bool = True,
    tags: list[str] | None = None,
    summary: str = "A useful reference for the project.",
) -> EvaluationResult:
    return EvaluationResult(
        relevance_score=relevance_score,
        worth_ingesting=worth_ingesting,
        tags=tags or ["python", "testing"],
        summary=summary,
    )


def _make_bookmark(url: str = "https://example.com") -> Any:
    from owlbear_knowledge.bookmark_store import Bookmark  # noqa: PLC0415

    return Bookmark(url=url, title="Existing", created_at=_now(), updated_at=_now())


class _SetSignal:
    def is_set(self) -> bool:
        return True


class _ClearSignal:
    def is_set(self) -> bool:
        return False


# ===========================================================================
# AC: BookmarkResult model — frozen, five fields, types, defaults
# ===========================================================================


class TestFromAC_BookmarkResultModel:  # noqa: N801
    """BookmarkResult is a frozen Pydantic model with five fields and correct defaults."""

    def test_import_bookmark_result(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        assert BookmarkResult is not None

    def test_url_is_required_field(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        result = BookmarkResult(url="https://example.com")
        assert result.url == "https://example.com"

    def test_all_five_fields_present(self) -> None:
        """BookmarkResult has exactly: url, bookmark, evaluation, ingested, skipped_reason."""
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        result = BookmarkResult(url="https://example.com")
        assert hasattr(result, "url")
        assert hasattr(result, "bookmark")
        assert hasattr(result, "evaluation")
        assert hasattr(result, "ingested")
        assert hasattr(result, "skipped_reason")

    def test_bookmark_defaults_none(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        result = BookmarkResult(url="https://example.com")
        assert result.bookmark is None

    def test_evaluation_defaults_none(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        result = BookmarkResult(url="https://example.com")
        assert result.evaluation is None

    def test_ingested_defaults_false(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        result = BookmarkResult(url="https://example.com")
        assert result.ingested is False

    def test_skipped_reason_defaults_none(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        result = BookmarkResult(url="https://example.com")
        assert result.skipped_reason is None

    def test_is_frozen(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415
        from pydantic import ValidationError  # noqa: PLC0415

        result = BookmarkResult(url="https://example.com")
        with pytest.raises(ValidationError):
            result.url = "https://mutated.com"  # type: ignore[misc]

    def test_accepts_all_fields(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkResult  # noqa: PLC0415

        bm = _make_bookmark()
        ev = _make_eval_result()
        result = BookmarkResult(
            url="https://example.com",
            bookmark=bm,
            evaluation=ev,
            ingested=True,
            skipped_reason="duplicate",
        )
        assert result.bookmark is bm
        assert result.evaluation is ev
        assert result.ingested is True
        assert result.skipped_reason == "duplicate"


# ===========================================================================
# AC: BookmarkPipeline constructor — web_read_fn and ingest_pipeline optional
# ===========================================================================


class TestFromAC_BookmarkPipelineConstructor:  # noqa: N801
    """Constructor accepts required + optional args; web_read_fn defaults to None."""

    def test_import_bookmark_pipeline(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        assert BookmarkPipeline is not None

    def test_constructor_minimal_without_web_read_fn(self) -> None:
        """bookmark_store and evaluator are the only required args."""
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        pipeline = BookmarkPipeline(
            bookmark_store=MagicMock(),
            evaluator=MagicMock(),
        )
        assert pipeline is not None

    def test_web_read_fn_optional_defaults_none(self) -> None:
        import inspect  # noqa: PLC0415

        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        sig = inspect.signature(BookmarkPipeline.__init__)
        default = sig.parameters["web_read_fn"].default
        assert default is None

    def test_ingest_pipeline_optional_defaults_none(self) -> None:
        import inspect  # noqa: PLC0415

        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        sig = inspect.signature(BookmarkPipeline.__init__)
        default = sig.parameters["ingest_pipeline"].default
        assert default is None

    def test_ingest_threshold_defaults_0_7(self) -> None:
        import inspect  # noqa: PLC0415

        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        sig = inspect.signature(BookmarkPipeline.__init__)
        default = sig.parameters["ingest_threshold"].default
        assert default == 0.7

    def test_constructor_all_params(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        pipeline = BookmarkPipeline(
            bookmark_store=MagicMock(),
            evaluator=MagicMock(),
            ingest_pipeline=MagicMock(),
            web_read_fn=AsyncMock(return_value="content"),
            ingest_threshold=0.5,
        )
        assert pipeline is not None


# ===========================================================================
# AC: process() dedup — returns early when BookmarkStore.get_by_url hits
# ===========================================================================


class TestFromAC_ProcessDedup:  # noqa: N801
    """process() dedup: skipped_reason set, returns early, existing bookmark returned."""

    def _make_pipeline_with_existing(self, url: str = "https://example.com") -> Any:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = _make_bookmark(url)
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock()

        return BookmarkPipeline(bookmark_store=store, evaluator=evaluator)

    @pytest.mark.asyncio
    async def test_dedup_returns_skipped_reason(self) -> None:
        pipeline = self._make_pipeline_with_existing()
        result = await pipeline.process("https://example.com")
        assert result.skipped_reason is not None
        assert result.skipped_reason != ""

    @pytest.mark.asyncio
    async def test_dedup_returns_existing_bookmark(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        existing = _make_bookmark()
        store = MagicMock()
        store.get_by_url.return_value = existing
        pipeline = BookmarkPipeline(bookmark_store=store, evaluator=MagicMock())
        result = await pipeline.process("https://example.com")
        assert result.bookmark is existing

    @pytest.mark.asyncio
    async def test_dedup_does_not_call_evaluate(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = _make_bookmark()
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock()
        pipeline = BookmarkPipeline(bookmark_store=store, evaluator=evaluator)
        await pipeline.process("https://example.com")
        evaluator.evaluate.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_dedup_when_url_not_found(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        pipeline = BookmarkPipeline(bookmark_store=store, evaluator=evaluator)
        result = await pipeline.process("https://example.com")
        # No early return — skipped_reason should not be about duplicate
        assert result.skipped_reason is None or "already" not in result.skipped_reason.lower()


# ===========================================================================
# AC: process() extraction failure — broad exception -> skipped_reason
# ===========================================================================


class TestFromAC_ProcessExtractionFailure:  # noqa: N801
    """web_read_fn raising any exception produces BookmarkResult with skipped_reason."""

    @pytest.mark.asyncio
    async def test_exception_produces_skipped_reason(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        web_read = AsyncMock(side_effect=RuntimeError("Network error"))
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=MagicMock(),
            web_read_fn=web_read,
        )
        result = await pipeline.process("https://failing.com")
        assert result.skipped_reason is not None

    @pytest.mark.asyncio
    async def test_exception_produces_no_bookmark(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        web_read = AsyncMock(side_effect=ConnectionError("Timeout"))
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=MagicMock(),
            web_read_fn=web_read,
        )
        result = await pipeline.process("https://failing.com")
        assert result.bookmark is None

    @pytest.mark.asyncio
    async def test_exception_does_not_propagate(self) -> None:
        """Broad exceptions are caught — process() must not raise."""
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        web_read = AsyncMock(side_effect=ValueError("Unexpected"))
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=MagicMock(),
            web_read_fn=web_read,
        )
        # Should not raise
        result = await pipeline.process("https://failing.com")
        assert result is not None


# ===========================================================================
# AC: process() evaluation — SourceEvaluator.evaluate called with content + context
# ===========================================================================


class TestFromAC_ProcessEvaluation:  # noqa: N801
    """evaluate() is called with extracted content and project_context arg."""

    @pytest.mark.asyncio
    async def test_evaluate_called_with_content(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        web_read = AsyncMock(return_value="extracted content here")
        pipeline = BookmarkPipeline(
            bookmark_store=store, evaluator=evaluator, web_read_fn=web_read
        )
        await pipeline.process("https://example.com")
        evaluator.evaluate.assert_called_once()
        call_args = evaluator.evaluate.call_args
        assert "extracted content here" in str(call_args)

    @pytest.mark.asyncio
    async def test_evaluate_called_with_project_context(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        web_read = AsyncMock(return_value="content")
        pipeline = BookmarkPipeline(
            bookmark_store=store, evaluator=evaluator, web_read_fn=web_read
        )
        ctx = {"name": "OwlBear", "description": "AI dev system"}
        await pipeline.process("https://example.com", project_context=ctx)
        evaluator.evaluate.assert_called_once()
        call_kwargs = evaluator.evaluate.call_args.kwargs
        assert call_kwargs.get("project_context") == ctx

    @pytest.mark.asyncio
    async def test_evaluation_result_in_bookmark_result(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        ev = _make_eval_result()
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=ev)
        web_read = AsyncMock(return_value="content")
        pipeline = BookmarkPipeline(
            bookmark_store=store, evaluator=evaluator, web_read_fn=web_read
        )
        result = await pipeline.process("https://example.com")
        assert result.evaluation is ev


# ===========================================================================
# AC: process() conditional ingest — 4-condition gate
# ===========================================================================


class TestFromAC_ProcessConditionalIngest:  # noqa: N801
    """Ingest triggers only when: pipeline not None AND content truthy AND score >= threshold AND worth_ingesting."""

    def _make_pipeline(
        self,
        *,
        eval_result: EvaluationResult | None = None,
        ingest_pipeline: Any = None,
        threshold: float = 0.7,
        web_content: str = "page content",
    ) -> Any:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=eval_result or _make_eval_result())
        web_read = AsyncMock(return_value=web_content)
        return BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            ingest_pipeline=ingest_pipeline,
            web_read_fn=web_read,
            ingest_threshold=threshold,
        )

    @pytest.mark.asyncio
    async def test_all_conditions_met_triggers_ingest(self) -> None:
        from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415

        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock(
            return_value=IngestResult(
                document_id="doc-1", chunk_count=2, entity_count=1, edge_count=0, status="ok"
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

    @pytest.mark.asyncio
    async def test_no_ingest_pipeline_skips_ingest(self) -> None:
        pipeline = self._make_pipeline(
            eval_result=_make_eval_result(relevance_score=0.9, worth_ingesting=True),
            ingest_pipeline=None,
        )
        result = await pipeline.process("https://example.com")
        assert result.ingested is False

    @pytest.mark.asyncio
    async def test_below_threshold_skips_ingest(self) -> None:
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
    async def test_not_worth_ingesting_skips_ingest(self) -> None:
        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock()
        pipeline = self._make_pipeline(
            eval_result=_make_eval_result(relevance_score=0.9, worth_ingesting=False),
            ingest_pipeline=ingest_mock,
        )
        result = await pipeline.process("https://example.com")
        assert result.ingested is False
        ingest_mock.ingest_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_exactly_at_threshold_triggers_ingest(self) -> None:
        """Score exactly == threshold: ingest is triggered (>= not >)."""
        from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415

        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock(
            return_value=IngestResult(
                document_id="doc-2", chunk_count=1, entity_count=0, edge_count=0, status="ok"
            )
        )
        pipeline = self._make_pipeline(
            eval_result=_make_eval_result(relevance_score=0.7, worth_ingesting=True),
            ingest_pipeline=ingest_mock,
            threshold=0.7,
        )
        result = await pipeline.process("https://example.com")
        assert result.ingested is True

    @pytest.mark.asyncio
    async def test_just_below_threshold_skips_ingest(self) -> None:
        """Score 0.699... < 0.7: ingest is skipped."""
        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock()
        pipeline = self._make_pipeline(
            eval_result=_make_eval_result(relevance_score=0.699, worth_ingesting=True),
            ingest_pipeline=ingest_mock,
            threshold=0.7,
        )
        result = await pipeline.process("https://example.com")
        assert result.ingested is False

    @pytest.mark.asyncio
    async def test_empty_content_skips_ingest(self) -> None:
        """Empty content (from web_read returning empty string) skips ingest."""
        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock()
        pipeline = self._make_pipeline(
            eval_result=_make_eval_result(relevance_score=0.9, worth_ingesting=True),
            ingest_pipeline=ingest_mock,
            web_content="",
        )
        result = await pipeline.process("https://example.com")
        assert result.ingested is False
        ingest_mock.ingest_text.assert_not_called()


# ===========================================================================
# AC: process() bookmark creation — field mapping from evaluation
# ===========================================================================


class TestFromAC_ProcessBookmarkCreation:  # noqa: N801
    """Bookmark is created with fields derived from EvaluationResult and process() args."""

    def _make_pipeline_for_creation(
        self,
        eval_result: EvaluationResult | None = None,
        ingest_result: Any = None,
    ) -> Any:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=eval_result or _make_eval_result())
        web_read = AsyncMock(return_value="some content")

        if ingest_result is not None:
            ingest_mock = MagicMock()
            ingest_mock.ingest_text = AsyncMock(return_value=ingest_result)
        else:
            ingest_mock = None

        return BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            ingest_pipeline=ingest_mock,
            web_read_fn=web_read,
        )

    @pytest.mark.asyncio
    async def test_title_truncated_from_summary_at_120(self) -> None:
        long_summary = "A" * 200
        ev = _make_eval_result(summary=long_summary)
        pipeline = self._make_pipeline_for_creation(eval_result=ev)
        result = await pipeline.process("https://example.com")
        assert result.bookmark is not None
        assert len(result.bookmark.title) <= 120
        assert result.bookmark.title == long_summary[:120]

    @pytest.mark.asyncio
    async def test_title_full_when_summary_short(self) -> None:
        ev = _make_eval_result(summary="Short summary")
        pipeline = self._make_pipeline_for_creation(eval_result=ev)
        result = await pipeline.process("https://example.com")
        assert result.bookmark is not None
        assert result.bookmark.title == "Short summary"

    @pytest.mark.asyncio
    async def test_tags_from_evaluation(self) -> None:
        ev = _make_eval_result(tags=["ai", "python", "testing"])
        pipeline = self._make_pipeline_for_creation(eval_result=ev)
        result = await pipeline.process("https://example.com")
        assert result.bookmark is not None
        assert result.bookmark.tags == ["ai", "python", "testing"]

    @pytest.mark.asyncio
    async def test_relevance_score_from_evaluation(self) -> None:
        ev = _make_eval_result(relevance_score=0.85)
        pipeline = self._make_pipeline_for_creation(eval_result=ev)
        result = await pipeline.process("https://example.com")
        assert result.bookmark is not None
        assert result.bookmark.relevance_score == pytest.approx(0.85)

    @pytest.mark.asyncio
    async def test_reason_from_evaluation_summary(self) -> None:
        ev = _make_eval_result(summary="Very relevant to project goals")
        pipeline = self._make_pipeline_for_creation(eval_result=ev)
        result = await pipeline.process("https://example.com")
        assert result.bookmark is not None
        # reason is set from evaluation (summary or a derived reason field)
        assert result.bookmark.reason is not None

    @pytest.mark.asyncio
    async def test_scope_passed_to_bookmark(self) -> None:
        pipeline = self._make_pipeline_for_creation()
        result = await pipeline.process("https://example.com", scope="project-x")
        assert result.bookmark is not None
        assert result.bookmark.scope == "project-x"

    @pytest.mark.asyncio
    async def test_document_id_from_ingest_result(self) -> None:
        from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415

        ingest_res = IngestResult(
            document_id="doc-abc", chunk_count=3, entity_count=1, edge_count=2, status="ok"
        )
        ev = _make_eval_result(relevance_score=0.9, worth_ingesting=True)
        pipeline = self._make_pipeline_for_creation(eval_result=ev, ingest_result=ingest_res)
        result = await pipeline.process("https://example.com")
        assert result.bookmark is not None
        assert result.bookmark.document_id == "doc-abc"


# ===========================================================================
# AC: process() cancel signal — checked between stages, returns partial results
# ===========================================================================


class TestFromAC_ProcessCancelSignal:  # noqa: N801
    """CancelSignal is checked between stages; partial results returned."""

    @pytest.mark.asyncio
    async def test_cancel_set_at_start_returns_empty_result(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline, BookmarkResult  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        pipeline = BookmarkPipeline(bookmark_store=store, evaluator=MagicMock())
        result = await pipeline.process("https://example.com", cancel=_SetSignal())
        assert isinstance(result, BookmarkResult)
        assert result.bookmark is None
        assert result.evaluation is None

    @pytest.mark.asyncio
    async def test_cancel_after_extract_before_evaluate_skips_evaluation(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        call_count = 0

        class _CancelAfterFirstCheck:
            def is_set(self) -> bool:
                nonlocal call_count
                call_count += 1
                return call_count > 1

        store = MagicMock()
        store.get_by_url.return_value = None
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        web_read = AsyncMock(return_value="content")
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            web_read_fn=web_read,
        )
        result = await pipeline.process("https://example.com", cancel=_CancelAfterFirstCheck())
        assert result.evaluation is None

    @pytest.mark.asyncio
    async def test_cancel_after_evaluate_skips_ingest(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        call_count = 0

        class _CancelAfterThirdCheck:
            def is_set(self) -> bool:
                nonlocal call_count
                call_count += 1
                return call_count > 2

        store = MagicMock()
        store.get_by_url.return_value = None
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        web_read = AsyncMock(return_value="content")
        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock()
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            ingest_pipeline=ingest_mock,
            web_read_fn=web_read,
        )
        result = await pipeline.process("https://example.com", cancel=_CancelAfterThirdCheck())
        # ingest should be skipped after evaluation
        ingest_mock.ingest_text.assert_not_called()
        assert result.ingested is False

    @pytest.mark.asyncio
    async def test_no_cancel_signal_runs_full_pipeline(self) -> None:
        """With cancel=None (default), pipeline runs all stages normally."""
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        web_read = AsyncMock(return_value="content")
        pipeline = BookmarkPipeline(
            bookmark_store=store, evaluator=evaluator, web_read_fn=web_read
        )
        result = await pipeline.process("https://example.com")
        assert result.bookmark is not None
        assert result.evaluation is not None


# ===========================================================================
# AC: process() no web_read_fn — graceful degradation when web_read_fn is None
# ===========================================================================


class TestFromAC_ProcessNoWebReadFn:  # noqa: N801
    """When web_read_fn is None, extraction is skipped and content defaults to empty."""

    @pytest.mark.asyncio
    async def test_no_web_read_fn_does_not_raise(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            web_read_fn=None,
        )
        # Must not raise
        result = await pipeline.process("https://example.com")
        assert result is not None

    @pytest.mark.asyncio
    async def test_no_web_read_fn_no_extraction_skipped_reason_or_bookmark(self) -> None:
        """Without web_read_fn, no content is fetched; result still valid."""
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            web_read_fn=None,
        )
        result = await pipeline.process("https://example.com")
        # Graceful: either returns a bookmark (eval on empty content) or skipped_reason
        assert result.bookmark is not None or result.skipped_reason is not None

    @pytest.mark.asyncio
    async def test_no_web_read_fn_does_not_ingest(self) -> None:
        """No content means ingest condition 'content truthy' is False — skip ingest."""
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        ingest_mock = MagicMock()
        ingest_mock.ingest_text = AsyncMock()
        store = MagicMock()
        store.get_by_url.return_value = None
        store.create.side_effect = lambda b: b
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval_result())
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            ingest_pipeline=ingest_mock,
            web_read_fn=None,
        )
        result = await pipeline.process("https://example.com")
        assert result.ingested is False
        ingest_mock.ingest_text.assert_not_called()
