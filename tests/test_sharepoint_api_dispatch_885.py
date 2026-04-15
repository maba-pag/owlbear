"""RED-phase tests for SHAREPOINT_API dispatch in RefreshOrchestrator (#885).

Covers AC from task #885 (Wire RefreshOrchestrator SHAREPOINT_API dispatch):

  AC1 - RefreshOrchestrator.__init__() accepts graph_content_fetcher parameter
  AC2 - SourceType.SHAREPOINT_API branch in refresh() dispatching to _handle_sharepoint_api()
  AC3 - _handle_sharepoint_api() nil-guard, metadata, ingest-status, and exception handling
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# AC1: graph_content_fetcher parameter in RefreshOrchestrator.__init__
# ---------------------------------------------------------------------------


class TestFromAC_GraphContentFetcherInit:
    """AC1: RefreshOrchestrator.__init__ accepts graph_content_fetcher parameter."""

    def test_orchestrator_accepts_graph_content_fetcher_kwarg(self) -> None:
        """RefreshOrchestrator.__init__ accepts graph_content_fetcher as a keyword argument."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = MagicMock()
        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            graph_content_fetcher=mock_fetcher,
        )
        assert orch is not None

    @pytest.mark.asyncio
    async def test_orchestrator_graph_content_fetcher_defaults_to_none_nil_guard(self) -> None:
        """When graph_content_fetcher is omitted, _handle_sharepoint_api returns empty RefreshResult (nil guard)."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
        )

        source = KnowledgeSource(
            name="sp-no-fetcher",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        result = await orch._handle_sharepoint_api(source)
        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.failed == 0

    def test_graph_content_fetcher_independent_of_content_fetcher(self) -> None:
        """graph_content_fetcher and content_fetcher are separate parameters."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        web_fetcher = MagicMock()
        graph_fetcher = MagicMock()
        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            content_fetcher=web_fetcher,
            graph_content_fetcher=graph_fetcher,
        )
        assert orch is not None


# ---------------------------------------------------------------------------
# AC2: SourceType.SHAREPOINT_API + refresh() dispatch
# ---------------------------------------------------------------------------


class TestFromAC_SourceTypeSharepointApi:
    """AC2: SourceType.SHAREPOINT_API exists and refresh() dispatches to _handle_sharepoint_api."""

    def test_sharepoint_api_member_exists(self) -> None:
        """SourceType.SHAREPOINT_API exists as an enum member."""
        from owlbear_knowledge.models import SourceType

        assert hasattr(SourceType, "SHAREPOINT_API")

    def test_sharepoint_api_string_value(self) -> None:
        """SourceType.SHAREPOINT_API has value 'sharepoint_api'."""
        from owlbear_knowledge.models import SourceType

        assert str(SourceType.SHAREPOINT_API) == "sharepoint_api"

    def test_sharepoint_api_usable_as_source_type_field(self) -> None:
        """KnowledgeSource accepts SHAREPOINT_API as source_type value."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        assert source.source_type == SourceType.SHAREPOINT_API

    @pytest.mark.asyncio
    async def test_refresh_routes_sharepoint_api_to_handler(self) -> None:
        """refresh() with SHAREPOINT_API source calls _handle_sharepoint_api, not other handlers."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_graph_fetcher = AsyncMock()
        mock_graph_fetcher.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))
        mock_store = MagicMock()
        mock_store.update = MagicMock()

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=mock_store,
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_graph_fetcher,
        )

        result = await orchestrator.refresh(source)
        assert result.refreshed == 1

    @pytest.mark.asyncio
    async def test_refresh_sharepoint_api_does_not_call_handle_authenticated_web(self) -> None:
        """refresh() with SHAREPOINT_API does not dispatch to _handle_authenticated_web."""
        from unittest.mock import patch

        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_graph_fetcher = AsyncMock()
        mock_graph_fetcher.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))
        mock_store = MagicMock()
        mock_store.update = MagicMock()

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=mock_store,
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_graph_fetcher,
        )

        with patch.object(
            orchestrator, "_handle_authenticated_web", wraps=orchestrator._handle_authenticated_web
        ) as spy_auth_web:
            await orchestrator.refresh(source)

        spy_auth_web.assert_not_called()


# ---------------------------------------------------------------------------
# AC3: _handle_sharepoint_api() contract
# ---------------------------------------------------------------------------


class TestFromAC_HandleSharepointApi:
    """AC3: _handle_sharepoint_api() nil-guard, metadata, ingest paths, exception handling."""

    @pytest.mark.asyncio
    async def test_nil_guard_returns_empty_result_when_no_graph_fetcher(self) -> None:
        """When graph_content_fetcher is None, _handle_sharepoint_api returns empty RefreshResult."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            graph_content_fetcher=None,
        )
        result = await orchestrator._handle_sharepoint_api(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_ok_status_increments_refreshed_counter(self) -> None:
        """When pipeline.ingest() returns status='ok', result.refreshed is incremented."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="sp content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_sharepoint_api(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 1
        assert result.skipped == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_skipped_status_increments_skipped_counter(self) -> None:
        """When pipeline.ingest() returns status='skipped', result.skipped is incremented."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="sp content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="skipped"))

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_sharepoint_api(source)

        assert isinstance(result, RefreshResult)
        assert result.skipped == 1
        assert result.refreshed == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_error_status_increments_failed_counter(self) -> None:
        """When pipeline.ingest() returns a non-ok/non-skipped status, result.failed is incremented."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="sp content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="error"))

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_sharepoint_api(source)

        assert isinstance(result, RefreshResult)
        assert result.failed == 1
        assert result.refreshed == 0
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_intake_metadata_uses_sharepoint_api_source_type(self) -> None:
        """IntakeResult passed to pipeline.ingest() has metadata source_type='sharepoint_api'."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="sp content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_sharepoint_api(source)

        intake_arg = mock_pipeline.ingest.call_args[0][0]
        assert intake_arg.metadata.get("source_type") == "sharepoint_api"

    @pytest.mark.asyncio
    async def test_intake_metadata_is_not_authenticated_web(self) -> None:
        """IntakeResult metadata source_type must not be 'authenticated_web'."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="sp content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_sharepoint_api(source)

        intake_arg = mock_pipeline.ingest.call_args[0][0]
        assert intake_arg.metadata.get("source_type") != "authenticated_web"

    @pytest.mark.asyncio
    async def test_fetched_content_forwarded_to_pipeline(self) -> None:
        """The string returned by graph_content_fetcher.fetch() is the content passed to pipeline.ingest()."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        fetched_content = "<html>SharePoint page content</html>"
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value=fetched_content)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_sharepoint_api(source)

        intake_arg = mock_pipeline.ingest.call_args[0][0]
        assert intake_arg.content == fetched_content

    @pytest.mark.asyncio
    async def test_ingest_called_with_source_scope(self) -> None:
        """pipeline.ingest() is called with scope=source.scope for each URL."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="sp content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            scope="team-finance",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_sharepoint_api(source)

        call_kwargs = mock_pipeline.ingest.call_args[1]
        assert call_kwargs.get("scope") == "team-finance"

    @pytest.mark.asyncio
    async def test_empty_url_list_returns_zero_counters(self) -> None:
        """When source.config has no URLs, handler returns all-zero RefreshResult."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()
        mock_pipeline = MagicMock()

        source = KnowledgeSource(
            name="sp-empty",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": []},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_sharepoint_api(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.skipped == 0
        assert result.failed == 0
        mock_fetcher.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_in_fetch_increments_failed_and_records_error(self) -> None:
        """When graph_content_fetcher.fetch() raises, failed is incremented and error is recorded."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(side_effect=RuntimeError("Graph API timeout"))
        mock_pipeline = MagicMock()

        source = KnowledgeSource(
            name="sp-error",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://tenant.sharepoint.com/sites/docs"]},
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_sharepoint_api(source)

        assert isinstance(result, RefreshResult)
        assert result.failed == 1
        assert result.refreshed == 0
        assert len(result.errors) == 1
        assert "Graph API timeout" in result.errors[0]

    @pytest.mark.asyncio
    async def test_cancel_signal_stops_url_iteration(self) -> None:
        """When cancel signal is set, URL iteration stops before all URLs are processed."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-cancel",
            source_type=SourceType.SHAREPOINT_API,
            config={
                "urls": [
                    "https://tenant.sharepoint.com/sites/a",
                    "https://tenant.sharepoint.com/sites/b",
                ]
            },
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        cancel = MagicMock()
        cancel.is_set = MagicMock(return_value=True)

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        await orchestrator._handle_sharepoint_api(source, cancel=cancel)

        assert mock_fetcher.fetch.call_count == 0

    @pytest.mark.asyncio
    async def test_mixed_url_outcomes_correct_counters(self) -> None:
        """Multiple URLs with mixed ingest outcomes produce correct refreshed/skipped/failed counts."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        statuses = ["ok", "skipped", "error"]
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="sp content")
        ingest_results = [MagicMock(status=s) for s in statuses]
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(side_effect=ingest_results)

        source = KnowledgeSource(
            name="sp-mixed",
            source_type=SourceType.SHAREPOINT_API,
            config={
                "urls": [
                    "https://tenant.sharepoint.com/sites/a",
                    "https://tenant.sharepoint.com/sites/b",
                    "https://tenant.sharepoint.com/sites/c",
                ]
            },
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_fetcher,
        )
        result = await orchestrator._handle_sharepoint_api(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 1
        assert result.skipped == 1
        assert result.failed == 1
