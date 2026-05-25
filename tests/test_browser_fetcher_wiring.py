from __future__ import annotations

# --- merged from tests/test_browser_fetcher_wiring_1325.py ---
"""Tests for task #1325: Browser fetcher wiring + RefreshOrchestrator fix.

AC coverage:
  AC1: app_lifespan passes a ContentFetcher instance to RefreshOrchestrator (td:2)
       - content_fetcher kwarg present in RefreshOrchestrator constructor call
       - Default fetcher is HttpxContentFetcher
       - A protocol-compatible alternative implementation is accepted
  AC2: app_lifespan passes graph_store to RefreshOrchestrator (td:1)
       - graph_store kwarg present in RefreshOrchestrator constructor call
  AC3: fetch_method maps "http"/""→ HttpxContentFetcher, "browser"→ protocol-compatible
       non-HTTP ContentFetcher placeholder (td:2)
       - select_content_fetcher("http") returns HttpxContentFetcher instance
       - select_content_fetcher("browser") returns ContentFetcher-compatible non-HTTP object
       - Empty / unset fetch_method defaults to HttpxContentFetcher
  AC4: RefreshOrchestrator.refresh completes without error when inter_doc_builder=None (td:1)
       - Refresh of AUTHENTICATED_WEB source with content_fetcher, no inter_doc_builder
       - _schedule_inter_doc_build safe-returns when inter_doc_builder is None
  AC5: refresh_source reads persisted fetch_method and selects corresponding ContentFetcher (td:2)
       - refresh_source with fetch_method="browser" invokes browser fetcher
       - refresh_source with fetch_method="http" invokes http fetcher
       - fetch_method read from the stored KnowledgeSource record at refresh time
  AC6: _BrowserContentFetcher.fetch() raises RuntimeError without embedding the source URL (td:1)
       - Error message must not contain the URL to prevent credential leakage into last_error
"""


from typing import Any, Self
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import owlbear_mcp_knowledge.server as server_module
from owlbear_knowledge.fetcher import HttpxContentFetcher
from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_knowledge.protocol import ContentFetcher
from owlbear_knowledge.refresh import RefreshOrchestrator
from owlbear_mcp_knowledge.server import app_lifespan, refresh_source


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = "2026-05-04T00:00:00+00:00"


def _make_source(
    *,
    source_type: SourceType = SourceType.AUTHENTICATED_WEB,
    fetch_method: str = "http",
    config: dict[str, Any] | None = None,
    enabled: bool = True,
) -> KnowledgeSource:
    """Factory for KnowledgeSource test fixtures."""
    return KnowledgeSource(
        name="test-source",
        source_type=source_type,
        fetch_method=fetch_method,
        config=config if config is not None else {"urls": ["https://example.com/page"]},
        enabled=enabled,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_mock_pipeline(
    *,
    status: str = "ok",
    document_id: str = "doc-id-1",
) -> MagicMock:
    """MagicMock IngestPipeline that returns a minimal IngestResult."""
    ingest_result = MagicMock()
    ingest_result.status = status
    ingest_result.document_id = document_id
    pipeline = MagicMock()
    pipeline.ingest = AsyncMock(return_value=ingest_result)
    return pipeline


def _make_mock_store(*sources: KnowledgeSource) -> MagicMock:
    """MagicMock KnowledgeSourceStore pre-loaded with *sources*."""
    store = MagicMock()
    store.list_all.return_value = list(sources)
    if sources:
        store.get.return_value = sources[0]
    return store


def _lifespan_heavy_patches() -> list[Any]:
    """Return patch objects for all heavy lifespan dependencies."""
    return [
        patch("owlbear_mcp_knowledge.server.init_db"),
        patch("owlbear_mcp_knowledge.server.GraphStore"),
        patch("owlbear_mcp_knowledge.server.QdrantVectorStore"),
        patch("owlbear_mcp_knowledge.server.BgeM3EmbeddingProvider"),
        patch("owlbear_mcp_knowledge.server.EntityExtractor"),
        patch("owlbear_mcp_knowledge.server.IntraDocGraphBuilder"),
        patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever"),
        patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        patch("owlbear_mcp_knowledge.server.DocumentStore"),
        patch("owlbear_mcp_knowledge.server.TextChunker"),
        patch("owlbear_mcp_knowledge.server.KnowledgeSourceStore"),
        patch("owlbear_mcp_knowledge.server.ContentInjectionGuard"),
        patch("owlbear_mcp_knowledge.server.IngestPipeline"),
    ]


class _PatchStack:
    """Enter a list of context managers, exit them all on __exit__."""

    def __init__(self, managers: list[Any]) -> None:
        self._managers = managers
        self._active: list[Any] = []

    def __enter__(self) -> Self:
        for mgr in self._managers:
            self._active.append(mgr.__enter__())
        return self

    def __exit__(self, *exc_info: object) -> None:
        for mgr in reversed(self._managers):
            mgr.__exit__(*exc_info)


# ---------------------------------------------------------------------------
# TestFromAC_ContentFetcherInjection
# AC1: app_lifespan passes a ContentFetcher instance to RefreshOrchestrator (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_ContentFetcherInjection:
    """AC1: app_lifespan must pass content_fetcher= kwarg to RefreshOrchestrator.

    Currently FAILS: RefreshOrchestrator is constructed without content_fetcher
    at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:308.
    """

    @pytest.fixture(autouse=True)
    def _patch_home(self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    @pytest.mark.asyncio
    async def test_app_lifespan_passes_content_fetcher_to_orchestrator(self) -> None:
        """RefreshOrchestrator receives a non-None content_fetcher kwarg in app_lifespan.

        Currently FAILS: content_fetcher is not passed in the constructor call.
        """
        orchestrator_cls = MagicMock(name="RefreshOrchestrator")
        patches = _lifespan_heavy_patches()
        with (
            patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", orchestrator_cls),
            _PatchStack(patches),
        ):
            async with app_lifespan(MagicMock()):
                pass

        orchestrator_cls.assert_called_once()
        _, kwargs = orchestrator_cls.call_args
        assert "content_fetcher" in kwargs, "RefreshOrchestrator must receive content_fetcher= kwarg from app_lifespan"
        assert kwargs["content_fetcher"] is not None, "content_fetcher must not be None"

    @pytest.mark.asyncio
    async def test_app_lifespan_httpx_fetcher_is_default_content_fetcher(self) -> None:
        """Without a browser override, app_lifespan supplies an HttpxContentFetcher.

        Currently FAILS: content_fetcher is not wired at all.
        """
        orchestrator_cls = MagicMock(name="RefreshOrchestrator")
        patches = _lifespan_heavy_patches()
        with (
            patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", orchestrator_cls),
            _PatchStack(patches),
        ):
            async with app_lifespan(MagicMock()):
                pass

        _, kwargs = orchestrator_cls.call_args
        content_fetcher = kwargs.get("content_fetcher")
        assert isinstance(content_fetcher, HttpxContentFetcher), (
            f"Default content_fetcher must be HttpxContentFetcher, got {type(content_fetcher)}"
        )

    @pytest.mark.asyncio
    async def test_browser_content_fetcher_mock_satisfies_content_fetcher_protocol(
        self,
    ) -> None:
        """A BrowserContentFetcher mock satisfies ContentFetcher and can be injected.

        Contract: app_lifespan must accept any object with async fetch(url) -> str.
        Currently FAILS: content_fetcher is not passed to RefreshOrchestrator.
        """
        browser_mock = AsyncMock()
        browser_mock.fetch = AsyncMock(return_value="page-content")

        # BrowserContentFetcher mock satisfies ContentFetcher protocol
        assert isinstance(browser_mock, ContentFetcher), (
            "browser mock with async fetch(url) must satisfy ContentFetcher protocol"
        )

        orchestrator_cls = MagicMock(name="RefreshOrchestrator")
        patches = _lifespan_heavy_patches()
        with (
            patch("owlbear_mcp_knowledge.server.RefreshOrchestrator", orchestrator_cls),
            _PatchStack(patches),
        ):
            async with app_lifespan(MagicMock()):
                pass

        _, kwargs = orchestrator_cls.call_args
        # The wired content_fetcher must satisfy the ContentFetcher protocol
        actual_fetcher = kwargs.get("content_fetcher")
        assert isinstance(actual_fetcher, ContentFetcher), (
            f"content_fetcher passed to RefreshOrchestrator must satisfy ContentFetcher, got {type(actual_fetcher)}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_FetchMethodSelection
# AC3: fetcher selection logic maps fetch_method to concrete ContentFetcher (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_FetchMethodSelection:
    """AC3: A selection function maps fetch_method string to ContentFetcher.

    Currently FAILS: no select_content_fetcher function exists in server module.
    """

    def test_select_content_fetcher_function_is_exported(self) -> None:
        """server module exposes a select_content_fetcher callable.

        Currently FAILS: function does not exist.
        """
        fn = getattr(server_module, "select_content_fetcher", None)
        assert fn is not None, "owlbear_mcp_knowledge.server must expose select_content_fetcher"
        assert callable(fn), "select_content_fetcher must be callable"

    def test_fetch_method_http_selects_httpx_content_fetcher(self) -> None:
        """select_content_fetcher('http') returns an HttpxContentFetcher instance.

        Currently FAILS: function does not exist.
        """
        select_fn = getattr(server_module, "select_content_fetcher", None)
        assert select_fn is not None, "select_content_fetcher not found — see AC3"
        fetcher = select_fn("http")
        assert isinstance(fetcher, HttpxContentFetcher), (
            f"'http' fetch_method must map to HttpxContentFetcher, got {type(fetcher)}"
        )

    def test_fetch_method_browser_selects_content_fetcher_protocol_impl(self) -> None:
        """select_content_fetcher('browser') returns a ContentFetcher-compatible object.

        Currently FAILS: function does not exist.
        """
        select_fn = getattr(server_module, "select_content_fetcher", None)
        assert select_fn is not None, "select_content_fetcher not found — see AC3"
        fetcher = select_fn("browser")
        assert fetcher is not None, "select_content_fetcher('browser') must not return None"
        assert isinstance(fetcher, ContentFetcher), (
            f"'browser' fetch_method must map to a ContentFetcher impl, got {type(fetcher)}"
        )
        # Must NOT be the HTTP implementation
        assert not isinstance(fetcher, HttpxContentFetcher), (
            "'browser' fetch_method must NOT return HttpxContentFetcher"
        )

    def test_fetch_method_empty_string_defaults_to_httpx_fetcher(self) -> None:
        """select_content_fetcher('') (unset) defaults to HttpxContentFetcher.

        Empty fetch_method means standard HTTP refresh — currently FAILS because
        select_content_fetcher does not exist.
        """
        select_fn = getattr(server_module, "select_content_fetcher", None)
        assert select_fn is not None, "select_content_fetcher not found — see AC3"
        fetcher = select_fn("")
        assert isinstance(fetcher, HttpxContentFetcher), (
            f"Empty fetch_method must default to HttpxContentFetcher, got {type(fetcher)}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_RefreshSourceFetchMethodIntegration
# AC5: refresh_source reads fetch_method and selects the corresponding ContentFetcher (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_RefreshSourceFetchMethodIntegration:
    """AC5: refresh_source MCP tool selects correct fetcher based on fetch_method.

    After #1326, the refresh path calls select_content_fetcher(source.fetch_method)
    to obtain the per-source fetcher. These tests patch select_content_fetcher so
    the test-controlled mocks are on the actual call path.

    Currently FAILS: select_content_fetcher does not exist in server module
    (patch raises AttributeError). Even after it exists, the wiring must be added
    to the refresh path before the fetch() assertions can pass.
    """

    @pytest.mark.asyncio
    async def test_refresh_source_browser_method_invokes_browser_content_fetcher(
        self,
    ) -> None:
        """When source.fetch_method='browser', refresh_source invokes the browser fetcher.

        Patches select_content_fetcher so the browser mock is on the actual call
        path taken by the refresh implementation.

        Currently FAILS: select_content_fetcher does not exist in server module;
        patch raises AttributeError before any assertion runs.
        """
        browser_fetcher = AsyncMock()
        browser_fetcher.fetch = AsyncMock(return_value="browser page content")

        source = _make_source(
            source_type=SourceType.AUTHENTICATED_WEB,
            fetch_method="browser",
        )
        pipeline = _make_mock_pipeline(status="ok")
        store = _make_mock_store(source)
        orchestrator = RefreshOrchestrator(store=store, pipeline=pipeline)

        app_ctx = MagicMock()
        app_ctx.source_store = store
        app_ctx.refresh_orchestrator = orchestrator

        mcp_ctx = MagicMock()
        mcp_ctx.request_context.lifespan_context = app_ctx

        # Patch select_content_fetcher to return the browser mock.
        # FAILS now: AttributeError (function not in server module).
        # After #1326 adds select_content_fetcher AND wires it in the refresh path,
        # the browser mock's fetch() gets called and the assertion passes.
        with patch(
            "owlbear_mcp_knowledge.server.select_content_fetcher",
            return_value=browser_fetcher,
        ):
            await refresh_source(mcp_ctx, source_id=source.id)

        browser_fetcher.fetch.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_source_http_method_invokes_httpx_content_fetcher(
        self,
    ) -> None:
        """When source.fetch_method='http', refresh_source invokes the http fetcher mock.

        Patches select_content_fetcher so the http mock is on the actual call path.

        Currently FAILS: select_content_fetcher does not exist in server module.
        """
        http_fetcher = AsyncMock()
        http_fetcher.fetch = AsyncMock(return_value="http page content")

        source = _make_source(
            source_type=SourceType.AUTHENTICATED_WEB,
            fetch_method="http",
        )
        pipeline = _make_mock_pipeline(status="ok")
        store = _make_mock_store(source)
        orchestrator = RefreshOrchestrator(store=store, pipeline=pipeline)

        app_ctx = MagicMock()
        app_ctx.source_store = store
        app_ctx.refresh_orchestrator = orchestrator

        mcp_ctx = MagicMock()
        mcp_ctx.request_context.lifespan_context = app_ctx

        # Patch select_content_fetcher to return the http mock.
        # FAILS now: AttributeError (function not in server module).
        with patch(
            "owlbear_mcp_knowledge.server.select_content_fetcher",
            return_value=http_fetcher,
        ):
            await refresh_source(mcp_ctx, source_id=source.id)

        http_fetcher.fetch.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_source_reads_fetch_method_from_persisted_source(
        self,
    ) -> None:
        """refresh_source selects different fetchers for sources with different fetch_method.

        Verifies that fetcher selection is driven by the persisted KnowledgeSource
        record's fetch_method field: "http" and "browser" must reach different mocks.

        Patches select_content_fetcher with a side_effect that dispatches on
        the method argument so both mocks are on the correct call paths.

        Currently FAILS: select_content_fetcher does not exist in server module.
        """
        http_fetcher = AsyncMock()
        http_fetcher.fetch = AsyncMock(return_value="http content")
        browser_fetcher = AsyncMock()
        browser_fetcher.fetch = AsyncMock(return_value="browser content")

        source_http = _make_source(fetch_method="http")
        source_browser = _make_source(fetch_method="browser")

        pipeline = _make_mock_pipeline(status="ok")
        store_http = _make_mock_store(source_http)
        store_browser = _make_mock_store(source_browser)

        orch_http = RefreshOrchestrator(store=store_http, pipeline=pipeline)
        orch_browser = RefreshOrchestrator(store=store_browser, pipeline=pipeline)

        ctx_http = MagicMock()
        ctx_http.source_store = store_http
        ctx_http.refresh_orchestrator = orch_http
        mcp_http = MagicMock()
        mcp_http.request_context.lifespan_context = ctx_http

        ctx_browser = MagicMock()
        ctx_browser.source_store = store_browser
        ctx_browser.refresh_orchestrator = orch_browser
        mcp_browser = MagicMock()
        mcp_browser.request_context.lifespan_context = ctx_browser

        def _select(method: str) -> object:
            return browser_fetcher if method == "browser" else http_fetcher

        # Patch select_content_fetcher with side_effect so each call dispatches
        # to the right mock based on fetch_method.
        # FAILS now: AttributeError (function not in server module).
        with patch("owlbear_mcp_knowledge.server.select_content_fetcher", side_effect=_select):
            await refresh_source(mcp_http, source_id=source_http.id)
            await refresh_source(mcp_browser, source_id=source_browser.id)

        # Each fetcher must have been called for its respective source.
        http_fetcher.fetch.assert_called()
        browser_fetcher.fetch.assert_called()
