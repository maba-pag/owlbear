"""Notification hook — alert user via sound/bell when lifecycle events occur.

Provides :class:`NotificationHook` — a hook that dispatches user-facing
notifications through a priority-ordered chain of backends.  Backends are
tried in order; the first successful one stops the chain.  All errors are
logged and swallowed.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

try:
    from slack_sdk.web.async_client import AsyncWebClient
except ImportError:  # pragma: no cover
    AsyncWebClient = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear.core.hooks import HookEvent, HookRegistry

logger = logging.getLogger(__name__)


@runtime_checkable
class NotificationBackend(Protocol):
    """A notification channel that can alert the user.

    Implementations must provide a :pyattr:`name` property and an async
    :meth:`notify` method that returns ``True`` on success.
    """

    @property
    def name(self) -> str: ...

    async def notify(self, message: str, event: HookEvent) -> bool: ...


class ConsoleBellBackend:
    r"""Writes the terminal bell character (``\a``) to stdout."""

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "bell"

    async def notify(self, message: str, event: HookEvent) -> bool:  # noqa: ARG002
        r"""Write ``\a`` to stdout and flush."""
        sys.stdout.write("\a")
        sys.stdout.flush()
        return True


class WinSoundBackend:
    """Plays a Windows system sound via :func:`winsound.MessageBeep`."""

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "sound"

    async def notify(self, message: str, event: HookEvent) -> bool:  # noqa: ARG002
        """Call :func:`winsound.MessageBeep`.  Returns ``False`` on non-Windows."""
        try:
            import winsound  # noqa: PLC0415
        except ImportError:
            return False
        try:
            winsound.MessageBeep(winsound.MB_ICONINFORMATION)
        except Exception:  # noqa: BLE001
            logger.warning("winsound.MessageBeep failed", exc_info=True)
            return False
        return True


class SlackNotificationBackend:
    """Sends lifecycle notifications to Slack via ``chat_postMessage``."""

    def __init__(self, bot_token: str | None, channel_id: str | None) -> None:
        self._bot_token = bot_token
        self._channel_id = channel_id

    @property
    def name(self) -> str:
        """Backend identifier."""
        return "slack"

    async def notify(self, message: str, event: HookEvent | None) -> bool:
        """Post a formatted notification message to the configured Slack channel."""
        if self._bot_token is None or self._channel_id is None:
            return False
        if AsyncWebClient is None:
            return False

        event_label = event.value if event is not None else "notification"

        try:
            client = AsyncWebClient(token=self._bot_token)
            await client.chat_postMessage(
                channel=self._channel_id,
                text=f"*{event_label}*: {message}",
            )
        except Exception:  # noqa: BLE001
            logger.warning("Slack chat_postMessage failed", exc_info=True)
            return False
        return True


class NotificationHook:
    """Hook that dispatches notifications to backends on configured events.

    Backends are tried in priority order.  The first backend returning
    ``True`` stops the chain.  Failures are logged and skipped — hook
    errors never propagate.

    Args:
        backends: Ordered list of notification backends to try.
        notification_events: Event value strings (e.g. ``"task_complete"``)
            that trigger notifications.
    """

    def __init__(
        self,
        backends: list[NotificationBackend],
        notification_events: list[str],
    ) -> None:
        self._backends = backends
        self._notification_events = notification_events

    async def __call__(self, data: dict[str, Any]) -> None:
        """Dispatch a notification through the backend chain."""
        event: HookEvent | None = data.get("_hook_event")

        if event is not None and event.value not in self._notification_events:
            return

        event_label = event.value if event is not None else "notification"
        message = data.get("message", f"OwlBear: {event_label}")

        for backend in self._backends:
            try:
                if await backend.notify(message, event):
                    return
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Notification backend %r failed for %s",
                    backend.name,
                    event_label,
                )

        logger.warning("All notification backends failed for event %s", event_label)

    def register(self, hooks: HookRegistry) -> None:
        """Register this hook on all events in *notification_events*."""
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        for event_name in self._notification_events:
            try:
                event = HookEvent(event_name)
            except ValueError:
                logger.warning("Unknown notification event %r, skipping", event_name)
                continue
            hooks.register(event, self._make_handler(event))

    def _make_handler(self, event: HookEvent) -> Callable:
        """Create a single-arg handler closure that injects event into data."""

        async def _handler(data: dict[str, Any]) -> None:
            merged = {"_hook_event": event, **data}
            await self(merged)

        return _handler
