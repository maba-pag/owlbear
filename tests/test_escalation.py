"""Tests for owlbear.core.escalation — EscalationHook (ON_ERROR → ask_user)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, PropertyMock

from owlbear.core.escalation import EscalationAction, EscalationHook
from owlbear.core.hooks import HookEvent, HookRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_channel(response: str = "retry") -> AsyncMock:
    """Create a mock ChannelPlugin."""
    channel = AsyncMock()
    type(channel).name = PropertyMock(return_value="test")
    channel.receive = AsyncMock(return_value=response)
    return channel


def _run(coro: object) -> Any:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    """EscalationHook does NOT auto-register; opt-in via register_on_error()."""

    def test_no_auto_registration_on_init(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel()
        EscalationHook(hooks=hooks, channel=channel)
        assert hooks.handlers.get(HookEvent.ON_ERROR, []) == []

    def test_register_on_error_adds_handler(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel()
        hook = EscalationHook(hooks=hooks, channel=channel)
        hook.register_on_error()
        assert hook._handler in hooks.handlers.get(HookEvent.ON_ERROR, [])

    def test_unregister_after_register_on_error(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel()
        hook = EscalationHook(hooks=hooks, channel=channel)
        hook.register_on_error()
        hook.unregister()
        assert hook._handler not in hooks.handlers.get(HookEvent.ON_ERROR, [])


# ---------------------------------------------------------------------------
# Escalation action enum
# ---------------------------------------------------------------------------


class TestEscalationAction:
    """EscalationAction has retry, skip, abort members."""

    def test_has_retry(self) -> None:
        assert EscalationAction.RETRY == "retry"

    def test_has_skip(self) -> None:
        assert EscalationAction.SKIP == "skip"

    def test_has_abort(self) -> None:
        assert EscalationAction.ABORT == "abort"

    def test_member_count(self) -> None:
        assert len(EscalationAction) == 3


# ---------------------------------------------------------------------------
# Escalation triggering
# ---------------------------------------------------------------------------


class TestEscalation:
    """When retries exhausted, escalate sends structured error to channel."""

    def test_escalate_sends_message_to_channel(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("retry")
        hook = EscalationHook(hooks=hooks, channel=channel)

        _run(
            hook.escalate(
                error=RuntimeError("connection refused"),
                tool_name="run_command",
                attempt=3,
            )
        )

        channel.send.assert_called_once()
        sent_msg = channel.send.call_args[0][0]
        assert "run_command" in sent_msg
        assert "connection refused" in sent_msg

    def test_escalate_includes_options(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("skip")
        hook = EscalationHook(hooks=hooks, channel=channel)

        _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="fetch",
                attempt=3,
            )
        )

        sent_msg = channel.send.call_args[0][0]
        assert "retry" in sent_msg.lower()
        assert "skip" in sent_msg.lower()
        assert "abort" in sent_msg.lower()

    def test_escalate_returns_retry(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("1")  # option 1 = retry
        hook = EscalationHook(hooks=hooks, channel=channel)

        result = _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=3,
            )
        )

        assert result is EscalationAction.RETRY

    def test_escalate_returns_skip(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("2")  # option 2 = skip
        hook = EscalationHook(hooks=hooks, channel=channel)

        result = _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=3,
            )
        )

        assert result is EscalationAction.SKIP

    def test_escalate_returns_abort(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("3")  # option 3 = abort
        hook = EscalationHook(hooks=hooks, channel=channel)

        result = _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=3,
            )
        )

        assert result is EscalationAction.ABORT

    def test_escalate_text_match_retry(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("retry")
        hook = EscalationHook(hooks=hooks, channel=channel)

        result = _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=3,
            )
        )

        assert result is EscalationAction.RETRY

    def test_escalate_text_match_skip(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("skip")
        hook = EscalationHook(hooks=hooks, channel=channel)

        result = _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=3,
            )
        )

        assert result is EscalationAction.SKIP

    def test_escalate_text_match_abort(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("abort")
        hook = EscalationHook(hooks=hooks, channel=channel)

        result = _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=3,
            )
        )

        assert result is EscalationAction.ABORT

    def test_escalate_includes_attempt_number(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("retry")
        hook = EscalationHook(hooks=hooks, channel=channel)

        _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=5,
            )
        )

        sent_msg = channel.send.call_args[0][0]
        assert "5" in sent_msg

    def test_escalate_defaults_to_abort_on_invalid_response(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("banana")
        hook = EscalationHook(hooks=hooks, channel=channel)

        result = _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=3,
            )
        )

        assert result is EscalationAction.ABORT

    def test_escalate_defaults_to_abort_on_none_response(self) -> None:
        hooks = HookRegistry()
        channel = AsyncMock()
        type(channel).name = PropertyMock(return_value="test")
        channel.receive = AsyncMock(return_value=None)
        hook = EscalationHook(hooks=hooks, channel=channel)

        result = _run(
            hook.escalate(
                error=RuntimeError("fail"),
                tool_name="t",
                attempt=3,
            )
        )

        assert result is EscalationAction.ABORT


# ---------------------------------------------------------------------------
# Hook integration — emit ON_ERROR triggers handler
# ---------------------------------------------------------------------------


class TestHookIntegration:
    """ON_ERROR emission triggers handler only after register_on_error()."""

    def test_on_error_hook_calls_escalate_after_opt_in(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("skip")
        hook = EscalationHook(hooks=hooks, channel=channel)
        hook.register_on_error()

        error_data = {
            "error": RuntimeError("timeout"),
            "tool_name": "fetch",
            "attempt": 3,
        }
        _run(hooks.emit(HookEvent.ON_ERROR, error_data))

        # Handler fires — channel.send should have been called
        channel.send.assert_called_once()

    def test_on_error_does_not_fire_without_opt_in(self) -> None:
        hooks = HookRegistry()
        channel = _make_channel("skip")
        EscalationHook(hooks=hooks, channel=channel)

        error_data = {
            "error": RuntimeError("timeout"),
            "tool_name": "fetch",
            "attempt": 3,
        }
        _run(hooks.emit(HookEvent.ON_ERROR, error_data))

        channel.send.assert_not_called()
