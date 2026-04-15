"""Failing RED-phase tests for #884: RefreshOrchestrator SHAREPOINT_API dispatch.

Corrected AC (from architecture review 2nd pass — supersedes original AC block):
  AC1  RefreshOrchestrator.refresh() routes SourceType.SHAREPOINT_API to a
       graph_content_fetcher dispatch branch
  AC2  Constructor accepts graph_content_fetcher: object | None = None parameter
       (follows content_fetcher naming convention from refresh.py L63)
  AC3  Iterates URLs from source.config["urls"], calls graph_content_fetcher.fetch(url)
       for content, creates IntakeResult(content=content, source=url,
       metadata={"source_type": "sharepoint_api"}) and calls pipeline.ingest(intake_result,
       scope=source.scope), counts ok/skipped/failed per _handle_authenticated_web pattern
  AC4  No-op (empty RefreshResult with zero counters and empty errors list) when
       graph_content_fetcher is None
  AC5  All tests fail (dispatch branch does not yet exist)

All tests MUST FAIL at RED phase.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 14, tzinfo=UTC).isoformat()
_SP_URL_1 = "https://contoso.sharepoint.com/sites/Eng/SitePages/Home.aspx"
_SP_URL_2 = "https://contoso.sharepoint.com/sites/HR/SitePages/Policy.aspx"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(urls: list[str], scope: str = "global"):
    from owlbear_knowledge.models import KnowledgeSource, SourceType

    return KnowledgeSource(
        name="sp-test-source",
        source_type=SourceType.SHAREPOINT_API,
        config={"urls": urls},
        scope=scope,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _ingest_result(status: str = "ok") -> MagicMock:
    r = MagicMock()
    r.status = status
    r.document_id = "doc-abc-001"
    return r


# ---------------------------------------------------------------------------
# TestFromAC_RefreshOrchestratorDispatch
# ---------------------------------------------------------------------------


class TestFromAC_RefreshOrchestratorDispatch:
    """AC1–AC5: RefreshOrchestrator dispatches SHAREPOINT_API to graph_content_fetcher."""

    # -----------------------------------------------------------------------
    # AC2 — Constructor parameter
    # -----------------------------------------------------------------------

    def test_constructor_accepts_graph_content_fetcher_keyword(self) -> None:
        """AC2: RefreshOrchestrator.__init__ accepts graph_content_fetcher as kwarg."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            graph_content_fetcher=mock_gcf,
        )
        assert orch is not None

    def test_constructor_graph_content_fetcher_defaults_to_none(self) -> None:
        """AC2: graph_content_fetcher is declared in __init__ signature with a None default."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        sig = inspect.signature(RefreshOrchestrator.__init__)
        param = sig.parameters.get("graph_content_fetcher")
        assert param is not None, "graph_content_fetcher parameter is not declared in __init__"
        assert param.default is None, "graph_content_fetcher default must be None"

    # -----------------------------------------------------------------------
    # AC1 — Routing: SHAREPOINT_API dispatched to graph_content_fetcher
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sharepoint_api_routes_to_graph_content_fetcher_not_content_fetcher(
        self,
    ) -> None:
        """AC1: SHAREPOINT_API calls graph_content_fetcher.fetch(), not content_fetcher.fetch()."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="sharepoint content")
        mock_cf = AsyncMock()
        mock_cf.fetch = AsyncMock(return_value="browser content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            content_fetcher=mock_cf,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])
        await orch.refresh(source)

        mock_gcf.fetch.assert_called()
        mock_cf.fetch.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sharepoint_api_does_not_raise_unsupported_type_error(self) -> None:
        """AC1 boundary: SHAREPOINT_API does not fall into the else-raise branch."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])

        # Should not raise ValueError("Unsupported source type")
        result = await orch.refresh(source)
        assert result is not None

    # -----------------------------------------------------------------------
    # AC3 — Fetch + ingest pattern
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_graph_content_fetcher_called_with_exact_url(self) -> None:
        """AC3: graph_content_fetcher.fetch() receives the exact URL from source.config['urls']."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="fetched content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])
        await orch.refresh(source)

        mock_gcf.fetch.assert_called_once_with(_SP_URL_1)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_pipeline_ingest_called_with_correct_intake_result_fields(self) -> None:
        """AC3: pipeline.ingest() receives IntakeResult with content, source=url, metadata."""
        from owlbear_knowledge.intake import IntakeResult
        from owlbear_knowledge.refresh import RefreshOrchestrator

        fetched_content = "the page content"
        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value=fetched_content)
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])
        await orch.refresh(source)

        mock_pipeline.ingest.assert_called_once()
        call_args = mock_pipeline.ingest.call_args
        intake_result = call_args[0][0]  # first positional arg

        assert isinstance(intake_result, IntakeResult)
        assert intake_result.content == fetched_content
        assert intake_result.source == _SP_URL_1
        assert intake_result.metadata == {"source_type": "sharepoint_api"}

    @pytest.mark.asyncio(loop_scope="function")
    async def test_pipeline_ingest_called_with_source_scope(self) -> None:
        """AC3: pipeline.ingest() passes scope=source.scope."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1], scope="engineering")
        await orch.refresh(source)

        mock_pipeline.ingest.assert_called_once()
        call_kwargs = mock_pipeline.ingest.call_args[1]
        assert call_kwargs.get("scope") == "engineering"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ingest_ok_increments_refreshed_counter(self) -> None:
        """AC3: ingest returns 'ok' → result.refreshed == 1."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])
        result = await orch.refresh(source)

        assert result.refreshed == 1
        assert result.skipped == 0
        assert result.failed == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ingest_skipped_increments_skipped_counter(self) -> None:
        """AC3: ingest returns 'skipped' → result.skipped == 1."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("skipped"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])
        result = await orch.refresh(source)

        assert result.skipped == 1
        assert result.refreshed == 0
        assert result.failed == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ingest_failed_status_increments_failed_counter(self) -> None:
        """AC3: ingest returns 'failed' → result.failed == 1."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("failed"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])
        result = await orch.refresh(source)

        assert result.failed == 1
        assert result.refreshed == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_urls_all_fetched_and_ingested(self) -> None:
        """AC3: multiple URLs → graph_content_fetcher.fetch() called once per URL."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1, _SP_URL_2])
        result = await orch.refresh(source)

        assert mock_gcf.fetch.call_count == 2
        assert mock_pipeline.ingest.call_count == 2
        assert result.refreshed == 2

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_urls_counters_aggregated_correctly(self) -> None:
        """AC3: mixed ok/skipped/failed ingest results → counters tallied per URL."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(
            side_effect=[
                _ingest_result("ok"),
                _ingest_result("skipped"),
                _ingest_result("failed"),
            ]
        )

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        sp_url_3 = "https://contoso.sharepoint.com/sites/IT/SitePages/Tools.aspx"
        source = _make_source([_SP_URL_1, _SP_URL_2, sp_url_3])
        result = await orch.refresh(source)

        assert result.refreshed == 1
        assert result.skipped == 1
        assert result.failed == 1

    # -----------------------------------------------------------------------
    # AC3 — Edge cases
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_urls_list_returns_zero_counters(self) -> None:
        """AC3 edge: source.config['urls'] is empty → zero-count RefreshResult."""
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([])
        result = await orch.refresh(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.skipped == 0
        assert result.failed == 0
        mock_gcf.fetch.assert_not_called()

    # -----------------------------------------------------------------------
    # AC3 — Error paths
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_exception_increments_failed_counter(self) -> None:
        """AC3 error: graph_content_fetcher.fetch() raises → failed += 1, error recorded."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(side_effect=RuntimeError("network error"))
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])
        result = await orch.refresh(source)

        assert result.failed == 1
        assert result.refreshed == 0
        assert len(result.errors) == 1
        assert "network error" in result.errors[0]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_pipeline_ingest_exception_increments_failed_counter(self) -> None:
        """AC3 error: pipeline.ingest() raises → failed += 1, error recorded."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(side_effect=IOError("ingest failure"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1])
        result = await orch.refresh(source)

        assert result.failed == 1
        assert len(result.errors) == 1
        assert "ingest failure" in result.errors[0]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fetch_exception_one_url_does_not_abort_subsequent_urls(self) -> None:
        """AC3 error: failure on one URL does not skip remaining URLs."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(
            side_effect=[RuntimeError("first fails"), "second content"]
        )
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1, _SP_URL_2])
        result = await orch.refresh(source)

        assert result.failed == 1
        assert result.refreshed == 1

    # -----------------------------------------------------------------------
    # AC3 — Boundary: CancelSignal
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_cancel_signal_stops_iteration_early(self) -> None:
        """AC3 boundary: CancelSignal set before second URL → second fetch not called."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        cancel = MagicMock()
        # Signal is NOT set on first check, IS set before second URL
        cancel.is_set = MagicMock(side_effect=[False, True])

        mock_gcf = AsyncMock()
        mock_gcf.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=_ingest_result("ok"))

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_content_fetcher=mock_gcf,
        )
        source = _make_source([_SP_URL_1, _SP_URL_2])
        await orch.refresh(source, cancel=cancel)

        assert mock_gcf.fetch.call_count == 1

    # -----------------------------------------------------------------------
    # AC4 — No-op when graph_content_fetcher is None
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_noop_when_graph_content_fetcher_is_none(self) -> None:
        """AC4: SHAREPOINT_API with no graph_content_fetcher → zero-count RefreshResult."""
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
        )
        source = _make_source([_SP_URL_1, _SP_URL_2])
        result = await orch.refresh(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []

    @pytest.mark.asyncio(loop_scope="function")
    async def test_noop_result_carries_source_id(self) -> None:
        """AC4: no-op RefreshResult.source_id matches source.id."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
        )
        source = _make_source([_SP_URL_1])
        result = await orch.refresh(source)

        assert result.source_id == source.id
