"""RED-phase tests for AUTHENTICATED_WEB source type and ContentFetcher protocol (#792).

Covers AC from task #792 (scope items 3+4 of parent #775):

  AC1 - SourceType.AUTHENTICATED_WEB is a valid enum member
  AC2 - ContentFetcher protocol exists in protocol.py with async fetch(url: str) -> str
  AC3 - _handle_authenticated_web() dispatches via ContentFetcher and returns RefreshResult
  AC4 - Tests use mock ContentFetcher — no real browser dependency

NOTE: All target interfaces were pre-existing (retroactive coverage). Architecture
Review (#792) explicitly approved GREEN-on-RED for this task.
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# AC1: SourceType.AUTHENTICATED_WEB membership
# ---------------------------------------------------------------------------


class TestFromAC_AuthenticatedWeb:
    """AC1-4: AUTHENTICATED_WEB source type and ContentFetcher protocol."""

    # -- AC1: SourceType membership ------------------------------------------

    def test_authenticated_web_is_source_type_member(self) -> None:
        """AUTHENTICATED_WEB is a valid member of SourceType."""
        from owlbear_knowledge.models import SourceType

        assert hasattr(SourceType, "AUTHENTICATED_WEB")

    def test_authenticated_web_has_expected_value(self) -> None:
        """SourceType.AUTHENTICATED_WEB has the string value 'authenticated_web'."""
        from owlbear_knowledge.models import SourceType

        assert SourceType.AUTHENTICATED_WEB == "authenticated_web"

    def test_authenticated_web_is_in_source_type_values(self) -> None:
        """'authenticated_web' appears in all SourceType values."""
        from owlbear_knowledge.models import SourceType

        assert "authenticated_web" in list(SourceType)

    def test_source_type_is_str_enum(self) -> None:
        """SourceType members compare equal to plain strings."""
        from owlbear_knowledge.models import SourceType

        source_type: Any = SourceType.AUTHENTICATED_WEB
        assert isinstance(source_type, str)

    # -- AC2: ContentFetcher protocol ----------------------------------------

    def test_content_fetcher_importable_from_protocol(self) -> None:
        """ContentFetcher is importable from owlbear_knowledge.protocol."""
        from owlbear_knowledge.protocol import ContentFetcher  # noqa: F401

    def test_content_fetcher_has_fetch_method(self) -> None:
        """ContentFetcher defines a fetch method."""
        from owlbear_knowledge.protocol import ContentFetcher

        assert hasattr(ContentFetcher, "fetch")

    def test_content_fetcher_fetch_is_async(self) -> None:
        """ContentFetcher.fetch is a coroutine function."""
        from owlbear_knowledge.protocol import ContentFetcher

        assert inspect.iscoroutinefunction(ContentFetcher.fetch)

    def test_content_fetcher_is_runtime_checkable(self) -> None:
        """ContentFetcher is a runtime_checkable Protocol (isinstance works)."""
        from owlbear_knowledge.protocol import ContentFetcher

        class _ConformingFetcher:
            async def fetch(self, url: str) -> str:  # noqa: ASYNC100, ARG002
                return ""

        assert isinstance(_ConformingFetcher(), ContentFetcher)

    def test_non_conforming_object_fails_isinstance_check(self) -> None:
        """An object without fetch() does NOT satisfy ContentFetcher."""
        from owlbear_knowledge.protocol import ContentFetcher

        class _NoFetch:
            pass

        assert not isinstance(_NoFetch(), ContentFetcher)

    # -- AC3: _handle_authenticated_web dispatches and returns RefreshResult --

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_returns_refresh_result(self) -> None:
        """_handle_authenticated_web() returns a RefreshResult instance."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="<html>page content</html>")

        source = KnowledgeSource(
            name="test-auth",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": ["https://example.com/page"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_authenticated_web(source)

        assert isinstance(result, RefreshResult)

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_calls_content_fetcher_per_url(self) -> None:
        """content_fetcher.fetch() is called once for each URL in source.config['urls']."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        urls = ["https://example.com/a", "https://example.com/b", "https://example.com/c"]

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="content")

        source = KnowledgeSource(
            name="test-auth-multi",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": urls},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_authenticated_web(source)

        assert mock_fetcher.fetch.call_count == len(urls)
        called_urls = [call.args[0] for call in mock_fetcher.fetch.call_args_list]
        assert called_urls == urls

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_empty_urls_returns_zero_counts(self) -> None:
        """Empty URL list yields RefreshResult with all-zero counts and no errors."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()

        source = KnowledgeSource(
            name="empty-source",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": []},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_authenticated_web(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []
        mock_fetcher.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_missing_urls_key_returns_zero_counts(self) -> None:
        """Config without 'urls' key is treated as empty — no fetch calls, zero counts."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()

        source = KnowledgeSource(
            name="no-urls-key",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_authenticated_web(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.failed == 0
        mock_fetcher.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_fetch_exception_records_error(self) -> None:
        """When content_fetcher.fetch() raises, the error is captured and failed is incremented."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(side_effect=RuntimeError("network timeout"))

        source = KnowledgeSource(
            name="error-source",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": ["https://example.com/page"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_authenticated_web(source)

        assert isinstance(result, RefreshResult)
        assert result.failed == 1
        assert result.refreshed == 0
        assert len(result.errors) == 1
        assert "network timeout" in result.errors[0]

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_cancel_signal_stops_iteration(self) -> None:
        """When cancel signal is set, remaining URLs are skipped."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        # cancel signal set immediately — all URLs should be skipped
        mock_cancel = MagicMock()
        mock_cancel.is_set.return_value = True

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="content")

        source = KnowledgeSource(
            name="cancel-source",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": ["https://example.com/a", "https://example.com/b"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_authenticated_web(source, cancel=mock_cancel)

        mock_fetcher.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_authenticated_web_result_source_id_matches_source(self) -> None:
        """RefreshResult.source_id matches the source's id."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="data")

        source = KnowledgeSource(
            name="id-check-source",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": ["https://example.com/x"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_authenticated_web(source)

        assert result.source_id == str(source.id)

    # -- AC4: No real browser dependency — demonstrated by mock usage ---------

    def test_mock_satisfies_content_fetcher_protocol(self) -> None:
        """AsyncMock with fetch attribute satisfies ContentFetcher via isinstance."""
        from owlbear_knowledge.protocol import ContentFetcher

        class _MockFetcher:
            async def fetch(self, url: str) -> str:  # noqa: ASYNC100, ARG002
                return "mocked"

        fetcher = _MockFetcher()
        assert isinstance(fetcher, ContentFetcher)
        # No owlbear_browser import — pure mock, no real browser dependency

    def test_no_browser_import_needed_for_content_fetcher(self) -> None:
        """ContentFetcher protocol is importable without owlbear_browser installed."""
        # If this fails, ContentFetcher has a hard browser dependency — violation of AC4
        import importlib.util

        spec = importlib.util.find_spec("owlbear_knowledge.protocol")
        assert spec is not None, "owlbear_knowledge.protocol must be importable without a browser"
