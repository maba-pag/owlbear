"""RED-phase tests for #871: Pivot MCP browser server from CDPConnectionManager to PlaywrightLauncher.

AC coverage:
  AC1  server.py imports PlaywrightLauncher from owlbear_browser.playwright_launcher
  AC2  AppContext field: launcher: PlaywrightLauncher | None (replaces cdp field)
  AC3  Lifespan creates PlaywrightLauncher instead of CDPConnectionManager
  AC4  BrowserContentFetcher receives Playwright context (launcher's BrowserContext) in lifespan
  AC5  No imports of owlbear_browser.cdp remain in serve/mcp-browser/

All tests FAIL on current HEAD:
  - AC1: owlbear_browser.playwright_launcher does not exist → ImportError
  - AC2: AppContext has cdp field (not launcher); no launcher field → AssertionError
  - AC3: patch("owlbear_mcp_browser.server.PlaywrightLauncher") raises AttributeError
         (PlaywrightLauncher is not in server module namespace)
  - AC4: Same AttributeError on PlaywrightLauncher patch; fetcher wiring uses CDP not Playwright
  - AC5: server.py imports CDPConnectionManager from owlbear_browser.cdp → assertions fail

Notes:
  AC6 (update existing tests): test_mcp_browser_session_837, test_mcp_browser_session_853,
  test_mcp_browser_session_854, and test_mcp_browser_lifespan_857 contain _make_mock_cdp /
  CDPConnectionManager patch patterns that the BUILDER must update during GREEN phase.
  AC7 (all tests pass) and AC8 (ruff clean) are verified during GREEN phase.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_page() -> MagicMock:
    """Return a mock Playwright Page with all tool-facing async methods."""
    page = MagicMock()
    page.url = "https://example.com/"
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value="<html><body><h1>Test</h1></body></html>")
    page.close = AsyncMock()
    locator = MagicMock()
    locator.click = AsyncMock()
    locator.fill = AsyncMock()
    locator.select_option = AsyncMock()
    locator.aria_snapshot = AsyncMock(return_value="- heading 'Test' [level=1]")
    page.locator = MagicMock(return_value=locator)
    return page


def _make_mock_browser_context(page: MagicMock) -> MagicMock:
    """Return a mock Playwright BrowserContext that can produce pages."""
    ctx = MagicMock()
    ctx.new_page = AsyncMock(return_value=page)
    ctx.close = AsyncMock()
    return ctx


def _make_mock_launcher(page: MagicMock) -> MagicMock:
    """Return a mock PlaywrightLauncher wired with a BrowserContext and page.

    Supports both async-CM (async with launcher) and explicit launch()/close()
    patterns so tests remain valid regardless of which pattern the builder chooses.
    """
    context = _make_mock_browser_context(page)
    launcher = MagicMock()
    launcher.context = context
    # Async context-manager protocol
    launcher.__aenter__ = AsyncMock(return_value=launcher)
    launcher.__aexit__ = AsyncMock(return_value=False)
    # Explicit launch / close protocol
    launcher.launch = AsyncMock()
    launcher.close = AsyncMock()
    return launcher


def _make_failing_launcher() -> MagicMock:
    """Return a mock PlaywrightLauncher whose startup always fails."""
    launcher = MagicMock()
    launcher.__aenter__ = AsyncMock(side_effect=RuntimeError("playwright unavailable"))
    launcher.__aexit__ = AsyncMock(return_value=False)
    launcher.launch = AsyncMock(side_effect=RuntimeError("playwright unavailable"))
    launcher.close = AsyncMock()
    return launcher


# ===========================================================================
# TestFromAC_PlaywrightLauncherImport — AC1
# ===========================================================================


class TestFromAC_PlaywrightLauncherImport:
    """AC1: server.py must import PlaywrightLauncher from owlbear_browser.playwright_launcher."""

    def test_playwright_launcher_module_importable(self) -> None:
        """owlbear_browser.playwright_launcher module exists and is importable.

        FAILS: owlbear_browser.playwright_launcher does not exist → ImportError.
        """
        import owlbear_browser.playwright_launcher  # noqa: F401

    def test_playwright_launcher_class_importable(self) -> None:
        """PlaywrightLauncher class is accessible from owlbear_browser.playwright_launcher.

        FAILS: owlbear_browser.playwright_launcher does not exist → ImportError.
        """
        from owlbear_browser.playwright_launcher import PlaywrightLauncher  # noqa: F401

    def test_server_module_exposes_playwright_launcher_at_runtime(self) -> None:
        """owlbear_mcp_browser.server must have PlaywrightLauncher as a runtime name.

        A TYPE_CHECKING-only import is insufficient — lifespan must instantiate it.

        FAILS: server.py does not import PlaywrightLauncher → hasattr returns False.
        """
        import owlbear_mcp_browser.server as server_module

        assert hasattr(server_module, "PlaywrightLauncher"), (
            "server module must expose PlaywrightLauncher at runtime; "
            "it is used in app_lifespan and must be patchable by tests"
        )

    def test_server_module_does_not_expose_cdp_connection_manager(self) -> None:
        """owlbear_mcp_browser.server must NOT have CDPConnectionManager after the pivot.

        FAILS: server.py currently imports CDPConnectionManager → hasattr returns True.
        """
        import owlbear_mcp_browser.server as server_module

        assert not hasattr(server_module, "CDPConnectionManager"), (
            "CDPConnectionManager must not remain in server module namespace after pivot; it is currently importable"
        )


# ===========================================================================
# TestFromAC_AppContextLauncherField — AC2
# ===========================================================================


class TestFromAC_AppContextLauncherField:
    """AC2: AppContext must expose launcher: PlaywrightLauncher | None, replacing cdp."""

    def test_appcontext_has_launcher_field(self) -> None:
        """AppContext dataclass must declare a 'launcher' field.

        FAILS: AppContext has no launcher field → AssertionError.
        """
        from owlbear_mcp_browser.server import AppContext

        fields = {f.name for f in dataclasses.fields(AppContext)}
        assert "launcher" in fields, f"'launcher' field missing from AppContext; found: {sorted(fields)}"

    def test_appcontext_launcher_defaults_to_none(self) -> None:
        """AppContext.launcher defaults to None when not supplied (graceful-degrade case).

        FAILS: no launcher field → AttributeError.
        """
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        ctx = AppContext(allowlist=DomainAllowlist(domains=[]))
        assert ctx.launcher is None

    def test_appcontext_accepts_launcher_kwarg(self) -> None:
        """AppContext constructor stores launcher= keyword argument.

        FAILS: no launcher field → TypeError (unexpected keyword argument).
        """
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import AppContext

        mock_launcher = MagicMock()
        ctx = AppContext(allowlist=DomainAllowlist(domains=[]), launcher=mock_launcher)
        assert ctx.launcher is mock_launcher

    def test_appcontext_cdp_field_removed(self) -> None:
        """AppContext must NOT have a 'cdp' field after the Playwright pivot.

        FAILS: AppContext currently has cdp field → assertion fails.
        """
        from owlbear_mcp_browser.server import AppContext

        fields = {f.name for f in dataclasses.fields(AppContext)}
        assert "cdp" not in fields, f"'cdp' field must be removed from AppContext after pivot; found: {sorted(fields)}"

    def test_appcontext_annotations_do_not_reference_cdp_connection_manager(self) -> None:
        """AppContext type annotations must not reference CDPConnectionManager after pivot.

        FAILS: AppContext.__annotations__['cdp'] → CDPConnectionManager | None.
        """
        from owlbear_mcp_browser.server import AppContext

        annotations_str = str(AppContext.__annotations__)
        assert "CDPConnectionManager" not in annotations_str, (
            f"AppContext annotations must not reference CDPConnectionManager after pivot; found in: {annotations_str}"
        )


# ===========================================================================
# TestFromAC_LifespanCreatesPlaywrightLauncher — AC3
# ===========================================================================


class TestFromAC_LifespanCreatesPlaywrightLauncher:
    """AC3: app_lifespan creates PlaywrightLauncher (not CDPConnectionManager)."""

    @pytest.mark.asyncio
    async def test_lifespan_sets_launcher_not_none_on_success(self) -> None:
        """Successful PlaywrightLauncher start: AppContext.launcher is not None.

        FAILS: patch target owlbear_mcp_browser.server.PlaywrightLauncher raises
        AttributeError — PlaywrightLauncher not imported in server.py.
        """
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.launcher is not None

    @pytest.mark.asyncio
    async def test_lifespan_sets_page_not_none_on_success(self) -> None:
        """Successful PlaywrightLauncher start: AppContext.page is not None.

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.page is not None

    @pytest.mark.asyncio
    async def test_lifespan_yields_launcher_none_on_failure(self) -> None:
        """PlaywrightLauncher startup failure: AppContext.launcher degrades to None.

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        from owlbear_mcp_browser.server import app_lifespan

        with patch(
            "owlbear_mcp_browser.server.PlaywrightLauncher",
            return_value=_make_failing_launcher(),
        ):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.launcher is None

    @pytest.mark.asyncio
    async def test_lifespan_yields_page_none_on_failure(self) -> None:
        """PlaywrightLauncher startup failure: AppContext.page degrades to None.

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        from owlbear_mcp_browser.server import app_lifespan

        with patch(
            "owlbear_mcp_browser.server.PlaywrightLauncher",
            return_value=_make_failing_launcher(),
        ):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.page is None

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_closes_launcher_on_clean_exit(self) -> None:
        """app_lifespan cleanup must stop PlaywrightLauncher after yielding.

        Accepts either async-CM exit (__aexit__) or explicit close() call.

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()):
                pass

        launcher_closed = mock_launcher.__aexit__.call_count > 0 or mock_launcher.close.await_count > 0
        assert launcher_closed, (
            "PlaywrightLauncher must be closed during lifespan cleanup; neither __aexit__ nor close() was called"
        )

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_closes_launcher_on_exception(self) -> None:
        """app_lifespan cleanup must close PlaywrightLauncher even when body raises.

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        _body_err = "simulated body error"
        with (
            patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher),
            pytest.raises(RuntimeError, match=_body_err),
        ):
            async with app_lifespan(MagicMock()):
                raise RuntimeError(_body_err)

        launcher_closed = mock_launcher.__aexit__.call_count > 0 or mock_launcher.close.await_count > 0
        assert launcher_closed, (
            "PlaywrightLauncher must be closed even when lifespan body raises; neither __aexit__ nor close() was called"
        )

    @pytest.mark.asyncio
    async def test_lifespan_does_not_read_browser_cdp_port_env(self) -> None:
        """app_lifespan must ignore BROWSER_CDP_PORT after pivot to Playwright.

        CDPConnectionManager required the CDP port; PlaywrightLauncher uses
        a persistent context and does not connect via CDP port at all.
        Setting an invalid port must not cause lifespan startup to fail.

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        import os

        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with (
            patch.dict(os.environ, {"BROWSER_CDP_PORT": "99999"}),
            patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher),
        ):
            async with app_lifespan(MagicMock()) as ctx:
                # Lifespan must succeed without trying to use the CDP port
                assert ctx.page is not None


# ===========================================================================
# TestFromAC_BrowserFetcherPlaywrightContext — AC4
# ===========================================================================


class TestFromAC_BrowserFetcherPlaywrightContext:
    """AC4: BrowserContentFetcher receives Playwright context (not CDP manager) in lifespan."""

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_not_none_on_success(self) -> None:
        """AppContext.fetcher is set (not None) on successful PlaywrightLauncher start.

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.fetcher is not None

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_constructed_with_playwright_context(self) -> None:
        """BrowserContentFetcher is called with PlaywrightLauncher.context, not CDPConnectionManager.

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        from owlbear_mcp_browser.server import app_lifespan

        mock_page = _make_mock_page()
        mock_launcher = _make_mock_launcher(mock_page)
        mock_fetcher_cls = MagicMock(return_value=MagicMock())

        with (
            patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher),
            patch("owlbear_mcp_browser.server.BrowserContentFetcher", mock_fetcher_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        assert mock_fetcher_cls.called, "BrowserContentFetcher must be instantiated in lifespan; not called"
        call_arg = (
            mock_fetcher_cls.call_args.args[0]
            if mock_fetcher_cls.call_args.args
            else next(iter(mock_fetcher_cls.call_args.kwargs.values()), None)
        )
        assert call_arg is mock_launcher.context, (
            f"BrowserContentFetcher must receive launcher.context specifically; got {call_arg!r}"
        )

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_none_on_launcher_failure(self) -> None:
        """AppContext.fetcher is None when PlaywrightLauncher fails (graceful degrade).

        FAILS: AttributeError on PlaywrightLauncher patch target.
        """
        from owlbear_mcp_browser.server import app_lifespan

        with patch(
            "owlbear_mcp_browser.server.PlaywrightLauncher",
            return_value=_make_failing_launcher(),
        ):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.fetcher is None


# ===========================================================================
# TestFromAC_NoCDPImportsInServer — AC5
# ===========================================================================


class TestFromAC_NoCDPImportsInServer:
    """AC5: No imports of owlbear_browser.cdp remain in serve/mcp-browser/ after pivot."""

    def test_server_does_not_have_cdp_connection_manager_in_namespace(self) -> None:
        """owlbear_mcp_browser.server must not expose CDPConnectionManager at runtime.

        FAILS: server.py currently imports CDPConnectionManager → hasattr returns True.
        """
        import owlbear_mcp_browser.server as server_module

        assert not hasattr(server_module, "CDPConnectionManager"), (
            "CDPConnectionManager must not be in server module namespace after pivot; "
            "currently importable from owlbear_browser.cdp"
        )

    def test_server_source_has_no_cdp_import_statement(self) -> None:
        """serve/mcp-browser server.py source must not contain 'owlbear_browser.cdp' import.

        FAILS: server.py source contains 'from owlbear_browser.cdp import CDPConnectionManager'.
        """
        import owlbear_mcp_browser.server as server_module

        source_path = Path(server_module.__file__)  # type: ignore[arg-type]
        text = source_path.read_text(encoding="utf-8")
        assert "owlbear_browser.cdp" not in text, (
            "server.py must not import from owlbear_browser.cdp after the Playwright pivot; "
            f"found 'owlbear_browser.cdp' in {source_path}"
        )
