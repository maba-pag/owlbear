"""Bootstrap hook assembly."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from owlbear.core.command_guard import CommandSafetyGuard
from owlbear.core.hooks import HookRegistry
from owlbear.core.lint_hook import AutoLintHook
from owlbear.core.notification_hook import ConsoleBellBackend, NotificationHook, WinSoundBackend
from owlbear.core.observability import EventStore, ObservabilityHook
from owlbear.core.subagent_hook import SubagentVerificationHook
from owlbear.core.test_hook import TestVerificationHook
from owlbear.tools.browser.safety import URLSafetyGuard

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import OwlBearSettings
    from owlbear.core.hook_reaction_router import Executor
    from owlbear.core.notification_hook import NotificationBackend
    from owlbear.core.progress import ProgressReporter

logger = logging.getLogger(__name__)


def _event_label(value: object) -> str:
    """Return a stable event label for reaction messages."""
    if value is None:
        return "notification"
    raw_value = getattr(value, "value", value)
    return str(raw_value)


def _make_notify_executor(backends: list[NotificationBackend]) -> Executor:
    """Build a backend-chain notify executor for hook reactions."""

    async def _executor(data: dict[str, Any]) -> None:
        event = data.get("_hook_event")
        event_name = _event_label(event)
        message = data.get("message", f"OwlBear: {event_name}")

        for backend in backends:
            try:
                if await backend.notify(str(message), event):
                    return
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Notification backend %r failed for %s",
                    backend.name,
                    event_name,
                    exc_info=True,
                )

        logger.warning("All notification backends failed for event %s", event_name)

    return _executor


def _make_escalate_executor(channel: ChannelPlugin) -> Executor:
    """Build a channel-send escalation executor for hook reactions."""

    async def _executor(data: dict[str, Any]) -> None:
        event_name = _event_label(data.get("_hook_event"))
        payload = {key: value for key, value in data.items() if key != "_hook_event"}
        await channel.send(f"Escalation [{event_name}] payload={payload!r}")

    return _executor


def build_hooks(
    settings: OwlBearSettings,
    *,
    workspace_root: Path | None = None,
    channel: ChannelPlugin | None = None,
) -> tuple[HookRegistry, ProgressReporter | None]:
    """Create a :class:`HookRegistry` with all standard hooks registered.

    Returns:
    -------
    tuple[HookRegistry, ProgressReporter | None]
        Fully-wired hook registry and optional progress reporter.  When
        ``settings.hook_reactions`` is non-empty, ``build_hooks()`` wires
        the real notify executor (``_make_notify_executor``) directly into
        ``reaction_executors["notify"]`` and, when *channel* is provided,
        the real escalate executor (``_make_escalate_executor``) into
        ``reaction_executors["escalate"]``; the retry slot stays noop.
        When the escalate action is configured but *channel* is ``None``,
        a warning is logged and the escalate slot falls back to noop.
    """
    hooks = HookRegistry()

    CommandSafetyGuard().register(hooks)
    URLSafetyGuard(config=settings.browser).register(hooks)
    AutoLintHook().register(hooks)
    SubagentVerificationHook().register(hooks)
    TestVerificationHook().register(hooks)

    if settings.lessons_injection_enabled:
        from owlbear.core.lessons_hook import LessonsInjectionHook  # noqa: PLC0415

        LessonsInjectionHook().register(hooks)

    notification_backends = [ConsoleBellBackend(), WinSoundBackend()]
    NotificationHook(
        backends=notification_backends,
        notification_events=settings.notification_events,
    ).register(hooks)

    if settings.hook_reactions:
        from owlbear.core.hook_reaction_router import HookReactionRouter  # noqa: PLC0415

        async def _noop(_data: object) -> None: ...

        executors = {
            "notify": _make_notify_executor(notification_backends),
            "retry": _noop,
            "escalate": _noop,
        }
        escalate_configured = any(
            "escalate" in getattr(rule, "actions", []) for rule in settings.hook_reactions
        )
        if channel is not None:
            executors["escalate"] = _make_escalate_executor(channel)
        elif escalate_configured:
            logger.warning(
                "Escalate hook reaction configured but no channel provided; using noop executor"
            )

        HookReactionRouter(
            rules=settings.hook_reactions,
            executors=executors,
        ).register(hooks)
        hooks.reaction_executors = executors

    if workspace_root is not None:
        event_path = workspace_root / ".owlbear" / "events.jsonl"
        ObservabilityHook(store=EventStore(event_path)).register(hooks)

    # Progress reporting — requires a channel and settings.progress_enabled
    progress_reporter: ProgressReporter | None = None
    if settings.progress_enabled and channel is not None:
        from owlbear.core.progress import ProgressReporter  # noqa: PLC0415

        progress_reporter = ProgressReporter(
            channel=channel,
            interval=settings.progress_interval,
            detail=settings.progress_detail,
        )
        progress_reporter.register(hooks)

    return hooks, progress_reporter
