"""HookedToolset — WrapperToolset that emits hook events around tool calls.

Wraps any :class:`~pydantic_ai.toolsets.AbstractToolset` and emits
:attr:`HookEvent.PRE_TOOL_USE` / :attr:`HookEvent.POST_TOOL_USE` hooks
via a :class:`HookRegistry` before and after each tool invocation.

Guards (callables that may raise) are invoked **directly** — not through
:meth:`HookRegistry.emit` — so their exceptions propagate instead of being
swallowed.  This allows :class:`~owlbear.core.command_guard.CommandSafetyGuard`
to block dangerous commands before execution.

Usage::

    from owlbear.tools.hooked import HookedToolset

    hooked = HookedToolset(wrapped=some_toolset, hooks=registry)
    agent = Agent("model", toolsets=[hooked])
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic_ai.toolsets.wrapper import WrapperToolset

from owlbear.core.command_guard import BlockedCommandError
from owlbear.core.hooks import HookEvent, HookRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic_ai._run_context import RunContext
    from pydantic_ai.toolsets.abstract import ToolsetTool

__all__ = ["HookedToolset"]

logger = logging.getLogger(__name__)


@dataclass
class HookedToolset(WrapperToolset):  # type: ignore[type-arg]
    """WrapperToolset that emits PRE/POST_TOOL_USE hooks around tool calls.

    Args:
        wrapped: The inner toolset to delegate to.
        hooks: Registry used to emit lifecycle events.
        guards: Callables invoked directly before tool execution.  If a guard
            raises :class:`~owlbear.core.command_guard.BlockedCommandError`,
            the tool call is aborted and the error message is returned to the
            model.  Unlike hooks, guard exceptions are **not** swallowed.
    """

    hooks: HookRegistry = None  # type: ignore[assignment]
    guards: list[Callable[..., object]] = field(default_factory=list)

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, object],
        ctx: RunContext,  # type: ignore[type-arg]
        tool: ToolsetTool,  # type: ignore[type-arg]
    ) -> object:
        """Emit hooks and run guards before delegating to the wrapped toolset."""
        # 1. Emit observability hooks (swallowed by HookRegistry.emit)
        await self.hooks.emit(HookEvent.PRE_TOOL_USE, {"tool_name": name, "args": tool_args})

        # 2. Run guards directly — BlockedCommandError propagates
        payload: dict[str, object] = {"tool_name": name, "args": tool_args}
        for guard in self.guards:
            try:
                result = guard(payload)
                if asyncio.iscoroutine(result):
                    await result
            except BlockedCommandError as exc:
                logger.warning("Guard blocked tool %r: %s", name, exc)
                return f"BLOCKED: {exc}"

        # 3. Execute the wrapped tool
        result = await super().call_tool(name, tool_args, ctx, tool)
        await self.hooks.emit(HookEvent.POST_TOOL_USE, {"tool_name": name, "result": result})
        return result
