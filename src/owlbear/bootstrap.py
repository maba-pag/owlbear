"""Bootstrap — procedural assembly of all OwlBear components.

Wires hooks, toolsets, channels, MCP servers, agent registry, and the main
:class:`OwlBearAgent` into a :class:`BootstrapResult`.  Each ``build_*``
helper is independently testable.

Usage::

    from owlbear.bootstrap import bootstrap
    result = await bootstrap(settings, workspace_root=Path("."))
    agent = result.agent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from owlbear.channels.cli import CLIChannel
from owlbear.core.agent import OwlBearAgent
from owlbear.core.agent_registry import AgentRegistry
from owlbear.core.command_guard import CommandSafetyGuard
from owlbear.core.context_hook import ContextInjectionHook
from owlbear.core.delegation import DelegationToolset
from owlbear.core.hooks import HookRegistry
from owlbear.core.lint_hook import AutoLintHook
from owlbear.core.notification_hook import ConsoleBellBackend, NotificationHook, WinSoundBackend
from owlbear.core.observability import EventStore, ObservabilityHook
from owlbear.core.subagent_hook import SubagentVerificationHook
from owlbear.core.test_hook import TestVerificationHook
from owlbear.memory.context import ContextManager
from owlbear.memory.session import SessionStore
from owlbear.memory.usage import UsageTracker
from owlbear.providers.copilot import create_copilot_model
from owlbear.tools.ask_user import AskUserToolset
from owlbear.tools.browser.config import BrowserConfig
from owlbear.tools.browser.toolset import BrowserToolset
from owlbear.tools.filesystem import FileToolset
from owlbear.tools.git_local import GitLocalToolset
from owlbear.tools.github_api import GitHubToolset
from owlbear.tools.hooked import HookedToolset
from owlbear.tools.mcp_registry import MCPServerRegistry
from owlbear.tools.mcp_servers import register_default_servers
from owlbear.tools.terminal import TerminalToolset

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pydantic_ai.toolsets.abstract import AbstractToolset

    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import OwlBearSettings
    from owlbear.skills.registry import SkillRegistry

__all__ = [
    "BootstrapResult",
    "bootstrap",
    "build_agent_registry",
    "build_hooks",
    "build_mcp_registry",
    "build_toolsets",
    "create_channel",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------


@dataclass
class BootstrapResult:
    """Everything produced by :func:`bootstrap`."""

    agent: OwlBearAgent
    channel: ChannelPlugin
    mcp_registry: MCPServerRegistry | None
    hooks: HookRegistry
    cleanup: list[Callable] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hook assembly
# ---------------------------------------------------------------------------


def build_hooks(settings: OwlBearSettings, *, workspace_root: Path | None = None) -> HookRegistry:
    """Create a :class:`HookRegistry` with all standard hooks registered.

    Args:
        settings: Application settings (notification events, etc.).
        workspace_root: Workspace path for observability event storage.

    Returns:
        Fully-wired :class:`HookRegistry`.
    """
    hooks = HookRegistry()

    CommandSafetyGuard().register(hooks)
    AutoLintHook().register(hooks)
    SubagentVerificationHook().register(hooks)
    TestVerificationHook().register(hooks)
    ContextInjectionHook().register(hooks)

    NotificationHook(
        backends=[ConsoleBellBackend(), WinSoundBackend()],
        notification_events=settings.notification_events,
    ).register(hooks)

    if workspace_root is not None:
        event_path = workspace_root / ".owlbear" / "events.jsonl"
        ObservabilityHook(store=EventStore(event_path)).register(hooks)

    return hooks


# ---------------------------------------------------------------------------
# Channel factory
# ---------------------------------------------------------------------------


def create_channel(settings: OwlBearSettings, channel_name: str) -> ChannelPlugin:
    """Dispatch to the correct channel adapter.

    Args:
        settings: Application settings (Slack tokens, etc.).
        channel_name: One of ``"cli"``, ``"slack"``, ``"voice"``.

    Returns:
        A :class:`ChannelPlugin` instance.

    Raises:
        ValueError: If *channel_name* is not recognized.
    """
    if channel_name == "cli":
        return CLIChannel()

    if channel_name == "slack":
        from owlbear.channels.slack import SlackChannel  # noqa: PLC0415

        has_all_slack = (
            settings.slack_app_token and settings.slack_bot_token and settings.slack_channel_id
        )
        if not has_all_slack:
            msg = "Slack channel requires slack_app_token, slack_bot_token, and slack_channel_id"
            raise ValueError(msg)
        return SlackChannel(
            app_token=settings.slack_app_token.get_secret_value(),
            bot_token=settings.slack_bot_token.get_secret_value(),
            channel_id=settings.slack_channel_id,
        )

    if channel_name == "voice":
        from owlbear.channels.voice import VoiceChannel  # noqa: PLC0415

        return VoiceChannel()

    msg = f"Unknown channel: {channel_name!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Toolset assembly
# ---------------------------------------------------------------------------


def build_toolsets(
    settings: OwlBearSettings,
    workspace: Path,
    hooks: HookRegistry,
    channel: ChannelPlugin,
) -> list[AbstractToolset]:
    """Build all toolsets, wrapping non-delegation ones in :class:`HookedToolset`.

    Args:
        settings: Application settings.
        workspace: Workspace root directory.
        hooks: Hook registry for HookedToolset wrapping.
        channel: Channel adapter for AskUserToolset.

    Returns:
        List of toolsets ready for the agent.
    """
    raw: list[AbstractToolset] = []

    raw.append(FileToolset(workspace_root=workspace))
    raw.append(TerminalToolset(workspace_root=workspace, hooks=hooks))
    raw.append(AskUserToolset(channel))
    raw.append(GitLocalToolset(workspace_root=workspace, hooks=hooks))
    raw.append(BrowserToolset(config=BrowserConfig()))

    # Conditional toolsets
    skills_dir = workspace / ".github" / "skills"
    if skills_dir.is_dir():
        try:
            from owlbear.skills.registry import SkillRegistry  # noqa: PLC0415

            raw.append(SkillRegistry(skills_dir))
        except Exception:  # noqa: BLE001
            logger.warning("Failed to create SkillRegistry", exc_info=True)

    if settings.github_token:
        try:
            raw.append(
                GitHubToolset(
                    token=settings.github_token,
                    owner=settings.github_owner,
                    repo=settings.github_repo,
                    hooks=hooks,
                )
            )
        except Exception:  # noqa: BLE001
            logger.warning("Failed to create GitHubToolset", exc_info=True)

    # Wrap non-delegation toolsets in HookedToolset
    wrapped: list[AbstractToolset] = [HookedToolset(wrapped=ts, hooks=hooks) for ts in raw]

    # DelegationToolset is NOT wrapped — it's internal dispatch
    wrapped.append(DelegationToolset())

    return wrapped


# ---------------------------------------------------------------------------
# MCP registry
# ---------------------------------------------------------------------------


def build_mcp_registry(settings: OwlBearSettings) -> MCPServerRegistry | None:
    """Build the MCP server registry, or ``None`` if no servers configured.

    Args:
        settings: Application settings with ``mcp_servers`` and ``github_token``.

    Returns:
        :class:`MCPServerRegistry` or ``None``.
    """
    if not settings.mcp_servers:
        return None

    registry = MCPServerRegistry()
    try:
        register_default_servers(registry, settings)
    except Exception:  # noqa: BLE001
        logger.warning("Failed to register MCP default servers", exc_info=True)
    return registry


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------


def build_agent_registry(
    settings: OwlBearSettings,
    toolsets: list[AbstractToolset],
    mcp_registry: MCPServerRegistry | None,
    skill_registry: SkillRegistry | None = None,
) -> AgentRegistry:
    """Build and scan the :class:`AgentRegistry`.

    Args:
        settings: Application settings with ``agents_dir``.
        toolsets: Full toolset list for building the tool resolver.
        mcp_registry: Optional MCP registry for ``mcp:`` prefixed tools.
        skill_registry: Optional :class:`SkillRegistry` instance.

    Returns:
        Scanned :class:`AgentRegistry`.
    """
    # Build a name → toolset resolver from the toolsets list
    tool_map: dict[str, AbstractToolset] = {}
    for ts in toolsets:
        inner = ts.wrapped if isinstance(ts, HookedToolset) else ts
        name = type(inner).__name__
        tool_map[name] = ts

    def _resolve(name: str) -> AbstractToolset:
        if name in tool_map:
            return tool_map[name]
        msg = f"Unknown tool: {name!r}"
        raise KeyError(msg)

    registry = AgentRegistry(
        agents_dir=settings.agents_dir,
        tool_resolver=_resolve,
        skill_registry=skill_registry,
        mcp_registry=mcp_registry,
    )
    registry.scan()
    return registry


# ---------------------------------------------------------------------------
# Main bootstrap
# ---------------------------------------------------------------------------


async def bootstrap(
    settings: OwlBearSettings,
    *,
    channel_name: str = "cli",
    workspace_root: Path | None = None,
) -> BootstrapResult:
    """Wire all OwlBear components and return a :class:`BootstrapResult`.

    Args:
        settings: Application settings.
        channel_name: Channel adapter name (``"cli"``, ``"slack"``, ``"voice"``).
        workspace_root: Workspace root directory. Uses CWD when ``None``.

    Returns:
        :class:`BootstrapResult` with all assembled components.
    """
    from pathlib import Path as _Path  # noqa: PLC0415

    workspace = workspace_root or _Path.cwd()
    cleanup: list[Callable] = []

    # 1. Hooks
    hooks = build_hooks(settings, workspace_root=workspace_root)

    # 2. Channel
    channel = create_channel(settings, channel_name)

    # 3. Toolsets
    toolsets = build_toolsets(settings, workspace, hooks, channel)

    # 4. MCP
    mcp_registry = build_mcp_registry(settings)

    # 5. Agent registry
    # Find SkillRegistry if present
    skill_reg = None
    for ts in toolsets:
        inner = ts.wrapped if isinstance(ts, HookedToolset) else ts
        if type(inner).__name__ == "SkillRegistry":
            skill_reg = inner
            break

    agent_registry = build_agent_registry(settings, toolsets, mcp_registry, skill_reg)

    # 6. Model
    model = await create_copilot_model(settings)

    # 7. Session, context, tracker
    owlbear_dir = workspace / ".owlbear"
    session = SessionStore(owlbear_dir / "session.jsonl")
    context = ContextManager(workspace)
    tracker = UsageTracker(settings.usage_path)

    # 8. Construct agent
    agent = OwlBearAgent(
        model=model,
        session=session,
        context=context,
        hooks=hooks,
        channel=channel,
        tracker=tracker,
        provider=settings.provider,
        toolsets=toolsets,
    )
    agent._deps.agent_registry = agent_registry  # noqa: SLF001

    return BootstrapResult(
        agent=agent,
        channel=channel,
        mcp_registry=mcp_registry,
        hooks=hooks,
        cleanup=cleanup,
    )
