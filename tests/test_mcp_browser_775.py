"""RED-phase tests for #790: owlbear_mcp_browser MCP server and domain allowlist.

AC coverage:
  AC1 - app_lifespan exists on owlbear-mcp-browser server;
        6 tools registered: navigate, click, type, select, read_text, snapshot
  AC2 - BROWSER_ALLOWED_DOMAINS configures DomainAllowlist in app_lifespan;
        deny-by-default when env var unset or empty
  AC3 - navigate() raises ToolError when URL hostname not in BROWSER_ALLOWED_DOMAINS;
        allowed domains pass without error
  AC4 - _apply_tool_exclusions reads BROWSER_TOOLS_EXCLUDE, removes tools,
        returns set[str], called in app_lifespan before yield

All tests MUST FAIL at RED phase:
  - app_lifespan not in server.py → ImportError
  - _apply_tool_exclusions not in server.py → ImportError
  - navigate() has no domain check → AssertionError (no ToolError raised)
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_server() -> MagicMock:
    """Return a MagicMock mimicking a FastMCP server with remove_tool."""
    server = MagicMock()
    server.remove_tool = MagicMock()
    return server


# ===========================================================================
# TestFromAC_MCPServerLifespan — AC1: app_lifespan wired to owlbear-mcp-browser
# ===========================================================================


class TestFromAC_MCPServerLifespan:
    """owlbear-mcp-browser server has app_lifespan and 6 registered tools (AC1)."""

    def test_app_lifespan_importable_from_server(self) -> None:
        """app_lifespan is importable from owlbear_mcp_browser.server."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]  # noqa: F401

    def test_mcp_server_has_lifespan_configured(self) -> None:
        """The FastMCP server instance has a lifespan callable configured (not None)."""
        from owlbear_mcp_browser.server import _mcp  # type: ignore[attr-defined]

        # lifespan is set only after #794 wires app_lifespan into the FastMCP constructor
        assert _mcp.settings.lifespan is not None

    def test_six_tools_registered_by_name(self) -> None:
        """All 6 expected tool names are present in mcp_app.list_tools() (AC1)."""
        from owlbear_mcp_browser.server import mcp_app  # type: ignore[attr-defined]

        tool_names = {t.name for t in mcp_app.list_tools()}
        assert {"navigate", "click", "type", "select", "read_text", "snapshot"} <= tool_names


# ===========================================================================
# TestFromAC_DomainAllowlistEnvVar — AC2: BROWSER_ALLOWED_DOMAINS via app_lifespan
# ===========================================================================


class TestFromAC_DomainAllowlistEnvVar:
    """app_lifespan reads BROWSER_ALLOWED_DOMAINS and configures DomainAllowlist (AC2)."""

    @pytest.mark.asyncio
    async def test_allowed_domains_configured_from_env_var(self) -> None:
        """app_lifespan reads BROWSER_ALLOWED_DOMAINS and lists those domains as allowed."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]

        mock_server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "sharepoint.example.com,intranet.corp"}):
            async with app_lifespan(mock_server) as ctx:
                # The context must carry an allowlist that permits listed domains
                from owlbear_mcp_browser.allowlist import DomainAllowlist

                assert isinstance(ctx.allowlist, DomainAllowlist)

    @pytest.mark.asyncio
    async def test_unset_env_var_produces_deny_by_default_allowlist(self) -> None:
        """When BROWSER_ALLOWED_DOMAINS is unset, app_lifespan creates an empty allowlist (deny-by-default)."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]

        mock_server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "BROWSER_ALLOWED_DOMAINS"}
        with patch.dict(os.environ, env_without, clear=True):
            async with app_lifespan(mock_server) as ctx:
                from owlbear_mcp_browser.allowlist import DomainAllowlist

                # Empty allowlist: check raises PermissionError for any URL
                assert isinstance(ctx.allowlist, DomainAllowlist)
                with pytest.raises(PermissionError):
                    ctx.allowlist.check("https://any.domain.com/page")

    @pytest.mark.asyncio
    async def test_empty_env_var_produces_deny_by_default_allowlist(self) -> None:
        """When BROWSER_ALLOWED_DOMAINS is set to empty string, all navigation is denied."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]

        mock_server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": ""}):
            async with app_lifespan(mock_server) as ctx:
                with pytest.raises(PermissionError):
                    ctx.allowlist.check("https://any.domain.com/page")

    @pytest.mark.asyncio
    async def test_comma_separated_domains_all_listed_as_allowed(self) -> None:
        """Comma-separated BROWSER_ALLOWED_DOMAINS entries are all treated as allowed."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]

        mock_server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "host-a.corp,host-b.corp"}):
            async with app_lifespan(mock_server) as ctx:
                # Both listed domains must be permitted
                ctx.allowlist.check("https://host-a.corp/page")  # must not raise
                ctx.allowlist.check("https://host-b.corp/page")  # must not raise

    @pytest.mark.asyncio
    async def test_single_domain_in_env_var_is_allowed(self) -> None:
        """A single-domain BROWSER_ALLOWED_DOMAINS permits only that domain."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]

        mock_server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "sharepoint.example.com"}):
            async with app_lifespan(mock_server) as ctx:
                ctx.allowlist.check("https://sharepoint.example.com/sites/IT")  # must not raise
                with pytest.raises(PermissionError):
                    ctx.allowlist.check("https://other.example.com/page")


# ===========================================================================
# TestFromAC_NavigateToolError — AC3: navigate() raises ToolError
# ===========================================================================


class TestFromAC_NavigateToolError:
    """navigate() raises ToolError for non-allowlisted domains; passes for allowed (AC3)."""

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_for_blocked_domain(self) -> None:
        """navigate() raises ToolError when URL hostname is not in BROWSER_ALLOWED_DOMAINS."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate  # type: ignore[attr-defined]

        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "example.com"}), pytest.raises(ToolError):
            await navigate(url="https://evil.com/malicious-page")

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_when_allowlist_is_empty(self) -> None:
        """navigate() raises ToolError when BROWSER_ALLOWED_DOMAINS is empty (deny-by-default)."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate  # type: ignore[attr-defined]

        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": ""}), pytest.raises(ToolError):
            await navigate(url="https://any-domain.com/page")

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_when_domain_not_configured(self) -> None:
        """navigate() raises ToolError when BROWSER_ALLOWED_DOMAINS is unset (deny-by-default)."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate  # type: ignore[attr-defined]

        env_without = {k: v for k, v in os.environ.items() if k != "BROWSER_ALLOWED_DOMAINS"}
        with patch.dict(os.environ, env_without, clear=True), pytest.raises(ToolError):
            await navigate(url="https://any-domain.com/page")

    @pytest.mark.asyncio
    async def test_navigate_does_not_raise_for_allowlisted_domain(self) -> None:
        """navigate() does not raise ToolError when URL hostname is in BROWSER_ALLOWED_DOMAINS."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]

        mock_server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "sharepoint.example.com"}):
            async with app_lifespan(mock_server):
                from owlbear_mcp_browser.server import navigate

                # Must not raise for the allowed domain
                await navigate(url="https://sharepoint.example.com/sites/IT/page")

    @pytest.mark.asyncio
    async def test_navigate_raises_tool_error_for_subdomain_not_in_allowlist(self) -> None:
        """navigate() raises ToolError for a subdomain of an allowed domain that is not itself listed."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_browser.server import navigate  # type: ignore[attr-defined]

        # "example.com" is listed, "sub.example.com" is NOT
        with patch.dict(os.environ, {"BROWSER_ALLOWED_DOMAINS": "example.com"}), pytest.raises(ToolError):
            await navigate(url="https://sub.example.com/page")


# ===========================================================================
# TestFromAC_ApplyToolExclusions — AC4: _apply_tool_exclusions contract
# ===========================================================================


class TestFromAC_ApplyToolExclusions:
    """_apply_tool_exclusions reads BROWSER_TOOLS_EXCLUDE and removes tools (AC4)."""

    def test_apply_tool_exclusions_importable_from_server(self) -> None:
        """_apply_tool_exclusions is importable from owlbear_mcp_browser.server."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]  # noqa: F401

    def test_single_tool_excluded_calls_remove_tool_once(self) -> None:
        """Excluding one tool calls remove_tool exactly once with that name."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_TOOLS_EXCLUDE": "navigate"}):
            _apply_tool_exclusions(server)

        server.remove_tool.assert_called_once_with("navigate")

    def test_multiple_tools_excluded_calls_remove_tool_for_each(self) -> None:
        """Comma-separated BROWSER_TOOLS_EXCLUDE calls remove_tool for each name."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_TOOLS_EXCLUDE": "navigate,click,snapshot"}):
            _apply_tool_exclusions(server)

        assert server.remove_tool.call_count == 3
        called_names = {call.args[0] for call in server.remove_tool.call_args_list}
        assert called_names == {"navigate", "click", "snapshot"}

    def test_no_env_var_remove_tool_never_called(self) -> None:
        """When BROWSER_TOOLS_EXCLUDE is not set, remove_tool is never called."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "BROWSER_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without, clear=True):
            _apply_tool_exclusions(server)

        server.remove_tool.assert_not_called()

    def test_empty_env_var_remove_tool_never_called(self) -> None:
        """When BROWSER_TOOLS_EXCLUDE is set to empty string, remove_tool is never called."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_TOOLS_EXCLUDE": ""}):
            _apply_tool_exclusions(server)

        server.remove_tool.assert_not_called()

    def test_whitespace_stripped_from_tool_names(self) -> None:
        """Leading/trailing whitespace around each name is stripped before calling remove_tool."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_TOOLS_EXCLUDE": " navigate ,  click "}):
            _apply_tool_exclusions(server)

        called_names = {call.args[0] for call in server.remove_tool.call_args_list}
        assert "navigate" in called_names
        assert "click" in called_names
        assert not any(" " in name for name in called_names)

    def test_invalid_tool_name_silently_ignored(self) -> None:
        """An unknown tool name causes remove_tool to raise but the exception is swallowed."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        server.remove_tool.side_effect = Exception("unknown tool: no_such_tool")
        with patch.dict(os.environ, {"BROWSER_TOOLS_EXCLUDE": "no_such_tool"}):
            _apply_tool_exclusions(server)  # must not propagate

    def test_returns_set_of_successfully_excluded_names(self) -> None:
        """_apply_tool_exclusions returns a set[str] of tools that were successfully removed."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_TOOLS_EXCLUDE": "navigate,snapshot"}):
            result = _apply_tool_exclusions(server)

        assert isinstance(result, set)
        assert result == {"navigate", "snapshot"}

    def test_returns_empty_set_when_no_env_var(self) -> None:
        """_apply_tool_exclusions returns an empty set when BROWSER_TOOLS_EXCLUDE is not set."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        env_without = {k: v for k, v in os.environ.items() if k != "BROWSER_TOOLS_EXCLUDE"}
        with patch.dict(os.environ, env_without, clear=True):
            result = _apply_tool_exclusions(server)

        assert result == set()

    def test_trailing_comma_does_not_produce_empty_tool_name(self) -> None:
        """A trailing comma in BROWSER_TOOLS_EXCLUDE does not call remove_tool with an empty string."""
        from owlbear_mcp_browser.server import _apply_tool_exclusions  # type: ignore[attr-defined]

        server = _make_mock_server()
        with patch.dict(os.environ, {"BROWSER_TOOLS_EXCLUDE": "navigate,"}):
            _apply_tool_exclusions(server)

        called_names = [call.args[0] for call in server.remove_tool.call_args_list]
        assert "" not in called_names

    @pytest.mark.asyncio
    async def test_lifespan_calls_apply_tool_exclusions_before_yield(self) -> None:
        """app_lifespan calls _apply_tool_exclusions during startup (before yield)."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]

        mock_server = _make_mock_server()
        with patch("owlbear_mcp_browser.server._apply_tool_exclusions") as mock_apply:
            async with app_lifespan(mock_server):
                mock_apply.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_passes_server_to_apply_tool_exclusions(self) -> None:
        """app_lifespan passes the server as the first argument to _apply_tool_exclusions."""
        from owlbear_mcp_browser.server import app_lifespan  # type: ignore[attr-defined]

        mock_server = _make_mock_server()
        with patch("owlbear_mcp_browser.server._apply_tool_exclusions") as mock_apply:
            async with app_lifespan(mock_server):
                call_args = mock_apply.call_args
                assert call_args is not None
                assert call_args.args[0] is mock_server
