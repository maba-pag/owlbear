"""Failing RED-phase tests for #879: GraphContentFetcher + SourceType.SHAREPOINT_API.

AC mapping (from task #879):
  AC1  GraphContentFetcher class satisfies ContentFetcher protocol (async def fetch(url: str) -> str)
  AC2  Uses MSAL Python for token acquisition (device-code or interactive flow)
  AC3  Resolves SharePoint URL → site-id via GET /sites/{hostname}:/{path}
  AC4  Fetches page content via GET /sites/{site-id}/pages/{page-id}?$expand=canvasLayout
  AC5  Concatenates innerHtml from text web parts → markdown output
  AC6  Add SourceType.SHAREPOINT_API enum value
  AC7  RefreshOrchestrator dispatches SHAREPOINT_API sources to Graph fetcher
  AC8  Dependencies: msal + httpx only (no msgraph-sdk)

All tests MUST FAIL at RED phase.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SP_URL = "https://contoso.sharepoint.com/sites/Engineering/SitePages/Overview.aspx"
_HOSTNAME = "contoso.sharepoint.com"
_SITE_ID = "contoso.sharepoint.com,abc11111-1111-1111-1111,def22222-2222-2222-2222"
_PAGE_ID = "page-abc-001"
_PAGE_NAME = "Overview.aspx"
_ACCESS_TOKEN = "mock-bearer-token-xyz"

_CANVAS_JSON: dict = {
    "canvasLayout": {
        "horizontalSections": [
            {
                "columns": [
                    {
                        "webparts": [
                            {
                                "innerHtml": "<p>Hello SharePoint world</p>",
                                "webPartType": "d1d91016-032f-456d-98a4-721247c305e8",
                            }
                        ]
                    }
                ]
            }
        ]
    }
}

_MULTI_WEBPART_CANVAS_JSON: dict = {
    "canvasLayout": {
        "horizontalSections": [
            {
                "columns": [
                    {
                        "webparts": [
                            {
                                "innerHtml": "<p>First section</p>",
                                "webPartType": "d1d91016-032f-456d-98a4-721247c305e8",
                            },
                            {
                                "innerHtml": "<p>Second section</p>",
                                "webPartType": "d1d91016-032f-456d-98a4-721247c305e8",
                            },
                        ]
                    }
                ]
            }
        ]
    }
}

_NOW = datetime(2026, 4, 14, tzinfo=UTC).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_msal_app(token: str = _ACCESS_TOKEN) -> MagicMock:
    """Return a mock PublicClientApplication that yields a valid token."""
    app = MagicMock()
    app.acquire_token_silent.return_value = None
    app.initiate_device_flow.return_value = {
        "user_code": "ABCDE",
        "message": "Visit https://microsoft.com/devicelogin and enter ABCDE",
    }
    app.acquire_token_by_device_flow.return_value = {
        "access_token": token,
        "token_type": "Bearer",
    }
    return app


def _make_httpx_client_mock(
    site_json: dict | None = None,
    pages_json: dict | None = None,
    canvas_json: dict | None = None,
) -> AsyncMock:
    """Return an async context-manager mock for httpx.AsyncClient with sequential GET responses.

    Mirrors the Graph API call sequence:
      1. GET /sites/{hostname}:/{path}   → site-id
      2. GET /sites/{site-id}/pages?...  → page listing
      3. GET /sites/{site-id}/pages/{page-id}/microsoft.graph.sitePage?$expand=canvasLayout
    """
    site_resp = MagicMock()
    site_resp.raise_for_status = MagicMock()
    site_resp.json.return_value = site_json if site_json is not None else {"id": _SITE_ID}

    pages_resp = MagicMock()
    pages_resp.raise_for_status = MagicMock()
    pages_resp.json.return_value = (
        pages_json if pages_json is not None else {"value": [{"id": _PAGE_ID, "name": _PAGE_NAME}]}
    )

    canvas_resp = MagicMock()
    canvas_resp.raise_for_status = MagicMock()
    canvas_resp.json.return_value = canvas_json if canvas_json is not None else _CANVAS_JSON

    client = AsyncMock()
    client.get = AsyncMock(side_effect=[site_resp, pages_resp, canvas_resp])
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# ---------------------------------------------------------------------------
# TestFromAC_SourceTypeSharePointAPI (AC6)
# ---------------------------------------------------------------------------


class TestFromAC_SourceTypeSharePointAPI:
    """AC6: SourceType.SHAREPOINT_API enum value exists with value 'sharepoint_api'."""

    def test_sharepoint_api_attribute_exists(self) -> None:
        """AC6: SourceType has a SHAREPOINT_API attribute."""
        from owlbear_knowledge.models import SourceType

        assert hasattr(SourceType, "SHAREPOINT_API")

    def test_sharepoint_api_value_is_sharepoint_api_string(self) -> None:
        """AC6: SourceType.SHAREPOINT_API equals the string 'sharepoint_api'."""
        from owlbear_knowledge.models import SourceType

        assert SourceType.SHAREPOINT_API == "sharepoint_api"

    def test_sharepoint_api_is_strenum_member(self) -> None:
        """AC6: 'sharepoint_api' appears when iterating SourceType members."""
        from owlbear_knowledge.models import SourceType

        values = [m.value for m in SourceType]
        assert "sharepoint_api" in values

    def test_knowledge_source_accepts_sharepoint_api_source_type(self) -> None:
        """AC6: KnowledgeSource can be constructed with source_type=SHAREPOINT_API."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType

        source = KnowledgeSource(
            name="sharepoint-source",
            source_type=SourceType.SHAREPOINT_API,
            created_at=_NOW,
            updated_at=_NOW,
        )
        assert source.source_type == SourceType.SHAREPOINT_API


# ---------------------------------------------------------------------------
# TestFromAC_GraphContentFetcher (AC1-5, AC8)
# ---------------------------------------------------------------------------


class TestFromAC_GraphContentFetcher:
    """AC1-5, AC8: GraphContentFetcher protocol conformance and Graph API logic."""

    # --- AC1: protocol conformance ---

    def test_graph_content_fetcher_importable(self) -> None:
        """AC1: GraphContentFetcher is importable from owlbear_knowledge.graph_fetcher."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher  # noqa: F401

    def test_satisfies_content_fetcher_protocol(self) -> None:
        """AC1: isinstance(fetcher, ContentFetcher) returns True."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher
        from owlbear_knowledge.protocol import ContentFetcher

        fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
        assert isinstance(fetcher, ContentFetcher)

    def test_fetch_is_async_coroutine(self) -> None:
        """AC1: fetch() is a coroutine function (async def)."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
        assert inspect.iscoroutinefunction(fetcher.fetch)

    # --- AC2: MSAL token acquisition ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_msal_public_client_app_used_for_token_acquisition(self) -> None:
        """AC2: PublicClientApplication is called to obtain a token during fetch()."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock()

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            await fetcher.fetch(_SP_URL)

        assert (
            mock_app.acquire_token_silent.called
            or mock_app.acquire_token_by_device_flow.called
            or mock_app.acquire_token_for_client.called
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_bearer_token_sent_in_authorization_header(self) -> None:
        """AC2: Authorization: Bearer <token> header is present in all Graph API GET calls."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app(token=_ACCESS_TOKEN)
        mock_client = _make_httpx_client_mock()

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            await fetcher.fetch(_SP_URL)

        assert mock_client.get.call_count >= 1
        for call in mock_client.get.call_args_list:
            headers = call.kwargs.get("headers") or (call.args[1] if len(call.args) > 1 else {})
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_auth_failure_raises_exception(self) -> None:
        """AC7/AC2 error: MSAL returns error dict -> fetch() raises."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = MagicMock()
        mock_app.acquire_token_silent.return_value = None
        mock_app.initiate_device_flow.return_value = {"user_code": "X", "message": "..."}
        mock_app.acquire_token_by_device_flow.return_value = {
            "error": "invalid_client",
            "error_description": "Client not registered.",
        }

        with patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app):
            fetcher = GraphContentFetcher(client_id="bad-id", tenant_id="bad-tenant")
            with pytest.raises((RuntimeError, ValueError)):
                await fetcher.fetch(_SP_URL)

    # --- AC3: SharePoint URL → site-id resolution ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_site_resolution_endpoint_includes_hostname_and_path(self) -> None:
        """AC3: First Graph API call targets the /sites/{hostname}:/{path} endpoint."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock()

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            await fetcher.fetch(_SP_URL)

        first_call_url: str = mock_client.get.call_args_list[0].args[0]
        assert _HOSTNAME in first_call_url
        assert "/sites/" in first_call_url

    @pytest.mark.asyncio(loop_scope="function")
    async def test_site_not_found_404_raises_exception(self) -> None:
        """AC7/AC3 error: 404 from site resolution request propagates as an exception."""
        import httpx

        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()

        site_resp = MagicMock()
        site_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        )
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=site_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            with pytest.raises(httpx.HTTPStatusError):
                await fetcher.fetch("https://missing.sharepoint.com/sites/NoSite/SitePages/P.aspx")

    @pytest.mark.asyncio(loop_scope="function")
    async def test_site_id_from_resolution_used_in_subsequent_api_calls(self) -> None:
        """AC3: The site-id returned by site resolution appears in downstream Graph API URLs."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        custom_site_id = "custom.sharepoint.com,aaaa1111,bbbb2222"
        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock(site_json={"id": custom_site_id})

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            await fetcher.fetch(_SP_URL)

        subsequent_urls = [call.args[0] for call in mock_client.get.call_args_list[1:]]
        assert any(custom_site_id in url for url in subsequent_urls)

    # --- AC4: page fetch with canvasLayout ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_canvas_layout_expansion_included_in_page_fetch_url(self) -> None:
        """AC4: At least one Graph API call includes 'canvasLayout' in the URL."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock()

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            await fetcher.fetch(_SP_URL)

        all_urls = [call.args[0] for call in mock_client.get.call_args_list]
        assert any("canvasLayout" in url for url in all_urls)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_page_endpoint_contains_resolved_site_id(self) -> None:
        """AC4: Page fetch URL includes the site-id from resolution, not a hardcoded value."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock()

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            await fetcher.fetch(_SP_URL)

        subsequent_urls = [call.args[0] for call in mock_client.get.call_args_list[1:]]
        assert any(_SITE_ID in url for url in subsequent_urls)

    # --- AC5: innerHtml extraction → markdown ---

    @pytest.mark.asyncio(loop_scope="function")
    async def test_inner_html_from_text_webpart_included_in_output(self) -> None:
        """AC5: Text content from innerHtml is present in the returned markdown string."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock(canvas_json=_CANVAS_JSON)

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            result = await fetcher.fetch(_SP_URL)

        assert isinstance(result, str)
        assert "Hello SharePoint world" in result

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_text_webparts_all_present_in_output(self) -> None:
        """AC5 edge: content from all text web parts is included in the output."""
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock(canvas_json=_MULTI_WEBPART_CANVAS_JSON)

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            result = await fetcher.fetch(_SP_URL)

        assert "First section" in result
        assert "Second section" in result

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_canvas_sections_returns_string(self) -> None:
        """AC5 boundary: canvas with no horizontal sections returns a str (possibly empty)."""
        empty_canvas: dict = {"canvasLayout": {"horizontalSections": []}}
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock(canvas_json=empty_canvas)

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            result = await fetcher.fetch(_SP_URL)

        assert isinstance(result, str)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_malformed_canvas_response_handled_gracefully(self) -> None:
        """AC7/AC5 error: canvas JSON missing 'canvasLayout' key does not raise — returns str."""
        malformed_canvas: dict = {"id": "page-001", "title": "My Page"}
        from owlbear_knowledge.graph_fetcher import GraphContentFetcher

        mock_app = _make_mock_msal_app()
        mock_client = _make_httpx_client_mock(canvas_json=malformed_canvas)

        with (
            patch("owlbear_knowledge.graph_fetcher.PublicClientApplication", return_value=mock_app),
            patch("owlbear_knowledge.graph_fetcher.httpx.AsyncClient", return_value=mock_client),
        ):
            fetcher = GraphContentFetcher(client_id="app-id", tenant_id="tenant-id")
            result = await fetcher.fetch(_SP_URL)

        assert isinstance(result, str)

    # --- AC8: dependency constraints ---

    def test_msal_package_is_importable(self) -> None:
        """AC8: msal is available as a project dependency."""
        import msal  # noqa: F401


# ---------------------------------------------------------------------------
# TestFromAC_RefreshOrchestratorDispatch (AC7)
# ---------------------------------------------------------------------------


class TestFromAC_RefreshOrchestratorDispatch:
    """AC7: RefreshOrchestrator dispatches SHAREPOINT_API sources to the graph_fetcher."""

    def test_orchestrator_accepts_graph_fetcher_keyword_argument(self) -> None:
        """AC7: RefreshOrchestrator.__init__ accepts graph_fetcher as a keyword argument."""
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch = AsyncMock(return_value="content")

        orch = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
            graph_fetcher=mock_fetcher,
        )
        assert orch is not None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sharepoint_api_source_dispatched_to_graph_fetcher_not_content_fetcher(
        self,
    ) -> None:
        """AC7: refresh() with SHAREPOINT_API routes to graph_fetcher.fetch(), not content_fetcher.fetch()."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_graph_fetcher = AsyncMock()
        mock_graph_fetcher.fetch = AsyncMock(return_value="sharepoint content")
        mock_content_fetcher = AsyncMock()
        mock_content_fetcher.fetch = AsyncMock(return_value="browser content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-source",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://contoso.sharepoint.com/sites/Eng/SitePages/Home.aspx"]},
            created_at=_NOW,
            updated_at=_NOW,
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            content_fetcher=mock_content_fetcher,
            graph_fetcher=mock_graph_fetcher,
        )
        await orchestrator.refresh(source)

        mock_graph_fetcher.fetch.assert_called_once()
        mock_content_fetcher.fetch.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_graph_fetcher_called_with_url_from_source_config(self) -> None:
        """AC7: graph_fetcher.fetch() receives the exact URL from source.config['urls']."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        sp_url = "https://contoso.sharepoint.com/sites/HR/SitePages/Policy.aspx"
        mock_graph_fetcher = AsyncMock()
        mock_graph_fetcher.fetch = AsyncMock(return_value="policy text")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-url-test",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": [sp_url]},
            created_at=_NOW,
            updated_at=_NOW,
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_fetcher=mock_graph_fetcher,
        )
        await orchestrator.refresh(source)

        mock_graph_fetcher.fetch.assert_called_once_with(sp_url)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sharepoint_api_without_graph_fetcher_returns_noop_result(self) -> None:
        """AC7: SHAREPOINT_API source with no graph_fetcher injected → zero-count RefreshResult."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator, RefreshResult

        source = KnowledgeSource(
            name="sp-noop",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://contoso.sharepoint.com/sites/A/SitePages/B.aspx"]},
            created_at=_NOW,
            updated_at=_NOW,
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=MagicMock(),
        )
        result = await orchestrator.refresh(source)

        assert isinstance(result, RefreshResult)
        assert result.refreshed == 0
        assert result.failed == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_sharepoint_api_refresh_does_not_raise_unsupported_type_error(
        self,
    ) -> None:
        """AC7 boundary: SHAREPOINT_API with graph_fetcher does not raise ValueError for 'unsupported type'."""
        from owlbear_knowledge.models import KnowledgeSource, SourceType
        from owlbear_knowledge.refresh import RefreshOrchestrator

        mock_graph_fetcher = AsyncMock()
        mock_graph_fetcher.fetch = AsyncMock(return_value="content")
        mock_pipeline = MagicMock()
        mock_pipeline.ingest = AsyncMock(return_value=MagicMock(status="ok"))

        source = KnowledgeSource(
            name="sp-novaluerror",
            source_type=SourceType.SHAREPOINT_API,
            config={"urls": ["https://contoso.sharepoint.com/sites/A/SitePages/B.aspx"]},
            created_at=_NOW,
            updated_at=_NOW,
        )

        orchestrator = RefreshOrchestrator(
            store=MagicMock(),
            pipeline=mock_pipeline,
            graph_fetcher=mock_graph_fetcher,
        )
        result = await orchestrator.refresh(source)
        assert result is not None
