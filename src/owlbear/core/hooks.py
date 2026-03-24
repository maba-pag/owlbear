"""Lightweight hook registry for OwlBear agent lifecycle events.

Handlers (sync or async callables) are registered per event and invoked in
registration order.  A failing handler is logged and skipped — it never
prevents subsequent handlers from running.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from enum import StrEnum
from typing import Any, Callable, Literal, NotRequired, TypedDict, get_args, overload  # noqa: UP035

from owlbear.core.test_hook import (
    TestResult,  # noqa: TC001  # runtime import needed for get_type_hints
)

logger = logging.getLogger(__name__)

__all__ = [
    "BudgetWarningData",
    "DaemonStartupData",
    "Handler",
    "HookEvent",
    "HookRegistry",
    "OnErrorData",
    "OnMessageData",
    "PostToolUseData",
    "PreToolUseData",
    "QuestionPendingData",
    "SessionEndData",
    "SessionStartData",
    "SubagentCompleteData",
    "TaskCompleteData",
    "emit_pre_tool_use",
]

Handler = Callable[[dict[str, Any]], None]
# Python 3.12 flattens Callable.__args__; restore the canonical get_args()
# form (list-wrapped params) so runtime introspection is consistent.
Handler.__args__ = get_args(Handler)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TypedDict payloads for each HookEvent
# ---------------------------------------------------------------------------


class PreToolUseData(TypedDict):
    """Payload for :attr:`HookEvent.PRE_TOOL_USE`."""

    tool_name: str
    args: dict[str, Any]


class PostToolUseData(TypedDict):
    """Payload for :attr:`HookEvent.POST_TOOL_USE`.

    Accepts both *HookedToolset* shape (``tool_name`` + ``result``) and
    *ApprovalGateToolset* shape (``tool_name`` + ``event_type`` +
    ``approval_required`` + ``approval_decision``).
    """

    tool_name: str
    result: NotRequired[object]
    event_type: NotRequired[str]
    approval_required: NotRequired[bool]
    approval_decision: NotRequired[str]
    grant_ttl: NotRequired[int]
    grant_max_uses: NotRequired[int]


class OnMessageData(TypedDict):
    """Payload for :attr:`HookEvent.ON_MESSAGE`."""

    prompt: str


class OnErrorData(TypedDict):
    """Payload for :attr:`HookEvent.ON_ERROR`."""

    error: Exception
    prompt: str


class SessionStartData(TypedDict):
    """Payload for :attr:`HookEvent.SESSION_START`."""

    session_id: str
    workspace_root: NotRequired[str]
    context: NotRequired[dict[str, str]]


class SessionEndData(TypedDict):
    """Payload for :attr:`HookEvent.SESSION_END`."""

    session_id: str
    messages: NotRequired[list]
    test_results: NotRequired[list[TestResult]]


class BudgetWarningData(TypedDict):
    """Payload for :attr:`HookEvent.BUDGET_WARNING`."""

    cost_usd: float
    limit_usd: float
    pct: float


class SubagentCompleteData(TypedDict):
    """Payload for :attr:`HookEvent.SUBAGENT_COMPLETE`."""

    task_id: NotRequired[str]
    created_files: NotRequired[list[str]]
    test_files: NotRequired[list[str]]
    result: NotRequired[object]
    verification: NotRequired[dict]


class TaskCompleteData(TypedDict):
    """Payload for :attr:`HookEvent.TASK_COMPLETE`.

    Valid ``outcome`` values:
    - ``"success"``
    - ``"failure"``
    - ``"budget_exceeded"``
    """

    task_id: str
    outcome: str


# Functional TypedDict form preserves __required_keys__/__optional_keys__
# under postponed annotations on Python 3.12.
QuestionPendingData = TypedDict(  # noqa: UP013
    "QuestionPendingData",
    {
        "source": str,
        "question": str,
        "tool_name": NotRequired[str],
    },
)
QuestionPendingData.__doc__ = (
    "Payload for :attr:`HookEvent.QUESTION_PENDING`."  # class form not possible; see comment above
)


class DaemonStartupData(TypedDict):
    """Payload for :attr:`HookEvent.DAEMON_STARTUP`."""

    channel: str
    config_dir: str


class HookEvent(StrEnum):
    """Lifecycle events that hooks can observe."""

    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    ON_MESSAGE = "on_message"
    ON_ERROR = "on_error"
    SUBAGENT_COMPLETE = "subagent_complete"
    TASK_COMPLETE = "task_complete"
    QUESTION_PENDING = "question_pending"
    BUDGET_WARNING = "budget_warning"
    DAEMON_STARTUP = "daemon_startup"


class HookRegistry:
    """Register and emit lifecycle hooks.

    Usage::

        registry = HookRegistry()
        registry.register(HookEvent.ON_MESSAGE, my_handler)
        await registry.emit(HookEvent.ON_MESSAGE, {"text": "hello"})

    Attributes:
        reaction_executors: Executor dict set by ``build_hooks()`` when
            ``hook_reactions`` is configured; ``None`` by default.  The daemon
            wiring layer replaces noop entries with real executors at startup
            (see task #992).
    """

    def __init__(self) -> None:
        self._handlers: dict[HookEvent, list[Handler]] = {}
        self.reaction_executors: dict[str, Any] | None = None

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

    @overload
    async def emit(
        self,
        event: Literal[HookEvent.PRE_TOOL_USE],
        data: PreToolUseData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.POST_TOOL_USE],
        data: PostToolUseData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.ON_MESSAGE],
        data: OnMessageData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.ON_ERROR],
        data: OnErrorData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.SESSION_START],
        data: SessionStartData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.SESSION_END],
        data: SessionEndData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.SUBAGENT_COMPLETE],
        data: SubagentCompleteData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.TASK_COMPLETE],
        data: TaskCompleteData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.QUESTION_PENDING],
        data: QuestionPendingData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: Literal[HookEvent.DAEMON_STARTUP],
        data: DaemonStartupData,
    ) -> None: ...
    @overload
    async def emit(
        self,
        event: HookEvent,
        data: dict[str, Any],
    ) -> None: ...

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


async def emit_pre_tool_use(
    hooks: HookRegistry | None,
    tool_name: str,
    args: dict[str, object],
) -> None:
    """Emit :attr:`HookEvent.PRE_TOOL_USE` if *hooks* is not ``None``."""
    if hooks is not None:
        await hooks.emit(HookEvent.PRE_TOOL_USE, {"tool_name": tool_name, "args": args})


# Resolve PEP 563 stringified annotations so inspect.signature() returns
# real types at runtime (needed by hook-consumer introspection tests).
emit_pre_tool_use.__annotations__ = {
    "hooks": HookRegistry | None,
    "tool_name": str,
    "args": dict[str, object],
    "return": None,
}
