"""Tests for HookedToolset — WrapperToolset that emits hook events around tool calls.

Covers: PRE_TOOL_USE emission with tool_name and args, POST_TOOL_USE emission
with tool_name and result, hook exception isolation, and preservation of
wrapped toolset behavior.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.tools.hooked import HookedToolset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_mock_toolset(return_value: object = "mock_result") -> MagicMock:
    """Create a mock AbstractToolset with an async call_tool."""
    mock_ts = MagicMock()
    mock_ts.call_tool = AsyncMock(return_value=return_value)
    return mock_ts


def _make_hooked(
    return_value: object = "mock_result",
    hooks: HookRegistry | None = None,
) -> tuple[HookedToolset, MagicMock]:
    """Create a HookedToolset wrapping a mock toolset."""
    if hooks is None:
        hooks = HookRegistry()
    mock_ts = _make_mock_toolset(return_value)
    hooked = HookedToolset(wrapped=mock_ts, hooks=hooks)
    return hooked, mock_ts


# ---------------------------------------------------------------------------
# PRE_TOOL_USE hook
# ---------------------------------------------------------------------------


class TestPreToolUseHook:
    """PRE_TOOL_USE hook fires before tool execution with correct data."""

    def test_pre_hook_fires_with_tool_name_and_args(self) -> None:
        """PRE_TOOL_USE receives {'tool_name': name, 'args': tool_args}."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        hooked, _ = _make_hooked(hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        _run(hooked.call_tool("greet", {"name": "World"}, ctx, tool))

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "greet"
        assert captured[0]["args"] == {"name": "World"}

    def test_pre_hook_fires_before_execution(self) -> None:
        """PRE_TOOL_USE fires before the wrapped call_tool runs."""
        hooks = HookRegistry()
        order: list[str] = []
        hooks.register(HookEvent.PRE_TOOL_USE, lambda _: order.append("pre"))

        mock_ts = MagicMock()

        async def tracking_call(*_args: object, **_kwargs: object) -> str:
            order.append("tool")
            return "result"

        mock_ts.call_tool = tracking_call

        hooked = HookedToolset(wrapped=mock_ts, hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        _run(hooked.call_tool("double", {"x": 5}, ctx, tool))
        assert order == ["pre", "tool"]


# ---------------------------------------------------------------------------
# POST_TOOL_USE hook
# ---------------------------------------------------------------------------


class TestPostToolUseHook:
    """POST_TOOL_USE hook fires after tool execution with correct data."""

    def test_post_hook_fires_with_tool_name_and_result(self) -> None:
        """POST_TOOL_USE receives {'tool_name': name, 'result': result}."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register(HookEvent.POST_TOOL_USE, captured.append)

        hooked, _ = _make_hooked(return_value="Hello!", hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(hooked.call_tool("greet", {"name": "World"}, ctx, tool))

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "greet"
        assert captured[0]["result"] == "Hello!"
        assert result == "Hello!"

    def test_post_hook_fires_after_execution(self) -> None:
        """POST_TOOL_USE fires after the wrapped call_tool runs."""
        hooks = HookRegistry()
        order: list[str] = []
        hooks.register(HookEvent.POST_TOOL_USE, lambda _: order.append("post"))

        mock_ts = MagicMock()

        async def tracking_call(*_args: object, **_kwargs: object) -> str:
            order.append("tool")
            return "result"

        mock_ts.call_tool = tracking_call

        hooked = HookedToolset(wrapped=mock_ts, hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        _run(hooked.call_tool("double", {"x": 5}, ctx, tool))
        assert order == ["tool", "post"]


# ---------------------------------------------------------------------------
# Hook exception isolation
# ---------------------------------------------------------------------------


class TestHookExceptionIsolation:
    """Exceptions in hooks do not prevent tool execution."""

    def test_failing_pre_hook_does_not_block_tool(self) -> None:
        """A raising PRE_TOOL_USE handler still allows the tool to run."""
        hooks = HookRegistry()

        def bad_pre_handler(_data: object) -> None:
            msg = "boom"
            raise RuntimeError(msg)

        hooks.register(HookEvent.PRE_TOOL_USE, bad_pre_handler)

        hooked, mock_ts = _make_hooked(return_value="Hello, Test!", hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        # Should not raise
        result = _run(hooked.call_tool("greet", {"name": "Test"}, ctx, tool))
        assert result == "Hello, Test!"
        mock_ts.call_tool.assert_called_once()

    def test_failing_post_hook_does_not_swallow_result(self) -> None:
        """A raising POST_TOOL_USE handler still returns the tool result."""
        hooks = HookRegistry()

        def bad_handler(_data: object) -> None:
            msg = "post boom"
            raise ValueError(msg)

        hooks.register(HookEvent.POST_TOOL_USE, bad_handler)

        hooked, _ = _make_hooked(return_value="Hello, Safe!", hooks=hooks)
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(hooked.call_tool("greet", {"name": "Safe"}, ctx, tool))
        assert result == "Hello, Safe!"


# ---------------------------------------------------------------------------
# Wrapped toolset behavior preservation
# ---------------------------------------------------------------------------


class TestWrappedBehaviorPreservation:
    """HookedToolset preserves the behavior of the wrapped toolset."""

    def test_tool_returns_correct_result(self) -> None:
        """Wrapped toolset tool still returns the expected value."""
        hooked, _ = _make_hooked(return_value="Hello, Alice!")
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(hooked.call_tool("greet", {"name": "Alice"}, ctx, tool))
        assert result == "Hello, Alice!"

    def test_call_tool_delegates_to_wrapped(self) -> None:
        """call_tool passes name, args, ctx, and tool to the wrapped toolset."""
        hooked, mock_ts = _make_hooked()
        ctx = MagicMock()
        tool = MagicMock()

        _run(hooked.call_tool("greet", {"name": "Bob"}, ctx, tool))

        mock_ts.call_tool.assert_called_once_with("greet", {"name": "Bob"}, ctx, tool)

    def test_is_wrapper_toolset(self) -> None:
        """HookedToolset is a WrapperToolset subclass."""
        from pydantic_ai.toolsets.wrapper import WrapperToolset

        hooked, _ = _make_hooked()
        assert isinstance(hooked, WrapperToolset)
