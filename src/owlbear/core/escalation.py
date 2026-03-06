"""Human escalation via channel prompt.

:class:`EscalationHook` sends a structured error summary to the user through a
:class:`~owlbear.channels.base.ChannelPlugin` and asks them to choose: **retry**,
**skip**, or **abort**.

The hook does **not** auto-register on ON_ERROR.  Call
:meth:`~EscalationHook.register_on_error` explicitly if you want hook-driven
escalation.  In the default OwlBear daemon, error recovery is owned by
``_recover_from_error`` — this class is kept as a public API for programmatic use.

Usage::

    hook = EscalationHook(hooks=registry, channel=channel)
    # Explicit opt-in if you want hook-driven firing:
    hook.register_on_error()
    # ... or call escalate() directly:
    action = await hook.escalate(error=exc, tool_name="fetch", attempt=3)
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import TYPE_CHECKING

from owlbear.core.errors import error_to_user_message
from owlbear.core.hooks import HookEvent

if TYPE_CHECKING:
    from owlbear.channels.base import ChannelPlugin
    from owlbear.core.hooks import HookRegistry

__all__ = ["EscalationAction", "EscalationHook"]

logger = logging.getLogger(__name__)

_OPTIONS = ["retry", "skip", "abort"]


class EscalationAction(StrEnum):
    """User-chosen action after an escalation prompt."""

    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


class EscalationHook:
    """Escalates errors to the user via a channel prompt.

    Does **not** auto-register on ON_ERROR.  Call :meth:`register_on_error`
    to opt in to hook-driven escalation.

    Args:
        hooks: The :class:`HookRegistry` for optional registration.
        channel: Channel adapter used to communicate with the user.
    """

    def __init__(self, *, hooks: HookRegistry, channel: ChannelPlugin) -> None:
        self._hooks = hooks
        self._channel = channel
        self._handler = self._on_error

    # -- public API ----------------------------------------------------------

    def register_on_error(self) -> None:
        """Opt-in: register the handler on ON_ERROR."""
        self._hooks.register(HookEvent.ON_ERROR, self._handler)

    def unregister(self) -> None:
        """Remove the ON_ERROR handler from the hook registry."""
        self._hooks.unregister(HookEvent.ON_ERROR, self._handler)

    async def escalate(
        self,
        *,
        error: Exception,
        tool_name: str,
        attempt: int,
    ) -> EscalationAction:
        """Send a structured error prompt and return the user's choice.

        Returns :attr:`EscalationAction.ABORT` when the response is
        unrecognisable or the channel returns ``None``.
        """
        message = (
            f"Error in tool '{tool_name}' after {attempt} attempt(s):\n"
            f"  {error_to_user_message(error)}\n\n"
            "How would you like to proceed?\n"
            "[1] retry\n"
            "[2] skip\n"
            "[3] abort\n"
            "Choose [1-3]:"
        )
        await self._channel.send(message)
        raw = await self._channel.receive()
        return self._parse_response(raw)

    # -- internals -----------------------------------------------------------

    async def _on_error(self, data: object) -> None:
        """Hook handler invoked on ON_ERROR events."""
        if not isinstance(data, dict):
            return
        error = data.get("error")
        if not isinstance(error, Exception):
            return
        tool_name = str(data.get("tool_name", "unknown"))
        attempt = int(data.get("attempt", 0))
        await self.escalate(error=error, tool_name=tool_name, attempt=attempt)

    @staticmethod
    def _parse_response(raw: str | None) -> EscalationAction:
        """Map raw user input to an :class:`EscalationAction`."""
        if raw is None:
            return EscalationAction.ABORT
        text = raw.strip().lower()
        # Index match
        idx_map = {
            "1": EscalationAction.RETRY,
            "2": EscalationAction.SKIP,
            "3": EscalationAction.ABORT,
        }
        if text in idx_map:
            return idx_map[text]
        # Text match
        try:
            return EscalationAction(text)
        except ValueError:
            return EscalationAction.ABORT
