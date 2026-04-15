"""RED-phase tests for #836: refactor mcp-browser tools to use ctx: Context + AppContext pattern.

AC coverage:
  AC1 - All 6 tools accept `ctx: Context` as first parameter:
        navigate, click, type_input, select, read_text, snapshot
  AC2 - navigate uses ctx.request_context.lifespan_context.allowlist
        instead of re-reading BROWSER_ALLOWED_DOMAINS env var on each call
  AC3 - All tools callable with a mocked ctx (tests pass ctx, not bare url/selector)
  AC4 - Existing allowlist behaviour preserved: blocked domains raise ToolError,
        allowed domains return the URL — verified through ctx-based allowlist

All tests MUST FAIL at RED phase:
  - Current navigate(url: str) has no ctx param → TypeError when called with ctx
  - Current click/type_input/select(selector, ...) have no ctx param → TypeError
  - Current read_text() / snapshot() have no params at all → TypeError
  - Signature inspection (AC1): first param is NOT "ctx" → AssertionError
  - AC2 env-override tests: current impl reads env var, ignores ctx → wrong behaviour
"""

from __future__ import annotations

import inspect
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mcp_ctx(allowlist=None) -> MagicMock:  # type: ignore[no-untyped-def]
    """Return a MagicMock ctx with AppContext.allowlist wired to *allowlist*.

    Defaults to a deny-all DomainAllowlist when *allowlist* is None.
    """
    from owlbear_mcp_browser.allowlist import DomainAllowlist
    from owlbear_mcp_browser.server import AppContext

    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(
        allowlist=allowlist if allowlist is not None else DomainAllowlist(domains=[])
    )
    return ctx


def _make_mcp_ctx_with_mock_page() -> MagicMock:
    """Return a MagicMock ctx with AppContext wired to a mock Playwright page.

    Used by click/type_input/select tests — these tools require a real page object
    and must not be called with page=None (they raise ToolError in that case).
    """
    from owlbear_mcp_browser.allowlist import DomainAllowlist
    from owlbear_mcp_browser.server import AppContext

    mock_locator = MagicMock()
    mock_locator.click = AsyncMock()
    mock_locator.fill = AsyncMock()
    mock_locator.select_option = AsyncMock()
    mock_page = MagicMock()
    mock_page.locator = MagicMock(return_value=mock_locator)

    ctx = MagicMock()
    ctx.request_context.lifespan_context = AppContext(
        allowlist=DomainAllowlist(domains=[]),
        page=mock_page,
    )
    return ctx


# ===========================================================================
# TestFromAC_ToolsAcceptContext — AC1: all 6 tools have ctx as first parameter
# ===========================================================================


class TestFromAC_ToolsAcceptContext:
    """All 6 mcp-browser tools must declare ctx: Context as their first parameter (AC1)."""

    def test_navigate_first_parameter_is_ctx(self) -> None:
        """navigate's first parameter must be named 'ctx'."""
        from owlbear_mcp_browser.server import navigate

        params = list(inspect.signature(navigate).parameters)
        assert params[0] == "ctx", f"Expected first param 'ctx', got {params[0]!r}"

    def test_click_first_parameter_is_ctx(self) -> None:
        """click's first parameter must be named 'ctx'."""
        from owlbear_mcp_browser.server import click

        params = list(inspect.signature(click).parameters)
        assert params[0] == "ctx", f"Expected first param 'ctx', got {params[0]!r}"

    def test_type_input_first_parameter_is_ctx(self) -> None:
        """type_input's first parameter must be named 'ctx'."""
        from owlbear_mcp_browser.server import type_input

        params = list(inspect.signature(type_input).parameters)
        assert params[0] == "ctx", f"Expected first param 'ctx', got {params[0]!r}"

    def test_select_first_parameter_is_ctx(self) -> None:
        """select's first parameter must be named 'ctx'."""
        from owlbear_mcp_browser.server import select

        params = list(inspect.signature(select).parameters)
        assert params[0] == "ctx", f"Expected first param 'ctx', got {params[0]!r}"

    def test_read_text_first_parameter_is_ctx(self) -> None:
        """read_text's first parameter must be named 'ctx'."""
        from owlbear_mcp_browser.server import read_text

        params = list(inspect.signature(read_text).parameters)
        assert len(params) >= 1, "read_text must accept at least one parameter (ctx)"
        assert params[0] == "ctx", f"Expected first param 'ctx', got {params[0]!r}"

    def test_snapshot_first_parameter_is_ctx(self) -> None:
        """snapshot's first parameter must be named 'ctx'."""
        from owlbear_mcp_browser.server import snapshot

        params = list(inspect.signature(snapshot).parameters)
        assert len(params) >= 1, "snapshot must accept at least one parameter (ctx)"
        assert params[0] == "ctx", f"Expected first param 'ctx', got {params[0]!r}"


# ===========================================================================
# TestFromAC_NavigateUsesLifespanAllowlist — AC2: navigate reads allowlist from ctx,
# not from BROWSER_ALLOWED_DOMAINS on each call
# ===========================================================================


class TestFromAC_NavigateUsesLifespanAllowlist:
    """navigate() must use ctx.request_context.lifespan_context.allowlist (AC2)."""

    @pytest.mark.asyncio
    async def test_navigate_blocked_by_ctx_allowlist_even_when_env_permits(self) -> None:
        """navigate raises ToolError when ctx.allowlist is empty, even if env var allows the domain.

        Proves navigate uses ctx, not the env var: env says 'allow', ctx says 'block' → ToolError.
        """
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx(DomainAllowlist(domains=[]))  # deny-all via ctx
        # env explicitly allows the same domain — current impl would pass, refactored should block
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "trusted.example.com"}), pytest.raises(ToolError):
            await navigate(ctx, url="https://trusted.example.com/page")

    @pytest.mark.asyncio
    async def test_navigate_permitted_by_ctx_allowlist_even_when_env_is_empty(self) -> None:
        """navigate succeeds when ctx.allowlist allows the domain, even if env var is empty.

        Proves navigate uses ctx, not the env var: env is empty (deny-all), ctx allows → no error.
        """
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx(DomainAllowlist(domains=["corp.intranet"]))
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": ""}):
            result = await navigate(ctx, url="https://corp.intranet/home")

        assert result == "https://corp.intranet/home"

    @pytest.mark.asyncio
    async def test_navigate_calls_allowlist_check_with_exact_url(self) -> None:
        """navigate() calls ctx.request_context.lifespan_context.allowlist.check(url)."""
        from owlbear_mcp_browser.server import navigate

        mock_allowlist = MagicMock()
        mock_allowlist.check = MagicMock()  # side_effect=None → allow
        ctx = MagicMock()
        ctx.request_context.lifespan_context.allowlist = mock_allowlist

        url = "https://anysite.example.com/path?q=1"
        await navigate(ctx, url=url)

        mock_allowlist.check.assert_called_once_with(url)

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_when_ctx_allowlist_check_raises(self) -> None:
        """navigate wraps PermissionError from ctx.allowlist.check into ToolError."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate

        mock_allowlist = MagicMock()
        mock_allowlist.check.side_effect = PermissionError("blocked by ctx allowlist")
        ctx = MagicMock()
        ctx.request_context.lifespan_context.allowlist = mock_allowlist

        with pytest.raises(ToolError):
            await navigate(ctx, url="https://blocked.example.com/")


# ===========================================================================
# TestFromAC_AllToolsCallableWithCtx — AC3: all 6 tools can be invoked with ctx
# ===========================================================================


class TestFromAC_AllToolsCallableWithCtx:
    """All 6 tools can be called with a mocked ctx as first argument (AC3)."""

    @pytest.mark.asyncio
    async def test_navigate_called_with_ctx_and_allowed_domain(self) -> None:
        """navigate(ctx, url=...) with an allowed domain returns the URL."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx(DomainAllowlist(domains=["safe.corp"]))
        result = await navigate(ctx, url="https://safe.corp/index")
        assert result == "https://safe.corp/index"

    @pytest.mark.asyncio
    async def test_click_called_with_ctx_and_selector(self) -> None:
        """click(ctx, selector=...) with a mock page returns a string result without error."""
        from owlbear_mcp_browser.server import click

        ctx = _make_mcp_ctx_with_mock_page()
        result = await click(ctx, selector="#submit-button")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_type_input_called_with_ctx_selector_and_text(self) -> None:
        """type_input(ctx, selector=..., text=...) with a mock page returns a string result without error."""
        from owlbear_mcp_browser.server import type_input

        ctx = _make_mcp_ctx_with_mock_page()
        result = await type_input(ctx, selector="#search", text="hello world")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_select_called_with_ctx_selector_and_value(self) -> None:
        """select(ctx, selector=..., value=...) with a mock page returns a string result without error."""
        from owlbear_mcp_browser.server import select

        ctx = _make_mcp_ctx_with_mock_page()
        result = await select(ctx, selector="#dropdown", value="option-a")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_read_text_called_with_ctx(self) -> None:
        """read_text(ctx) returns a string result without error."""
        from owlbear_mcp_browser.server import read_text

        ctx = _make_mcp_ctx()
        result = await read_text(ctx)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_snapshot_called_with_ctx(self) -> None:
        """snapshot(ctx) returns a string result without error."""
        from owlbear_mcp_browser.server import snapshot

        ctx = _make_mcp_ctx()
        result = await snapshot(ctx)
        assert isinstance(result, str)


# ===========================================================================
# TestFromAC_AllowlistBehaviorPreservedViaCtx — AC4: existing allowlist contract
# preserved when delivered via ctx instead of env var
# ===========================================================================


class TestFromAC_AllowlistBehaviorPreservedViaCtx:
    """Allowlist behaviour is preserved: blocked → ToolError, allowed → URL returned (AC4)."""

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_for_domain_not_in_ctx_allowlist(self) -> None:
        """navigate raises ToolError when the URL's hostname is not in ctx.allowlist."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx(DomainAllowlist(domains=["allowed.corp"]))
        with pytest.raises(ToolError):
            await navigate(ctx, url="https://notallowed.evil.com/page")

    @pytest.mark.asyncio
    async def test_navigate_returns_url_for_domain_in_ctx_allowlist(self) -> None:
        """navigate returns the URL string when the hostname is in ctx.allowlist."""
        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx(DomainAllowlist(domains=["sharepoint.example.com"]))
        result = await navigate(ctx, url="https://sharepoint.example.com/sites/IT")
        assert result == "https://sharepoint.example.com/sites/IT"

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_when_ctx_allowlist_is_empty(self) -> None:
        """navigate raises ToolError when ctx.allowlist is empty (deny-by-default)."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.allowlist import DomainAllowlist
        from owlbear_mcp_browser.server import navigate

        ctx = _make_mcp_ctx(DomainAllowlist(domains=[]))
        with pytest.raises(ToolError):
            await navigate(ctx, url="https://any.example.com/page")
