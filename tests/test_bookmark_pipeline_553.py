"""RED-phase tests for BookmarkPipeline AC deviations (#553).

Covers the 4 contract requirements NOT tested in #552:
1. dedup calls get_by_url(url, scope) — not get_by_url(url)
2. ingest_text called with metadata={url: url}, scope=scope kwargs
3. Bookmark.description set to evaluation.summary
4. cancel parameter is keyword-only (after * in signature)
"""

from __future__ import annotations

import inspect
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


def _make_eval(
    *,
    relevance_score: float = 0.9,
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


def _make_store(*, existing: Any = None) -> MagicMock:
    store = MagicMock()
    store.get_by_url.return_value = existing
    store.create.side_effect = lambda b: b
    return store


def _make_ingest_mock(*, document_id: str = "doc-1") -> MagicMock:
    from owlbear_knowledge.ingest import IngestResult  # noqa: PLC0415

    ingest_mock = MagicMock()
    ingest_mock.ingest_text = AsyncMock(
        return_value=IngestResult(
            document_id=document_id,
            chunk_count=2,
            entity_count=1,
            edge_count=0,
            status="ok",
        )
    )
    return ingest_mock


class _SetSignal:
    def is_set(self) -> bool:
        return True


class _ClearSignal:
    def is_set(self) -> bool:
        return False


# ===========================================================================
# AC: Stage 1 dedup calls get_by_url(url, scope) — bug: current omits scope
# ===========================================================================


class TestFromAC_DedupeScope:  # noqa: N801
    """BookmarkPipeline.process() must call store.get_by_url(url, scope)."""

    def _make_pipeline(self, *, web_content: str = "content") -> tuple[Any, MagicMock]:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = _make_store()
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval())
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            web_read_fn=AsyncMock(return_value=web_content),
        )
        return pipeline, store

    @pytest.mark.asyncio
    async def test_dedup_called_with_scope_default_global(self) -> None:
        """Stage 1 dedup passes scope='global' (default) to get_by_url."""
        pipeline, store = self._make_pipeline()
        await pipeline.process("https://example.com")
        store.get_by_url.assert_called_with("https://example.com", "global")

    @pytest.mark.asyncio
    async def test_dedup_called_with_custom_scope(self) -> None:
        """Stage 1 dedup forwards the scope argument to get_by_url."""
        pipeline, store = self._make_pipeline()
        await pipeline.process("https://example.com", scope="team")
        store.get_by_url.assert_called_with("https://example.com", "team")

    @pytest.mark.asyncio
    async def test_dedup_scope_not_hardcoded(self) -> None:
        """Two calls with different scopes both forward the correct scope."""
        pipeline, store = self._make_pipeline()
        await pipeline.process("https://example.com", scope="alpha")
        await pipeline.process("https://example.com", scope="beta")
        store.get_by_url.assert_any_call("https://example.com", "alpha")
        store.get_by_url.assert_any_call("https://example.com", "beta")


# ===========================================================================
# AC: Stage 4 ingest_text with metadata={url: url}, scope=scope — bug: missing kwargs
# ===========================================================================


class TestFromAC_IngestKwargs:  # noqa: N801
    """ingest_pipeline.ingest_text must be called with metadata and scope kwargs."""

    def _make_pipeline_with_ingest(
        self,
        *,
        eval_result: EvaluationResult | None = None,
        web_content: str = "page content",
        threshold: float = 0.7,
    ) -> tuple[Any, MagicMock, str]:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = _make_store()
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=eval_result or _make_eval())
        ingest_mock = _make_ingest_mock()
        url = "https://example.com"
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            ingest_pipeline=ingest_mock,
            web_read_fn=AsyncMock(return_value=web_content),
            ingest_threshold=threshold,
        )
        return pipeline, ingest_mock, url

    @pytest.mark.asyncio
    async def test_ingest_text_called_with_url_in_metadata(self) -> None:
        """ingest_text must receive metadata={'url': url}."""
        pipeline, ingest_mock, url = self._make_pipeline_with_ingest()
        await pipeline.process(url)
        call_kwargs = ingest_mock.ingest_text.call_args.kwargs
        assert call_kwargs.get("metadata") == {"url": url}

    @pytest.mark.asyncio
    async def test_ingest_text_called_with_scope_kwarg_default(self) -> None:
        """ingest_text must receive scope='global' by default."""
        pipeline, ingest_mock, url = self._make_pipeline_with_ingest()
        await pipeline.process(url, scope="global")
        call_kwargs = ingest_mock.ingest_text.call_args.kwargs
        assert call_kwargs.get("scope") == "global"

    @pytest.mark.asyncio
    async def test_ingest_text_called_with_custom_scope(self) -> None:
        """ingest_text must forward the scope arg passed to process()."""
        pipeline, ingest_mock, url = self._make_pipeline_with_ingest()
        await pipeline.process(url, scope="team")
        call_kwargs = ingest_mock.ingest_text.call_args.kwargs
        assert call_kwargs.get("scope") == "team"

    @pytest.mark.asyncio
    async def test_ingest_text_full_call_signature(self) -> None:
        """ingest_text(content, metadata={'url': url}, scope=scope) — all three."""
        pipeline, ingest_mock, url = self._make_pipeline_with_ingest(web_content="page content")
        await pipeline.process(url, scope="project-x")
        ingest_mock.ingest_text.assert_called_once_with(
            "page content",
            metadata={"url": url},
            scope="project-x",
        )


# ===========================================================================
# AC: Stage 5 Bookmark created with description=evaluation.summary — bug: missing
# ===========================================================================


class TestFromAC_BookmarkDescription:  # noqa: N801
    """Bookmark.description must equal evaluation.summary."""

    def _make_pipeline_for_bookmark(
        self,
        *,
        summary: str = "A useful reference for the project.",
    ) -> tuple[Any, str]:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = _make_store()
        ev = _make_eval(summary=summary)
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=ev)
        url = "https://example.com"
        pipeline = BookmarkPipeline(
            bookmark_store=store,
            evaluator=evaluator,
            web_read_fn=AsyncMock(return_value="extracted content"),
        )
        return pipeline, url

    @pytest.mark.asyncio
    async def test_bookmark_description_equals_evaluation_summary(self) -> None:
        """Bookmark.description must be set to evaluation.summary."""
        pipeline, url = self._make_pipeline_for_bookmark(summary="A useful reference for the project.")
        result = await pipeline.process(url)
        assert result.bookmark is not None
        assert result.bookmark.description == "A useful reference for the project."

    @pytest.mark.asyncio
    async def test_bookmark_description_full_not_truncated(self) -> None:
        """description is the full summary, not the truncated title[:120]."""
        long_summary = "B" * 200
        pipeline, url = self._make_pipeline_for_bookmark(summary=long_summary)
        result = await pipeline.process(url)
        assert result.bookmark is not None
        # description must be full 200-char summary, not the 120-char title
        assert result.bookmark.description == long_summary
        assert len(result.bookmark.description) == 200  # type: ignore[arg-type]

    @pytest.mark.asyncio
    async def test_bookmark_description_not_none(self) -> None:
        """description must not be None when evaluation.summary is non-empty."""
        pipeline, url = self._make_pipeline_for_bookmark(summary="Some summary text.")
        result = await pipeline.process(url)
        assert result.bookmark is not None
        assert result.bookmark.description is not None


# ===========================================================================
# AC: cancel parameter is keyword-only (*, cancel=None) — bug: currently positional
# ===========================================================================


class TestFromAC_CancelKeywordOnly:  # noqa: N801
    """process() cancel parameter must be keyword-only (declared after *)."""

    def test_cancel_param_is_keyword_only_in_signature(self) -> None:
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        sig = inspect.signature(BookmarkPipeline.process)
        param = sig.parameters["cancel"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY

    @pytest.mark.asyncio
    async def test_cancel_positional_arg_raises_type_error(self) -> None:
        """Passing cancel as a positional argument must raise TypeError."""
        from owlbear_knowledge.bookmark_pipeline import BookmarkPipeline  # noqa: PLC0415

        store = _make_store()
        evaluator = MagicMock()
        evaluator.evaluate = AsyncMock(return_value=_make_eval())
        pipeline = BookmarkPipeline(bookmark_store=store, evaluator=evaluator)
        with pytest.raises(TypeError):
            # After fix: process(url, None, "global", None, signal) raises TypeError
            # because cancel is keyword-only; calling with 5 positional args fails.
            await pipeline.process("https://example.com", None, "global", None, _ClearSignal())
