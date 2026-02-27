"""Lightweight hook registry for OwlBear agent lifecycle events.

Handlers (sync or async callables) are registered per event and invoked in
registration order.  A failing handler is logged and skipped — it never
prevents subsequent handlers from running.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from enum import StrEnum

logger = logging.getLogger(__name__)

Handler = Callable[[object], object]


class HookEvent(StrEnum):
    """Lifecycle events that hooks can observe."""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    ON_MESSAGE = "on_message"
    ON_ERROR = "on_error"
    SUBAGENT_COMPLETE = "subagent_complete"


class HookRegistry:
    """Register and emit lifecycle hooks.

    Usage::

        registry = HookRegistry()
        registry.register(HookEvent.ON_MESSAGE, my_handler)
        await registry.emit(HookEvent.ON_MESSAGE, {"text": "hello"})
    """

    def __init__(self) -> None:
        self._handlers: dict[HookEvent, list[Handler]] = {}

    # -- public API ----------------------------------------------------------

    @property
    def handlers(self) -> dict[HookEvent, list[Handler]]:
        """Snapshot of registered handlers (mutable ref for now)."""
        return self._handlers

    def register(self, event: HookEvent, handler: Handler) -> None:
        """Append *handler* to the list for *event*."""
        self._handlers.setdefault(event, []).append(handler)

    def unregister(self, event: HookEvent, handler: Handler) -> None:
        """Remove *handler* from *event*.  No-op if not found."""
        handlers = self._handlers.get(event)
        if handlers is None:
            return
        with contextlib.suppress(ValueError):
            handlers.remove(handler)

    def clear(self) -> None:
        """Remove all handlers for every event."""
        self._handlers.clear()

    async def emit(self, event: HookEvent, data: object) -> None:
        """Invoke every handler registered for *event*, in order.

        Sync handlers are called directly; async handlers are awaited.
        Exceptions are logged and swallowed so one bad handler cannot block
        the rest.
        """
        for handler in self._handlers.get(event, []):
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception(
                    "Hook handler %r failed for event %s",
                    handler,
                    event.value,
                )
