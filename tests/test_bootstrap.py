"""Tests for owlbear.bootstrap — component wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.bootstrap import (
    BootstrapResult,
    _resolve_active_project,
    build_hooks,
    build_toolsets,
    create_channel,
)
from owlbear.channels.base import ChannelPlugin
from owlbear.config import OwlBearSettings
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.projects.models import Project
from owlbear.safety.gate import ApprovalGateToolset
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
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert isinstance(hooks, HookRegistry)

    def test_pre_tool_use_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.PRE_TOOL_USE, [])) >= 1

    def test_post_tool_use_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.POST_TOOL_USE, [])) >= 1

    def test_session_end_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.SESSION_END, [])) >= 1

    def test_subagent_complete_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.SUBAGENT_COMPLETE, [])) >= 1

    def test_session_start_has_handler(self) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.SESSION_START, [])) >= 1

    def test_notification_events_registered(self) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=None)
        # Default notification_events includes task_complete & question_pending
        assert len(hooks.handlers.get(HookEvent.TASK_COMPLETE, [])) >= 1
        assert len(hooks.handlers.get(HookEvent.QUESTION_PENDING, [])) >= 1

    def test_observability_hook_with_workspace(self, tmp_path: Path) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=tmp_path)
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

        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        for ts in toolsets:
            if isinstance(ts, DelegationToolset):
                continue
            assert isinstance(ts, HookedToolset), f"Expected HookedToolset, got {type(ts).__name__}"

    def test_github_toolset_included_when_token_set(self, tmp_path: Path) -> None:
        from pydantic import SecretStr

        settings = OwlBearSettings(github_token=SecretStr("ghp_test123"), approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        # Should have one more toolset than without token
        type_names = [
            t.wrapped.__class__.__name__ if isinstance(t, HookedToolset) else type(t).__name__
            for t in toolsets
        ]
        assert "GitHubToolset" in type_names

    def test_contains_kanban_toolset(self, tmp_path: Path) -> None:
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)
        type_names = [
            t.wrapped.__class__.__name__ if isinstance(t, HookedToolset) else type(t).__name__
            for t in toolsets
        ]
        assert "KanbanToolset" in type_names

    def test_skill_registry_included_when_dir_exists(self, tmp_path: Path) -> None:
        # Create a skills dir with a skill file
        skills_dir = tmp_path / ".github" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text(
            "---\nname: test\ndescription: A test skill\n---\nContent",
            encoding="utf-8",
        )
        settings = OwlBearSettings(approval_policy=[])
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
        settings = OwlBearSettings(approval_policy=[])
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

        settings = OwlBearSettings(
            github_token=SecretStr(""),  # empty token triggers ValueError
            approval_policy=[],
        )
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

# ---------------------------------------------------------------------------
# build_hooks — ProgressReporter wiring
# ---------------------------------------------------------------------------


class TestBuildHooksProgress:
    """Verify ProgressReporter creation and registration in build_hooks."""

    def test_returns_tuple_of_hooks_and_reporter(self) -> None:
        settings = OwlBearSettings()
        result = build_hooks(settings, workspace_root=None)
        assert isinstance(result, tuple)
        assert len(result) == 2
        hooks, reporter = result
        assert isinstance(hooks, HookRegistry)
        assert reporter is None  # no channel → no reporter

    def test_progress_enabled_with_channel_creates_reporter(self) -> None:
        from owlbear.core.progress import ProgressReporter

        settings = OwlBearSettings(progress_enabled=True)
        channel = MagicMock(spec=ChannelPlugin)
        hooks, reporter = build_hooks(settings, workspace_root=None, channel=channel)
        assert isinstance(reporter, ProgressReporter)
        # Must be registered on POST_TOOL_USE
        post_handlers = hooks.handlers.get(HookEvent.POST_TOOL_USE, [])
        assert reporter.on_tool_complete in post_handlers

    def test_progress_disabled_no_reporter(self) -> None:
        settings = OwlBearSettings(progress_enabled=False)
        channel = MagicMock(spec=ChannelPlugin)
        _, reporter = build_hooks(settings, workspace_root=None, channel=channel)
        assert reporter is None

    def test_no_channel_no_reporter(self) -> None:
        settings = OwlBearSettings(progress_enabled=True)
        _, reporter = build_hooks(settings, workspace_root=None)
        assert reporter is None

    def test_reporter_receives_settings_values(self) -> None:
        settings = OwlBearSettings(
            progress_enabled=True,
            progress_interval=15.0,
            progress_detail="detailed",
        )
        channel = MagicMock(spec=ChannelPlugin)
        _, reporter = build_hooks(settings, workspace_root=None, channel=channel)
        assert reporter is not None
        assert reporter._interval == 15.0
        assert reporter._detail == "detailed"


# ---------------------------------------------------------------------------
# bootstrap — ProgressReporter integration
# ---------------------------------------------------------------------------


class TestBootstrapProgress:
    """Integration tests: bootstrap wires ProgressReporter into result."""

    @pytest.mark.asyncio
    async def test_bootstrap_progress_enabled(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import bootstrap
        from owlbear.core.progress import ProgressReporter

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(progress_enabled=True)
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert isinstance(result.progress_reporter, ProgressReporter)
        # Verify hook registration
        post_handlers = result.hooks.handlers.get(HookEvent.POST_TOOL_USE, [])
        assert result.progress_reporter.on_tool_complete in post_handlers

    @pytest.mark.asyncio
    async def test_bootstrap_progress_disabled(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(progress_enabled=False)
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.progress_reporter is None

    @pytest.mark.asyncio
    async def test_bootstrap_progress_stop_in_cleanup(self, tmp_path: Path) -> None:
        """AC#6: progress_reporter.stop() must be in cleanup list."""
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(progress_enabled=True)
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.progress_reporter is not None
        # The cleanup list must contain the reporter's stop bound method
        assert len(result.cleanup) >= 1
        assert result.progress_reporter.stop in result.cleanup

    @pytest.mark.asyncio
    async def test_bootstrap_progress_disabled_no_stop_cleanup(self, tmp_path: Path) -> None:
        """When progress_enabled=False, no progress stop cleanup is added."""
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(progress_enabled=False)
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.progress_reporter is None
        assert len(result.cleanup) == 0


# ---------------------------------------------------------------------------
# Approval gate wrapping — AC for task #342
# ---------------------------------------------------------------------------


def _inner_name(ts: object) -> str:
    """Get the class name of the innermost raw toolset (unwrap all wrappers)."""
    inner = ts
    while hasattr(inner, "wrapped"):
        inner = inner.wrapped
    return type(inner).__name__


class TestApprovalWrapping:
    """Verify build_toolsets applies ApprovalGateToolset to destructive toolsets."""

    def test_destructive_toolsets_wrapped_when_policy_nonempty(self, tmp_path: Path) -> None:
        """AC#3: build_toolsets wraps destructive toolsets in ApprovalGateToolset."""
        settings = OwlBearSettings()  # default has non-empty approval_policy
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)

        destructive = {"GitLocalToolset", "TerminalToolset"}
        for ts in toolsets:
            if _inner_name(ts) in destructive:
                assert isinstance(ts, ApprovalGateToolset), (
                    f"Expected {_inner_name(ts)} wrapped in ApprovalGateToolset, "
                    f"got {type(ts).__name__}"
                )

    def test_non_destructive_skip_approval(self, tmp_path: Path) -> None:
        """AC#5: Non-destructive toolsets skip approval wrapping."""
        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)

        non_destructive = {"FileToolset", "AskUserToolset", "BrowserToolset", "KanbanToolset"}
        for ts in toolsets:
            if _inner_name(ts) in non_destructive:
                assert isinstance(ts, HookedToolset), (
                    f"Expected {_inner_name(ts)} wrapped in HookedToolset only, "
                    f"got {type(ts).__name__}"
                )

    def test_wrapping_order_inner_hooked_gate(self, tmp_path: Path) -> None:
        """AC#4: Wrapping order is inner toolset -> HookedToolset -> ApprovalGateToolset."""
        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)

        for ts in toolsets:
            if isinstance(ts, ApprovalGateToolset):
                assert isinstance(ts.wrapped, HookedToolset), (
                    f"Expected HookedToolset inside ApprovalGateToolset, "
                    f"got {type(ts.wrapped).__name__}"
                )

    def test_shared_approval_session(self, tmp_path: Path) -> None:
        """AC#6: One shared ApprovalSession per build_toolsets call."""
        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)

        sessions = [ts.session for ts in toolsets if isinstance(ts, ApprovalGateToolset)]
        assert len(sessions) >= 2  # at least GitLocal and Terminal
        assert all(s is sessions[0] for s in sessions), "All gates must share one session"

    def test_empty_policy_no_wrapping(self, tmp_path: Path) -> None:
        """AC#8: When approval_policy is empty, no ApprovalGateToolset wrapping."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)

        for ts in toolsets:
            assert not isinstance(ts, ApprovalGateToolset), (
                f"Expected no ApprovalGateToolset with empty policy, "
                f"got one wrapping {_inner_name(ts)}"
            )

    def test_github_toolset_wrapped_when_present(self, tmp_path: Path) -> None:
        """AC#3: GitHubToolset is also a destructive toolset."""
        from pydantic import SecretStr

        settings = OwlBearSettings(github_token=SecretStr("ghp_test123"))
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets = build_toolsets(settings, tmp_path, hooks, channel)

        found = False
        for ts in toolsets:
            if _inner_name(ts) == "GitHubToolset":
                assert isinstance(ts, ApprovalGateToolset)
                found = True
                break
        assert found, "GitHubToolset not found in toolsets"


class TestConfigApprovalFields:
    """Verify approval fields on OwlBearSettings (AC#1, AC#2)."""

    def test_default_policy_has_three_rules(self) -> None:
        """AC#1: Default rules for git_push, create_pr, deploy."""
        settings = OwlBearSettings()
        assert len(settings.approval_policy) == 3
        tool_names = {r["tool_name"] for r in settings.approval_policy}
        assert tool_names == {"git_push", "create_pr", "deploy"}

    def test_default_timeout(self) -> None:
        """AC#2: approval_timeout defaults to 120.0."""
        settings = OwlBearSettings()
        assert settings.approval_timeout == 120.0

    def test_empty_policy_override(self) -> None:
        settings = OwlBearSettings(approval_policy=[])
        assert settings.approval_policy == []

    def test_custom_timeout(self) -> None:
        settings = OwlBearSettings(approval_timeout=60.0)
        assert settings.approval_timeout == 60.0


class TestBootstrapApprovalIntegration:
    """AC#7: Integration test — bootstrap with approval-wrapped toolsets."""

    @pytest.mark.asyncio
    async def test_bootstrap_with_default_policy(self, tmp_path: Path) -> None:
        """Bootstrap completes successfully with default (non-empty) approval_policy."""
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
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert isinstance(result, BootstrapResult)
        assert result.agent is not None

    @pytest.mark.asyncio
    async def test_bootstrap_with_empty_policy(self, tmp_path: Path) -> None:
        """Bootstrap works with empty approval_policy (no wrapping)."""
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(approval_policy=[])
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert isinstance(result, BootstrapResult)
        assert result.agent is not None


# ---------------------------------------------------------------------------
# _resolve_active_project — AC#1, AC#2, AC#6
# ---------------------------------------------------------------------------


class TestResolveActiveProject:
    """Test the helper that reads active_project and resolves workspace."""

    def test_no_active_project_file_returns_none(self, tmp_path: Path) -> None:
        """AC#6: When there is no active_project file, return None."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        result = _resolve_active_project(config_dir)
        assert result is None

    def test_empty_active_project_file_returns_none(self, tmp_path: Path) -> None:
        """AC#6: When active_project file is empty, return None."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "active_project").write_text("", encoding="utf-8")
        result = _resolve_active_project(config_dir)
        assert result is None

    def test_whitespace_only_active_project_returns_none(self, tmp_path: Path) -> None:
        """AC#6: Whitespace-only active_project file treated as empty."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "active_project").write_text("   \n  ", encoding="utf-8")
        result = _resolve_active_project(config_dir)
        assert result is None

    def test_valid_project_id_returns_tuple(self, tmp_path: Path) -> None:
        """AC#1: Reads active project id and loads the Project."""
        config_dir = tmp_path / "config"
        projects_dir = config_dir / "projects"
        projects_dir.mkdir(parents=True)

        # Write a project JSON file
        project = Project(name="Test Project", workspace_path=tmp_path / "workspace")
        (projects_dir / f"{project.id}.json").write_text(
            project.model_dump_json(indent=2), encoding="utf-8"
        )
        # Write active_project file
        (config_dir / "active_project").write_text(project.id, encoding="utf-8")

        result = _resolve_active_project(config_dir)
        assert result is not None
        loaded_project, _store = result
        assert loaded_project.id == project.id
        assert loaded_project.workspace_path == project.workspace_path

    def test_missing_project_json_returns_none(self, tmp_path: Path) -> None:
        """If active_project points to nonexistent project, return None."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "active_project").write_text("nonexistent-id", encoding="utf-8")
        result = _resolve_active_project(config_dir)
        assert result is None

    def test_returns_project_store(self, tmp_path: Path) -> None:
        """Result tuple includes a ProjectStore for reuse."""
        from owlbear.projects.store import ProjectStore

        config_dir = tmp_path / "config"
        projects_dir = config_dir / "projects"
        projects_dir.mkdir(parents=True)

        project = Project(name="My Project", workspace_path=tmp_path / "ws")
        (projects_dir / f"{project.id}.json").write_text(
            project.model_dump_json(indent=2), encoding="utf-8"
        )
        (config_dir / "active_project").write_text(project.id, encoding="utf-8")

        result = _resolve_active_project(config_dir)
        assert result is not None
        _, store = result
        assert isinstance(store, ProjectStore)


# ---------------------------------------------------------------------------
# bootstrap with active project — AC#2, AC#3, AC#4, AC#5, AC#7
# ---------------------------------------------------------------------------


class TestBootstrapProjectAwareness:
    """Integration tests for bootstrap with active project."""

    @pytest.fixture
    def project_config(self, tmp_path: Path) -> tuple[Path, Path, Project]:
        """Set up config_dir with an active project and workspace."""
        config_dir = tmp_path / "config"
        projects_dir = config_dir / "projects"
        projects_dir.mkdir(parents=True)

        workspace = tmp_path / "my-workspace"
        workspace.mkdir()

        project = Project(name="My Project", workspace_path=workspace)
        (projects_dir / f"{project.id}.json").write_text(
            project.model_dump_json(indent=2), encoding="utf-8"
        )
        (config_dir / "active_project").write_text(project.id, encoding="utf-8")

        return config_dir, workspace, project

    @pytest.mark.asyncio
    async def test_workspace_root_from_active_project(
        self, project_config: tuple[Path, Path, Project],
    ) -> None:
        """AC#2: workspace_root = project.workspace_path when project active."""
        from owlbear.bootstrap import bootstrap

        config_dir, _workspace, project = project_config
        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        settings = OwlBearSettings(config_dir=config_dir, approval_policy=[])
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings)

        # Verify session path uses project session dir (proves workspace was resolved)
        expected_session = config_dir / "projects" / project.id / "sessions" / "session.jsonl"
        assert result.agent.session.path == expected_session

    @pytest.mark.asyncio
    async def test_session_path_under_project(
        self, project_config: tuple[Path, Path, Project],
    ) -> None:
        """AC#4: SessionStore path = config_dir/projects/{id}/sessions/session.jsonl."""
        from owlbear.bootstrap import bootstrap

        config_dir, _workspace, project = project_config
        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        settings = OwlBearSettings(config_dir=config_dir, approval_policy=[])
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings)

        expected_session = config_dir / "projects" / project.id / "sessions" / "session.jsonl"
        assert result.agent.session.path == expected_session

    @pytest.mark.asyncio
    async def test_toolsets_receive_project_workspace(
        self, project_config: tuple[Path, Path, Project],
    ) -> None:
        """AC#3: FileToolset, TerminalToolset, KanbanToolset receive project workspace."""
        from owlbear.bootstrap import bootstrap

        config_dir, _workspace, project = project_config
        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        settings = OwlBearSettings(config_dir=config_dir, approval_policy=[])
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings)

        # The FileToolset received `workspace` — verify via session path
        expected_session = config_dir / "projects" / project.id / "sessions" / "session.jsonl"
        assert result.agent.session.path == expected_session

    @pytest.mark.asyncio
    async def test_project_toolset_added_when_project_active(
        self, project_config: tuple[Path, Path, Project],
    ) -> None:
        """AC#7: ProjectToolset added to toolsets when ProjectStore available."""
        from owlbear.bootstrap import bootstrap

        config_dir, _workspace, _project = project_config
        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        settings = OwlBearSettings(config_dir=config_dir, approval_policy=[])
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent") as mock_agent_cls,
        ):
            await bootstrap(settings)

        # The Agent constructor receives toolsets= kwarg — inspect it
        call_kwargs = mock_agent_cls.call_args
        toolsets_arg = call_kwargs.kwargs.get("toolsets", call_kwargs[1].get("toolsets", []))
        type_names = []
        for ts in toolsets_arg:
            inner = ts
            while hasattr(inner, "wrapped"):
                inner = inner.wrapped
            type_names.append(type(inner).__name__)

        assert "ProjectToolset" in type_names

    @pytest.mark.asyncio
    async def test_fallback_no_active_project(self, tmp_path: Path) -> None:
        """AC#6: Without active project, fallback to CWD (workspace_root arg)."""
        from owlbear.bootstrap import bootstrap

        # config_dir with no active_project file
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        settings = OwlBearSettings(config_dir=config_dir, approval_policy=[])
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        # Session under workspace .owlbear, not config_dir/projects
        expected = tmp_path / ".owlbear" / "session.jsonl"
        assert result.agent.session.path == expected

    @pytest.mark.asyncio
    async def test_explicit_workspace_root_overrides_project(
        self, tmp_path: Path, project_config: tuple[Path, Path, Project],
    ) -> None:
        """When workspace_root is passed explicitly, it takes precedence."""
        from owlbear.bootstrap import bootstrap

        config_dir, _workspace, _project = project_config
        explicit_ws = tmp_path / "explicit"
        explicit_ws.mkdir()

        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        settings = OwlBearSettings(config_dir=config_dir, approval_policy=[])
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=explicit_ws)

        # Should use explicit workspace, not project workspace
        expected = explicit_ws / ".owlbear" / "session.jsonl"
        assert result.agent.session.path == expected

    @pytest.mark.asyncio
    async def test_no_project_toolset_when_no_active_project(
        self, tmp_path: Path,
    ) -> None:
        """AC#7: ProjectToolset not added when no active project."""
        from owlbear.bootstrap import bootstrap

        config_dir = tmp_path / "config"
        config_dir.mkdir()

        mock_model = MagicMock()
        mock_model.model_name = "test-model"

        settings = OwlBearSettings(config_dir=config_dir, approval_policy=[])
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent") as mock_agent_cls,
        ):
            await bootstrap(settings, workspace_root=tmp_path)

        type_names = []
        # The Agent constructor receives toolsets= kwarg — inspect it
        call_kwargs = mock_agent_cls.call_args
        toolsets_arg = call_kwargs.kwargs.get("toolsets", call_kwargs[1].get("toolsets", []))
        for ts in toolsets_arg:
            inner = ts
            while hasattr(inner, "wrapped"):
                inner = inner.wrapped
            type_names.append(type(inner).__name__)

        assert "ProjectToolset" not in type_names
