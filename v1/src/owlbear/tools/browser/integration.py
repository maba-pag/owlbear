"""Crawl-to-ingest integration — bridges WebCrawler and IngestPipeline.

Provides :func:`crawl_and_ingest`, which crawls a set of URLs and feeds
each page's content into the knowledge ingestion pipeline as raw text.
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.memory.knowledge.cancellation import CancelSignal
    from owlbear.memory.knowledge.ingest import IngestPipeline, IngestResult
    from owlbear.tools.browser.crawl_config import CrawlConfig
    from owlbear.tools.browser.crawler import WebCrawler

logger = logging.getLogger(__name__)


async def crawl_and_ingest(
    crawler: WebCrawler,
    pipeline: IngestPipeline,
    config: CrawlConfig,
    *,
    cancel: CancelSignal | None = None,
) -> list[IngestResult]:
    """Crawl URLs and ingest each page through the knowledge pipeline.

    Args:
        crawler (WebCrawler): A
            :class:`~owlbear.tools.browser.crawler.WebCrawler` instance.
        pipeline (IngestPipeline): A
            :class:`~owlbear.memory.knowledge.ingest.IngestPipeline` instance.
        config (CrawlConfig): Crawl configuration (seed URLs, limits, etc.).
        cancel (CancelSignal | None): Optional cooperative cancellation
            signal. When set, the loop stops before ingesting the next
            page. Any object satisfying :class:`CancelSignal` (e.g.
            :class:`asyncio.Event`) is accepted.

    Returns:
        list[IngestResult]: One result per successfully ingested page.
            Pages that fail during ingestion are logged and skipped.
    """
    crawl_result = await crawler.crawl(config)
    results: list[IngestResult] = []

    for page in crawl_result.pages:
        if cancel is not None and cancel.is_set():
            break
        metadata = {
            "url": page.url,
            "title": page.title,
            "source_type": "crawl",
        }
        try:
            ingest_result = await _ingest_page(
                pipeline,
                text=page.content,
                metadata=metadata,
                cancel=cancel,
            )
            results.append(ingest_result)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Ingest failed for crawled page %s",
                page.url,
                exc_info=True,
            )

    return results


async def _ingest_page(
    pipeline: IngestPipeline,
    *,
    text: str,
    metadata: dict[str, str],
    cancel: CancelSignal | None,
) -> IngestResult:
    """Call ingest_text for one page and pass cancel= when supported."""
    if cancel is None or not _supports_cancel_kwarg(pipeline.ingest_text):
        return await pipeline.ingest_text(text=text, metadata=metadata)

    return await pipeline.ingest_text(text=text, metadata=metadata, cancel=cancel)


def _supports_cancel_kwarg(callable_obj: object) -> bool:
    """Return True when *callable_obj* supports ``cancel=``."""
    side_effect = getattr(callable_obj, "side_effect", None)
    target = side_effect if callable(side_effect) else callable_obj

    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return True

    for param in signature.parameters.values():
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            return True
        if param.name == "cancel":
            return True
    return False
