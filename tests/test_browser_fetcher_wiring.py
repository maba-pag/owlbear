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
        patch("owlbear_mcp_knowledge.server.InterDocGraphBuilder"),
        patch("owlbear_mcp_knowledge.server.GraphAugmentedRetriever"),
        patch("owlbear_mcp_knowledge.server.KnowledgeQueryService"),
        patch("owlbear_mcp_knowledge.server.DocumentStore"),
        patch("owlbear_mcp_knowledge.server.TextChunker"),
        patch("owlbear_mcp_knowledge.server.KnowledgeSourceStore"),
        patch("owlbear_mcp_knowledge.server.ContentInjectionGuard"),
        patch("owlbear_mcp_knowledge.server.IngestPipeline"),
        patch("owlbear_mcp_knowledge.server.BookmarkStore"),
        patch("owlbear_mcp_knowledge.server.SourceEvaluator"),
        patch("owlbear_mcp_knowledge.server.BookmarkPipeline"),
        patch("owlbear_mcp_knowledge.server.ConsolidationService"),
        patch(
            "owlbear_mcp_knowledge.server.make_evaluate_fn",
            return_value=AsyncMock(),
        ),
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
    def _patch_home(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        assert "content_fetcher" in kwargs, (
            "RefreshOrchestrator must receive content_fetcher= kwarg from app_lifespan"
        )
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
            f"content_fetcher passed to RefreshOrchestrator must satisfy ContentFetcher, "
            f"got {type(actual_fetcher)}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_GraphStoreInjection
# AC2: app_lifespan passes graph_store to RefreshOrchestrator for inter-doc edges (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_GraphStoreInjection:
    """AC2: app_lifespan must pass graph_store= kwarg to RefreshOrchestrator.

    Currently FAILS: RefreshOrchestrator is constructed without graph_store
    at serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:308.
    """

    @pytest.fixture(autouse=True)
    def _patch_home(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    @pytest.mark.asyncio
    async def test_app_lifespan_passes_graph_store_to_refresh_orchestrator(
        self,
    ) -> None:
        """RefreshOrchestrator receives the same GraphStore instance as AppContext.

        Currently FAILS: graph_store is not passed in the RefreshOrchestrator
        constructor call at server.py:308.
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
        assert "graph_store" in kwargs, (
            "RefreshOrchestrator must receive graph_store= kwarg from app_lifespan "
            "(needed for inter-doc edge building after refresh)"
        )
        assert kwargs["graph_store"] is not None, (
            "graph_store must not be None — it must be the same GraphStore used by AppContext"
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
        assert fn is not None, (
            "owlbear_mcp_knowledge.server must expose select_content_fetcher"
        )
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
        assert fetcher is not None, (
            "select_content_fetcher('browser') must not return None"
        )
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
# TestFromAC_RefreshWithoutInterDocBuilder
# AC4: RefreshOrchestrator.refresh completes without error when inter_doc_builder=None (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_RefreshWithoutInterDocBuilder:
    """AC4: refresh_source MCP tool completes without error when inter_doc_builder=None.

    The lifespan-created RefreshOrchestrator omits inter_doc_builder when no
    structured_extractor is configured (no LLM API key). After AC1 wires
    content_fetcher, the refresh must still succeed for AUTHENTICATED_WEB sources.

    Currently FAILS: app_lifespan does not pass content_fetcher= to RefreshOrchestrator
    (AC1 gap), so _handle_authenticated_web returns a no-op (refreshed=0 instead of 1).
    """

    @pytest.fixture(autouse=True)
    def _patch_home(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        monkeypatch.delenv("OWLBEAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    @pytest.mark.asyncio
    async def test_refresh_source_completes_when_inter_doc_builder_is_none(
        self,
    ) -> None:
        """refresh with content_fetcher but no inter_doc_builder returns refreshed=1.

        Tests that _schedule_inter_doc_build safe-returns when inter_doc_builder=None,
        allowing a full refresh to complete. Uses the lifespan context so that the
        AC1 wiring of content_fetcher= is exercised end-to-end.

        Patches HttpxContentFetcher.fetch to return deterministic content so the
        test does not make real HTTP calls.

        Currently FAILS: content_fetcher is not wired in app_lifespan (AC1 gap),
        so _handle_authenticated_web returns refreshed=0 instead of 1.
        """
        source = _make_source(
            source_type=SourceType.AUTHENTICATED_WEB,
            fetch_method="http",
        )
        mock_source_store = _make_mock_store(source)
        pipeline = _make_mock_pipeline(status="ok")

        patches = _lifespan_heavy_patches()
        # Exclude both KnowledgeSourceStore and IngestPipeline so our explicit
        # controlled mocks are not shadowed by the generic heavy-patch stubs.
        patches_filtered = [
            p
            for p in patches
            if "KnowledgeSourceStore" not in str(p) and "IngestPipeline" not in str(p)
        ]

        with (
            patch(
                "owlbear_mcp_knowledge.server.KnowledgeSourceStore",
                return_value=mock_source_store,
            ),
            patch("owlbear_mcp_knowledge.server.IngestPipeline", return_value=pipeline),
            # Patch fetch so no real HTTP request is made; fetch_method="http" will
            # use HttpxContentFetcher after AC1 is implemented.
            patch(
                "owlbear_knowledge.fetcher.HttpxContentFetcher.fetch",
                new=AsyncMock(return_value="<html>page content</html>"),
            ),
            _PatchStack(patches_filtered),
        ):
            async with app_lifespan(MagicMock()) as ctx:
                orchestrator = ctx.refresh_orchestrator
                # inter_doc_builder is None (no LLM API key set via monkeypatch)
                result = await orchestrator.refresh(source)

        # After AC1 wires content_fetcher=HttpxContentFetcher(), the patched fetch
        # returns "page content" → pipeline mock returns ok → refreshed=1.
        # _schedule_inter_doc_build safe-returns (inter_doc_builder=None) without error.
        # Currently FAILS: content_fetcher=None → no-op → refreshed=0.
        assert result.refreshed == 1, (
            f"refresh must succeed (refreshed=1) when content_fetcher is wired "
            f"and inter_doc_builder=None; got refreshed={result.refreshed}"
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
        with patch(
            "owlbear_mcp_knowledge.server.select_content_fetcher", side_effect=_select
        ):
            await refresh_source(mcp_http, source_id=source_http.id)
            await refresh_source(mcp_browser, source_id=source_browser.id)

        # Each fetcher must have been called for its respective source.
        http_fetcher.fetch.assert_called()
        browser_fetcher.fetch.assert_called()


# ---------------------------------------------------------------------------
# TestFromAC_BrowserFetcherErrorSanitization
# AC6: _BrowserContentFetcher.fetch() raises RuntimeError without embedding source URL (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_BrowserFetcherErrorSanitization:
    """AC6: _BrowserContentFetcher.fetch() error message must not contain the source URL.

    Currently FAILS: server.py:63 embeds {url!r} in the RuntimeError message.
    URLs can carry embedded credentials or query tokens; echoing the URL into the
    message causes str(exc) → errors → last_error persistence to leak secrets.

    Builder fix: remove {url!r} from the f-string so the message says only
    "browser fetcher not wired" (or similar) without the URL.
    """

    @pytest.mark.asyncio
    async def test_browser_fetcher_error_does_not_embed_source_url(self) -> None:
        """RuntimeError from _BrowserContentFetcher.fetch() must not contain the URL.

        Calling fetch() with a URL containing a sensitive token must raise
        RuntimeError whose message does not echo the URL back, preventing
        credential leakage via errors.append(str(exc)) → last_error persistence.

        Currently FAILS: server.py:63 embeds f\"...URL {url!r}\" in the message,
        so the full URL (including query tokens) appears in the error string.
        """
        secret_url = "https://secret.example.com/token?key=abc"
        fetcher = server_module._BrowserContentFetcher()

        with pytest.raises(RuntimeError) as exc_info:
            await fetcher.fetch(secret_url)

        error_msg = str(exc_info.value)
        assert secret_url not in error_msg, (
            f"RuntimeError message must not contain the source URL to prevent "
            f"credential leakage into persisted last_error; got: {error_msg!r}"
        )


# --- merged from tests/test_browser_fetcher_wiring_1326.py ---
"""Tests for task #1326: inter_doc_builder=None kwargs assertion.

AC coverage:
  AC3 (refined): inter_doc_builder=None passed to RefreshOrchestrator in both
       app_lifespan and refresh_source; asserted via constructor kwargs check
       (same pattern as AC1 content_fetcher kwarg assertion in
       test_browser_fetcher_wiring_1325.py:174-176) — must fail if
       inter_doc_builder is changed to non-None regardless of API key env vars
       (td:1)

These tests are discriminating: they inspect RefreshOrchestrator constructor
kwargs directly and do NOT rely on env var clearing to prove the behaviour.
If inter_doc_builder is changed to non-None in either wiring site, both tests
fail regardless of which API keys are present in the environment.
"""


from typing import Any, Self
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_knowledge.models import KnowledgeSource, SourceType
from owlbear_mcp_knowledge.server import app_lifespan, refresh_source


# ---------------------------------------------------------------------------
# Helpers (mirrors test_browser_fetcher_wiring_1325 for self-contained clarity)
# ---------------------------------------------------------------------------


def _make_source_1326(
    *,
    source_type: SourceType = SourceType.AUTHENTICATED_WEB,
    fetch_method: str = "http",
) -> KnowledgeSource:
    """Factory for KnowledgeSource test fixtures."""
    return KnowledgeSource(
        name="test-source",
        source_type=source_type,
        fetch_method=fetch_method,
        config={"urls": ["https://example.com/page"]},
        enabled=True,
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# TestFromAC_InterDocBuilderNoneWiring
# AC3 (refined): kwargs-assertion — independent of env var state
# ---------------------------------------------------------------------------


class TestFromAC_InterDocBuilderNoneWiring:
    """AC3 (refined): RefreshOrchestrator must receive inter_doc_builder=None in both
    app_lifespan and refresh_source wiring sites.

    Discriminating pattern (same as AC1 in test_browser_fetcher_wiring_1325.py):
    - Patch RefreshOrchestrator with a MagicMock
    - Run the code under test
    - Inspect constructor kwargs directly
    - Assert inter_doc_builder kwarg is present and equals None

    These tests do NOT clear API key env vars (no monkeypatch.delenv), so they
    remain discriminating regardless of which keys are set.  If inter_doc_builder
    is changed to non-None in either site the test fails — the env-var escape
    hatch used by the old test is closed.
    """

    @pytest.fixture(autouse=True)
    def _patch_home(
        self, tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Redirect home to avoid touching real user data; no env var clearing.
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    @pytest.mark.asyncio
    async def test_app_lifespan_inter_doc_builder_kwarg_is_none(self) -> None:
        """app_lifespan passes inter_doc_builder=None to RefreshOrchestrator.

        Patches RefreshOrchestrator to capture constructor kwargs, then asserts
        the inter_doc_builder kwarg is present and None.  Does not rely on API
        key env vars — the assertion is on the kwarg value itself.

        Fails if inter_doc_builder is changed to a non-None value in app_lifespan.
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
        assert "inter_doc_builder" in kwargs, (
            "RefreshOrchestrator must receive inter_doc_builder= kwarg from app_lifespan; "
            "kwarg was absent"
        )
        assert kwargs["inter_doc_builder"] is None, (
            f"inter_doc_builder kwarg must be None in app_lifespan wiring, "
            f"got {kwargs['inter_doc_builder']!r}; "
            "enrichment must not be enabled in the lifespan orchestrator"
        )

    @pytest.mark.asyncio
    async def test_refresh_source_inter_doc_builder_kwarg_is_none(self) -> None:
        """refresh_source passes inter_doc_builder=None to its per-run RefreshOrchestrator.

        Patches RefreshOrchestrator to capture constructor kwargs, then asserts
        the inter_doc_builder kwarg is present and None.  Does not rely on API
        key env vars.

        Fails if inter_doc_builder is changed to a non-None value in refresh_source.
        """
        source = _make_source_1326(fetch_method="http")

        refresh_result = MagicMock()
        refresh_result.refreshed = 1
        refresh_result.skipped = 0
        refresh_result.failed = 0
        refresh_result.source_id = source.id

        orchestrator_cls = MagicMock(name="RefreshOrchestrator")
        orchestrator_instance = MagicMock()
        orchestrator_instance.refresh = AsyncMock(return_value=refresh_result)
        orchestrator_cls.return_value = orchestrator_instance

        app_ctx = MagicMock()
        app_ctx.source_store = MagicMock()
        app_ctx.source_store.get.return_value = source
        app_ctx.refresh_orchestrator = MagicMock()  # non-None → guard passes
        app_ctx.ingest_pipeline = MagicMock()  # non-None → guard passes
        app_ctx.graph_store = MagicMock()

        mcp_ctx = MagicMock()
        mcp_ctx.request_context.lifespan_context = app_ctx

        with patch(
            "owlbear_mcp_knowledge.server.RefreshOrchestrator", orchestrator_cls
        ):
            await refresh_source(mcp_ctx, source_id=source.id)

        orchestrator_cls.assert_called_once()
        _, kwargs = orchestrator_cls.call_args
        assert "inter_doc_builder" in kwargs, (
            "RefreshOrchestrator must receive inter_doc_builder= kwarg from refresh_source; "
            "kwarg was absent"
        )
        assert kwargs["inter_doc_builder"] is None, (
            f"inter_doc_builder kwarg must be None in refresh_source wiring, "
            f"got {kwargs['inter_doc_builder']!r}; "
            "enrichment must not be enabled in per-run refresh orchestrator"
        )
