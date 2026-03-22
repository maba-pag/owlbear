"""Tests for crawl-to-ingest pipeline integration."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.memory.knowledge.ingest import IngestResult
from owlbear.tools.browser.crawl_config import CrawlConfig
from owlbear.tools.browser.crawler import CrawlPage, CrawlResult, WebCrawler
from owlbear.tools.browser.integration import crawl_and_ingest

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_SEED = ["https://example.com"]
_CONFIG = CrawlConfig(seed_urls=_SEED, max_pages=10, delay_seconds=0)

_PAGE_A = CrawlPage(
    url="https://example.com/a",
    content="Page A content",
    title="Page A",
)
_PAGE_B = CrawlPage(
    url="https://example.com/b",
    content="Page B content",
    title="Page B",
)

_RESULT_A = IngestResult(
    document_id="aaa",
    chunk_count=2,
    entity_count=1,
    edge_count=1,
    status="indexed",
)
_RESULT_B = IngestResult(
    document_id="bbb",
    chunk_count=3,
    entity_count=0,
    edge_count=0,
    status="indexed",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_crawler(pages: list[CrawlPage], errors: list[str] | None = None) -> MagicMock:
    """Return a mock WebCrawler whose crawl() returns the given pages."""
    crawler = MagicMock(spec=WebCrawler)
    result = CrawlResult(
        pages=pages,
        total_pages=len(pages),
        errors=errors or [],
    )
    crawler.crawl = AsyncMock(return_value=result)
    return crawler


def _mock_pipeline(results: list[IngestResult]) -> MagicMock:
    """Return a mock IngestPipeline whose ingest_text() returns results in order."""
    pipeline = MagicMock()
    pipeline.ingest_text = AsyncMock(side_effect=results)
    return pipeline


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCrawlAndIngestSignature:
    """crawl_and_ingest() accepts WebCrawler, IngestPipeline, CrawlConfig."""

    @pytest.mark.asyncio
    async def test_accepts_correct_args(self) -> None:
        """Function can be called with the three expected arguments."""
        crawler = _mock_crawler([])
        pipeline = _mock_pipeline([])
        result = await crawl_and_ingest(crawler, pipeline, _CONFIG)
        assert isinstance(result, list)


class TestCrawlAndIngestHappyPath:
    """Each CrawlPage feeds into IngestPipeline.ingest_text() as text with URL metadata."""

    @pytest.mark.asyncio
    async def test_returns_one_result_per_page(self) -> None:
        crawler = _mock_crawler([_PAGE_A, _PAGE_B])
        pipeline = _mock_pipeline([_RESULT_A, _RESULT_B])

        results = await crawl_and_ingest(crawler, pipeline, _CONFIG)

        assert len(results) == 2
        assert results[0] is _RESULT_A
        assert results[1] is _RESULT_B

    @pytest.mark.asyncio
    async def test_passes_page_content_as_text(self) -> None:
        crawler = _mock_crawler([_PAGE_A])
        pipeline = _mock_pipeline([_RESULT_A])

        await crawl_and_ingest(crawler, pipeline, _CONFIG)

        call_args = pipeline.ingest_text.call_args_list[0]
        assert call_args.kwargs["text"] == "Page A content"

    @pytest.mark.asyncio
    async def test_passes_url_metadata(self) -> None:
        crawler = _mock_crawler([_PAGE_A])
        pipeline = _mock_pipeline([_RESULT_A])

        await crawl_and_ingest(crawler, pipeline, _CONFIG)

        call_args = pipeline.ingest_text.call_args_list[0]
        # metadata should include the URL
        metadata = call_args.kwargs.get("metadata") or call_args[0][1]
        assert metadata["url"] == "https://example.com/a"
        assert metadata["source_type"] == "crawl"

    @pytest.mark.asyncio
    async def test_calls_crawler_crawl_with_config(self) -> None:
        crawler = _mock_crawler([])
        pipeline = _mock_pipeline([])

        await crawl_and_ingest(crawler, pipeline, _CONFIG)

        crawler.crawl.assert_awaited_once_with(_CONFIG)


class TestCrawlAndIngestErrorHandling:
    """Errors in individual pages logged but do not halt batch."""

    @pytest.mark.asyncio
    async def test_single_page_error_does_not_halt(self) -> None:
        """If ingest_text fails on one page, others still process."""
        crawler = _mock_crawler([_PAGE_A, _PAGE_B])
        pipeline = MagicMock()
        pipeline.ingest_text = AsyncMock(
            side_effect=[RuntimeError("boom"), _RESULT_B],
        )

        results = await crawl_and_ingest(crawler, pipeline, _CONFIG)

        # Should still return one result (the successful one)
        assert len(results) == 1
        assert results[0] is _RESULT_B

    @pytest.mark.asyncio
    async def test_error_is_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """Errors for individual pages are logged."""
        crawler = _mock_crawler([_PAGE_A])
        pipeline = MagicMock()
        pipeline.ingest_text = AsyncMock(side_effect=RuntimeError("ingest boom"))

        with caplog.at_level(logging.WARNING):
            results = await crawl_and_ingest(crawler, pipeline, _CONFIG)

        assert len(results) == 0
        assert "ingest boom" in caplog.text

    @pytest.mark.asyncio
    async def test_all_pages_fail_returns_empty(self) -> None:
        """If all pages fail, return empty list."""
        crawler = _mock_crawler([_PAGE_A, _PAGE_B])
        pipeline = MagicMock()
        pipeline.ingest_text = AsyncMock(side_effect=RuntimeError("fail"))

        results = await crawl_and_ingest(crawler, pipeline, _CONFIG)

        assert results == []


class TestCrawlAndIngestEmptyResult:
    """Empty crawl result returns empty list."""

    @pytest.mark.asyncio
    async def test_no_pages_returns_empty_list(self) -> None:
        crawler = _mock_crawler([])
        pipeline = _mock_pipeline([])

        results = await crawl_and_ingest(crawler, pipeline, _CONFIG)

        assert results == []
        pipeline.ingest_text.assert_not_awaited()


class TestCrawlAndIngestMocking:
    """All deps mocked (WebCrawler.crawl, IngestPipeline.ingest_text)."""

    @pytest.mark.asyncio
    async def test_crawler_is_mocked(self) -> None:
        crawler = _mock_crawler([_PAGE_A])
        pipeline = _mock_pipeline([_RESULT_A])

        await crawl_and_ingest(crawler, pipeline, _CONFIG)

        crawler.crawl.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pipeline_is_mocked(self) -> None:
        crawler = _mock_crawler([_PAGE_A])
        pipeline = _mock_pipeline([_RESULT_A])

        await crawl_and_ingest(crawler, pipeline, _CONFIG)

        pipeline.ingest_text.assert_awaited_once()


# ===========================================================================
# cancel= parameter — cooperative cancellation seam (task #880)
# ===========================================================================


class TestFromAC_CrawlCancellation:
    """cancel= signal stops crawl_and_ingest at page-ingest boundaries."""

    @pytest.mark.asyncio
    async def test_stops_before_next_page_when_cancel_is_set_between_page_ingests(
        self,
    ) -> None:
        """crawl_and_ingest(cancel=) does not ingest the next page once cancel is set."""
        cancel = asyncio.Event()
        crawler = _mock_crawler([_PAGE_A, _PAGE_B])
        pipeline = MagicMock()

        async def ingest_and_cancel(*_args: object, **_kwargs: object) -> IngestResult:
            cancel.set()
            return _RESULT_A

        pipeline.ingest_text = AsyncMock(side_effect=ingest_and_cancel)

        results = await crawl_and_ingest(crawler, pipeline, _CONFIG, cancel=cancel)

        assert len(results) == 1
        assert results[0] is _RESULT_A
        assert pipeline.ingest_text.await_count == 1

    @pytest.mark.asyncio
    async def test_returns_only_ingest_results_produced_before_cancellation(
        self,
    ) -> None:
        """Only IngestResult values from pages processed before cancel are returned."""
        cancel = asyncio.Event()
        page_c = CrawlPage(url="https://example.com/c", content="Page C", title="Page C")
        result_c = IngestResult(
            document_id="ccc", chunk_count=1, entity_count=0, edge_count=0, status="indexed"
        )
        crawler = _mock_crawler([_PAGE_A, _PAGE_B, page_c])
        pipeline = MagicMock()
        call_count = 0

        async def ingest_with_cancel(*_args: object, **_kwargs: object) -> IngestResult:
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # 2 of 3 pages
                cancel.set()
            return [_RESULT_A, _RESULT_B, result_c][call_count - 1]

        pipeline.ingest_text = AsyncMock(side_effect=ingest_with_cancel)

        results = await crawl_and_ingest(crawler, pipeline, _CONFIG, cancel=cancel)

        assert len(results) == 2
        assert results[0] is _RESULT_A
        assert results[1] is _RESULT_B

    @pytest.mark.asyncio
    async def test_cancel_set_before_first_page_returns_empty_list(self) -> None:
        """If cancel is already set on entry, no pages are ingested."""
        cancel = asyncio.Event()
        cancel.set()
        crawler = _mock_crawler([_PAGE_A, _PAGE_B])
        pipeline = _mock_pipeline([_RESULT_A, _RESULT_B])

        results = await crawl_and_ingest(crawler, pipeline, _CONFIG, cancel=cancel)

        assert results == []
        pipeline.ingest_text.assert_not_awaited()
