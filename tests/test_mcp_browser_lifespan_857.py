"""RED-phase tests for #857: Wire BrowserContentFetcher into MCP browser app_lifespan (AC2).

AC coverage:
  AC2 — app_lifespan() creates CDPConnectionManager + BrowserContentFetcher
         (guarded, fallback to None on failure).  CDPConnectionManager is
         disconnected in the finally block after yield.

Gap addressed: existing RED tests (test_mcp_browser_fetcher_852.py) cover AC1/AC3-AC6
via direct AppContext construction.  None test that app_lifespan() actually creates and
wires a BrowserContentFetcher into the yielded AppContext.

All tests MUST FAIL at RED phase:
  - current app_lifespan yields AppContext(cdp=..., page=...) with fetcher=None (default)
  - no call to BrowserContentFetcher() exists in app_lifespan at all
  => assertions on ctx.fetcher will be AssertionError / AttributeError
  => patch on owlbear_mcp_browser.server.BrowserContentFetcher raises AttributeError
     (the name is only TYPE_CHECKING-imported, not available at runtime yet)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_browser.server import app_lifespan

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_launcher() -> MagicMock:
    """Return a MagicMock PlaywrightLauncher that launches and closes cleanly.

    Provides a mock BrowserContext via .context so the fetcher-wiring branch
    inside the lifespan can call BrowserContentFetcher(launcher.context).
    """
    page = MagicMock()
    page.close = AsyncMock()  # lifespan awaits page.close() in finally block
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    launcher = MagicMock()
    launcher.context = context
    launcher.launch = AsyncMock()
    launcher.close = AsyncMock()
    launcher.__aenter__ = AsyncMock(return_value=launcher)
    launcher.__aexit__ = AsyncMock(return_value=False)
    return launcher


# ===========================================================================
# TestFromAC_LifespanBrowserFetcherWiring — AC2
# ===========================================================================


class TestFromAC_LifespanBrowserFetcherWiring:
    """app_lifespan creates BrowserContentFetcher on successful PlaywrightLauncher.launch() (AC2).

    Updated for #871 Playwright pivot: CDPConnectionManager replaced by PlaywrightLauncher.
    """

    # ------------------------------------------------------------------
    # Happy-path: connect succeeds → fetcher is populated
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_is_not_none_when_cdp_connect_succeeds(self) -> None:
        """AC2: app_lifespan sets AppContext.fetcher to a non-None object on successful launch."""
        mock_launcher = _make_mock_launcher()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.fetcher is not None, (
                    "AppContext.fetcher must be set when PlaywrightLauncher launches successfully;"
                    " got None — app_lifespan is not creating BrowserContentFetcher"
                )

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_is_browser_content_fetcher_instance(self) -> None:
        """AC2: AppContext.fetcher is a BrowserContentFetcher after successful launch."""
        from owlbear_browser.fetcher import BrowserContentFetcher

        mock_launcher = _make_mock_launcher()

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx:
                assert isinstance(ctx.fetcher, BrowserContentFetcher), (
                    f"AppContext.fetcher must be a BrowserContentFetcher instance;"
                    f" got {type(ctx.fetcher)!r}"
                )

    # ------------------------------------------------------------------
    # Contract: BrowserContentFetcher constructed with the right CDPConnectionManager
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_browser_content_fetcher_constructed_with_cdp_manager(self) -> None:
        """AC2: BrowserContentFetcher is called with launcher.context (Playwright BrowserContext)."""
        mock_launcher = _make_mock_launcher()
        mock_fetcher_cls = MagicMock(return_value=MagicMock())

        with (
            patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher),
            patch("owlbear_mcp_browser.server.BrowserContentFetcher", mock_fetcher_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_fetcher_cls.assert_called_once_with(mock_launcher.context)

    # ------------------------------------------------------------------
    # Edge: each lifespan invocation creates an independent fetcher
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_creates_independent_fetcher_per_invocation(self) -> None:
        """AC2: Separate lifespan invocations each create a fresh BrowserContentFetcher."""
        mock_launcher = _make_mock_launcher()
        fetcher1: object | None = None
        fetcher2: object | None = None

        with patch("owlbear_mcp_browser.server.PlaywrightLauncher", return_value=mock_launcher):
            async with app_lifespan(MagicMock()) as ctx1:
                fetcher1 = ctx1.fetcher
            async with app_lifespan(MagicMock()) as ctx2:
                fetcher2 = ctx2.fetcher

        assert fetcher1 is not None, "First lifespan invocation must provide a non-None fetcher"
        assert fetcher2 is not None, "Second lifespan invocation must provide a non-None fetcher"
        assert fetcher1 is not fetcher2, (
            "Each lifespan invocation must create an independent BrowserContentFetcher"
        )
