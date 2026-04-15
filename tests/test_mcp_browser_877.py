"""RED-phase tests for #877: resolve page=None behavior conflict in mcp-browser tools.

AC coverage:
  AC2  read_text() and snapshot() return last_content fallback when page is None.
       — Currently both raise ToolError on current HEAD: tests fail as expected.
  AC8  navigate() AppContext dry-run: returns url when AppContext.fetcher is None and
       page is None (allowlist check still enforced). Arch-adjudicated per #877 review.

AC1 (click/type/select raise ToolError when page is None) is already implemented and
covered by existing PASSING tests in 837/853/854 — new tests for AC1 would pass
immediately and are therefore not RED-phase tests.

All 5 tests MUST FAIL on current HEAD:
  - read_text with page=None raises ToolError instead of returning last_content
  - snapshot with page=None raises ToolError instead of returning last_content
  - navigate with AppContext(fetcher=None, page=None) raises ToolError instead of returning url
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_URL = "https://safe.example.com/page"
_LAST_CONTENT = "# Example Page\n\nSome content fetched in a previous navigate call."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mcp_ctx_no_page(last_content: str = "") -> MagicMock:
    """Return a mock MCP ctx backed by AppContext with page=None and given last_content."""
    from owlbear_mcp_browser.allowlist import DomainAllowlist
    from owlbear_mcp_browser.server import AppContext

    app_ctx = AppContext(
        allowlist=DomainAllowlist(domains=["safe.example.com"]),
        launcher=None,
        page=None,
        last_content=last_content,
    )
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ===========================================================================
# TestFromAC_ReadTextPageNoneFallback — AC2: read_text returns last_content when page is None
# ===========================================================================


class TestFromAC_ReadTextPageNoneFallback:
    """read_text() must return last_content (not raise ToolError) when page is None (AC2)."""

    @pytest.mark.asyncio
    async def test_read_text_returns_last_content_when_page_none(self) -> None:
        """read_text() returns the stored last_content when page is None."""
        from owlbear_mcp_browser.server import read_text

        ctx = _make_mcp_ctx_no_page(last_content=_LAST_CONTENT)

        # FAILS on HEAD: read_text raises ToolError("No browser session") instead
        result = await read_text(ctx)
        assert result == _LAST_CONTENT

    @pytest.mark.asyncio
    async def test_read_text_returns_empty_string_when_page_none_and_no_cached_content(self) -> None:
        """read_text() returns empty string when page is None and last_content is empty."""
        from owlbear_mcp_browser.server import read_text

        ctx = _make_mcp_ctx_no_page(last_content="")

        # FAILS on HEAD: raises ToolError instead of returning ""
        result = await read_text(ctx)
        assert result == ""


# ===========================================================================
# TestFromAC_SnapshotPageNoneFallback — AC2: snapshot returns last_content when page is None
# ===========================================================================


class TestFromAC_SnapshotPageNoneFallback:
    """snapshot() must return last_content (not raise ToolError) when page is None (AC2)."""

    @pytest.mark.asyncio
    async def test_snapshot_returns_last_content_when_page_none(self) -> None:
        """snapshot() returns the stored last_content when page is None."""
        from owlbear_mcp_browser.server import snapshot

        ctx = _make_mcp_ctx_no_page(last_content=_LAST_CONTENT)

        # FAILS on HEAD: snapshot raises ToolError("No browser session") instead
        result = await snapshot(ctx)
        assert result == _LAST_CONTENT

    @pytest.mark.asyncio
    async def test_snapshot_returns_empty_string_when_page_none_and_no_cached_content(self) -> None:
        """snapshot() returns empty string when page is None and last_content is empty."""
        from owlbear_mcp_browser.server import snapshot

        ctx = _make_mcp_ctx_no_page(last_content="")

        # FAILS on HEAD: raises ToolError instead of returning ""
        result = await snapshot(ctx)
        assert result == ""


# ===========================================================================
# TestFromAC_NavigateAppContextDryRun — arch-adjudicated: navigate returns url dry-run
# ===========================================================================


class TestFromAC_NavigateAppContextDryRun:
    """navigate() returns url when AppContext has no fetcher and page is None (AC8 / arch adjudication)."""

    @pytest.mark.asyncio
    async def test_navigate_returns_url_when_appcontext_no_fetcher_no_page(self) -> None:
        """navigate() returns the URL when AppContext.fetcher is None and page is None.

        The allowlist still enforced — the domain is allowed, so navigate should succeed
        and return url as a dry-run (consistent with the non-AppContext fallback path).
        """
        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx_no_page()

        # FAILS on HEAD: navigate raises ToolError("No browser session") when fetcher is None
        result = await navigate(ctx, _ALLOWED_URL)
        assert result == _ALLOWED_URL
