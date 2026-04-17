"""RED-phase tests for #850: Add ctx: Context to all 6 mcp-browser tools, use lifespan allowlist.

AC coverage:
  AC2 — All 6 tools accept ctx: Context as first parameter.
         navigate is covered by TestFromAC_NavigateToolError in test_mcp_browser_775.py;
         this file covers the 5 remaining tools (click, type_input, select, read_text, snapshot).
  AC3 — navigate() reads the domain allowlist exclusively from
         ctx.request_context.lifespan_context.allowlist — BROWSER_ALLOWED_DOMAINS env var
         is no longer consulted at call time.

AC1 (import statement) is an internal server.py change verified by AC2/AC3 tests passing
(ctx: Context type hint requires the import).

All tests MUST FAIL at RED phase:
  - click/type_input/select/read_text/snapshot have no ctx parameter
    → TypeError on each call
  - navigate() still reads BROWSER_ALLOWED_DOMAINS at call time
    → assertions about ctx-source allowlist fail (or TypeError whilst ctx param absent)
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_browser.allowlist import DomainAllowlist
from owlbear_mcp_browser.server import AppContext


# ---------------------------------------------------------------------------
# Helpers — same pattern as test_mcp_browser_775.py
# ---------------------------------------------------------------------------


def _make_app_ctx(domains: list[str]) -> AppContext:
    """Return an AppContext with a DomainAllowlist for the given domains."""
    return AppContext(allowlist=DomainAllowlist(domains=domains))


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    """Return a MagicMock ctx with app_ctx wired into lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ===========================================================================
# TestFromAC_CtxParameterOnAllTools — AC2: remaining 5 tools accept ctx first
# ===========================================================================


class TestFromAC_CtxParameterOnAllTools:
    """click, type_input, select, read_text, snapshot accept ctx: Context as first parameter (AC2)."""

    @pytest.mark.asyncio
    async def test_click_accepts_ctx_as_first_parameter(self) -> None:
        """click() accepts ctx as first positional arg and returns the selector string."""
        from owlbear_mcp_browser.server import click  # type: ignore[attr-defined]

        mock_locator = MagicMock()
        mock_locator.click = AsyncMock()
        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]), page=mock_page)
        ctx = _make_mcp_ctx(app_ctx)
        result = await click(ctx, selector="#submit-btn")
        assert result == "#submit-btn"

    @pytest.mark.asyncio
    async def test_type_input_accepts_ctx_as_first_parameter(self) -> None:
        """type_input() accepts ctx as first positional arg and returns 'selector:text'."""
        from owlbear_mcp_browser.server import type_input  # type: ignore[attr-defined]

        mock_locator = MagicMock()
        mock_locator.fill = AsyncMock()
        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]), page=mock_page)
        ctx = _make_mcp_ctx(app_ctx)
        result = await type_input(ctx, selector="#search", text="hello world")
        assert result == "#search:hello world"

    @pytest.mark.asyncio
    async def test_select_accepts_ctx_as_first_parameter(self) -> None:
        """select() accepts ctx as first positional arg and returns 'selector:value'."""
        from owlbear_mcp_browser.server import select  # type: ignore[attr-defined]

        mock_locator = MagicMock()
        mock_locator.select_option = AsyncMock()
        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]), page=mock_page)
        ctx = _make_mcp_ctx(app_ctx)
        result = await select(ctx, selector="#dropdown", value="option-1")
        assert result == "#dropdown:option-1"

    @pytest.mark.asyncio
    async def test_read_text_accepts_ctx_as_first_parameter(self) -> None:
        """read_text() accepts ctx as first positional arg and returns a string."""
        from owlbear_mcp_browser.server import read_text  # type: ignore[attr-defined]

        mock_page = MagicMock()
        mock_page.url = "https://example.com/"
        mock_page.content = AsyncMock(return_value="<html><body>Hello world</body></html>")
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]), page=mock_page)
        ctx = _make_mcp_ctx(app_ctx)
        result = await read_text(ctx)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_snapshot_accepts_ctx_as_first_parameter(self) -> None:
        """snapshot() accepts ctx as first positional arg and returns a string."""
        from owlbear_mcp_browser.server import snapshot  # type: ignore[attr-defined]

        mock_locator = MagicMock()
        mock_locator.aria_snapshot = AsyncMock(return_value="- heading: Hello\n")
        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        app_ctx = AppContext(allowlist=DomainAllowlist(domains=[]), page=mock_page)
        ctx = _make_mcp_ctx(app_ctx)
        result = await snapshot(ctx)
        assert isinstance(result, str)


# ===========================================================================
# TestFromAC_NavigateUsesLifespanCtx — AC3: navigate() reads allowlist from ctx
# ===========================================================================


class TestFromAC_NavigateUsesLifespanCtx:
    """navigate() reads the domain allowlist from ctx.request_context.lifespan_context.allowlist,
    not from the BROWSER_ALLOWED_DOMAINS environment variable (AC3).
    """

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_when_ctx_empty_even_if_env_var_allows(self) -> None:
        """navigate() raises ToolError when ctx allowlist is empty, even if BROWSER_ALLOWED_DOMAINS allows the domain."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate  # type: ignore[attr-defined]

        ctx = _make_mcp_ctx(_make_app_ctx([]))  # empty ctx allowlist — deny by default
        # env var allows the domain, but navigate must NOT consult it
        with (
            patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "trusted.example.com"}),
            pytest.raises(ToolError),
        ):
            await navigate(ctx, url="https://trusted.example.com/page")

    @pytest.mark.asyncio
    async def test_navigate_permits_url_when_ctx_allows_even_if_env_var_is_empty(self) -> None:
        """navigate() does not raise when ctx allowlist contains the domain, even if BROWSER_ALLOWED_DOMAINS is unset."""
        from owlbear_mcp_browser.server import navigate  # type: ignore[attr-defined]

        mock_fetcher = MagicMock()
        mock_fetcher.fetch = AsyncMock(return_value="# Page")
        app_ctx = AppContext(
            allowlist=DomainAllowlist(domains=["trusted.example.com"]),
            fetcher=mock_fetcher,
        )
        ctx = _make_mcp_ctx(app_ctx)
        env_without = {k: v for k, v in os.environ.items() if k != "BROWSER_ALLOWED_DOMAINS"}
        with patch.dict(os.environ, env_without, clear=True):
            # must not raise — ctx allowlist permits the domain
            await navigate(ctx, url="https://trusted.example.com/page")

    @pytest.mark.asyncio
    async def test_navigate_ctx_allowlist_blocks_domain_present_only_in_env_var(self) -> None:
        """navigate() raises ToolError for a domain present in BROWSER_ALLOWED_DOMAINS but absent from ctx allowlist."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate  # type: ignore[attr-defined]

        # ctx allowlist has a different domain; env var has env-only.example.com
        ctx = _make_mcp_ctx(_make_app_ctx(["other.example.com"]))
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "env-only.example.com"}), pytest.raises(ToolError):
            await navigate(ctx, url="https://env-only.example.com/page")
