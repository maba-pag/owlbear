"""Integration tests for owlbear.bootstrap — full smoke test."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from pydantic_ai.models.test import TestModel

from owlbear.bootstrap import BootstrapResult, bootstrap
from owlbear.channels.cli import CLIChannel
from owlbear.config import OwlBearSettings
from owlbear.core.agent import OwlBearAgent
from owlbear.core.agent_registry import AgentRegistry
from owlbear.core.hooks import HookEvent
from owlbear.tools.hooked import HookedToolset


def _make_settings(tmp_path: Path, **overrides: object) -> OwlBearSettings:
    """Build test-safe settings pointing at *tmp_path*."""
    defaults = {
        "copilot_token_path": tmp_path / "token.json",
        "agents_dir": tmp_path / "agents",
        "usage_path": tmp_path / "usage.jsonl",
    }
    defaults.update(overrides)
    return OwlBearSettings(**defaults)  # type: ignore[arg-type]


def _toolset_names(result: BootstrapResult) -> set[str]:
    """Extract inner toolset class names from a bootstrap result."""
    names: set[str] = set()
    for ts in result.agent.inner._user_toolsets:
        if isinstance(ts, HookedToolset):
            names.add(type(ts.wrapped).__name__)
        else:
            names.add(type(ts).__name__)
    return names


# -- Fixtures ---------------------------------------------------------------


@pytest_asyncio.fixture
async def cli_result(tmp_path: Path) -> BootstrapResult:
    """Bootstrap with CLI channel, mocked model."""
    settings = _make_settings(tmp_path)
    with patch("owlbear.bootstrap.create_copilot_model", new_callable=AsyncMock) as m:
        m.return_value = "test"
        return await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)


# -- Tests ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_result_is_bootstrap_result(cli_result: BootstrapResult) -> None:
    assert isinstance(cli_result, BootstrapResult)


@pytest.mark.asyncio
async def test_agent_is_owlbear_agent(cli_result: BootstrapResult) -> None:
    assert isinstance(cli_result.agent, OwlBearAgent)


@pytest.mark.asyncio
async def test_channel_is_cli(cli_result: BootstrapResult) -> None:
    assert isinstance(cli_result.channel, CLIChannel)


@pytest.mark.asyncio
async def test_mcp_registry_none_when_not_configured(cli_result: BootstrapResult) -> None:
    assert cli_result.mcp_registry is None


@pytest.mark.asyncio
async def test_hooks_registered(cli_result: BootstrapResult) -> None:
    expected = {
        HookEvent.PRE_TOOL_USE,
        HookEvent.POST_TOOL_USE,
        HookEvent.ON_MESSAGE,
        HookEvent.ON_ERROR,
        HookEvent.SESSION_START,
        HookEvent.SESSION_END,
        HookEvent.SUBAGENT_COMPLETE,
        HookEvent.TASK_COMPLETE,
    }
    for ev in expected:
        assert ev in cli_result.hooks.handlers, f"Missing hook: {ev}"
        assert len(cli_result.hooks.handlers[ev]) >= 1, f"No handlers for {ev}"


@pytest.mark.asyncio
async def test_core_toolsets_present(cli_result: BootstrapResult) -> None:
    names = _toolset_names(cli_result)
    for required in ("FileToolset", "TerminalToolset", "AskUserToolset", "DelegationToolset"):
        assert required in names, f"Missing toolset: {required}"


@pytest.mark.asyncio
async def test_agent_registry_set(cli_result: BootstrapResult) -> None:
    assert isinstance(cli_result.agent._deps.agent_registry, AgentRegistry)


@pytest.mark.asyncio
async def test_cleanup_is_list(cli_result: BootstrapResult) -> None:
    assert isinstance(cli_result.cleanup, list)


@pytest.mark.asyncio
async def test_no_github_toolset_without_token(cli_result: BootstrapResult) -> None:
    names = _toolset_names(cli_result)
    assert "GitHubToolset" not in names


@pytest.mark.asyncio
async def test_github_toolset_with_token(tmp_path: Path) -> None:
    from pydantic import SecretStr

    settings = _make_settings(tmp_path, github_token=SecretStr("ghp_test123"))
    with patch("owlbear.bootstrap.create_copilot_model", new_callable=AsyncMock) as m:
        m.return_value = "test"
        result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)
    names = _toolset_names(result)
    assert "GitHubToolset" in names


@pytest.mark.asyncio
async def test_agent_turn_e2e(tmp_path: Path) -> None:
    """Verify agent.turn() works end-to-end with the test model."""
    settings = _make_settings(tmp_path)
    model = TestModel(custom_output_text="Hello!", call_tools=[])
    with patch("owlbear.bootstrap.create_copilot_model", new_callable=AsyncMock) as m:
        m.return_value = model
        result = await bootstrap(settings, channel_name="cli", workspace_root=tmp_path)
    reply = await result.agent.turn("Say hello")
    assert reply == "Hello!"
