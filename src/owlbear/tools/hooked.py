"""HookedToolset — WrapperToolset that emits hook events around tool calls.

Wraps any :class:`~pydantic_ai.toolsets.AbstractToolset` and emits
:attr:`HookEvent.PRE_TOOL_USE` / :attr:`HookEvent.POST_TOOL_USE` hooks
via a :class:`HookRegistry` before and after each tool invocation.

Usage::

    from owlbear.tools.hooked import HookedToolset

    hooked = HookedToolset(wrapped=some_toolset, hooks=registry)
    agent = Agent("model", toolsets=[hooked])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.toolsets.wrapper import WrapperToolset

from owlbear.core.hooks import HookEvent, HookRegistry

if TYPE_CHECKING:
    from pydantic_ai._run_context import RunContext
    from pydantic_ai.toolsets.abstract import ToolsetTool

__all__ = ["HookedToolset"]


@dataclass
class HookedToolset(WrapperToolset):  # type: ignore[type-arg]
    """WrapperToolset that emits PRE/POST_TOOL_USE hooks around tool calls.

    Args:
        wrapped: The inner toolset to delegate to.
        hooks: Registry used to emit lifecycle events.
    """

    hooks: HookRegistry = None  # type: ignore[assignment]

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, object],
        ctx: RunContext,  # type: ignore[type-arg]
        tool: ToolsetTool,  # type: ignore[type-arg]
    ) -> object:
        """Emit hooks before and after delegating to the wrapped toolset."""
        await self.hooks.emit(HookEvent.PRE_TOOL_USE, {"tool_name": name, "args": tool_args})
        result = await super().call_tool(name, tool_args, ctx, tool)
        await self.hooks.emit(HookEvent.POST_TOOL_USE, {"tool_name": name, "result": result})
        return result
