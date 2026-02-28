"""Tests for MCP server factory functions (GitHub, Git, Fetch).

Validates that each factory function produces the correct MCPServerStdio
configuration and that register_default_servers wires everything into
the registry.  All tests are fully mocked — no real npx/subprocess calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from owlbear.config import OwlBearSettings
from owlbear.tools.mcp_registry import MCPServerRegistry

# ---------------------------------------------------------------------------
# GitHub MCP server
# ---------------------------------------------------------------------------


class TestGitHubMCPServer:
    """github_mcp_server(token) produces correct MCPServerStdio config."""

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_command_is_npx(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import github_mcp_server

        github_mcp_server("ghp_test123")
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["command"] == "npx"

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_args_include_github_package(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import github_mcp_server

        github_mcp_server("ghp_test123")
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["args"] == ["-y", "@modelcontextprotocol/server-github"]

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_env_contains_token(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import github_mcp_server

        github_mcp_server("ghp_secret")
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["env"] == {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_secret"}

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_tool_prefix_is_github(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import github_mcp_server

        github_mcp_server("ghp_test123")
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["tool_prefix"] == "github"

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_returns_mcp_server_instance(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import github_mcp_server

        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        result = github_mcp_server("ghp_test123")
        assert result is mock_instance


# ---------------------------------------------------------------------------
# Git MCP server
# ---------------------------------------------------------------------------


class TestGitMCPServer:
    """git_mcp_server() produces correct MCPServerStdio config."""

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_command_is_npx(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import git_mcp_server

        git_mcp_server()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["command"] == "npx"

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_args_include_git_package(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import git_mcp_server

        git_mcp_server()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["args"] == ["-y", "@modelcontextprotocol/server-git"]

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_no_env_vars(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import git_mcp_server

        git_mcp_server()
        call_kwargs = mock_cls.call_args.kwargs
        # No env key should be passed (or None).
        assert call_kwargs.get("env") is None

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_tool_prefix_git_mcp(self, mock_cls: MagicMock) -> None:
        """tool_prefix='git_mcp' to avoid conflict with native GitLocalToolset."""
        from owlbear.tools.mcp_servers import git_mcp_server

        git_mcp_server()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["tool_prefix"] == "git_mcp"

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_returns_mcp_server_instance(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import git_mcp_server

        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        result = git_mcp_server()
        assert result is mock_instance


# ---------------------------------------------------------------------------
# Fetch MCP server
# ---------------------------------------------------------------------------


class TestFetchMCPServer:
    """fetch_mcp_server() produces correct MCPServerStdio config."""

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_command_is_npx(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import fetch_mcp_server

        fetch_mcp_server()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["command"] == "npx"

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_args_include_fetch_package(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import fetch_mcp_server

        fetch_mcp_server()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["args"] == ["-y", "@modelcontextprotocol/server-fetch"]

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_no_env_vars(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import fetch_mcp_server

        fetch_mcp_server()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs.get("env") is None

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_tool_prefix_is_fetch(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import fetch_mcp_server

        fetch_mcp_server()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["tool_prefix"] == "fetch"

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_returns_mcp_server_instance(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import fetch_mcp_server

        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        result = fetch_mcp_server()
        assert result is mock_instance


# ---------------------------------------------------------------------------
# register_default_servers
# ---------------------------------------------------------------------------


class TestRegisterDefaultServers:
    """register_default_servers wires factory functions into registry."""

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_registers_all_three_with_token(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import register_default_servers

        mock_cls.return_value = MagicMock()
        settings = OwlBearSettings(github_token="ghp_test123")  # type: ignore[arg-type]
        registry = MCPServerRegistry()

        register_default_servers(registry, settings)
        assert sorted(registry.names()) == ["fetch", "git", "github"]

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_skips_github_without_token(self, mock_cls: MagicMock) -> None:
        from owlbear.tools.mcp_servers import register_default_servers

        mock_cls.return_value = MagicMock()
        settings = OwlBearSettings()  # No github_token
        registry = MCPServerRegistry()

        register_default_servers(registry, settings)
        assert sorted(registry.names()) == ["fetch", "git"]

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_github_token_passed_from_settings(self, mock_cls: MagicMock) -> None:
        """Token is extracted via get_secret_value() from settings."""
        from owlbear.tools.mcp_servers import register_default_servers

        mock_cls.return_value = MagicMock()
        settings = OwlBearSettings(github_token="ghp_from_settings")  # type: ignore[arg-type]
        registry = MCPServerRegistry()

        register_default_servers(registry, settings)

        # Find the call that has GITHUB_PERSONAL_ACCESS_TOKEN in env.
        github_call = None
        for call in mock_cls.call_args_list:
            env = call.kwargs.get("env")
            if env and "GITHUB_PERSONAL_ACCESS_TOKEN" in env:
                github_call = call
                break

        assert github_call is not None
        assert github_call.kwargs["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"] == "ghp_from_settings"

    @patch("owlbear.tools.mcp_servers.MCPServerStdio")
    def test_idempotent_re_registration(self, mock_cls: MagicMock) -> None:
        """Calling register_default_servers twice should overwrite, not duplicate."""
        from owlbear.tools.mcp_servers import register_default_servers

        mock_cls.return_value = MagicMock()
        settings = OwlBearSettings()
        registry = MCPServerRegistry()

        register_default_servers(registry, settings)
        register_default_servers(registry, settings)
        assert sorted(registry.names()) == ["fetch", "git"]
