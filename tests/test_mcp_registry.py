"""Tests for MCP server registry and mcp: tool resolver integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pydantic_ai.models
import pytest
from pydantic_ai import Agent
from pydantic_ai.toolsets import FunctionToolset

from owlbear.config import OwlBearSettings
from owlbear.tools.mcp_registry import MCPServerRegistry

# Block real LLM calls.
pydantic_ai.models.ALLOW_MODEL_REQUESTS = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> MCPServerRegistry:
    """Return a fresh empty MCPServerRegistry."""
    return MCPServerRegistry()


@pytest.fixture
def mock_stdio_server() -> MagicMock:
    """Mock MCPServerStdio instance."""
    server = MagicMock()
    server.__class__.__name__ = "MCPServerStdio"
    return server


@pytest.fixture
def mock_http_server() -> MagicMock:
    """Mock MCPServerSSE instance."""
    server = MagicMock()
    server.__class__.__name__ = "MCPServerSSE"
    return server


def _make_async_server(name: str = "mock") -> MagicMock:
    """Create a mock MCP server with async context-manager support."""
    server = MagicMock()
    server.__aenter__ = AsyncMock(return_value=server)
    server.__aexit__ = AsyncMock(return_value=None)
    server.__class__.__name__ = name
    return server


# ---------------------------------------------------------------------------
# MCPServerRegistry — core operations
# ---------------------------------------------------------------------------


class TestMCPServerRegistryInit:
    """MCPServerRegistry() initializes with empty registry."""

    def test_empty_on_creation(self, registry: MCPServerRegistry) -> None:
        assert registry.names() == []


class TestMCPServerRegistryRegister:
    """register(name, server) stores server config."""

    def test_register_stores_server(
        self, registry: MCPServerRegistry, mock_stdio_server: MagicMock
    ) -> None:
        registry.register("github", mock_stdio_server)
        assert "github" in registry.names()

    def test_register_overwrite(
        self, registry: MCPServerRegistry, mock_stdio_server: MagicMock
    ) -> None:
        registry.register("github", mock_stdio_server)
        new_server = MagicMock()
        registry.register("github", new_server)
        assert registry.get("github") is new_server


class TestMCPServerRegistryGet:
    """get(name) returns the registered server or raises KeyError."""

    def test_get_returns_registered(
        self, registry: MCPServerRegistry, mock_stdio_server: MagicMock
    ) -> None:
        registry.register("github", mock_stdio_server)
        assert registry.get("github") is mock_stdio_server

    def test_get_nonexistent_raises(self, registry: MCPServerRegistry) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            registry.get("nonexistent")


class TestMCPServerRegistryNames:
    """names() returns list of registered server names."""

    def test_names_sorted(
        self,
        registry: MCPServerRegistry,
        mock_stdio_server: MagicMock,
        mock_http_server: MagicMock,
    ) -> None:
        registry.register("fetch", mock_http_server)
        registry.register("github", mock_stdio_server)
        assert registry.names() == ["fetch", "github"]


# ---------------------------------------------------------------------------
# MCPServerRegistry.from_config
# ---------------------------------------------------------------------------


class TestMCPServerRegistryFromConfig:
    """from_config builds registry from settings dict."""

    @patch("owlbear.tools.mcp_registry.MCPServerStdio")
    def test_stdio_server_from_config(self, mock_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        config: dict[str, Any] = {
            "github": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_TOKEN": "tok"},
                "tool_prefix": "github",
            }
        }
        reg = MCPServerRegistry.from_config(config)
        mock_cls.assert_called_once_with(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "tok"},
            tool_prefix="github",
        )
        assert reg.get("github") is mock_instance

    @patch("owlbear.tools.mcp_registry.MCPServerSSE")
    def test_sse_server_from_config(self, mock_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        config: dict[str, Any] = {
            "fetch": {
                "type": "sse",
                "url": "http://localhost:8080",
                "tool_prefix": "fetch",
            }
        }
        reg = MCPServerRegistry.from_config(config)
        mock_cls.assert_called_once_with(
            url="http://localhost:8080",
            tool_prefix="fetch",
        )
        assert reg.get("fetch") is mock_instance

    def test_unknown_type_raises(self) -> None:
        config: dict[str, Any] = {"bad": {"type": "websocket", "url": "ws://localhost"}}
        with pytest.raises(ValueError, match="websocket"):
            MCPServerRegistry.from_config(config)

    @patch("owlbear.tools.mcp_registry.MCPServerStdio")
    @patch("owlbear.tools.mcp_registry.MCPServerSSE")
    def test_multiple_servers_from_config(self, mock_sse: MagicMock, mock_stdio: MagicMock) -> None:
        mock_stdio.return_value = MagicMock()
        mock_sse.return_value = MagicMock()

        config: dict[str, Any] = {
            "github": {"type": "stdio", "command": "npx", "args": []},
            "fetch": {"type": "sse", "url": "http://localhost:8080"},
        }
        reg = MCPServerRegistry.from_config(config)
        assert len(reg.names()) == 2
        mock_stdio.assert_called_once()
        mock_sse.assert_called_once()


# ---------------------------------------------------------------------------
# OwlBearSettings.mcp_servers field
# ---------------------------------------------------------------------------


class TestOwlBearSettingsMCPServers:
    """mcp_servers field in OwlBearSettings parses JSON dict."""

    def test_default_is_none(self) -> None:
        settings = OwlBearSettings()
        assert settings.mcp_servers is None

    def test_parses_json_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "OWLBEAR_MCP_SERVERS",
            '{"github": {"type": "stdio", "command": "npx", "args": ["-y", "srv"]}}',
        )
        settings = OwlBearSettings()
        assert settings.mcp_servers is not None
        assert "github" in settings.mcp_servers
        assert settings.mcp_servers["github"]["type"] == "stdio"


# ---------------------------------------------------------------------------
# MCPServerRegistry — lifecycle (async context manager + health check)
# ---------------------------------------------------------------------------


class TestMCPServerRegistryAenter:
    """__aenter__ starts all registered servers."""

    @pytest.mark.asyncio
    async def test_aenter_starts_all_servers(self) -> None:
        """All registered servers have __aenter__ called."""
        s1 = _make_async_server("s1")
        s2 = _make_async_server("s2")
        reg = MCPServerRegistry()
        reg.register("alpha", s1)
        reg.register("beta", s2)

        async with reg:
            s1.__aenter__.assert_awaited_once()
            s2.__aenter__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aenter_returns_self(self) -> None:
        """async with registry as r: r is the registry."""
        reg = MCPServerRegistry()
        async with reg as r:
            assert r is reg

    @pytest.mark.asyncio
    async def test_aenter_tracks_started_servers(self) -> None:
        """Successfully started servers are tracked in _started."""
        s1 = _make_async_server("s1")
        reg = MCPServerRegistry()
        reg.register("alpha", s1)

        async with reg:
            assert "alpha" in reg._started


class TestMCPServerRegistryAexit:
    """__aexit__ stops all servers gracefully."""

    @pytest.mark.asyncio
    async def test_aexit_stops_all_servers(self) -> None:
        """All started servers have __aexit__ called on exit."""
        s1 = _make_async_server("s1")
        s2 = _make_async_server("s2")
        reg = MCPServerRegistry()
        reg.register("alpha", s1)
        reg.register("beta", s2)

        async with reg:
            pass

        s1.__aexit__.assert_awaited_once()
        s2.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_clears_started_set(self) -> None:
        """After exit, _started is empty."""
        s1 = _make_async_server("s1")
        reg = MCPServerRegistry()
        reg.register("alpha", s1)

        async with reg:
            assert len(reg._started) == 1

        assert len(reg._started) == 0

    @pytest.mark.asyncio
    async def test_aexit_continues_on_server_stop_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """If one server __aexit__ raises, others still get stopped."""
        s1 = _make_async_server("s1")
        s2 = _make_async_server("s2")
        s1.__aexit__ = AsyncMock(side_effect=RuntimeError("stop failed"))
        reg = MCPServerRegistry()
        reg.register("alpha", s1)
        reg.register("beta", s2)

        with caplog.at_level(logging.WARNING):
            async with reg:
                pass

        # s2 still stopped despite s1 raising
        s2.__aexit__.assert_awaited_once()
        assert "stop failed" in caplog.text


class TestMCPServerRegistryHealthCheck:
    """health_check() returns status dict per server."""

    @pytest.mark.asyncio
    async def test_health_check_all_alive(self) -> None:
        """All started servers report alive."""
        s1 = _make_async_server("s1")
        s2 = _make_async_server("s2")
        reg = MCPServerRegistry()
        reg.register("alpha", s1)
        reg.register("beta", s2)

        async with reg:
            status = reg.health_check()

        assert status == {"alpha": True, "beta": True}

    @pytest.mark.asyncio
    async def test_health_check_empty_registry(self) -> None:
        """Empty registry returns empty dict."""
        reg = MCPServerRegistry()
        async with reg:
            status = reg.health_check()
        assert status == {}

    @pytest.mark.asyncio
    async def test_health_check_partial_start(self) -> None:
        """Server that failed to start reports not alive."""
        s1 = _make_async_server("s1")
        s2 = _make_async_server("s2")
        s2.__aenter__ = AsyncMock(side_effect=RuntimeError("crash"))
        reg = MCPServerRegistry()
        reg.register("alpha", s1)
        reg.register("beta", s2)

        async with reg:
            status = reg.health_check()

        assert status == {"alpha": True, "beta": False}


class TestMCPServerRegistryCrashHandling:
    """Server crash during start is logged, not propagated."""

    @pytest.mark.asyncio
    async def test_server_start_failure_logged_and_skipped(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """If a server __aenter__ raises, it is logged and others still start."""
        s1 = _make_async_server("s1")
        s2 = _make_async_server("s2")
        s1.__aenter__ = AsyncMock(side_effect=RuntimeError("start crash"))
        reg = MCPServerRegistry()
        reg.register("alpha", s1)
        reg.register("beta", s2)

        with caplog.at_level(logging.WARNING):
            async with reg:
                pass

        # s2 was started despite s1 crashing
        s2.__aenter__.assert_awaited_once()
        assert "start crash" in caplog.text
        assert "alpha" not in reg._started

    @pytest.mark.asyncio
    async def test_all_servers_fail_still_exits_cleanly(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """If all servers fail to start, context manager still works."""
        s1 = _make_async_server("s1")
        s1.__aenter__ = AsyncMock(side_effect=RuntimeError("fail"))
        reg = MCPServerRegistry()
        reg.register("alpha", s1)

        with caplog.at_level(logging.WARNING):
            async with reg:
                status = reg.health_check()

        assert status == {"alpha": False}


class TestMCPServerRegistryDaemonIntegration:
    """Integration: registry lifecycle wraps daemon loop."""

    @pytest.mark.asyncio
    async def test_registry_usable_as_context_manager_around_work(self) -> None:
        """Simulates daemon wrapping its loop in async with registry."""
        s1 = _make_async_server("s1")
        reg = MCPServerRegistry()
        reg.register("service", s1)

        work_done = False
        async with reg:
            # Simulate daemon work
            assert reg.health_check() == {"service": True}
            work_done = True

        assert work_done
        # After exit, servers stopped
        s1.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exception_in_daemon_loop_still_stops_servers(self) -> None:
        """If the daemon loop raises, __aexit__ still runs."""
        s1 = _make_async_server("s1")
        reg = MCPServerRegistry()
        reg.register("service", s1)

        msg = "daemon error"
        with pytest.raises(ValueError, match=msg):
            async with reg:
                raise ValueError(msg)

        s1.__aexit__.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tool resolver mcp: prefix integration
# ---------------------------------------------------------------------------


class TestToolResolverMCPPrefix:
    """tool_resolver recognizes 'mcp:github' prefix and returns MCPServer toolset."""

    def test_mcp_prefix_resolves_to_mcp_server(self, tmp_path: Path) -> None:
        """mcp:github should return the registered MCPServer instance."""
        from owlbear.core.agent_registry import AgentRegistry

        mock_server = MagicMock()
        mcp_reg = MCPServerRegistry()
        mcp_reg.register("github", mock_server)

        def resolver(_name: str) -> FunctionToolset:
            return FunctionToolset()

        registry = AgentRegistry(
            tmp_path,
            resolver,
            default_model="test",
            mcp_registry=mcp_reg,
        )

        md = tmp_path / "mcp_agent.md"
        md.write_text(
            "---\nname: mcp_agent\ndescription: Uses MCP\ntools:\n  - mcp:github\n---\nBody.\n",
            encoding="utf-8",
        )
        registry.scan()
        agent = registry.get("mcp_agent")
        assert isinstance(agent, Agent)

    def test_nonmcp_prefix_still_uses_function_resolver(self, tmp_path: Path) -> None:
        """'filesystem' prefix still returns FunctionToolset (no regression)."""
        from owlbear.core.agent_registry import AgentRegistry

        mock_toolset = FunctionToolset()

        def resolver(_name: str) -> FunctionToolset:
            return mock_toolset

        registry = AgentRegistry(
            tmp_path,
            resolver,
            default_model="test",
        )

        md = tmp_path / "fs_agent.md"
        md.write_text(
            "---\nname: fs_agent\ndescription: Uses FS tools\ntools:\n  - filesystem\n---\nBody.\n",
            encoding="utf-8",
        )
        registry.scan()
        agent = registry.get("fs_agent")
        assert isinstance(agent, Agent)

    def test_mcp_prefix_unknown_server_raises(self, tmp_path: Path) -> None:
        """mcp:unknown should raise KeyError during agent build."""
        from owlbear.core.agent_registry import AgentRegistry

        mcp_reg = MCPServerRegistry()

        def resolver(_name: str) -> FunctionToolset:
            return FunctionToolset()

        registry = AgentRegistry(
            tmp_path,
            resolver,
            default_model="test",
            mcp_registry=mcp_reg,
        )

        md = tmp_path / "bad_agent.md"
        md.write_text(
            "---\nname: bad_agent\ndescription: Bad MCP\ntools:\n  - mcp:unknown\n---\nBody.\n",
            encoding="utf-8",
        )
        registry.scan()
        with pytest.raises(KeyError, match="unknown"):
            registry.get("bad_agent")
