"""Tests for BookmarkPipeline — orchestrator: extract, evaluate, ingest, store.

TDD tests for tasks #400 and #404.  All external dependencies (web_read,
SourceEvaluator, IngestPipeline, BookmarkStore) are mocked.
"""

from __future__ import annotations

import asyncio
import builtins
import sqlite3
import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.memory.knowledge.bookmark import Bookmark, BookmarkStore
from owlbear.memory.knowledge.bookmark_pipeline import (
    BookmarkPipeline,
    BookmarkResult,
    _default_web_read,
)
from owlbear.memory.knowledge.evaluator import EvaluationResult
from owlbear.memory.knowledge.ingest import IngestResult

# ---------------------------------------------------------------------------
# DDL — standalone bookmarks table for unit tests
# ---------------------------------------------------------------------------

_CREATE_BOOKMARKS = """\
CREATE TABLE IF NOT EXISTS bookmarks (
    id             TEXT PRIMARY KEY,
    url            TEXT NOT NULL,
    title          TEXT NOT NULL,
    description    TEXT,
    tags           TEXT NOT NULL DEFAULT '[]',
    relevance_score REAL NOT NULL DEFAULT 0.0,
    reason         TEXT,
    scope          TEXT NOT NULL DEFAULT 'global',
    document_id    TEXT,
    content_hash   TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    UNIQUE(url, scope)
)
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.now(tz=UTC).isoformat()

SAMPLE_URL = "https://example.com/article"
SAMPLE_CONTENT = "This is a great article about Python async patterns."
SAMPLE_REASON = "Relevant to async agent work"

SAMPLE_PROJECT_CONTEXT = {
    "name": "OwlBear",
    "description": "AI development system",
    "goals": ["autonomous coding", "knowledge management"],
}


def _high_score_result() -> EvaluationResult:
    """Score above default threshold (0.7), worth ingesting."""
    return EvaluationResult(
        relevance_score=0.85,
        tags=["python", "async"],
        summary="Great async article.",
        worth_ingesting=True,
    )


def _low_score_result() -> EvaluationResult:
    """Score below default threshold (0.7), not worth ingesting."""
    return EvaluationResult(
        relevance_score=0.3,
        tags=["misc"],
        summary="Low quality content.",
        worth_ingesting=False,
    )


def _above_threshold_not_worth() -> EvaluationResult:
    """Score above threshold but worth_ingesting=False."""
    return EvaluationResult(
        relevance_score=0.9,
        tags=["python"],
        summary="High score but not worth ingesting.",
        worth_ingesting=False,
    )


def _mock_ingest_result() -> IngestResult:
    return IngestResult(
        document_id="doc-123",
        chunk_count=5,
        entity_count=3,
        edge_count=2,
        status="completed",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def conn() -> sqlite3.Connection:
    """In-memory SQLite with bookmarks table."""
    c = sqlite3.connect(":memory:")
    c.execute(_CREATE_BOOKMARKS)
    c.commit()
    return c


@pytest.fixture
def store(conn: sqlite3.Connection) -> BookmarkStore:
    return BookmarkStore(conn)


@pytest.fixture
def mock_evaluator() -> AsyncMock:
    """Mock SourceEvaluator with a high-score default."""
    evaluator = AsyncMock()
    evaluator.evaluate = AsyncMock(return_value=_high_score_result())
    return evaluator


@pytest.fixture
def mock_ingest() -> AsyncMock:
    """Mock IngestPipeline."""
    ingest = AsyncMock()
    ingest.ingest_text = AsyncMock(return_value=_mock_ingest_result())
    return ingest


@pytest.fixture
def mock_web_read() -> AsyncMock:
    """Mock web_read_fn returning sample content."""
    return AsyncMock(return_value=SAMPLE_CONTENT)


@pytest.fixture
def pipeline(
    store: BookmarkStore,
    mock_evaluator: AsyncMock,
    mock_ingest: AsyncMock,
    mock_web_read: AsyncMock,
) -> BookmarkPipeline:
    """Fully-mocked BookmarkPipeline."""
    return BookmarkPipeline(
        bookmark_store=store,
        evaluator=mock_evaluator,
        ingest_pipeline=mock_ingest,
        web_read_fn=mock_web_read,
    )


# ===========================================================================
# BookmarkResult model tests
# ===========================================================================


class TestBookmarkResult:
    """BookmarkResult dataclass basic validation."""

    def test_create_with_all_fields(self) -> None:
        result = BookmarkResult(
            url=SAMPLE_URL,
            bookmark=None,
            evaluation=None,
            ingested=False,
            skipped_reason="duplicate",
        )
        assert result.url == SAMPLE_URL
        assert result.skipped_reason == "duplicate"
        assert result.ingested is False

    def test_defaults(self) -> None:
        result = BookmarkResult(url=SAMPLE_URL)
        assert result.bookmark is None
        assert result.evaluation is None
        assert result.ingested is False
        assert result.skipped_reason is None


# ===========================================================================
# Full pipeline — happy path
# ===========================================================================


class TestBookmarkPipelineHappyPath:
    """Full pipeline: web_read -> evaluate -> ingest -> bookmark."""

    @pytest.mark.asyncio
    async def test_full_pipeline_high_score(
        self,
        pipeline: BookmarkPipeline,
        mock_web_read: AsyncMock,
        mock_evaluator: AsyncMock,
        mock_ingest: AsyncMock,
        store: BookmarkStore,
    ) -> None:
        """High-score content is evaluated, ingested, and bookmarked."""
        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        # web_read was called
        mock_web_read.assert_awaited_once_with(SAMPLE_URL)

        # evaluator was called with extracted content
        mock_evaluator.evaluate.assert_awaited_once_with(SAMPLE_CONTENT, SAMPLE_PROJECT_CONTEXT)

        # ingest was called (high score + worth_ingesting)
        mock_ingest.ingest_text.assert_awaited_once()

        # bookmark was stored
        assert result.bookmark is not None
        assert result.bookmark.url == SAMPLE_URL
        assert result.bookmark.relevance_score == 0.85
        assert result.ingested is True
        assert result.skipped_reason is None
        assert result.evaluation is not None
        assert result.evaluation.relevance_score == 0.85

        # verify bookmark is in the store
        stored = store.get_by_url(SAMPLE_URL)
        assert stored is not None
        assert stored.url == SAMPLE_URL

    @pytest.mark.asyncio
    async def test_bookmark_has_evaluation_metadata(
        self,
        pipeline: BookmarkPipeline,
    ) -> None:
        """Bookmark captures tags, summary, and reason from evaluation."""
        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        assert result.bookmark is not None
        assert result.bookmark.reason == SAMPLE_REASON
        assert result.bookmark.tags == ["python", "async"]
        assert result.bookmark.description == "Great async article."

    @pytest.mark.asyncio
    async def test_custom_scope(
        self,
        pipeline: BookmarkPipeline,
        store: BookmarkStore,
    ) -> None:
        """Pipeline respects the scope parameter."""
        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            scope="project-x",
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        assert result.bookmark is not None
        assert result.bookmark.scope == "project-x"

        stored = store.get_by_url(SAMPLE_URL, scope="project-x")
        assert stored is not None


# ===========================================================================
# Dedup tests
# ===========================================================================


class TestBookmarkPipelineDedup:
    """Duplicate URL+scope is skipped early."""

    @pytest.mark.asyncio
    async def test_duplicate_url_skipped(
        self,
        pipeline: BookmarkPipeline,
        store: BookmarkStore,
        mock_web_read: AsyncMock,
        mock_evaluator: AsyncMock,
    ) -> None:
        """If URL already bookmarked in same scope, skip entirely."""
        # Pre-insert a bookmark
        existing = Bookmark(
            url=SAMPLE_URL,
            title="Existing",
            scope="global",
            created_at=NOW,
            updated_at=NOW,
        )
        store.create(existing)

        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        assert result.skipped_reason is not None
        reason_lower = result.skipped_reason.lower()
        assert "duplicate" in reason_lower or "already" in reason_lower
        assert result.ingested is False
        assert result.evaluation is None

        # web_read and evaluator should NOT have been called
        mock_web_read.assert_not_awaited()
        mock_evaluator.evaluate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_same_url_different_scope_not_dedup(
        self,
        pipeline: BookmarkPipeline,
        store: BookmarkStore,
    ) -> None:
        """Same URL in different scope is NOT a duplicate."""
        existing = Bookmark(
            url=SAMPLE_URL,
            title="Existing",
            scope="other-scope",
            created_at=NOW,
            updated_at=NOW,
        )
        store.create(existing)

        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            scope="global",
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        # Not skipped — different scope
        assert result.skipped_reason is None
        assert result.bookmark is not None


# ===========================================================================
# Ingest threshold tests
# ===========================================================================


class TestBookmarkPipelineThreshold:
    """Ingest threshold logic: low score skips ingest, high score triggers it."""

    @pytest.mark.asyncio
    async def test_low_score_skips_ingest(
        self,
        pipeline: BookmarkPipeline,
        mock_evaluator: AsyncMock,
        mock_ingest: AsyncMock,
    ) -> None:
        """Score below threshold => bookmark stored but ingest skipped."""
        mock_evaluator.evaluate = AsyncMock(return_value=_low_score_result())

        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        # Bookmark still created
        assert result.bookmark is not None
        assert result.bookmark.relevance_score == 0.3

        # Ingest NOT called
        mock_ingest.ingest_text.assert_not_awaited()
        assert result.ingested is False

        # Evaluation still recorded
        assert result.evaluation is not None
        assert result.evaluation.relevance_score == 0.3

    @pytest.mark.asyncio
    async def test_high_score_but_not_worth_ingesting(
        self,
        pipeline: BookmarkPipeline,
        mock_evaluator: AsyncMock,
        mock_ingest: AsyncMock,
    ) -> None:
        """Score above threshold but worth_ingesting=False => no ingest."""
        mock_evaluator.evaluate = AsyncMock(return_value=_above_threshold_not_worth())

        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        mock_ingest.ingest_text.assert_not_awaited()
        assert result.ingested is False
        assert result.bookmark is not None

    @pytest.mark.asyncio
    async def test_custom_threshold(
        self,
        store: BookmarkStore,
        mock_evaluator: AsyncMock,
        mock_ingest: AsyncMock,
        mock_web_read: AsyncMock,
    ) -> None:
        """Custom threshold=0.5 allows lower scores to trigger ingest."""
        mock_evaluator.evaluate = AsyncMock(
            return_value=EvaluationResult(
                relevance_score=0.6,
                tags=["ok"],
                summary="Decent content.",
                worth_ingesting=True,
            )
        )

        pipe = BookmarkPipeline(
            bookmark_store=store,
            evaluator=mock_evaluator,
            ingest_pipeline=mock_ingest,
            web_read_fn=mock_web_read,
            ingest_threshold=0.5,
        )

        result = await pipe.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        # 0.6 >= 0.5 and worth_ingesting=True => ingest called
        mock_ingest.ingest_text.assert_awaited_once()
        assert result.ingested is True


# ===========================================================================
# No ingest pipeline
# ===========================================================================


class TestBookmarkPipelineNoIngest:
    """Pipeline works without an ingest pipeline (ingest_pipeline=None)."""

    @pytest.mark.asyncio
    async def test_no_ingest_pipeline_still_bookmarks(
        self,
        store: BookmarkStore,
        mock_evaluator: AsyncMock,
        mock_web_read: AsyncMock,
    ) -> None:
        """When ingest_pipeline is None, bookmark is created but no ingest."""
        pipe = BookmarkPipeline(
            bookmark_store=store,
            evaluator=mock_evaluator,
            ingest_pipeline=None,
            web_read_fn=mock_web_read,
        )

        result = await pipe.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        assert result.bookmark is not None
        assert result.ingested is False
        assert result.evaluation is not None


# ===========================================================================
# Edge cases
# ===========================================================================


class TestBookmarkPipelineEdgeCases:
    """Edge cases: empty content, web_read failure."""

    @pytest.mark.asyncio
    async def test_web_read_returns_empty(
        self,
        pipeline: BookmarkPipeline,
        mock_web_read: AsyncMock,
        mock_ingest: AsyncMock,
    ) -> None:
        """Empty content from web_read => bookmark with zero score, no ingest."""
        mock_web_read.return_value = ""

        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        # Should still create a bookmark but with low/zero score
        assert result.bookmark is not None
        assert result.ingested is False
        mock_ingest.ingest_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_web_read_returns_none(
        self,
        pipeline: BookmarkPipeline,
        mock_web_read: AsyncMock,
        mock_ingest: AsyncMock,
    ) -> None:
        """None content from web_read => bookmark with zero score, no ingest."""
        mock_web_read.return_value = None

        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        assert result.bookmark is not None
        assert result.ingested is False
        mock_ingest.ingest_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_web_read_raises(
        self,
        pipeline: BookmarkPipeline,
        mock_web_read: AsyncMock,
    ) -> None:
        """web_read failure => BookmarkResult with skipped_reason."""
        mock_web_read.side_effect = RuntimeError("Network error")

        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        assert result.skipped_reason is not None
        assert result.bookmark is None
        assert result.ingested is False

    @pytest.mark.asyncio
    async def test_no_reason(
        self,
        pipeline: BookmarkPipeline,
    ) -> None:
        """Pipeline works with reason=None."""
        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=None,
            project_context=SAMPLE_PROJECT_CONTEXT,
        )

        assert result.bookmark is not None
        assert result.bookmark.reason is None

    @pytest.mark.asyncio
    async def test_no_project_context(
        self,
        pipeline: BookmarkPipeline,
    ) -> None:
        """Pipeline works with project_context=None (evaluator returns default)."""
        result = await pipeline.process(
            url=SAMPLE_URL,
            reason=SAMPLE_REASON,
            project_context=None,
        )

        assert result.evaluation is not None
        assert result.bookmark is not None


# ===========================================================================
# Import guard — _default_web_read trafilatura
# ===========================================================================


class TestDefaultWebReadImportGuard:
    """_default_web_read raises ImportError with install hint when trafilatura missing."""

    @pytest.mark.asyncio
    async def test_raises_import_error_when_trafilatura_unavailable(self) -> None:
        """Calling _default_web_read without trafilatura raises ImportError."""
        _real_import = builtins.__import__

        def _deny_trafilatura(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return _real_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=_deny_trafilatura),
            pytest.raises(ImportError, match=r"uv pip install 'owlbear\[search\]'"),
        ):
            await _default_web_read("https://example.com")

    @pytest.mark.asyncio
    async def test_error_message_contains_install_command(self) -> None:
        """The ImportError message includes the exact install command."""
        _real_import = builtins.__import__

        def _deny_trafilatura(name: str, *args: object, **kwargs: object) -> object:
            if name == "trafilatura":
                msg = f"No module named '{name}'"
                raise ModuleNotFoundError(msg)
            return _real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_deny_trafilatura):
            with pytest.raises(ImportError) as exc_info:
                await _default_web_read("https://example.com")
            assert "uv pip install 'owlbear[search]'" in str(exc_info.value)


# ===========================================================================
# _default_web_read — fetch & extract (happy path, HTTP errors)
# ===========================================================================


class TestDefaultWebReadFetch:
    """Tests for _default_web_read: successful fetch+extract and HTTP errors."""

    @pytest.mark.asyncio
    async def test_happy_path_returns_extracted_text(self) -> None:
        """Successful HTTP GET + trafilatura extract returns text content."""
        mock_resp = MagicMock()
        mock_resp.text = "<html><body>Python async patterns</body></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract = MagicMock(return_value="Python async patterns")

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict(sys.modules, {"trafilatura": mock_trafilatura}),
            patch("owlbear.core.retry.TRANSIENT_RETRY", lambda fn: fn),
        ):
            result = await _default_web_read("https://example.com/article")

        assert result == "Python async patterns"
        mock_client.get.assert_awaited_once_with("https://example.com/article")
        mock_resp.raise_for_status.assert_called_once()
        mock_trafilatura.extract.assert_called_once_with(mock_resp.text)

    @pytest.mark.asyncio
    async def test_http_error_propagates(self) -> None:
        """HTTPStatusError from raise_for_status propagates to caller."""
        import httpx

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Internal Server Error",
                request=httpx.Request("GET", "https://example.com/fail"),
                response=httpx.Response(500),
            ),
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict(sys.modules, {"trafilatura": mock_trafilatura}),
            patch("owlbear.core.retry.TRANSIENT_RETRY", lambda fn: fn),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await _default_web_read("https://example.com/fail")

    @pytest.mark.asyncio
    async def test_extract_returns_none(self) -> None:
        """When trafilatura.extract returns None, function returns None."""
        mock_resp = MagicMock()
        mock_resp.text = ""
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract = MagicMock(return_value=None)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch.dict(sys.modules, {"trafilatura": mock_trafilatura}),
            patch("owlbear.core.retry.TRANSIENT_RETRY", lambda fn: fn),
        ):
            result = await _default_web_read("https://example.com/empty")

        assert result is None


# ===========================================================================
# cancel= parameter — cooperative cancellation seam (task #880)
# ===========================================================================


class TestFromAC_BookmarkCancellation:
    """cancel= checks at each stage boundary; earlier-stage state is preserved on exit."""

    @pytest.mark.asyncio
    async def test_cancel_before_extract_leaves_evaluation_and_bookmark_unset(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """Cancel signal pre-set on entry to process() → no web_read, evaluation, or bookmark."""
        cancel = asyncio.Event()
        cancel.set()

        mock_web_read = AsyncMock(return_value=SAMPLE_CONTENT)
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(return_value=_high_score_result())

        bp = BookmarkPipeline(
            bookmark_store=BookmarkStore(conn),
            evaluator=mock_evaluator,
            ingest_pipeline=AsyncMock(),
            web_read_fn=mock_web_read,
        )

        result = await bp.process(SAMPLE_URL, cancel=cancel)

        assert result.evaluation is None
        assert result.bookmark is None
        mock_web_read.assert_not_awaited()
        mock_evaluator.evaluate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cancel_before_evaluate_leaves_evaluation_and_bookmark_unset(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """Cancel fires during web_read (before evaluate is called) → no evaluation or bookmark."""
        cancel = asyncio.Event()

        async def web_read_and_cancel(_url: str) -> str:
            cancel.set()  # fires between extract and evaluate
            return SAMPLE_CONTENT

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(return_value=_high_score_result())

        bp = BookmarkPipeline(
            bookmark_store=BookmarkStore(conn),
            evaluator=mock_evaluator,
            ingest_pipeline=AsyncMock(),
            web_read_fn=web_read_and_cancel,
        )

        result = await bp.process(SAMPLE_URL, cancel=cancel)

        assert result.evaluation is None
        assert result.bookmark is None
        mock_evaluator.evaluate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cancel_before_ingest_preserves_evaluation_and_skips_ingest_and_store(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """Cancel fires after evaluate → evaluation is preserved; ingest and store are skipped."""
        cancel = asyncio.Event()

        async def evaluate_and_cancel(_content: str, _context: object) -> EvaluationResult:
            cancel.set()  # fires between evaluate and ingest
            return _high_score_result()

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = evaluate_and_cancel

        mock_ingest = MagicMock()
        mock_ingest.ingest_text = AsyncMock(return_value=_mock_ingest_result())

        bp = BookmarkPipeline(
            bookmark_store=BookmarkStore(conn),
            evaluator=mock_evaluator,
            ingest_pipeline=mock_ingest,
            web_read_fn=AsyncMock(return_value=SAMPLE_CONTENT),
        )

        result = await bp.process(SAMPLE_URL, cancel=cancel)

        assert result.evaluation is not None
        assert result.evaluation.relevance_score == 0.85
        assert result.ingested is False
        assert result.bookmark is None
        mock_ingest.ingest_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cancel_before_store_leaves_bookmark_unset_preserving_earlier_stage_state(
        self,
        conn: sqlite3.Connection,
    ) -> None:
        """Cancel fires after ingest → earlier-stage state preserved; bookmark is None."""
        cancel = asyncio.Event()

        async def ingest_and_cancel(*_args: object, **_kwargs: object) -> IngestResult:
            cancel.set()  # fires between ingest and store
            return _mock_ingest_result()

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(return_value=_high_score_result())

        mock_ingest = MagicMock()
        mock_ingest.ingest_text = ingest_and_cancel

        bp = BookmarkPipeline(
            bookmark_store=BookmarkStore(conn),
            evaluator=mock_evaluator,
            ingest_pipeline=mock_ingest,
            web_read_fn=AsyncMock(return_value=SAMPLE_CONTENT),
        )

        result = await bp.process(SAMPLE_URL, cancel=cancel)

        assert result.evaluation is not None
        assert result.ingested is True  # ingest completed before cancel check for store
        assert result.bookmark is None
