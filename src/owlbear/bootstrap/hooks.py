"""Bootstrap hook assembly."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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
    from owlbear.core.progress import ProgressReporter

logger = logging.getLogger(__name__)


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
        Fully-wired hook registry and optional progress reporter.
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

    NotificationHook(
        backends=[ConsoleBellBackend(), WinSoundBackend()],
        notification_events=settings.notification_events,
    ).register(hooks)

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
