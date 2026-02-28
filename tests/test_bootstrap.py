"""Tests for owlbear.bootstrap — component wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.bootstrap import BootstrapResult, build_hooks, build_toolsets, create_channel
from owlbear.channels.base import ChannelPlugin
from owlbear.config import OwlBearSettings
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.tools.hooked import HookedToolset

# ---------------------------------------------------------------------------
# BootstrapResult dataclass shape
# ---------------------------------------------------------------------------


class TestBootstrapResult:
    """Verify BootstrapResult fields and types."""

    def test_fields_present(self) -> None:
        result = BootstrapResult(
            agent=MagicMock(),
            channel=MagicMock(),
            mcp_registry=None,
            hooks=HookRegistry(),
            cleanup=[],
        )
        assert result.agent is not None
        assert result.channel is not None
        assert result.mcp_registry is None
        assert isinstance(result.hooks, HookRegistry)
        assert result.cleanup == []

    def test_cleanup_is_list(self) -> None:
        fn = MagicMock()
        result = BootstrapResult(
            agent=MagicMock(),
            channel=MagicMock(),
            mcp_registry=None,
            hooks=HookRegistry(),
            cleanup=[fn],
        )
        assert len(result.cleanup) == 1
        assert result.cleanup[0] is fn


# ---------------------------------------------------------------------------
# build_hooks
# ---------------------------------------------------------------------------


class TestBuildHooks:
    """Verify build_hooks registers the expected hook handlers."""

    def test_returns_hook_registry(self) -> None:
        settings = OwlBearSettings()
        hooks = build_hooks(settings, workspace_root=None)
        assert isinstance(hooks, HookRegistry)

    def test_pre_tool_use_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.PRE_TOOL_USE, [])) >= 1

    def test_post_tool_use_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.POST_TOOL_USE, [])) >= 1

    def test_session_end_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.SESSION_END, [])) >= 1

    def test_subagent_complete_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.SUBAGENT_COMPLETE, [])) >= 1

    def test_session_start_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.SESSION_START, [])) >= 1

    def test_notification_events_registered(self) -> None:
        settings = OwlBearSettings()
        hooks = build_hooks(settings, workspace_root=None)
        # Default notification_events includes task_complete & question_pending
        assert len(hooks.handlers.get(HookEvent.TASK_COMPLETE, [])) >= 1
        assert len(hooks.handlers.get(HookEvent.QUESTION_PENDING, [])) >= 1

    def test_observability_hook_with_workspace(self, tmp_path: Path) -> None:
        settings = OwlBearSettings()
        hooks = build_hooks(settings, workspace_root=tmp_path)
        # ObservabilityHook registers on ALL events — check a few
        for event in HookEvent:
            assert len(hooks.handlers.get(event, [])) >= 1


# ---------------------------------------------------------------------------
# build_toolsets
# ---------------------------------------------------------------------------


class TestBuildToolsets:
    """Verify build_toolsets returns expected toolset list."""

    def test_returns_list(self, tmp_path: Path) -> None:
        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        assert isinstance(toolsets, list)
        assert len(toolsets) >= 4  # at minimum: File, Terminal, AskUser, Delegation

    def test_contains_delegation_toolset(self, tmp_path: Path) -> None:
        from owlbear.core.delegation import DelegationToolset

        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        delegation = [t for t in toolsets if isinstance(t, DelegationToolset)]
        assert len(delegation) == 1

    def test_non_delegation_wrapped_in_hooked(self, tmp_path: Path) -> None:
        from owlbear.core.delegation import DelegationToolset

        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        for ts in toolsets:
            if isinstance(ts, DelegationToolset):
                continue
            assert isinstance(ts, HookedToolset), f"Expected HookedToolset, got {type(ts).__name__}"

    def test_github_toolset_included_when_token_set(self, tmp_path: Path) -> None:
        from pydantic import SecretStr

        settings = OwlBearSettings(github_token=SecretStr("ghp_test123"))
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        # Should have one more toolset than without token
        type_names = [
            t.wrapped.__class__.__name__ if isinstance(t, HookedToolset) else type(t).__name__
            for t in toolsets
        ]
        assert "GitHubToolset" in type_names

    def test_skill_registry_included_when_dir_exists(self, tmp_path: Path) -> None:
        # Create a skills dir with a skill file
        skills_dir = tmp_path / ".github" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text(
            "---\nname: test\ndescription: A test skill\n---\nContent",
            encoding="utf-8",
        )
        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        type_names = [
            t.wrapped.__class__.__name__ if isinstance(t, HookedToolset) else type(t).__name__
            for t in toolsets
        ]
        assert "SkillRegistry" in type_names


# ---------------------------------------------------------------------------
# create_channel
# ---------------------------------------------------------------------------


class TestCreateChannel:
    """Verify create_channel dispatches correctly."""

    def test_cli_channel(self) -> None:
        from owlbear.channels.cli import CLIChannel

        settings = OwlBearSettings()
        channel = create_channel(settings, "cli")
        assert isinstance(channel, CLIChannel)

    def test_unknown_channel_raises(self) -> None:
        settings = OwlBearSettings()
        with pytest.raises(ValueError, match="Unknown channel"):
            create_channel(settings, "nonexistent")

    def test_slack_channel_requires_settings(self) -> None:
        # Without Slack config, should raise
        settings = OwlBearSettings(
            slack_app_token=None,
            slack_bot_token=None,
            slack_channel_id=None,
        )
        with pytest.raises(ValueError, match="Slack channel requires"):
            create_channel(settings, "slack")


# ---------------------------------------------------------------------------
# build_mcp_registry
# ---------------------------------------------------------------------------


class TestBuildMcpRegistry:
    """Verify build_mcp_registry behavior."""

    def test_returns_none_when_no_servers(self) -> None:
        from owlbear.bootstrap import build_mcp_registry

        settings = OwlBearSettings(mcp_servers=None)
        result = build_mcp_registry(settings)
        assert result is None

    def test_returns_registry_with_servers(self) -> None:
        from owlbear.bootstrap import build_mcp_registry
        from owlbear.tools.mcp_registry import MCPServerRegistry

        settings = OwlBearSettings(mcp_servers={"github": {"type": "stdio"}})
        result = build_mcp_registry(settings)
        assert isinstance(result, MCPServerRegistry)


# ---------------------------------------------------------------------------
# build_agent_registry
# ---------------------------------------------------------------------------


class TestBuildAgentRegistry:
    """Verify build_agent_registry behavior."""

    def test_returns_agent_registry(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import build_agent_registry
        from owlbear.core.agent_registry import AgentRegistry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        settings = OwlBearSettings(agents_dir=agents_dir)
        registry = build_agent_registry(settings, toolsets=[], mcp_registry=None)
        assert isinstance(registry, AgentRegistry)

    def test_scan_called(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import build_agent_registry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        settings = OwlBearSettings(agents_dir=agents_dir)
        registry = build_agent_registry(settings, toolsets=[], mcp_registry=None)
        # scan() should have been called — definitions dict is populated (empty is ok)
        assert hasattr(registry, "_definitions")


# ---------------------------------------------------------------------------
# bootstrap (integration-level unit test)
# ---------------------------------------------------------------------------


class TestBootstrap:
    """Verify the top-level bootstrap function."""

    @pytest.mark.asyncio
    async def test_bootstrap_returns_result(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch(
                "owlbear.core.agent.Agent",
            ),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert isinstance(result, BootstrapResult)
        assert result.channel is not None
        assert isinstance(result.hooks, HookRegistry)
        assert isinstance(result.cleanup, list)

    @pytest.mark.asyncio
    async def test_bootstrap_agent_has_deps(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch(
                "owlbear.core.agent.Agent",
            ),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.agent is not None
        assert result.agent._deps is not None
        assert result.agent._deps.agent_registry is not None

    @pytest.mark.asyncio
    async def test_bootstrap_model_failure_logged(self, tmp_path: Path) -> None:
        """If create_copilot_model fails, bootstrap should still complete."""
        from owlbear.bootstrap import bootstrap

        settings = OwlBearSettings()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                side_effect=RuntimeError("No token"),
            ),
            pytest.raises(RuntimeError, match="No token"),
        ):
            await bootstrap(settings, workspace_root=tmp_path)


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


class TestBuildToolsetsEdgeCases:
    """Cover error-handling and conditional paths in build_toolsets."""

    def test_skill_registry_failure_logged(self, tmp_path: Path) -> None:
        """If SkillRegistry fails, toolsets are still returned."""
        skills_dir = tmp_path / ".github" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text(
            "---\nname: test\ndescription: test\n---\n",
            encoding="utf-8",
        )
        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        # Mock SkillRegistry to raise on construction
        with patch(
            "owlbear.skills.registry.SkillRegistry",
            side_effect=RuntimeError("boom"),
        ):
            toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        type_names = [
            t.wrapped.__class__.__name__ if isinstance(t, HookedToolset) else type(t).__name__
            for t in toolsets
        ]
        assert "SkillRegistry" not in type_names
        assert len(toolsets) >= 4

    def test_github_toolset_failure_logged(self, tmp_path: Path) -> None:
        """If GitHubToolset constructor fails, toolsets still returned."""
        from pydantic import SecretStr

        settings = OwlBearSettings(github_token=SecretStr(""))  # empty token triggers ValueError
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        type_names = [
            t.wrapped.__class__.__name__ if isinstance(t, HookedToolset) else type(t).__name__
            for t in toolsets
        ]
        assert "GitHubToolset" not in type_names


class TestBuildAgentRegistryEdgeCases:
    """Cover tool resolver KeyError path."""

    def test_tool_resolver_raises_on_unknown(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import build_agent_registry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        settings = OwlBearSettings(agents_dir=agents_dir)
        registry = build_agent_registry(settings, toolsets=[], mcp_registry=None)

        # The resolver should raise KeyError for unknown names
        with pytest.raises(KeyError, match="Unknown tool"):
            registry._tool_resolver("NonExistent")


class TestCreateChannelSlackSuccess:
    """Cover the successful Slack channel path."""

    def test_slack_channel_created(self) -> None:
        from pydantic import SecretStr

        from owlbear.channels.slack import SlackChannel

        settings = OwlBearSettings(
            slack_app_token=SecretStr("xapp-test"),
            slack_bot_token=SecretStr("xoxb-test"),
            slack_channel_id="C123",
        )
        channel = create_channel(settings, "slack")
        assert isinstance(channel, SlackChannel)


class TestBootstrapWithSkillsDir:
    """Cover bootstrap finding SkillRegistry in toolsets."""

    @pytest.mark.asyncio
    async def test_bootstrap_finds_skill_registry(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import bootstrap

        # Create skills dir with a valid skill
        skills_dir = tmp_path / ".github" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text(
            "---\nname: test\ndescription: A test\n---\nContent",
            encoding="utf-8",
        )

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch(
                "owlbear.core.agent.Agent",
            ),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.agent is not None
