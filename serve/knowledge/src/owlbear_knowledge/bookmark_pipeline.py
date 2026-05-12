"""Bookmark pipeline: evaluate and optionally ingest a URL into the knowledge store."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from owlbear_knowledge.bookmark_store import Bookmark
from owlbear_knowledge.evaluator import EvaluationResult  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from owlbear_knowledge.bookmark_store import BookmarkStore
    from owlbear_knowledge.cancellation import CancelSignal
    from owlbear_knowledge.evaluator import SourceEvaluator
    from owlbear_knowledge.ingest import IngestPipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class BookmarkResult(BaseModel):
    """Result of processing a single URL through the bookmark pipeline."""

    model_config = ConfigDict(frozen=True)

    url: str
    bookmark: Bookmark | None = None
    evaluation: EvaluationResult | None = None
    ingested: bool = False
    skipped_reason: str | None = None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class BookmarkPipeline:
    """Orchestrates dedup, extraction, evaluation, storage, and optional ingest.

    Args:
        bookmark_store: Store for persisting bookmarks.
        evaluator: Source evaluator for scoring content relevance.
        ingest_pipeline: Optional ingest pipeline; skipped when None.
        web_read_fn: Required async callable that fetches URL HTML content.
        ingest_threshold: Minimum relevance_score to trigger ingest.
    """

    def __init__(
        self,
        *,
        bookmark_store: BookmarkStore | object,
        evaluator: SourceEvaluator | object,
        ingest_pipeline: IngestPipeline | object | None = None,
        web_read_fn: Callable[[str], Awaitable[str | None]],
        ingest_threshold: float = 0.7,
    ) -> None:
        self._store = bookmark_store
        self._evaluator = evaluator
        self._ingest_pipeline = ingest_pipeline
        self._web_read_fn = web_read_fn
        self._ingest_threshold = ingest_threshold

    async def process(  # noqa: PLR0911
        self,
        url: str,
        reason: str | None = None,
        scope: str = "global",
        project_context: dict[str, object] | None = None,
        *,
        cancel: CancelSignal | None = None,
    ) -> BookmarkResult:
        """Process a URL through the bookmark pipeline.

        Stages (with cooperative cancellation between each):
            0. Dedup — return early if already bookmarked.
            1. Cancel check before extraction.
            2. Extract content via web_read_fn.
            3. Cancel check before evaluation.
            4. Evaluate relevance.
            5. Create and store bookmark.
            6. Optionally ingest if above threshold and worth_ingesting.

        Args:
            url: The URL to process.
            reason: Optional reason for bookmarking.
            scope: Logical scope for the bookmark.
            project_context: Optional project metadata forwarded to evaluator.
            cancel: Optional CancelSignal; checked between stages.

        Returns:
            BookmarkResult describing what happened.
        """
        # Stage 0 — dedup
        existing = self._store.get_by_url(url, scope)
        if existing is not None:
            return BookmarkResult(
                url=url,
                bookmark=existing,
                skipped_reason=f"Already bookmarked: {url}",
            )

        # Stage 1 — cancel check before extract
        if cancel is not None and cancel.is_set():
            return BookmarkResult(url=url)

        # Stage 2 — extract content (skip when no web_read_fn)
        content: str = ""
        if self._web_read_fn is not None:
            try:
                fetched = await self._web_read_fn(url)
            except Exception as exc:  # noqa: BLE001
                return BookmarkResult(url=url, skipped_reason=str(exc))
            if fetched is None:
                return BookmarkResult(url=url, skipped_reason="No content fetched")
            content = fetched

        # Stage 3 — cancel check before evaluate
        if cancel is not None and cancel.is_set():
            return BookmarkResult(url=url)

        # Stage 4 — evaluate
        evaluation: EvaluationResult = await self._evaluator.evaluate(
            content, project_context=project_context
        )

        # Stage 5 — cancel check before create/ingest
        if cancel is not None and cancel.is_set():
            return BookmarkResult(url=url, evaluation=evaluation)

        # Stage 6 — conditional ingest
        ingested = False
        document_id: str | None = None
        if (
            self._ingest_pipeline is not None
            and content
            and evaluation.relevance_score >= self._ingest_threshold
            and evaluation.worth_ingesting
        ):
            try:
                ingest_result = await self._ingest_pipeline.ingest_text(
                    content, metadata={"url": url}, scope=scope
                )
                ingested = True
                document_id = getattr(ingest_result, "document_id", None)
            except Exception:
                logger.exception("Ingest failed for %r", url)

        # Stage 7 — create and store bookmark
        now = datetime.now(tz=UTC).isoformat()
        title = evaluation.summary[:120] if evaluation.summary else url
        effective_reason = reason if reason is not None else evaluation.summary
        bookmark = Bookmark(
            url=url,
            title=title,
            description=evaluation.summary,
            tags=list(evaluation.tags),
            relevance_score=evaluation.relevance_score,
            reason=effective_reason,
            scope=scope,
            document_id=document_id,
            created_at=now,
            updated_at=now,
        )
        stored = self._store.create(bookmark)

        return BookmarkResult(
            url=url,
            bookmark=stored,
            evaluation=evaluation,
            ingested=ingested,
        )
