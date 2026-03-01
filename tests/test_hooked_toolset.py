"""Tests for HookedToolset — WrapperToolset that emits hook events around tool calls.

Covers: PRE_TOOL_USE emission with tool_name and args, POST_TOOL_USE emission
with tool_name and result, hook exception isolation, preservation of
wrapped toolset behavior, and guard-based command blocking.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from owlbear.core.command_guard import CommandSafetyGuard
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


# ---------------------------------------------------------------------------
# Guard-based command blocking (#343)
# ---------------------------------------------------------------------------


class TestGuardBlocksDangerousCommands:
    """HookedToolset with guards blocks dangerous commands before tool execution."""

    def test_guard_blocks_dangerous_command_returns_error_string(self) -> None:
        """When CommandSafetyGuard raises BlockedCommandError, call_tool returns error string."""
        hooks = HookRegistry()
        guard = CommandSafetyGuard()
        hooked, mock_ts = _make_hooked(hooks=hooks)
        hooked.guards = [guard]
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(
            hooked.call_tool(
                "run_command",
                {"command": "rm -rf /"},
                ctx,
                tool,
            )
        )

        # Should return an error string, not the tool result
        assert isinstance(result, str)
        assert "BLOCKED" in result or "blocked" in result.lower()
        # Tool should NOT have been called
        mock_ts.call_tool.assert_not_called()

    def test_guard_allows_safe_command(self) -> None:
        """Safe commands pass through guards and execute normally."""
        hooks = HookRegistry()
        guard = CommandSafetyGuard()
        hooked, mock_ts = _make_hooked(return_value="echo output", hooks=hooks)
        hooked.guards = [guard]
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(
            hooked.call_tool(
                "run_command",
                {"command": "echo hello"},
                ctx,
                tool,
            )
        )

        assert result == "echo output"
        mock_ts.call_tool.assert_called_once()

    def test_guard_blocks_file_write_to_env(self) -> None:
        """Guard blocks .env file writes and returns error string."""
        hooks = HookRegistry()
        guard = CommandSafetyGuard()
        hooked, mock_ts = _make_hooked(hooks=hooks)
        hooked.guards = [guard]
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(
            hooked.call_tool(
                "create_file",
                {"path": ".env"},
                ctx,
                tool,
            )
        )

        assert isinstance(result, str)
        assert "BLOCKED" in result or "blocked" in result.lower()
        mock_ts.call_tool.assert_not_called()

    def test_no_guards_default(self) -> None:
        """HookedToolset without guards behaves as before."""
        hooked, mock_ts = _make_hooked(return_value="ok")
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(hooked.call_tool("run_command", {"command": "rm -rf /"}, ctx, tool))

        # Without guards, dangerous commands go through (hooks swallow the error)
        assert result == "ok"
        mock_ts.call_tool.assert_called_once()


class TestGuardObservabilityHooksStillSwallow:
    """Other hooks (observability, notification) still swallow their exceptions."""

    def test_observability_hook_exception_swallowed_with_guard(self) -> None:
        """A failing observability hook does not block execution with guards."""
        hooks = HookRegistry()

        def bad_observer(_data: object) -> None:
            msg = "observability boom"
            raise RuntimeError(msg)

        hooks.register(HookEvent.PRE_TOOL_USE, bad_observer)

        guard = CommandSafetyGuard()
        hooked, mock_ts = _make_hooked(return_value="success", hooks=hooks)
        hooked.guards = [guard]
        ctx = MagicMock()
        tool = MagicMock()

        # Safe command — observability hook raises but gets swallowed by emit()
        result = _run(
            hooked.call_tool("run_command", {"command": "echo hello"}, ctx, tool)
        )

        assert result == "success"
        mock_ts.call_tool.assert_called_once()

    def test_guard_blocks_even_when_observability_hook_present(self) -> None:
        """Guard still blocks dangerous commands even with other hooks registered."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        guard = CommandSafetyGuard()
        hooked, mock_ts = _make_hooked(hooks=hooks)
        hooked.guards = [guard]
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(
            hooked.call_tool("run_command", {"command": "rm -rf /"}, ctx, tool)
        )

        assert isinstance(result, str)
        assert "BLOCKED" in result or "blocked" in result.lower()
        mock_ts.call_tool.assert_not_called()
        # Observability hook still ran via emit (before guard check)
        assert len(captured) == 1


class TestGuardWithAsyncCallable:
    """Guards work with async callables (CommandSafetyGuard.__call__ is async)."""

    def test_async_guard_blocks_command(self) -> None:
        """An async guard callable that raises BlockedCommandError blocks the tool."""
        guard = CommandSafetyGuard()

        hooks = HookRegistry()
        hooked, mock_ts = _make_hooked(hooks=hooks)
        hooked.guards = [guard]
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(
            hooked.call_tool("run_command", {"command": "rm -rf /"}, ctx, tool)
        )

        assert isinstance(result, str)
        assert "BLOCKED" in result or "blocked" in result.lower()
        mock_ts.call_tool.assert_not_called()
