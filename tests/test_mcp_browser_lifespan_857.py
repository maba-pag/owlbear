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


def _make_mock_cdp() -> MagicMock:
    """Return a MagicMock CDPConnectionManager that connects and disconnects cleanly.

    ``_browser.contexts`` is set to an empty list so the page-extraction branch
    inside the current lifespan does not try to index into a MagicMock iterable.
    """
    cdp = MagicMock()
    cdp.connect = AsyncMock()
    cdp.disconnect = AsyncMock()
    cdp._browser.contexts = []  # noqa: SLF001 — prevent page extraction side-effect
    return cdp


# ===========================================================================
# TestFromAC_LifespanBrowserFetcherWiring — AC2
# ===========================================================================


class TestFromAC_LifespanBrowserFetcherWiring:
    """app_lifespan creates BrowserContentFetcher on successful CDPConnectionManager.connect() (AC2).

    RED rationale: current app_lifespan() never instantiates BrowserContentFetcher —
    AppContext.fetcher remains None (the field default).  Every test below asserts a
    post-connect state that cannot be satisfied until the builder adds the wiring.
    """

    # ------------------------------------------------------------------
    # Happy-path: connect succeeds → fetcher is populated
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_is_not_none_when_cdp_connect_succeeds(self) -> None:
        """AC2: app_lifespan sets AppContext.fetcher to a non-None object on successful connect.

        FAILS at RED because app_lifespan yields AppContext(fetcher=None).
        """
        mock_cdp = _make_mock_cdp()

        with patch("owlbear_mcp_browser.server._CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(MagicMock()) as ctx:
                assert ctx.fetcher is not None, (
                    "AppContext.fetcher must be set when CDPConnectionManager connects successfully;"
                    " got None — app_lifespan is not creating BrowserContentFetcher"
                )

    @pytest.mark.asyncio
    async def test_lifespan_fetcher_is_browser_content_fetcher_instance(self) -> None:
        """AC2: AppContext.fetcher is a BrowserContentFetcher after successful connect (not just non-None).

        FAILS at RED because ctx.fetcher is None → isinstance(None, BrowserContentFetcher) is False.
        """
        from owlbear_browser.fetcher import BrowserContentFetcher

        mock_cdp = _make_mock_cdp()

        with patch("owlbear_mcp_browser.server._CDPConnectionManager", return_value=mock_cdp):
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
        """AC2: BrowserContentFetcher(cdp) is called with the CDPConnectionManager instance.

        FAILS at RED with AttributeError:
          patch("owlbear_mcp_browser.server.BrowserContentFetcher") raises AttributeError
          because BrowserContentFetcher is only TYPE_CHECKING-imported in server.py —
          it does not exist as a runtime name in the server module until the builder adds
          the import.
        """
        mock_cdp = _make_mock_cdp()
        mock_fetcher_cls = MagicMock(return_value=MagicMock())

        with (
            patch("owlbear_mcp_browser.server._CDPConnectionManager", return_value=mock_cdp),
            patch("owlbear_mcp_browser.server.BrowserContentFetcher", mock_fetcher_cls),
        ):
            async with app_lifespan(MagicMock()):
                pass

        mock_fetcher_cls.assert_called_once_with(mock_cdp)

    # ------------------------------------------------------------------
    # Edge: each lifespan invocation creates an independent fetcher
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lifespan_creates_independent_fetcher_per_invocation(self) -> None:
        """AC2: Separate lifespan invocations each create a fresh BrowserContentFetcher.

        FAILS at RED because fetcher1 and fetcher2 are both None:
          assert None is not None  → False.
        """
        mock_cdp = _make_mock_cdp()
        fetcher1: object | None = None
        fetcher2: object | None = None

        with patch("owlbear_mcp_browser.server._CDPConnectionManager", return_value=mock_cdp):
            async with app_lifespan(MagicMock()) as ctx1:
                fetcher1 = ctx1.fetcher
            async with app_lifespan(MagicMock()) as ctx2:
                fetcher2 = ctx2.fetcher

        assert fetcher1 is not None, "First lifespan invocation must provide a non-None fetcher"
        assert fetcher2 is not None, "Second lifespan invocation must provide a non-None fetcher"
        assert fetcher1 is not fetcher2, (
            "Each lifespan invocation must create an independent BrowserContentFetcher"
        )
