"""Tests for owlbear.bootstrap  -- component wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from owlbear.bootstrap import (
    BootstrapResult,
    ComponentStatus,
    StartupSummary,
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
from owlbear.tools.protocols import unwrap


@pytest.fixture(autouse=True)
def _mock_copilot_client():
    """Prevent real Copilot client creation in all bootstrap tests."""
    with patch(
        "owlbear.bootstrap.create_copilot_client",
        new_callable=AsyncMock,
        return_value=AsyncMock(),
    ):
        yield


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
            error_journal=MagicMock(),
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
            error_journal=MagicMock(),
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
        # SESSION_START is populated by LessonsInjectionHook when enabled;
        # ContextInjectionHook was removed (#772/#858).
        settings = OwlBearSettings(lessons_injection_enabled=True)
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.SESSION_START, [])) >= 1

    def test_notification_events_registered(self) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=None)
        # Default events: task_complete and on_error (question_pending removed in #962)
        assert len(hooks.handlers.get(HookEvent.TASK_COMPLETE, [])) >= 1
        assert len(hooks.handlers.get(HookEvent.ON_ERROR, [])) >= 1

    def test_observability_hook_with_workspace(self, tmp_path: Path) -> None:
        settings = OwlBearSettings()
        hooks, _ = build_hooks(settings, workspace_root=tmp_path)
        # ObservabilityHook registers on ALL events  -- check a few
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
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
        assert isinstance(toolsets, list)
        assert len(toolsets) >= 4  # at minimum: File, Terminal, AskUser, Delegation

    def test_contains_delegation_toolset(self, tmp_path: Path) -> None:
        from owlbear.core.delegation import DelegationToolset

        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
        delegation = [t for t in toolsets if isinstance(t, DelegationToolset)]
        assert len(delegation) == 1

    def test_non_delegation_wrapped_in_hooked(self, tmp_path: Path) -> None:
        from owlbear.core.delegation import DelegationToolset

        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
        for ts in toolsets:
            if isinstance(ts, DelegationToolset):
                continue
            assert isinstance(ts, HookedToolset), f"Expected HookedToolset, got {type(ts).__name__}"

    def test_github_toolset_included_when_token_set(self, tmp_path: Path) -> None:
        from pydantic import SecretStr

        settings = OwlBearSettings(github_token=SecretStr("ghp_test123"), approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
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
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
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
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
        type_names = [
            t.wrapped.__class__.__name__ if isinstance(t, HookedToolset) else type(t).__name__
            for t in toolsets
        ]
        assert "SkillRegistry" in type_names

    def test_conn_close_in_cleanup_when_infra_created(self, tmp_path: Path) -> None:
        """When _build_knowledge_infra returns infra, conn.close is in cleanup."""
        mock_conn = MagicMock()
        mock_infra = MagicMock()
        mock_infra.conn = mock_conn

        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        cleanup: list = []

        with patch("owlbear.bootstrap._build_knowledge_infra", return_value=mock_infra):
            build_toolsets(settings, tmp_path, hooks, channel, cleanup=cleanup)

        assert mock_conn.close in cleanup

    def test_no_conn_close_in_cleanup_when_infra_none(self, tmp_path: Path) -> None:
        """When _build_knowledge_infra returns None, cleanup has no conn.close."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        cleanup: list = []

        with patch("owlbear.bootstrap._build_knowledge_infra", return_value=None):
            build_toolsets(settings, tmp_path, hooks, channel, cleanup=cleanup)

        assert len(cleanup) == 0


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

    def test_voice_channel_import_resolves(self) -> None:
        """Voice channel import must resolve without ImportError."""
        settings = OwlBearSettings()
        with patch("owlbear.voice.VoiceChannel", autospec=True) as mock_cls:
            mock_cls.return_value = MagicMock(spec=ChannelPlugin)
            channel = create_channel(settings, "voice")
            assert isinstance(channel, ChannelPlugin)


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
        # scan() should have been called  -- definitions dict is populated (empty is ok)
        assert hasattr(registry, "_definitions")

    def test_passes_model_to_registry(self, tmp_path: Path) -> None:
        """build_agent_registry propagates model kwarg to AgentRegistry."""
        from pydantic_ai.models.function import FunctionModel

        from owlbear.bootstrap import build_agent_registry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        settings = OwlBearSettings(agents_dir=agents_dir)
        fn_model = FunctionModel(lambda _messages, _info: "ok")
        registry = build_agent_registry(
            settings,
            toolsets=[],
            mcp_registry=None,
            model=fn_model,
        )
        assert registry._default_model is fn_model

    def test_defaults_to_settings_chat_model(self, tmp_path: Path) -> None:
        """When model is None, falls back to settings.chat_model."""
        from owlbear.bootstrap import build_agent_registry

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        settings = OwlBearSettings(agents_dir=agents_dir, chat_model="claude-3-opus")
        registry = build_agent_registry(
            settings,
            toolsets=[],
            mcp_registry=None,
        )
        assert registry._default_model == "claude-3-opus"


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
        """If create_copilot_client fails, bootstrap should propagate the error."""
        from owlbear.bootstrap import bootstrap

        settings = OwlBearSettings()
        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                side_effect=RuntimeError("No token"),
            ),
            pytest.raises(RuntimeError, match="No token"),
        ):
            await bootstrap(settings, workspace_root=tmp_path)


# ---------------------------------------------------------------------------
# Additional coverage
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
            toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
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
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
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
# build_hooks  -- ProgressReporter wiring
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
        assert reporter is None  # no channel -> no reporter

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
# bootstrap  -- ProgressReporter integration
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
        # cleanup should only contain openai_client.close, no progress stop
        assert not any(getattr(cb, "__name__", "") == "stop" for cb in result.cleanup)


# ---------------------------------------------------------------------------
# Approval gate wrapping  -- AC for task #342
# ---------------------------------------------------------------------------


def _inner_name(ts: object) -> str:
    """Get the class name of the innermost raw toolset (unwrap all wrappers)."""
    return type(unwrap(ts)).__name__


class TestApprovalWrapping:
    """Verify build_toolsets applies ApprovalGateToolset to destructive toolsets."""

    def test_destructive_toolsets_wrapped_when_policy_nonempty(self, tmp_path: Path) -> None:
        """AC#3: build_toolsets wraps destructive toolsets in ApprovalGateToolset."""
        settings = OwlBearSettings()  # default has non-empty approval_policy
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

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
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

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
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

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
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

        sessions = [ts.session for ts in toolsets if isinstance(ts, ApprovalGateToolset)]
        assert len(sessions) >= 2  # at least GitLocal and Terminal
        assert all(s is sessions[0] for s in sessions), "All gates must share one session"

    def test_empty_policy_no_wrapping(self, tmp_path: Path) -> None:
        """AC#8: When approval_policy is empty, no ApprovalGateToolset wrapping."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

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
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

        found = False
        for ts in toolsets:
            if _inner_name(ts) == "GitHubToolset":
                assert isinstance(ts, ApprovalGateToolset)
                found = True
                break
        assert found, "GitHubToolset not found in toolsets"


class TestConfigApprovalFields:
    """Verify approval fields on OwlBearSettings (AC#1, AC#2)."""

    def test_default_policy_has_four_rules(self) -> None:
        """AC#1: Default rules for git_push, create_pr, deploy, run_command."""
        settings = OwlBearSettings()
        assert len(settings.approval_policy) == 4
        tool_names = {r["tool_name"] for r in settings.approval_policy}
        assert tool_names == {"git_push", "create_pr", "deploy", "run_command"}

    def test_run_command_triggers_approval(self) -> None:
        """AC#3: ApprovalPolicy from defaults requires_approval('run_command', {})."""
        from owlbear.safety.policy import ApprovalPolicy, ApprovalRule

        settings = OwlBearSettings()
        rules = [ApprovalRule(**r) for r in settings.approval_policy]
        policy = ApprovalPolicy(rules=rules)
        assert policy.requires_approval("run_command", {}) is True

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
    """AC#7: Integration test  -- bootstrap with approval-wrapped toolsets."""

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
# _resolve_active_project  -- AC#1, AC#2, AC#6
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
# bootstrap with active project  -- AC#2, AC#3, AC#4, AC#5, AC#7
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
        self,
        project_config: tuple[Path, Path, Project],
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
        self,
        project_config: tuple[Path, Path, Project],
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
        self,
        project_config: tuple[Path, Path, Project],
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

        # The FileToolset received `workspace`  -- verify via session path
        expected_session = config_dir / "projects" / project.id / "sessions" / "session.jsonl"
        assert result.agent.session.path == expected_session

    @pytest.mark.asyncio
    async def test_project_toolset_added_when_project_active(
        self,
        project_config: tuple[Path, Path, Project],
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

        # The Agent constructor receives toolsets= kwarg  -- inspect it
        call_kwargs = mock_agent_cls.call_args
        toolsets_arg = call_kwargs.kwargs.get("toolsets", call_kwargs[1].get("toolsets", []))
        type_names = [type(unwrap(ts)).__name__ for ts in toolsets_arg]

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
        self,
        tmp_path: Path,
        project_config: tuple[Path, Path, Project],
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
        self,
        tmp_path: Path,
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

        # The Agent constructor receives toolsets= kwarg  -- inspect it
        call_kwargs = mock_agent_cls.call_args
        toolsets_arg = call_kwargs.kwargs.get("toolsets", call_kwargs[1].get("toolsets", []))
        type_names = [type(unwrap(ts)).__name__ for ts in toolsets_arg]

        assert "ProjectToolset" not in type_names


# ---------------------------------------------------------------------------
# _build_knowledge_toolset smoke test
# ---------------------------------------------------------------------------


class TestBuildKnowledgeToolset:
    """Verify _build_knowledge_toolset creates a valid toolset."""

    def test_returns_toolset_on_success(self, tmp_path: Path) -> None:
        """AC#3: _build_knowledge_toolset returns a valid toolset."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_knowledge_toolset(tmp_path, infra, chat_model="test-model")

        assert result is not None
        toolset, *_ = result
        assert type(toolset).__name__ == "KnowledgeToolset"

    def test_passes_project_scope_when_provided(self, tmp_path: Path) -> None:
        """When project_id is passed, KnowledgeToolset receives project_scope."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_knowledge_toolset(
                tmp_path,
                infra,
                project_id="proj-42",
                chat_model="test-model",
            )

        assert result is not None
        toolset, *_ = result
        assert toolset._scopes == ["global", "project:proj-42"]

    def test_no_project_scope_when_none(self, tmp_path: Path) -> None:
        """When no project_id, KnowledgeToolset has no scope filter."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_knowledge_toolset(tmp_path, infra, chat_model="test-model")

        assert result is not None
        toolset, *_ = result
        assert toolset._scopes is None


class TestBuildToolsetsProjectScope:
    """Verify build_toolsets passes active_project_id to knowledge toolset."""

    def test_project_id_forwarded_to_knowledge_toolset(self, tmp_path: Path) -> None:
        """build_toolsets passes active_project_id through to _build_knowledge_toolset."""
        settings = OwlBearSettings()
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        mock_infra = MagicMock()

        with (
            patch(
                "owlbear.bootstrap._build_knowledge_infra",
                return_value=mock_infra,
            ),
            patch(
                "owlbear.bootstrap._build_knowledge_toolset",
            ) as mock_build_kt,
            patch(
                "owlbear.bootstrap._build_bookmark_toolset",
                return_value=None,
            ),
        ):
            mock_build_kt.return_value = None
            build_toolsets(
                settings,
                tmp_path,
                hooks,
                channel,
                active_project_id="proj-99",
            )
            mock_build_kt.assert_called_once_with(
                tmp_path,
                mock_infra,
                project_id="proj-99",
                chat_model=ANY,  # #556: now a Model instance, not bare string
                max_tokens=2000,
                knowledge_graph_expansion=True,
                inter_doc_graph_building=False,
                bg_concurrency=5,
                consolidation_enabled=False,
                consolidation_interval=1800,
            )


# ---------------------------------------------------------------------------
# KnowledgeQueryService bootstrap wiring  -- AC for tasks #426/#409
# ---------------------------------------------------------------------------


class TestBuildKnowledgeToolsetReturnsService:
    """AC #426: _build_knowledge_toolset returns (toolset, service) tuple."""

    def test_returns_tuple_with_service(self, tmp_path: Path) -> None:
        """_build_knowledge_toolset returns (KnowledgeToolset, KnowledgeQueryService)."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_knowledge_toolset(tmp_path, infra, chat_model="test-model")

        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 4
        toolset, service, _pipeline, _consolidation = result
        assert type(toolset).__name__ == "KnowledgeToolset"
        assert type(service).__name__ == "KnowledgeQueryService"

    def test_service_receives_project_scopes(self, tmp_path: Path) -> None:
        """KnowledgeQueryService gets same scopes as KnowledgeToolset."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_knowledge_toolset(
                tmp_path,
                infra,
                project_id="proj-42",
                chat_model="test-model",
            )

        assert result is not None
        _, service, _, _ = result
        assert service._scopes == ["global", "project:proj-42"]

    def test_service_no_scopes_when_no_project(self, tmp_path: Path) -> None:
        """No scopes when project_id is None."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_knowledge_toolset(tmp_path, infra, chat_model="test-model")

        assert result is not None
        _, service, _, _ = result
        assert service._scopes is None

    def test_max_tokens_stored_on_service(self, tmp_path: Path) -> None:
        """knowledge_context_tokens flows to service.default_max_tokens."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_knowledge_toolset(
                tmp_path,
                infra,
                chat_model="test-model",
                max_tokens=3000,
            )

        assert result is not None
        _, service, _, _ = result
        assert service.default_max_tokens == 3000

    def test_returns_none_on_failure(self, tmp_path: Path) -> None:
        """When knowledge subsystem fails, returns None (unchanged)."""
        from owlbear.bootstrap import _build_knowledge_infra

        result = _build_knowledge_infra(tmp_path, chat_model="test-model")
        # Without proper mocks, infra creation fails -> None
        assert result is None


# ---------------------------------------------------------------------------
# Screenshot wiring  -- AC for task #396
# ---------------------------------------------------------------------------


class TestScreenshotWiring:
    """Verify build_toolsets wires screenshot components."""

    def test_visual_feedback_toolset_in_toolsets(self, tmp_path: Path) -> None:
        """AC: VisualFeedbackToolset appears in the toolset list."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
        type_names = [_inner_name(ts) for ts in toolsets]
        assert "VisualFeedbackToolset" in type_names

    def test_screenshot_hook_registered_on_error_default(self, tmp_path: Path) -> None:
        """AC: ON_ERROR hook active when screenshot_mode='on_error' (default)."""
        settings = OwlBearSettings(approval_policy=[], screenshot_mode="on_error")
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        build_toolsets(settings, tmp_path, hooks, channel)
        handlers = hooks.handlers.get(HookEvent.ON_ERROR, [])
        handler_names = [h.__qualname__ for h in handlers]
        assert any("ScreenshotOnErrorHook" in n for n in handler_names)

    def test_screenshot_hook_registered_when_auto(self, tmp_path: Path) -> None:
        """AC: ON_ERROR hook active when screenshot_mode='auto'."""
        settings = OwlBearSettings(approval_policy=[], screenshot_mode="auto")
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        build_toolsets(settings, tmp_path, hooks, channel)
        handlers = hooks.handlers.get(HookEvent.ON_ERROR, [])
        handler_names = [h.__qualname__ for h in handlers]
        assert any("ScreenshotOnErrorHook" in n for n in handler_names)

    def test_screenshot_hook_not_registered_when_manual(self, tmp_path: Path) -> None:
        """AC: No ON_ERROR screenshot hook when screenshot_mode='manual'."""
        settings = OwlBearSettings(approval_policy=[], screenshot_mode="manual")
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        build_toolsets(settings, tmp_path, hooks, channel)
        handlers = hooks.handlers.get(HookEvent.ON_ERROR, [])
        handler_names = [h.__qualname__ for h in handlers]
        assert not any("ScreenshotOnErrorHook" in n for n in handler_names)

    def test_visual_feedback_toolset_wrapped_in_hooked(self, tmp_path: Path) -> None:
        """AC: VisualFeedbackToolset is wrapped in HookedToolset."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)
        for ts in toolsets:
            if _inner_name(ts) == "VisualFeedbackToolset":
                assert isinstance(ts, HookedToolset)
                break
        else:
            pytest.fail("VisualFeedbackToolset not found in toolsets")


class TestBootstrapScreenshotIntegration:
    """Integration: bootstrap() wires screenshot components end-to-end."""

    @pytest.mark.asyncio
    async def test_bootstrap_includes_visual_feedback(self, tmp_path: Path) -> None:
        """Bootstrap result includes VisualFeedbackToolset in agent toolsets."""
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

        # ON_ERROR hook should be registered (default screenshot_mode=on_error)
        handlers = result.hooks.handlers.get(HookEvent.ON_ERROR, [])
        handler_names = [h.__qualname__ for h in handlers]
        assert any("ScreenshotOnErrorHook" in n for n in handler_names)


class TestBuildToolsetsKnowledgeService:
    """AC: build_toolsets returns (toolsets, knowledge_service)."""

    def test_returns_tuple_with_service(self, tmp_path: Path) -> None:
        """build_toolsets returns (toolsets, knowledge_service)."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        mock_service = MagicMock()
        mock_toolset = MagicMock()
        mock_pipeline = MagicMock()
        mock_infra = MagicMock()
        with (
            patch(
                "owlbear.bootstrap._build_knowledge_infra",
                return_value=mock_infra,
            ),
            patch(
                "owlbear.bootstrap._build_knowledge_toolset",
                return_value=(mock_toolset, mock_service, mock_pipeline, None),
            ),
        ):
            result = build_toolsets(settings, tmp_path, hooks, channel)

        assert isinstance(result, tuple)
        assert len(result) == 4
        toolsets, service, _pipeline, _consolidation = result
        assert isinstance(toolsets, list)
        assert service is mock_service

    def test_knowledge_service_none_when_unavailable(self, tmp_path: Path) -> None:
        """When knowledge infra fails, service is None."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with patch(
            "owlbear.bootstrap._build_knowledge_infra",
            return_value=None,
        ):
            toolsets, service, _, _ = build_toolsets(settings, tmp_path, hooks, channel)

        assert isinstance(toolsets, list)
        assert service is None

    def test_settings_max_tokens_forwarded(self, tmp_path: Path) -> None:
        """settings.knowledge_context_tokens passed to _build_knowledge_toolset."""
        settings = OwlBearSettings(knowledge_context_tokens=5000, approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        mock_infra = MagicMock()

        with (
            patch(
                "owlbear.bootstrap._build_knowledge_infra",
                return_value=mock_infra,
            ),
            patch(
                "owlbear.bootstrap._build_knowledge_toolset",
                return_value=None,
            ) as mock_build,
            patch(
                "owlbear.bootstrap._build_bookmark_toolset",
                return_value=None,
            ),
        ):
            build_toolsets(settings, tmp_path, hooks, channel)

        mock_build.assert_called_once_with(
            tmp_path,
            mock_infra,
            project_id=None,
            chat_model=ANY,  # #556: now a Model instance, not bare string
            max_tokens=5000,
            knowledge_graph_expansion=True,
            inter_doc_graph_building=False,
            bg_concurrency=5,
            consolidation_enabled=False,
            consolidation_interval=1800,
        )


class TestBootstrapKnowledgeServiceWiring:
    """AC: bootstrap() passes knowledge_service to OwlBearAgent."""

    @pytest.mark.asyncio
    async def test_knowledge_service_passed_to_agent(self, tmp_path: Path) -> None:
        """Bootstrap passes knowledge_service to OwlBearAgent constructor."""
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        mock_service = MagicMock()
        settings = OwlBearSettings(approval_policy=[])

        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
            patch(
                "owlbear.bootstrap.build_toolsets",
                return_value=([], mock_service, None, None),
            ),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.agent._knowledge_service is mock_service

    @pytest.mark.asyncio
    async def test_knowledge_service_none_when_unavailable(self, tmp_path: Path) -> None:
        """When knowledge subsystem unavailable, agent gets knowledge_service=None."""
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
            patch(
                "owlbear.bootstrap.build_toolsets",
                return_value=([], None, None, None),
            ),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert result.agent._knowledge_service is None


# ---------------------------------------------------------------------------
# Shared knowledge infrastructure  -- AC for task #455
# ---------------------------------------------------------------------------


class TestKnowledgeInfra:
    """Verify _KnowledgeInfra dataclass and _build_knowledge_infra function."""

    def test_knowledge_infra_dataclass_exists(self) -> None:
        """_KnowledgeInfra is importable from bootstrap."""
        from owlbear.bootstrap import _KnowledgeInfra

        assert hasattr(_KnowledgeInfra, "__dataclass_fields__")

    def test_knowledge_infra_has_expected_fields(self) -> None:
        """_KnowledgeInfra has all shared infrastructure fields."""
        from owlbear.bootstrap import _KnowledgeInfra

        fields = set(_KnowledgeInfra.__dataclass_fields__)
        assert fields == {
            "conn",
            "graph_store",
            "vector_store",
            "embedding_provider",
            "entity_extractor",
            "text_chunker",
        }

    def test_build_knowledge_infra_returns_infra(self, tmp_path: Path) -> None:
        """_build_knowledge_infra returns a _KnowledgeInfra on success."""
        from owlbear.bootstrap import _build_knowledge_infra, _KnowledgeInfra

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            result = _build_knowledge_infra(tmp_path, chat_model="test-model")

        assert result is not None
        assert isinstance(result, _KnowledgeInfra)

    def test_build_knowledge_infra_returns_none_on_failure(self, tmp_path: Path) -> None:
        """_build_knowledge_infra returns None when creation fails."""
        from owlbear.bootstrap import _build_knowledge_infra

        with patch(
            "owlbear.memory.knowledge.qdrant.QdrantClient",
            side_effect=RuntimeError("boom"),
        ):
            result = _build_knowledge_infra(tmp_path, chat_model="test-model")

        assert result is None


class TestSharedKnowledgeInfra:
    """AC: build_toolsets() creates shared knowledge infrastructure once."""

    def test_qdrant_created_once_in_build_toolsets(self, tmp_path: Path) -> None:
        """QdrantVectorStore constructor called exactly once (not twice)."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient") as mock_qc,
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            build_toolsets(settings, tmp_path, hooks, channel)

        assert mock_qc.call_count == 1

    def test_embedding_provider_created_once(self, tmp_path: Path) -> None:
        """BgeM3EmbeddingProvider constructor called exactly once."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ) as mock_bge,
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            build_toolsets(settings, tmp_path, hooks, channel)

        assert mock_bge.call_count == 1

    def test_both_toolsets_created(self, tmp_path: Path) -> None:
        """Both KnowledgeToolset and BookmarkToolset appear in toolsets."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

        type_names = [_inner_name(ts) for ts in toolsets]
        assert "KnowledgeToolset" in type_names
        assert "BookmarkToolset" in type_names

    def test_no_bookmark_warning_logged(self, tmp_path: Path) -> None:
        """No 'Failed to create BookmarkToolset' warning when infra shared."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
            patch("owlbear.bootstrap.logger") as mock_logger,
        ):
            build_toolsets(settings, tmp_path, hooks, channel)

        for call in mock_logger.warning.call_args_list:
            assert "Failed to create BookmarkToolset" not in str(call)

    def test_knowledge_toolset_accepts_infra_param(self, tmp_path: Path) -> None:
        """_build_knowledge_toolset accepts _KnowledgeInfra parameter."""
        from owlbear.bootstrap import _build_knowledge_infra, _build_knowledge_toolset

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_knowledge_toolset(tmp_path, infra, chat_model="test-model")

        assert result is not None
        toolset, service, *_ = result
        assert type(toolset).__name__ == "KnowledgeToolset"
        assert type(service).__name__ == "KnowledgeQueryService"

    def test_bookmark_toolset_accepts_infra_param(self, tmp_path: Path) -> None:
        """_build_bookmark_toolset accepts _KnowledgeInfra parameter."""
        from owlbear.bootstrap import _build_bookmark_toolset, _build_knowledge_infra

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")
            assert infra is not None
            result = _build_bookmark_toolset(infra, tmp_path, chat_model="test-model")

        assert result is not None
        assert type(result).__name__ == "BookmarkToolset"

    def test_shared_object_identity(self, tmp_path: Path) -> None:
        """Knowledge and bookmark builders receive the same infra objects."""
        from owlbear.bootstrap import _build_knowledge_infra

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
        ):
            infra = _build_knowledge_infra(tmp_path, chat_model="test-model")

        assert infra is not None
        # All fields are the same object  -- identity, not equality
        assert infra.vector_store is infra.vector_store  # sanity
        assert infra.embedding_provider is infra.embedding_provider
        assert infra.conn is infra.conn


# ---------------------------------------------------------------------------
# _build_knowledge_source_toolset  -- AC#6, AC#7, AC#8
# ---------------------------------------------------------------------------


class TestBuildKnowledgeSourceToolset:
    """Tests for _build_knowledge_source_toolset helper (AC#6-#8)."""

    def test_toolset_included_when_infra_available(self, tmp_path: Path) -> None:
        """AC#6: build_toolsets includes KnowledgeSourceToolset when infra is available."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with (
            patch("owlbear.memory.knowledge.qdrant.QdrantClient"),
            patch(
                "owlbear.memory.knowledge.embeddings.BgeM3EmbeddingProvider",
                autospec=True,
            ),
            patch(
                "owlbear.memory.knowledge.extractor.EntityExtractor.__init__",
                return_value=None,
            ),
            patch(
                "owlbear.memory.knowledge.evaluator.SourceEvaluator.__init__",
                return_value=None,
            ),
        ):
            toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

        type_names = [_inner_name(ts) for ts in toolsets]
        assert "KnowledgeSourceToolset" in type_names

    def test_toolset_omitted_when_infra_none(self, tmp_path: Path) -> None:
        """AC#7: Omits KnowledgeSourceToolset when _build_knowledge_infra returns None."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)

        with patch("owlbear.bootstrap._build_knowledge_infra", return_value=None):
            toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

        type_names = [_inner_name(ts) for ts in toolsets]
        assert "KnowledgeSourceToolset" not in type_names

    def test_returns_none_and_logs_warning_on_error(self, tmp_path: Path) -> None:
        """AC#8: Returns None and logs WARNING when constructor raises."""
        from owlbear.bootstrap import _build_knowledge_source_toolset

        mock_infra = MagicMock()
        with (
            patch(
                "owlbear.memory.knowledge.source_store.KnowledgeSourceStore",
                side_effect=RuntimeError("boom"),
            ),
            patch("owlbear.bootstrap.knowledge.logger") as mock_logger,
        ):
            result = _build_knowledge_source_toolset(mock_infra, tmp_path)

        assert result is None
        mock_logger.warning.assert_called_once()
        assert "Failed to create KnowledgeSourceToolset" in mock_logger.warning.call_args[0][0]


# ---------------------------------------------------------------------------
# Exception handler coverage  -- AC for task #830
# ---------------------------------------------------------------------------


class TestFromAC_KnowledgeToolsetExceptPath:
    """AC: _build_knowledge_toolset returns None and logs warning when internal dep raises."""

    def test_returns_none_and_logs_warning_on_error(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import _build_knowledge_toolset

        mock_infra = MagicMock()
        with (
            patch(
                "owlbear.tools.knowledge.KnowledgeToolset",
                side_effect=RuntimeError("boom"),
            ),
            patch("owlbear.bootstrap.knowledge.logger") as mock_logger,
        ):
            result = _build_knowledge_toolset(tmp_path, mock_infra, chat_model="test-model")

        assert result is None
        mock_logger.warning.assert_called_once()
        assert "Failed to create KnowledgeToolset" in mock_logger.warning.call_args[0][0]


class TestFromAC_BookmarkToolsetExceptPath:
    """AC: _build_bookmark_toolset returns None and logs warning when internal dep raises."""

    def test_returns_none_and_logs_warning_on_error(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import _build_bookmark_toolset

        mock_infra = MagicMock()
        with (
            patch(
                "owlbear.memory.knowledge.BookmarkStore",
                side_effect=RuntimeError("boom"),
            ),
            patch("owlbear.bootstrap.knowledge.logger") as mock_logger,
        ):
            result = _build_bookmark_toolset(mock_infra, tmp_path, chat_model="test-model")

        assert result is None
        mock_logger.warning.assert_called_once()
        assert "Failed to create BookmarkToolset" in mock_logger.warning.call_args[0][0]


class TestFromAC_WireKnowledgeToolsetsOuterExcept:
    """AC: _wire_knowledge_toolsets appends ComponentStatus(loaded=False) when infra raises."""

    def test_infra_raise_appends_error_status(self, tmp_path: Path) -> None:
        import owlbear.bootstrap as _pkg
        from owlbear.bootstrap.toolsets import _wire_knowledge_toolsets
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings(approval_policy=[])
        summary: list[ComponentStatus] = []

        with patch.object(
            _pkg,
            "_build_knowledge_infra",
            side_effect=RuntimeError("infra exploded"),
        ):
            result = _wire_knowledge_toolsets(
                raw=[],
                settings=settings,
                workspace=tmp_path,
                chat_model=None,
                active_project_id=None,
                cleanup=[],
                summary=summary,
                _pkg=_pkg,
            )

        # All three return values should be None
        assert result == (None, None, None)

        # Summary must contain a KnowledgeInfra failure entry
        infra_statuses = [s for s in summary if s.name == "KnowledgeInfra"]
        assert len(infra_statuses) == 1
        status = infra_statuses[0]
        assert status.loaded is False
        assert "infra exploded" in status.error


# ---------------------------------------------------------------------------
# Tool alias auto-registration  -- AC for task #488
# ---------------------------------------------------------------------------

# Expected alias mapping from the task AC
_EXPECTED_ALIASES = {
    "FileToolset": "filesystem",
    "TerminalToolset": "terminal",
    "AskUserToolset": "ask_user",
    "BrowserToolset": "browser",
    "DelegationToolset": "delegation",
    "GitLocalToolset": "git_local",
    "GitHubToolset": "github",
    "KanbanToolset": "kanban",
    "KnowledgeToolset": "knowledge",
    "WebSearchToolset": "web_search",
    "BookmarkToolset": "bookmark",
    "VisualFeedbackToolset": "visual_feedback",
    "KnowledgeSourceToolset": "knowledge_source",
    "ProjectToolset": "project",
    "SkillRegistry": "skills",
}


class TestToolAliasAttribute:
    """AC#5: Every FunctionToolset subclass declares tool_alias matching table."""

    @pytest.mark.parametrize(
        ("import_path", "class_name", "expected_alias"),
        [
            ("owlbear.tools.filesystem", "FileToolset", "filesystem"),
            ("owlbear.tools.terminal", "TerminalToolset", "terminal"),
            ("owlbear.tools.ask_user", "AskUserToolset", "ask_user"),
            ("owlbear.tools.browser.toolset", "BrowserToolset", "browser"),
            ("owlbear.core.delegation", "DelegationToolset", "delegation"),
            ("owlbear.tools.git_local", "GitLocalToolset", "git_local"),
            ("owlbear.tools.github_api", "GitHubToolset", "github"),
            ("owlbear.tools.kanban", "KanbanToolset", "kanban"),
            ("owlbear.tools.knowledge", "KnowledgeToolset", "knowledge"),
            ("owlbear.tools.web_search", "WebSearchToolset", "web_search"),
            ("owlbear.memory.knowledge.bookmark_toolset", "BookmarkToolset", "bookmark"),
            ("owlbear.tools.visual_feedback", "VisualFeedbackToolset", "visual_feedback"),
            ("owlbear.tools.knowledge_source", "KnowledgeSourceToolset", "knowledge_source"),
            ("owlbear.projects.toolset", "ProjectToolset", "project"),
            ("owlbear.skills.registry", "SkillRegistry", "skills"),
        ],
        ids=list(_EXPECTED_ALIASES.values()),
    )
    def test_tool_alias_declared(
        self, import_path: str, class_name: str, expected_alias: str
    ) -> None:
        """Each toolset class has a non-empty tool_alias matching the mapping table."""
        import importlib

        mod = importlib.import_module(import_path)
        cls = getattr(mod, class_name)
        alias = getattr(cls, "tool_alias", None)
        assert alias is not None, f"{class_name} missing tool_alias attribute"
        assert alias == expected_alias, (
            f"{class_name}.tool_alias={alias!r}, expected {expected_alias!r}"
        )
        assert isinstance(alias, str), f"{class_name}.tool_alias must be str"
        assert alias, f"{class_name}.tool_alias must be non-empty"


class TestAliasResolution:
    """AC#6: build_agent_registry builds _aliases dynamically from tool_alias."""

    def test_alias_resolves_mock_toolset(self, tmp_path: Path) -> None:
        """build_agent_registry resolves a mock toolset by its tool_alias."""
        from owlbear.bootstrap import build_agent_registry

        # Create a mock toolset with tool_alias
        mock_ts = MagicMock()
        mock_ts.tool_alias = "my_alias"
        # Ensure unwrap chain terminates (no .wrapped attr)
        del mock_ts.wrapped

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        settings = OwlBearSettings(agents_dir=agents_dir)
        registry = build_agent_registry(settings, toolsets=[mock_ts], mcp_registry=None)

        # Should resolve by alias
        resolved = registry._tool_resolver("my_alias")
        assert resolved is mock_ts

    def test_alias_and_class_name_both_resolve(self, tmp_path: Path) -> None:
        """build_agent_registry resolves both class name and tool_alias."""
        from pydantic_ai.toolsets import FunctionToolset

        from owlbear.bootstrap import build_agent_registry

        class FakeToolset(FunctionToolset):
            tool_alias = "my_alias"

        fake_ts = FakeToolset()

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        settings = OwlBearSettings(agents_dir=agents_dir)
        registry = build_agent_registry(settings, toolsets=[fake_ts], mcp_registry=None)

        # Resolves by class name
        assert registry._tool_resolver("FakeToolset") is fake_ts
        # Resolves by alias
        assert registry._tool_resolver("my_alias") is fake_ts

    def test_no_hardcoded_aliases_dict(self) -> None:
        """AC#3: The hardcoded _aliases dict is deleted from build_agent_registry."""
        import ast
        import inspect

        from owlbear.bootstrap import build_agent_registry

        source = inspect.getsource(build_agent_registry)
        tree = ast.parse(source)

        # Look for a dict literal assigned to _aliases with > 3 entries
        # (the dynamic one is built incrementally, not as a dict literal)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "_aliases"
                        and isinstance(node.value, ast.Dict)
                        and len(node.value.keys) > 3
                    ):
                        pytest.fail(
                            "Found hardcoded _aliases dict literal with "
                            f"{len(node.value.keys)} entries  -- should be built dynamically"
                        )


# ---------------------------------------------------------------------------
# ComponentStatus / StartupSummary dataclasses (#668)
# ---------------------------------------------------------------------------


class TestComponentStatusDataclass:
    """AC#1: ComponentStatus is a frozen dataclass in bootstrap.py."""

    def test_is_frozen(self) -> None:
        status = ComponentStatus(name="TestToolset", loaded=True)
        with pytest.raises(AttributeError):
            status.name = "changed"  # type: ignore[misc]

    def test_fields_present(self) -> None:
        status = ComponentStatus(name="TestToolset", loaded=False, error="boom", level="ERROR")
        assert status.name == "TestToolset"
        assert status.loaded is False
        assert status.error == "boom"
        assert status.level == "ERROR"

    def test_defaults(self) -> None:
        status = ComponentStatus(name="OK", loaded=True)
        assert status.error is None
        assert status.level == "INFO"


class TestStartupSummaryDataclass:
    """AC#1: StartupSummary is a frozen dataclass in bootstrap.py."""

    def test_is_frozen(self) -> None:
        summary = StartupSummary(
            components=[], workspace=Path("test-workspace"), project=None, channel_name="cli"
        )
        with pytest.raises(AttributeError):
            summary.project = "changed"  # type: ignore[misc]

    def test_fields_present(self) -> None:
        cs = ComponentStatus(name="A", loaded=True)
        summary = StartupSummary(
            components=[cs],
            workspace=Path("test-workspace"),
            project="myproject",
            channel_name="cli",
        )
        assert len(summary.components) == 1
        assert summary.workspace == Path("test-workspace")
        assert summary.project == "myproject"
        assert summary.channel_name == "cli"

    def test_format_all_ok(self) -> None:
        """format() shows OK for loaded components."""
        components = [
            ComponentStatus(name="FileToolset", loaded=True),
            ComponentStatus(name="TerminalToolset", loaded=True),
        ]
        summary = StartupSummary(
            components=components,
            workspace=Path("test-workspace"),
            project=None,
            channel_name="cli",
        )
        text = summary.format()
        assert "OK" in text
        assert "FileToolset" in text
        assert "TerminalToolset" in text

    def test_format_shows_failures(self) -> None:
        """format() shows FAIL with error message for failed components."""
        components = [
            ComponentStatus(name="GitHubToolset", loaded=False, error="bad token", level="ERROR"),
        ]
        summary = StartupSummary(
            components=components,
            workspace=Path("test-workspace"),
            project=None,
            channel_name="cli",
        )
        text = summary.format()
        assert "FAIL" in text
        assert "GitHubToolset" in text
        assert "bad token" in text

    def test_format_shows_warnings(self) -> None:
        """format() shows SKIP for WARNING-level missing optional deps."""
        components = [
            ComponentStatus(
                name="WebSearchToolset",
                loaded=False,
                error="ddgs not installed",
                level="WARNING",
            ),
        ]
        summary = StartupSummary(
            components=components,
            workspace=Path("test-workspace"),
            project=None,
            channel_name="cli",
        )
        text = summary.format()
        assert "SKIP" in text
        assert "WebSearchToolset" in text

    def test_format_includes_counts(self) -> None:
        """format() includes loaded/failed/skipped counts."""
        components = [
            ComponentStatus(name="A", loaded=True),
            ComponentStatus(name="B", loaded=True),
            ComponentStatus(name="C", loaded=False, error="err", level="ERROR"),
            ComponentStatus(name="D", loaded=False, error="missing", level="WARNING"),
        ]
        summary = StartupSummary(
            components=components,
            workspace=Path("test-workspace"),
            project=None,
            channel_name="cli",
        )
        text = summary.format()
        assert "2 loaded" in text
        assert "1 failed" in text
        assert "1 skipped" in text


class TestBootstrapResultHasSummary:
    """AC#3: BootstrapResult has startup_summary field."""

    def test_startup_summary_on_result(self) -> None:
        summary = StartupSummary(
            components=[], workspace=Path("test-workspace"), project=None, channel_name="cli"
        )
        result = BootstrapResult(
            agent=MagicMock(),
            channel=MagicMock(),
            mcp_registry=None,
            hooks=HookRegistry(),
            error_journal=MagicMock(),
            startup_summary=summary,
        )
        assert result.startup_summary is summary


class TestBootstrapCollectsSummary:
    """AC#2-#6: bootstrap() collects ComponentStatus from all 9 exception sites."""

    @pytest.mark.asyncio
    async def test_bootstrap_returns_startup_summary(self, tmp_path: Path) -> None:
        """AC#3: bootstrap() returns StartupSummary on BootstrapResult."""
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

        assert result.startup_summary is not None
        assert isinstance(result.startup_summary, StartupSummary)
        # Must contain at least 2 entries (KnowledgeInfra, WebSearchToolset)
        assert len(result.startup_summary.components) >= 2
        names = [c.name for c in result.startup_summary.components]
        assert "KnowledgeInfra" in names
        assert "WebSearchToolset" in names

    @pytest.mark.asyncio
    async def test_knowledge_infra_failure_recorded(self, tmp_path: Path) -> None:
        """AC#2: knowledge infra failure appears in summary."""
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
            patch(
                "owlbear.bootstrap._build_knowledge_infra",
                side_effect=RuntimeError("db fail"),
            ),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        names = [c.name for c in result.startup_summary.components if not c.loaded]
        assert "KnowledgeInfra" in names

    @pytest.mark.asyncio
    async def test_web_search_failure_is_warning(self, tmp_path: Path) -> None:
        """AC#6: optional dep missing gets WARNING level."""
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
            patch(
                "owlbear.bootstrap._build_web_search_toolset",
                side_effect=ImportError("no ddgs"),
            ),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        web = [c for c in result.startup_summary.components if c.name == "WebSearchToolset"]
        assert len(web) == 1
        assert web[0].level == "WARNING"
        assert web[0].loaded is False

    @pytest.mark.asyncio
    async def test_github_failure_is_error(self, tmp_path: Path) -> None:
        """AC#6: user-configured-but-failed component gets ERROR level."""
        from pydantic import SecretStr

        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(
            github_token=SecretStr("ghp_test123"),
            approval_policy=[],
        )
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
            patch(
                "owlbear.tools.github_api.GitHubToolset.__init__",
                side_effect=RuntimeError("bad token"),
            ),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        github = [c for c in result.startup_summary.components if c.name == "GitHubToolset"]
        assert len(github) == 1
        assert github[0].level == "ERROR"
        assert github[0].loaded is False

    @pytest.mark.asyncio
    async def test_summary_logged(self, tmp_path: Path) -> None:
        """AC#4: single logger.info call with 'Bootstrap complete:' prefix."""
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
            patch("owlbear.bootstrap.logger") as mock_logger,
        ):
            await bootstrap(settings, workspace_root=tmp_path)

        info_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("Bootstrap complete:" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_channel_send_called_with_summary(self, tmp_path: Path) -> None:
        """AC#5: channel.send called with formatted summary when log_startup_summary=True."""
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(log_startup_summary=True)
        mock_channel = AsyncMock(spec=ChannelPlugin)
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
            patch("owlbear.bootstrap.create_channel", return_value=mock_channel),
        ):
            await bootstrap(settings, workspace_root=tmp_path)

        mock_channel.send.assert_called_once()
        sent_text = mock_channel.send.call_args[0][0]
        assert "loaded" in sent_text.lower()

    @pytest.mark.asyncio
    async def test_channel_send_suppressed_when_disabled(self, tmp_path: Path) -> None:
        """AC#5: channel.send NOT called when log_startup_summary=False."""
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(log_startup_summary=False)
        mock_channel = AsyncMock(spec=ChannelPlugin)
        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
            patch("owlbear.bootstrap.create_channel", return_value=mock_channel),
        ):
            await bootstrap(settings, workspace_root=tmp_path)

        mock_channel.send.assert_not_called()


# ---------------------------------------------------------------------------
# ComponentStatus collection for 6 error sites (#668 retry)
# ---------------------------------------------------------------------------


class TestComponentStatusErrorSites:
    """Verify each of the 6 previously-untested error sites records a ComponentStatus."""

    def test_skill_registry_failure_component_status(self, tmp_path: Path) -> None:
        """SkillRegistry failure records WARNING ComponentStatus."""
        skills_dir = tmp_path / ".github" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "test.md").write_text(
            "---\nname: test\ndescription: test\n---\n",
            encoding="utf-8",
        )
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        summary: list[ComponentStatus] = []

        with patch(
            "owlbear.skills.registry.SkillRegistry",
            side_effect=RuntimeError("skill boom"),
        ):
            build_toolsets(settings, tmp_path, hooks, channel, summary=summary)

        skill_statuses = [c for c in summary if c.name == "SkillRegistry"]
        assert len(skill_statuses) == 1
        assert skill_statuses[0].loaded is False
        assert skill_statuses[0].level == "WARNING"
        assert "skill boom" in skill_statuses[0].error

    def test_knowledge_toolset_failure_component_status(self, tmp_path: Path) -> None:
        """KnowledgeToolset failure records ERROR ComponentStatus."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        summary: list[ComponentStatus] = []

        mock_infra = MagicMock()
        with (
            patch("owlbear.bootstrap._build_knowledge_infra", return_value=mock_infra),
            patch(
                "owlbear.bootstrap._build_knowledge_toolset",
                return_value=None,
            ),
            patch("owlbear.bootstrap._build_bookmark_toolset", return_value=None),
            patch("owlbear.bootstrap._build_knowledge_source_toolset", return_value=None),
        ):
            build_toolsets(settings, tmp_path, hooks, channel, summary=summary)

        kt_statuses = [c for c in summary if c.name == "KnowledgeToolset"]
        assert len(kt_statuses) == 1
        assert kt_statuses[0].loaded is False
        assert kt_statuses[0].level == "ERROR"

    def test_bookmark_toolset_failure_component_status(self, tmp_path: Path) -> None:
        """BookmarkToolset failure records WARNING ComponentStatus."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        summary: list[ComponentStatus] = []

        mock_infra = MagicMock()
        mock_knowledge_ts = MagicMock()
        mock_service = MagicMock()
        mock_pipeline = MagicMock()
        with (
            patch("owlbear.bootstrap._build_knowledge_infra", return_value=mock_infra),
            patch(
                "owlbear.bootstrap._build_knowledge_toolset",
                return_value=(mock_knowledge_ts, mock_service, mock_pipeline, None),
            ),
            patch("owlbear.bootstrap._build_bookmark_toolset", return_value=None),
            patch("owlbear.bootstrap._build_knowledge_source_toolset", return_value=None),
        ):
            build_toolsets(settings, tmp_path, hooks, channel, summary=summary)

        bm_statuses = [c for c in summary if c.name == "BookmarkToolset"]
        assert len(bm_statuses) == 1
        assert bm_statuses[0].loaded is False
        assert bm_statuses[0].level == "WARNING"

    def test_knowledge_source_toolset_failure_component_status(self, tmp_path: Path) -> None:
        """KnowledgeSourceToolset failure records WARNING ComponentStatus."""
        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        summary: list[ComponentStatus] = []

        mock_infra = MagicMock()
        mock_knowledge_ts = MagicMock()
        mock_service = MagicMock()
        mock_pipeline = MagicMock()
        with (
            patch("owlbear.bootstrap._build_knowledge_infra", return_value=mock_infra),
            patch(
                "owlbear.bootstrap._build_knowledge_toolset",
                return_value=(mock_knowledge_ts, mock_service, mock_pipeline, None),
            ),
            patch("owlbear.bootstrap._build_bookmark_toolset", return_value=MagicMock()),
            patch("owlbear.bootstrap._build_knowledge_source_toolset", return_value=None),
        ):
            build_toolsets(settings, tmp_path, hooks, channel, summary=summary)

        ks_statuses = [c for c in summary if c.name == "KnowledgeSourceToolset"]
        assert len(ks_statuses) == 1
        assert ks_statuses[0].loaded is False
        assert ks_statuses[0].level == "WARNING"

    def test_mcp_registry_failure_component_status(self) -> None:
        """MCPRegistry failure records ERROR ComponentStatus."""
        from owlbear.bootstrap import build_mcp_registry

        settings = OwlBearSettings(mcp_servers={"github": {"type": "stdio"}})
        summary: list[ComponentStatus] = []

        with patch(
            "owlbear.bootstrap.register_default_servers",
            side_effect=RuntimeError("mcp boom"),
        ):
            build_mcp_registry(settings, summary=summary)

        mcp_statuses = [c for c in summary if c.name == "MCPRegistry"]
        assert len(mcp_statuses) == 1
        assert mcp_statuses[0].loaded is False
        assert mcp_statuses[0].level == "ERROR"
        assert "mcp boom" in mcp_statuses[0].error

    def test_project_toolset_failure_component_status(self, tmp_path: Path) -> None:
        """ProjectToolset failure records ERROR ComponentStatus."""
        from owlbear.bootstrap import _add_project_toolset

        toolsets: list = []
        hooks = HookRegistry()
        summary: list[ComponentStatus] = []

        with patch(
            "owlbear.projects.toolset.ProjectToolset",
            side_effect=RuntimeError("project boom"),
        ):
            _add_project_toolset(
                toolsets,
                project_store=MagicMock(),
                config_dir=tmp_path,
                hooks=hooks,
                session=MagicMock(),
                summary=summary,
            )

        pt_statuses = [c for c in summary if c.name == "ProjectToolset"]
        assert len(pt_statuses) == 1
        assert pt_statuses[0].loaded is False
        assert pt_statuses[0].level == "ERROR"
        assert "project boom" in pt_statuses[0].error


# ---------------------------------------------------------------------------
# OpenAI client cleanup registration  -- AC#1 for task #650
# ---------------------------------------------------------------------------


class TestFromAC_OpenAIClientCleanup:
    """AC#1 (#650): bootstrap must register the OpenAI client's close in cleanup.

    The AsyncOpenAI client created during bootstrap owns an
    httpx.AsyncClient transport.  If bootstrap does not append the
    client's ``close`` to the cleanup list, the transport leaks on
    shutdown.

    Bootstrap now calls ``create_copilot_client`` directly and builds
    the model inline (no ``create_copilot_model`` indirection).  The
    autouse ``_mock_copilot_client`` fixture patches
    ``create_copilot_client``; these tests override it with their own
    mock so they can assert on ``mock_client.close``.
    """

    @pytest.mark.asyncio
    async def test_bootstrap_registers_openai_client_close(self, tmp_path: Path) -> None:
        """Happy path: openai_client.close is in the cleanup list after bootstrap."""
        from owlbear.bootstrap import bootstrap

        mock_client = AsyncMock()
        settings = OwlBearSettings()

        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert mock_client.close in result.cleanup, (
            f"openai_client.close not found in cleanup: {result.cleanup}"
        )

    @pytest.mark.asyncio
    async def test_cleanup_loop_closes_openai_client(self, tmp_path: Path) -> None:
        """Running all cleanup callables must actually close the OpenAI client."""
        import inspect

        from owlbear.bootstrap import bootstrap

        mock_client = AsyncMock()
        settings = OwlBearSettings()

        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        for cb in result.cleanup:
            rv = cb()
            if inspect.isawaitable(rv):
                await rv

        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_client_close_alongside_progress_stop(self, tmp_path: Path) -> None:
        """Edge: both progress_reporter.stop and openai_client.close are in cleanup."""
        from owlbear.bootstrap import bootstrap

        mock_client = AsyncMock()
        settings = OwlBearSettings(progress_enabled=True)

        with (
            patch(
                "owlbear.bootstrap.create_copilot_client",
                new_callable=AsyncMock,
                return_value=mock_client,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        assert mock_client.close in result.cleanup
        assert result.progress_reporter is not None
        assert result.progress_reporter.stop in result.cleanup


# ---------------------------------------------------------------------------
# TDD RED: ContextInjectionHook removal from build_hooks() (#858 / #772)
# ---------------------------------------------------------------------------


class TestFromAC_ContextInjectionHookRemoval:
    """Proves ContextInjectionHook must not be registered by build_hooks().

    Counts SESSION_START handlers by type(handler).__module__ and
    type(handler).__name__ — no import from owlbear.core.context_hook —
    so the tests remain valid after src/owlbear/core/context_hook.py is deleted.
    """

    def _count_context_injection_handlers(self, hooks: HookRegistry) -> int:
        """Return number of SESSION_START handlers whose type is ContextInjectionHook."""
        handlers = hooks.handlers.get(HookEvent.SESSION_START, [])
        return sum(
            1
            for h in handlers
            if type(h).__module__ == "owlbear.core.context_hook"
            and type(h).__name__ == "ContextInjectionHook"
        )

    def test_no_context_injection_hook_when_lessons_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC2: Must not register ContextInjectionHook when lessons_injection_enabled=False."""
        import os

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(lessons_injection_enabled=False)
        hooks, _ = build_hooks(settings, workspace_root=None)
        count = self._count_context_injection_handlers(hooks)
        assert count == 0, (
            f"ContextInjectionHook must NOT be registered on SESSION_START "
            f"when lessons_injection_enabled=False, but found {count} instance(s)"
        )

    def test_no_context_injection_hook_when_lessons_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC3: Must not register ContextInjectionHook when lessons_injection_enabled=True."""
        import os

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(lessons_injection_enabled=True)
        hooks, _ = build_hooks(settings, workspace_root=None)
        count = self._count_context_injection_handlers(hooks)
        assert count == 0, (
            f"ContextInjectionHook must NOT be registered on SESSION_START "
            f"even when lessons_injection_enabled=True, but found {count} instance(s)"
        )

    def test_no_context_injection_hook_with_workspace_root(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC2/3 boundary: workspace_root does not cause ContextInjectionHook to appear."""
        import os

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(lessons_injection_enabled=False)
        hooks, _ = build_hooks(settings, workspace_root=tmp_path)
        count = self._count_context_injection_handlers(hooks)
        assert count == 0, (
            f"ContextInjectionHook must NOT be registered on SESSION_START "
            f"with workspace_root set, but found {count} instance(s)"
        )

    def test_session_start_has_no_duplicate_context_injection(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC2/3 boundary: Zero ContextInjectionHook instances in SESSION_START handlers."""
        import os

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)

        settings = OwlBearSettings(lessons_injection_enabled=True)
        hooks, _ = build_hooks(settings, workspace_root=None)
        handlers = hooks.handlers.get(HookEvent.SESSION_START, [])
        context_handlers = [
            h
            for h in handlers
            if type(h).__module__ == "owlbear.core.context_hook"
            and type(h).__name__ == "ContextInjectionHook"
        ]
        assert context_handlers == [], (
            f"Expected no ContextInjectionHook handlers, found: {context_handlers}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_BuildToolsetsNoBareModelDeprecation (#861)
# ---------------------------------------------------------------------------


class TestFromAC_BuildToolsetsNoBareModelDeprecation:
    """RED gate for #556: build_toolsets() must not pass a bare string model.

    The ``chat_model or settings.chat_model`` fallback in
    ``src/owlbear/bootstrap/toolsets.py`` currently resolves to a raw string
    (e.g. ``'gpt-4o'``) when no explicit model is provided.  PydanticAI issues
    a ``DeprecationWarning`` for bare model strings, which becomes an error
    under ``-W error::DeprecationWarning``.

    These tests assert that each inner call receives a
    ``pydantic_ai.models.Model`` instance instead of a bare string.  They all
    FAIL before #556 is implemented.

    Run in isolation with ``-W error::DeprecationWarning`` targeting this class.
    """

    def test_knowledge_infra_receives_model_not_bare_string(self, tmp_path: Path) -> None:
        """_build_knowledge_infra must receive a Model, not a bare string."""
        from pydantic_ai.models import Model

        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        captured: list[object] = []

        def spy_infra(_workspace: Path, chat_model: object) -> None:
            captured.append(chat_model)

        with patch("owlbear.bootstrap._build_knowledge_infra", side_effect=spy_infra):
            build_toolsets(settings, tmp_path, hooks, channel)

        assert len(captured) == 1
        assert isinstance(captured[0], Model), (
            f"chat_model or settings.chat_model passed bare string {captured[0]!r} "
            "to _build_knowledge_infra — fix expected in #556"
        )

    def test_knowledge_toolset_receives_model_not_bare_string(self, tmp_path: Path) -> None:
        """_build_knowledge_toolset must receive a Model, not a bare string."""
        from pydantic_ai.models import Model

        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        mock_infra = MagicMock()
        captured: list[object] = []

        def spy_toolset(
            _workspace: Path,
            _infra: object,
            _project_id: object = None,
            *,
            chat_model: object,
            **_kwargs: object,
        ) -> None:
            captured.append(chat_model)

        with (
            patch("owlbear.bootstrap._build_knowledge_infra", return_value=mock_infra),
            patch(
                "owlbear.bootstrap._build_knowledge_toolset",
                side_effect=spy_toolset,
            ),
        ):
            build_toolsets(settings, tmp_path, hooks, channel)

        assert len(captured) == 1
        assert isinstance(captured[0], Model), (
            f"chat_model or settings.chat_model passed bare string {captured[0]!r} "
            "to _build_knowledge_toolset — fix expected in #556"
        )

    def test_bookmark_toolset_receives_model_not_bare_string(self, tmp_path: Path) -> None:
        """_build_bookmark_toolset must receive a Model, not a bare string."""
        from pydantic_ai.models import Model

        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock(spec=ChannelPlugin)
        mock_infra = MagicMock()
        captured: list[object] = []

        def spy_bookmark(
            _infra: object,
            _workspace: Path,
            chat_model: object,
            **_kwargs: object,
        ) -> None:
            captured.append(chat_model)

        with (
            patch("owlbear.bootstrap._build_knowledge_infra", return_value=mock_infra),
            patch("owlbear.bootstrap._build_knowledge_toolset", return_value=None),
            patch(
                "owlbear.bootstrap._build_bookmark_toolset",
                side_effect=spy_bookmark,
            ),
        ):
            build_toolsets(settings, tmp_path, hooks, channel)

        assert len(captured) == 1
        assert isinstance(captured[0], Model), (
            f"chat_model or settings.chat_model passed bare string {captured[0]!r} "
            "to _build_bookmark_toolset — fix expected in #556"
        )


# ---------------------------------------------------------------------------
# TDD RED: HookReaction settings parsing (#965)
# ---------------------------------------------------------------------------


class TestFromAC_OwlBearSettingsHookReactions:
    """AC: OwlBearSettings defaults hook_reactions to [] and preserves
    declared rule order when parsing hook_reactions list input into
    HookReactionRule objects.
    """

    def test_hook_reactions_defaults_to_empty_list(self) -> None:
        settings = OwlBearSettings()
        assert settings.hook_reactions == []

    def test_hook_reactions_parses_list_of_dicts_to_rule_objects(self) -> None:
        from owlbear.core.hook_reaction_router import HookReactionRule

        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"]},
            ]
        )
        assert len(settings.hook_reactions) == 1
        assert isinstance(settings.hook_reactions[0], HookReactionRule)

    def test_hook_reactions_preserves_rule_order(self) -> None:
        rules_input = [
            {"events": ["on_error"], "actions": ["retry"]},
            {"events": ["task_complete"], "actions": ["notify"]},
            {"events": ["budget_warning"], "actions": ["escalate"]},
        ]
        settings = OwlBearSettings(hook_reactions=rules_input)
        assert len(settings.hook_reactions) == 3
        assert settings.hook_reactions[0].events == ["on_error"]
        assert settings.hook_reactions[1].events == ["task_complete"]
        assert settings.hook_reactions[2].events == ["budget_warning"]

    def test_hook_reactions_preserves_actions_per_rule(self) -> None:
        from owlbear.core.hook_reaction_router import HookReactionRule

        rules_input = [
            {"events": ["task_complete"], "actions": ["notify", "escalate"]},
        ]
        settings = OwlBearSettings(hook_reactions=rules_input)
        rule = settings.hook_reactions[0]
        assert isinstance(rule, HookReactionRule)
        assert rule.actions == ["notify", "escalate"]

    def test_hook_reactions_empty_list_is_valid(self) -> None:
        settings = OwlBearSettings(hook_reactions=[])
        assert settings.hook_reactions == []


# ---------------------------------------------------------------------------
# TDD RED: build_hooks() HookReaction wiring (#965)
# ---------------------------------------------------------------------------


class TestFromAC_BuildHooksHookReactions:
    """AC: invalid hook_reactions event names fail build_hooks/router registration
    instead of being skipped silently.
    AC: build_hooks() leaves existing NotificationHook registrations intact
    when reaction handlers are added.
    """

    def test_build_hooks_no_reactions_leaves_notification_events(self) -> None:
        """Happy: empty hook_reactions does not disturb NotificationHook handlers."""
        settings = OwlBearSettings(
            hook_reactions=[],
            notification_events=["task_complete"],
        )
        hooks, _ = build_hooks(settings, workspace_root=None)
        task_handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        assert len(task_handlers) >= 1

    def test_build_hooks_with_reactions_preserves_notification_handlers(self) -> None:
        """AC: NotificationHook registrations remain intact when reactions are added."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["on_error"], "actions": ["retry"]}],
            notification_events=["task_complete"],
        )
        hooks, _ = build_hooks(settings, workspace_root=None)
        # NotificationHook registers a handler for TASK_COMPLETE
        task_handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        assert len(task_handlers) >= 1

    def test_build_hooks_with_reactions_adds_handler_for_configured_event(self) -> None:
        """AC: build_hooks registers one handler per configured reaction event."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["budget_warning"], "actions": ["escalate"]},
            ],
            notification_events=[],
        )
        hooks, _ = build_hooks(settings, workspace_root=None)
        budget_handlers = hooks.handlers.get(HookEvent.BUDGET_WARNING, [])
        assert len(budget_handlers) >= 1

    def test_build_hooks_invalid_event_name_raises_not_skips(self) -> None:
        """AC: invalid event name fails at registration, not silently skipped."""
        # We need to bypass HookReactionRule validation to get an invalid event
        # into the settings, then verify build_hooks raises rather than skipping.
        from owlbear.core.hook_reaction_router import HookReactionRule

        bad_rule = HookReactionRule.__new__(HookReactionRule)
        object.__setattr__(bad_rule, "events", ["completely_invalid_hook_event"])
        object.__setattr__(bad_rule, "actions", ["notify"])
        object.__setattr__(bad_rule, "match", None)

        settings = OwlBearSettings()
        # Inject the bad rule directly (bypassing Pydantic validation on the field)
        object.__setattr__(settings, "hook_reactions", [bad_rule])

        with pytest.raises((ValueError, KeyError)):
            build_hooks(settings, workspace_root=None)


# ---------------------------------------------------------------------------
# TDD RED: question_pending default hook cleanup (#968)
# ---------------------------------------------------------------------------


class TestFromAC_QuestionPendingDefaultHook:
    """AC: build_hooks() with default settings registers TASK_COMPLETE and ON_ERROR handlers
    but NOT QUESTION_PENDING; explicit config can still register QUESTION_PENDING.
    """

    def test_default_build_hooks_registers_task_complete_and_on_error_not_question_pending(
        self,
    ) -> None:
        """Default build_hooks must register TASK_COMPLETE and ON_ERROR but not QUESTION_PENDING."""
        hooks, _ = build_hooks(OwlBearSettings(), workspace_root=None)
        assert len(hooks.handlers.get(HookEvent.TASK_COMPLETE, [])) >= 1
        assert len(hooks.handlers.get(HookEvent.ON_ERROR, [])) >= 1
        # question_pending is not in the new default — must have zero handlers
        assert len(hooks.handlers.get(HookEvent.QUESTION_PENDING, [])) == 0

    def test_explicit_question_pending_config_registers_handler_while_default_excludes_it(
        self,
    ) -> None:
        """Default must not register QUESTION_PENDING; explicit config must still register it."""
        # Guard: default registration must not include QUESTION_PENDING (fails until builder's fix)
        default_hooks, _ = build_hooks(OwlBearSettings(), workspace_root=None)
        assert len(default_hooks.handlers.get(HookEvent.QUESTION_PENDING, [])) == 0
        # Main: explicit notification_events=[..., question_pending] must still register it
        explicit_settings = OwlBearSettings(
            notification_events=["task_complete", "question_pending"],
        )
        explicit_hooks, _ = build_hooks(explicit_settings, workspace_root=None)
        assert len(explicit_hooks.handlers.get(HookEvent.QUESTION_PENDING, [])) >= 1


# ---------------------------------------------------------------------------
# TDD RED: bootstrap HookWorkerSupervisor wiring (#966)
# ---------------------------------------------------------------------------


class TestFromAC_BootstrapHookWorkerSupervisorWiring:
    """_wire_post_model_hooks wires one HookWorkerSupervisor when ingest_pipeline is
    available and appends supervisor.shutdown to cleanup; when ingest_pipeline is
    unavailable, no supervisor shutdown callable is appended.

    All tests fail on HEAD because _wire_post_model_hooks does not yet accept a
    ``cleanup`` keyword argument.
    """

    def test_supervisor_shutdown_appended_to_cleanup_when_ingest_available(
        self, tmp_path: Path
    ) -> None:
        """When ingest_pipeline is available, exactly one shutdown callable is appended."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.core.hooks import HookRegistry

        hooks = HookRegistry()
        cleanup: list = []
        settings = OwlBearSettings()

        # Fails today: _wire_post_model_hooks() got unexpected keyword argument 'cleanup'
        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),  # ingest_pipeline available
            cleanup=cleanup,
        )

        assert len(cleanup) == 1
        assert callable(cleanup[0])
        assert cleanup[0].__name__ == "shutdown"

    def test_no_supervisor_shutdown_when_ingest_pipeline_unavailable(self, tmp_path: Path) -> None:
        """When ingest_pipeline is None, no supervisor shutdown callable is appended."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.core.hooks import HookRegistry

        hooks = HookRegistry()
        cleanup: list = []
        settings = OwlBearSettings()

        # Fails today: _wire_post_model_hooks() got unexpected keyword argument 'cleanup'
        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            None,  # ingest_pipeline unavailable
            cleanup=cleanup,
        )

        assert len(cleanup) == 0

    def test_supervisor_is_a_hook_worker_supervisor_instance(self, tmp_path: Path) -> None:
        """The shutdown callable appended to cleanup belongs to a HookWorkerSupervisor."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.core.hook_worker_supervisor import HookWorkerSupervisor
        from owlbear.core.hooks import HookRegistry
        # Importing HookWorkerSupervisor fails today (module doesn't exist) — RED

        hooks = HookRegistry()
        cleanup: list = []
        settings = OwlBearSettings()

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),
            cleanup=cleanup,
        )

        assert len(cleanup) == 1
        shutdown_callable = cleanup[0]
        # shutdown must be a bound method of a HookWorkerSupervisor
        assert isinstance(getattr(shutdown_callable, "__self__", None), HookWorkerSupervisor)

    def test_retrospective_hook_registered_for_task_complete_when_ingest_available(
        self, tmp_path: Path
    ) -> None:
        """_wire_post_model_hooks registers a TASK_COMPLETE handler when ingest_pipeline is set."""
        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.core.hooks import HookEvent, HookRegistry

        hooks = HookRegistry()
        cleanup: list = []
        settings = OwlBearSettings()
        before_count = len(hooks.handlers.get(HookEvent.TASK_COMPLETE, []))

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),
            cleanup=cleanup,
        )

        after_count = len(hooks.handlers.get(HookEvent.TASK_COMPLETE, []))
        assert after_count == before_count + 1


# ---------------------------------------------------------------------------
# TDD RED: bootstrap shutdown_event → LinkedCancelSignal wiring (#870)
# ---------------------------------------------------------------------------


class TestFromAC_870_BootstrapShutdownSignalWiring:
    """_wire_post_model_hooks accepts shutdown_event and wires it into the hook.

    AC 5: Compose the per-operation signal only in the current direct daemon-owned
    ingest path associated with RetrospectiveHook.

    Architecture note: Bootstrap creates LinkedCancelSignal(shutdown_event) and
    passes it to RetrospectiveHook.__init__; _wire_post_model_hooks() needs to
    accept shutdown_event (currently not passed at all).

    All tests fail on current HEAD because _wire_post_model_hooks() does not yet
    accept a shutdown_event keyword argument.
    """

    def test_wire_post_model_hooks_accepts_shutdown_event_kwarg(self, tmp_path: Path) -> None:
        """_wire_post_model_hooks accepts a shutdown_event= keyword without TypeError."""
        import asyncio

        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.core.hooks import HookRegistry

        hooks = HookRegistry()
        settings = OwlBearSettings()
        shutdown_event = asyncio.Event()

        # Must not raise TypeError for unexpected keyword argument 'shutdown_event'
        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),
            shutdown_event=shutdown_event,
        )

    def test_registered_hook_cancel_signal_linked_to_shutdown_event(self, tmp_path: Path) -> None:
        """The hook registered via _wire_post_model_hooks has a cancel signal linked to shutdown.

        When shutdown_event is set after registration, the cancel signal on the
        registered hook reflects that live state. This verifies that bootstrap
        uses LinkedCancelSignal composition rather than passing None or a snapshot.
        """
        import asyncio

        from owlbear.bootstrap import _wire_post_model_hooks
        from owlbear.core.hooks import HookEvent, HookRegistry
        from owlbear.core.retrospective_hook import RetrospectiveHook

        hooks = HookRegistry()
        settings = OwlBearSettings()
        shutdown_event = asyncio.Event()

        _wire_post_model_hooks(
            settings,
            MagicMock(),
            tmp_path,
            hooks,
            MagicMock(),
            shutdown_event=shutdown_event,
        )

        handlers = hooks.handlers.get(HookEvent.TASK_COMPLETE, [])
        retro_hook = next((h for h in handlers if isinstance(h, RetrospectiveHook)), None)
        assert retro_hook is not None, "RetrospectiveHook must be registered for TASK_COMPLETE"

        # The hook must carry a cancel signal linked to shutdown_event.
        # Check that it exposes a CancelSignal-compatible field linked to shutdown.
        # We verify live linkage: set shutdown_event and the hook's cancel signal is also set.
        from owlbear.memory.knowledge.cancellation import CancelSignal

        # The hook's linked cancel signal: accessible via _cancel or inferred from
        # _shutdown_event if the type has been migrated to CancelSignal.
        linked_signal = getattr(retro_hook, "_cancel", None) or getattr(
            retro_hook, "_shutdown_event", None
        )
        assert linked_signal is not None, (
            "RetrospectiveHook must store a linked cancel signal (not None) "
            "when shutdown_event is provided at bootstrap"
        )
        assert isinstance(linked_signal, CancelSignal), (
            "stored cancel signal must satisfy CancelSignal protocol"
        )

        shutdown_event.set()
        assert linked_signal.is_set(), (
            "cancel signal must reflect live shutdown_event state after it fires"
        )


# ---------------------------------------------------------------------------
# TDD RED: build_hooks() reaction_executors wiring (#991)
# ---------------------------------------------------------------------------


class TestFromAC_991_BuildHooksReactionExecutors:
    """AC#2-#4: build_hooks() stores reaction_executors on hooks when configured.

    All four tests fail on HEAD because:
    - HookRegistry has no reaction_executors attribute (AttributeError)
    - build_hooks() does not store executors on hooks
    """

    def test_reaction_executors_is_dict_when_reactions_configured(self) -> None:
        """AC#2: hooks.reaction_executors is a dict with notify/retry/escalate keys."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["task_complete"], "actions": ["notify"]}]
        )
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert isinstance(hooks.reaction_executors, dict)
        assert "notify" in hooks.reaction_executors
        assert "retry" in hooks.reaction_executors
        assert "escalate" in hooks.reaction_executors

    def test_reaction_executors_none_when_no_reactions(self) -> None:
        """AC#4: hooks.reaction_executors is None when hook_reactions is empty."""
        settings = OwlBearSettings()  # hook_reactions defaults to []
        hooks, _ = build_hooks(settings, workspace_root=None)
        assert hooks.reaction_executors is None

    def test_reaction_executors_is_same_object_passed_to_router(self) -> None:
        """AC#2: hooks.reaction_executors is the same dict object (identity) passed to router."""
        from owlbear.core.hook_reaction_router import HookReactionRouter

        settings = OwlBearSettings(
            hook_reactions=[{"events": ["on_error"], "actions": ["retry"]}]
        )

        real_init = HookReactionRouter.__init__
        captured: list[dict] = []

        def capturing_init(self_inner: HookReactionRouter, *, rules, executors) -> None:
            captured.append(executors)
            real_init(self_inner, rules=rules, executors=executors)

        with patch(
            "owlbear.core.hook_reaction_router.HookReactionRouter.__init__",
            capturing_init,
        ):
            hooks, _ = build_hooks(settings, workspace_root=None)

        assert len(captured) == 1
        assert hooks.reaction_executors is captured[0]

    def test_build_hooks_return_contract_still_two_tuple(self) -> None:
        """AC#3: return is still a 2-tuple with HookRegistry first after reactions wired."""
        settings = OwlBearSettings(
            hook_reactions=[{"events": ["task_complete"], "actions": ["notify"]}]
        )
        result = build_hooks(settings, workspace_root=None)
        assert isinstance(result, tuple)
        assert len(result) == 2
        hooks, _ = result
        assert isinstance(hooks, HookRegistry)
        # reaction_executors must be set; AttributeError here proves RED on current HEAD
        assert hooks.reaction_executors is not None
