"""BookmarkPipeline — orchestrator: extract, evaluate, ingest, store.

Orchestrates the full bookmark flow:
1. Dedup check (URL already bookmarked in this scope?)
2. Extract content via ``web_read_fn(url)``
3. Evaluate relevance via :class:`SourceEvaluator`
4. Conditionally ingest into the knowledge base
5. Store the bookmark via :class:`BookmarkStore`
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from owlbear.memory.knowledge.bookmark import Bookmark
from owlbear.memory.knowledge.evaluator import EvaluationResult  # noqa: TC001 — Pydantic runtime

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from owlbear.memory.knowledge.bookmark import BookmarkStore
    from owlbear.memory.knowledge.evaluator import SourceEvaluator
    from owlbear.memory.knowledge.ingest import IngestPipeline

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class BookmarkResult(BaseModel):
    """Outcome of a :meth:`BookmarkPipeline.process` call."""

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
    """Orchestrate URL → extract → evaluate → ingest → bookmark.

    Parameters
    ----------
    bookmark_store:
        CRUD façade for the ``bookmarks`` table.
    evaluator:
        LLM-based source relevance evaluator.
    ingest_pipeline:
        Optional knowledge ingest pipeline.  When ``None``, ingestion is
        skipped even if the evaluation score is high.
    web_read_fn:
        Async callable ``(url) -> str | None``.  Defaults to a simple
        httpx + trafilatura extraction if not provided.
    ingest_threshold:
        Minimum ``relevance_score`` required to trigger ingestion
        (also requires ``worth_ingesting=True``).
    """

    def __init__(
        self,
        bookmark_store: BookmarkStore,
        evaluator: SourceEvaluator,
        ingest_pipeline: IngestPipeline | None = None,
        web_read_fn: Callable[[str], Awaitable[str | None]] | None = None,
        ingest_threshold: float = 0.7,
    ) -> None:
        self._store = bookmark_store
        self._evaluator = evaluator
        self._ingest = ingest_pipeline
        self._web_read = web_read_fn or _default_web_read
        self._threshold = ingest_threshold

    # -- public API ----------------------------------------------------------

    async def process(
        self,
        url: str,
        reason: str | None = None,
        scope: str = "global",
        project_context: dict[str, Any] | None = None,
    ) -> BookmarkResult:
        """Run the full bookmark pipeline for *url*.

        Returns
        -------
        BookmarkResult
            Contains the stored bookmark, evaluation, ingestion flag, and
            any skip reason.
        """
        # 1. Dedup check
        existing = self._store.get_by_url(url, scope)
        if existing is not None:
            return BookmarkResult(
                url=url,
                bookmark=existing,
                skipped_reason="Already bookmarked in this scope",
            )

        # 2. Extract content
        try:
            content = await self._web_read(url)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to read %s", url, exc_info=True)
            return BookmarkResult(
                url=url,
                skipped_reason=f"Failed to extract content from {url}",
            )

        # 3. Evaluate relevance
        evaluation = await self._evaluator.evaluate(content or "", project_context)

        # 4. Conditionally ingest
        ingested = False
        document_id: str | None = None
        should_ingest = (
            self._ingest is not None
            and content
            and evaluation.relevance_score >= self._threshold
            and evaluation.worth_ingesting
        )
        if should_ingest:
            assert self._ingest is not None  # for type narrowing
            assert content is not None  # guarded by `content` truthiness above
            result = await self._ingest.ingest_text(content, metadata={"url": url}, scope=scope)
            ingested = not result.skipped
            if ingested:
                document_id = result.document_id

        # 5. Create bookmark
        now = datetime.now(tz=UTC).isoformat()
        bookmark = Bookmark(
            url=url,
            title=evaluation.summary[:120] if evaluation.summary else url,
            description=evaluation.summary or None,
            tags=list(evaluation.tags),
            relevance_score=evaluation.relevance_score,
            reason=reason,
            scope=scope,
            document_id=document_id,
            created_at=now,
            updated_at=now,
        )
        self._store.create(bookmark)

        return BookmarkResult(
            url=url,
            bookmark=bookmark,
            evaluation=evaluation,
            ingested=ingested,
        )


# ---------------------------------------------------------------------------
# Default web reader
# ---------------------------------------------------------------------------


async def _default_web_read(url: str) -> str | None:
    """Fetch *url* with httpx and extract text with trafilatura.

    This is the fallback used when no ``web_read_fn`` is provided to
    :class:`BookmarkPipeline`.  Retries transient HTTP errors.
    """
    import httpx  # noqa: PLC0415
    import trafilatura  # noqa: PLC0415

    from owlbear.core.retry import TRANSIENT_RETRY  # noqa: PLC0415

    @TRANSIENT_RETRY
    async def _fetch(target: str) -> httpx.Response:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(target)
            resp.raise_for_status()
        return resp

    resp = await _fetch(url)
    return trafilatura.extract(resp.text)
