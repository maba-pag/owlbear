"""Crawl-to-ingest integration — bridges WebCrawler and IngestPipeline.

Provides :func:`crawl_and_ingest`, which crawls a set of URLs and feeds
each page's content into the knowledge ingestion pipeline as raw text.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.memory.knowledge.ingest import IngestPipeline, IngestResult
    from owlbear.tools.browser.crawl_config import CrawlConfig
    from owlbear.tools.browser.crawler import WebCrawler

logger = logging.getLogger(__name__)


async def crawl_and_ingest(
    crawler: WebCrawler,
    pipeline: IngestPipeline,
    config: CrawlConfig,
) -> list[IngestResult]:
    """Crawl URLs and ingest each page through the knowledge pipeline.

    Parameters
    ----------
    crawler:
        A :class:`~owlbear.tools.browser.crawler.WebCrawler` instance.
    pipeline:
        A :class:`~owlbear.memory.knowledge.ingest.IngestPipeline` instance.
    config:
        Crawl configuration (seed URLs, limits, etc.).

    Returns
    -------
    list[IngestResult]
        One result per successfully ingested page.  Pages that fail during
        ingestion are logged and skipped.
    """
    crawl_result = await crawler.crawl(config)
    results: list[IngestResult] = []

    for page in crawl_result.pages:
        metadata = {
            "url": page.url,
            "title": page.title,
            "source_type": "crawl",
        }
        try:
            ingest_result = await pipeline.ingest_text(
                text=page.content,
                metadata=metadata,
            )
            results.append(ingest_result)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Ingest failed for crawled page %s",
                page.url,
                exc_info=True,
            )

    return results
