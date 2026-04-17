"""RED-phase tests for AUTHENTICATED_WEB source type and ContentFetcher protocol (#796).

Covers AC from task #796 (Scope items 3+4 from #775, implementation task):

  AC1 - SourceType.AUTHENTICATED_WEB is a valid enum member
  AC2 - ContentFetcher protocol in protocol.py: runtime-checkable, async fetch(url: str) -> str
  AC3 - refresh.py _handle_authenticated_web() dispatched by source_type
  AC4 - RefreshOrchestrator.__init__() accepts optional content_fetcher param

NOTE: All target interfaces were pre-existing (retroactive coverage). Architecture
Review (#796) explicitly approved GREEN-on-RED for this task: "All AC items are
already implemented in the codebase. Builder should verify tests pass and confirm
no-op."  Tests are written against the contract; all pass immediately in GREEN-on-RED.
"""

from __future__ import annotations

import inspect
import typing
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# AC1: SourceType.AUTHENTICATED_WEB enum membership
# ---------------------------------------------------------------------------


class TestFromAC_SourceTypeAuthenticatedWeb:
    """AC1: SourceType includes AUTHENTICATED_WEB."""

    def test_authenticated_web_member_exists(self) -> None:
        """SourceType.AUTHENTICATED_WEB exists as an enum member."""
        from owlbear_knowledge.models import SourceType

        assert hasattr(SourceType, "AUTHENTICATED_WEB")

    def test_authenticated_web_string_value(self) -> None:
        """SourceType.AUTHENTICATED_WEB has value 'authenticated_web'."""
        from owlbear_knowledge.models import SourceType

        assert str(SourceType.AUTHENTICATED_WEB) == "authenticated_web"

    def test_authenticated_web_usable_as_source_type_field(self) -> None:
        """KnowledgeSource accepts AUTHENTICATED_WEB as source_type value."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType

        source = KnowledgeSource(
            name="test",
            source_type=SourceType.AUTHENTICATED_WEB,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        assert source.source_type == SourceType.AUTHENTICATED_WEB


# ---------------------------------------------------------------------------
# AC2: ContentFetcher protocol shape
# ---------------------------------------------------------------------------


class TestFromAC_ContentFetcherProtocol:
    """AC2: ContentFetcher protocol is runtime-checkable with async fetch(url: str) -> str."""

    def test_content_fetcher_importable(self) -> None:
        """ContentFetcher is importable from owlbear_knowledge.protocol."""
        from owlbear_knowledge.protocol import ContentFetcher  # noqa: F401

    def test_content_fetcher_is_runtime_checkable(self) -> None:
        """isinstance() works against ContentFetcher (runtime_checkable)."""
        from owlbear_knowledge.protocol import ContentFetcher

        class _Conforming:
            async def fetch(self, url: str) -> str:  # noqa: ASYNC100, ARG002
                return ""

        assert isinstance(_Conforming(), ContentFetcher)

    def test_object_missing_fetch_is_not_content_fetcher(self) -> None:
        """An object without fetch() does not satisfy ContentFetcher."""
        from owlbear_knowledge.protocol import ContentFetcher

        assert not isinstance(object(), ContentFetcher)

    def test_fetch_method_is_coroutine(self) -> None:
        """ContentFetcher.fetch is declared as a coroutine function."""
        from owlbear_knowledge.protocol import ContentFetcher

        assert inspect.iscoroutinefunction(ContentFetcher.fetch)

    def test_fetch_signature_has_url_parameter(self) -> None:
        """ContentFetcher.fetch signature includes a 'url' parameter."""
        from owlbear_knowledge.protocol import ContentFetcher

        sig = inspect.signature(ContentFetcher.fetch)
        assert "url" in sig.parameters

    def test_fetch_return_annotation_is_str(self) -> None:
        """ContentFetcher.fetch is annotated to return str (resolved via get_type_hints)."""
        from owlbear_knowledge.protocol import ContentFetcher

        hints = typing.get_type_hints(ContentFetcher.fetch)
        assert hints.get("return") is str


# ---------------------------------------------------------------------------
# AC3: _handle_authenticated_web dispatched by source_type + ingest status paths
# ---------------------------------------------------------------------------


class TestFromAC_HandleAuthenticatedWebDispatch:
    """AC3: refresh() dispatches AUTHENTICATED_WEB to _handle_authenticated_web."""

    @pytest.mark.asyncio
    async def test_refresh_routes_authenticated_web_to_handler(self) -> None:
        """refresh() with AUTHENTICATED_WEB source invokes _handle_authenticated_web, not _handle_url_list."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="auth-source",
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

        with patch.object(orchestrator, "_handle_url_list", wraps=orchestrator._handle_url_list) as spy_url_list:
            await orchestrator.refresh(source)

        spy_url_list.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_skipped_status_increments_skipped_counter(self) -> None:
        """When pipeline.ingest() returns status='skipped', result.skipped is incremented."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="page content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="skipped"))

        source = KnowledgeSource(
            name="skip-source",
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
        assert result.skipped == 1
        assert result.refreshed == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_ingest_error_status_increments_failed_counter(self) -> None:
        """When pipeline.ingest() returns a non-ok/non-skipped status, result.failed is incremented."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="page content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="error"))

        source = KnowledgeSource(
            name="fail-source",
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
        assert result.failed == 1
        assert result.refreshed == 0
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_fetched_content_forwarded_to_pipeline(self) -> None:
        """The string returned by content_fetcher.fetch() is the content passed to pipeline.ingest()."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        fetched_content = "<html>policy document body</html>"
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value=fetched_content)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="content-source",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": ["https://example.com/policy"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_authenticated_web(source)

        intake_arg = mock_pipeline.ingest.call_args[0][0]
        assert intake_arg.content == fetched_content

    @pytest.mark.asyncio
    async def test_ingest_called_with_source_scope(self) -> None:
        """pipeline.ingest() is called with scope=source.scope for each URL."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="scoped-source",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": ["https://example.com/page"]},
            scope="team-a",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_authenticated_web(source)

        call_kwargs = mock_pipeline.ingest.call_args[1]
        assert call_kwargs.get("scope") == "team-a"

    @pytest.mark.asyncio
    async def test_mixed_url_outcomes_correct_counters(self) -> None:
        """Multiple URLs with mixed ingest outcomes produce correct refreshed/skipped/failed counts."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        statuses = ["ok", "skipped", "error"]
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="content")

        ingest_results = [MagicMock(status=s) for s in statuses]
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(side_effect=ingest_results)

        source = KnowledgeSource(
            name="mixed-source",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": ["https://a.example.com", "https://b.example.com", "https://c.example.com"]},
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
        assert result.refreshed == 1
        assert result.skipped == 1
        assert result.failed == 1


# ---------------------------------------------------------------------------
# AC4: RefreshOrchestrator.__init__() accepts optional content_fetcher
# ---------------------------------------------------------------------------


class TestFromAC_ContentFetcherInjection:
    """AC4: RefreshOrchestrator accepts optional content_fetcher: ContentFetcher | None."""

    def test_orchestrator_accepts_content_fetcher_kwarg(self) -> None:
        """RefreshOrchestrator.__init__ accepts content_fetcher as a keyword argument."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = MagicMock()
        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        assert orch is not None

    def test_content_fetcher_is_optional_defaults_to_none(self) -> None:
        """RefreshOrchestrator can be constructed without content_fetcher (defaults to None)."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        sig = inspect.signature(RefreshOrchestrator.__init__)
        param = sig.parameters.get("content_fetcher")
        assert param is not None
        assert param.default is None

    def test_content_fetcher_none_with_no_urls_is_zero_result(self) -> None:
        """When content_fetcher=None and source has no URLs, refresh returns zero counts."""
        import asyncio

        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        source = KnowledgeSource(
            name="no-fetcher-no-urls",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": []},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=None,
        )
        result = asyncio.get_event_loop().run_until_complete(orch._handle_authenticated_web(source))

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []

    def test_injected_fetcher_retained_by_orchestrator(self) -> None:
        """The injected content_fetcher object is retained by the orchestrator."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = MagicMock()
        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=mock_fetcher,
        )
        assert mock_fetcher in vars(orch).values()


# ---------------------------------------------------------------------------
# Builder-discovered: content_fetcher=None + non-empty URLs should be no-op
# ---------------------------------------------------------------------------


class TestBuilderDiscovered_NullFetcherBehavior:
    """Builder-discovered: _handle_authenticated_web with content_fetcher=None and URLs present is a no-op."""

    def test_null_fetcher_with_urls_returns_zero_counts(self) -> None:
        """When content_fetcher=None and source has URLs, refresh returns zero counts (no-op per docstring)."""
        import asyncio

        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        source = KnowledgeSource(
            name="null-fetcher-with-urls",
            source_type=SourceType.AUTHENTICATED_WEB,
            config={"urls": ["https://example.com/page1", "https://example.com/page2"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=None,
        )
        result = asyncio.get_event_loop().run_until_complete(orch._handle_authenticated_web(source))

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []
