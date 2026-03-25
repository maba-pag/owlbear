"""Tests for #987 — HookReaction notify and escalate executor wiring.

RED phase tests from AC lines in #987.  The functions _make_notify_executor
and _make_escalate_executor do not yet exist in owlbear.bootstrap.hooks;
this file will fail with ImportError on every test until #957 implements them.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These two imports do not exist until the builder implements #957.
# The ImportError propagates to every test in this module — all tests go RED.
from owlbear.bootstrap.hooks import (
    _make_escalate_executor,
    _make_notify_executor,
    build_hooks,
)
from owlbear.config import OwlBearSettings
from owlbear.core.hooks import HookEvent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings_with(actions: list[str]) -> OwlBearSettings:
    """Return OwlBearSettings with a single hook reaction rule for task_complete."""
    return OwlBearSettings(
        hook_reactions=[{"events": ["task_complete"], "actions": actions}],
    )


def _make_backend(*, returns: bool | Exception) -> MagicMock:
    """Return a mock NotificationBackend whose notify() returns or raises."""
    backend = MagicMock()
    if isinstance(returns, Exception):
        backend.notify = AsyncMock(side_effect=returns)
    else:
        backend.notify = AsyncMock(return_value=returns)
    backend.name = "mock-backend"
    return backend


# ---------------------------------------------------------------------------
# AC1 + AC4 — _make_notify_executor factory
# ---------------------------------------------------------------------------


class TestFromAC_987_NotifyExecutorFactory:
    """Contract tests for _make_notify_executor(backends) factory.

    AC1: Iterates backends in declared order, stops on first True success.
    AC4: Backend that raises is caught, warning logged, chain continues.
    """

    @pytest.mark.asyncio
    async def test_first_success_stops_chain(self) -> None:
        """AC1 happy: executor stops at the first backend that returns True."""
        backend_a = _make_backend(returns=True)
        backend_b = _make_backend(returns=True)

        executor = _make_notify_executor([backend_a, backend_b])
        await executor({"_hook_event": HookEvent.TASK_COMPLETE})

        backend_a.notify.assert_called_once()
        backend_b.notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_backends_tried_when_all_fail(self) -> None:
        """AC1 edge: all backends are called when every backend returns False."""
        backends = [_make_backend(returns=False) for _ in range(3)]

        executor = _make_notify_executor(backends)
        await executor({})

        for backend in backends:
            backend.notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_backend_call_order_preserved(self) -> None:
        """AC1 boundary: backends are called in the declared list order."""
        call_order: list[int] = []

        def _make_ordered(idx: int, *, success: bool) -> MagicMock:
            b = MagicMock()
            b.name = f"backend-{idx}"

            async def _notify(_msg: str, _evt: Any) -> bool:
                call_order.append(idx)
                return success

            b.notify = _notify
            return b

        backend_first = _make_ordered(0, success=False)
        backend_second = _make_ordered(1, success=True)
        executor = _make_notify_executor([backend_first, backend_second])
        await executor({})

        assert call_order == [0, 1]

    @pytest.mark.asyncio
    async def test_raising_backend_continues_chain(self) -> None:
        """AC4 happy: chain continues to next backend after one raises."""
        backend_bad = _make_backend(returns=RuntimeError("backend error"))
        backend_good = _make_backend(returns=True)

        executor = _make_notify_executor([backend_bad, backend_good])
        await executor({})

        backend_good.notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_does_not_propagate_to_caller(self) -> None:
        """AC4 error: exception from a backend must not propagate upstream."""
        backend = _make_backend(returns=ValueError("boom"))

        executor = _make_notify_executor([backend])
        # Must not raise — failure isolation is the contract
        await executor({})

    @pytest.mark.asyncio
    async def test_warning_logged_on_backend_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC4 edge: a warning-or-higher log record is emitted when a backend raises."""
        backend = _make_backend(returns=RuntimeError("fail"))

        executor = _make_notify_executor([backend])
        with caplog.at_level(logging.WARNING):
            await executor({})

        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings, "Expected at least one WARNING when a backend raises"

    @pytest.mark.asyncio
    async def test_backend_exception_warning_names_failing_backend(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC4 stronger: per-backend exception warning identifies the backend by name.

        This distinguishes the per-backend warning (which names the backend) from
        the generic all-backends-failed warning.  Removing the backend-specific
        warning path would leave no record referencing the backend name.
        """
        backend = _make_backend(returns=RuntimeError("fail"))
        backend.name = "test-backend-xyz"

        executor = _make_notify_executor([backend])
        with caplog.at_level(logging.WARNING):
            await executor({})

        named_warnings = [
            r
            for r in caplog.records
            if r.levelno >= logging.WARNING and "test-backend-xyz" in r.getMessage()
        ]
        all_warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert named_warnings, (
            "Backend-failure warning must identify the specific backend name "
            f"'test-backend-xyz'. Warnings found: {all_warnings}"
        )


# ---------------------------------------------------------------------------
# AC2 + AC5 — _make_escalate_executor factory
# ---------------------------------------------------------------------------


class TestFromAC_987_EscalateExecutorFactory:
    """Contract tests for _make_escalate_executor(channel) factory.

    AC2: Calls channel.send() exactly once with a message containing the event
         name and a payload summary.
    AC5: Exceptions from channel.send() propagate to the caller (no swallowing).
    """

    @pytest.mark.asyncio
    async def test_send_called_exactly_once(self) -> None:
        """AC2 happy: channel.send is called exactly once per executor invocation."""
        channel = AsyncMock()
        channel.send = AsyncMock()

        executor = _make_escalate_executor(channel)
        await executor({"_hook_event": HookEvent.TASK_COMPLETE})

        channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_contains_event_name(self) -> None:
        """AC2 happy: the escalation message contains the triggering event name."""
        channel = AsyncMock()

        executor = _make_escalate_executor(channel)
        await executor({"_hook_event": HookEvent.ON_ERROR})

        sent_message: str = channel.send.call_args[0][0]
        assert "on_error" in sent_message, (
            f"Escalation message must reference the event name. Got: {sent_message!r}"
        )

    @pytest.mark.asyncio
    async def test_message_contains_payload_summary(self) -> None:
        """AC2 edge: the escalation message contains something from the payload."""
        channel = AsyncMock()

        payload = {"_hook_event": HookEvent.ON_ERROR, "detail": "sentinel-xyz"}
        executor = _make_escalate_executor(channel)
        await executor(payload)

        sent_message: str = channel.send.call_args[0][0]
        # Either the key or the value must appear in the summary
        assert "sentinel-xyz" in sent_message or "detail" in sent_message, (
            f"Escalation message must include payload information. Got: {sent_message!r}"
        )

    @pytest.mark.asyncio
    async def test_send_exception_propagates(self) -> None:
        """AC5 error: exceptions from channel.send() must propagate (not be swallowed)."""
        channel = AsyncMock()
        channel.send = AsyncMock(side_effect=ConnectionError("channel down"))

        executor = _make_escalate_executor(channel)
        with pytest.raises(ConnectionError, match="channel down"):
            await executor({"_hook_event": HookEvent.TASK_COMPLETE})


# ---------------------------------------------------------------------------
# AC3 — build_hooks() noop fallback when channel is None
# ---------------------------------------------------------------------------


class TestFromAC_987_BuildHooksNoneChannelEscalate:
    """build_hooks() must log a warning and wire a noop escalate executor
    when channel=None and the escalate action is configured (AC3).
    """

    def test_warning_logged_when_channel_none_escalate_configured(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC3 error: build_hooks() emits a WARNING when channel=None + escalate rule."""
        settings = _settings_with(["escalate"])

        with caplog.at_level(logging.WARNING, logger="owlbear.bootstrap.hooks"):
            build_hooks(settings, channel=None)

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_records, "Expected a warning when escalate is configured but channel is None"

    def test_noop_escalate_executor_wired_when_channel_none(self) -> None:
        """AC3 boundary: the escalate executor passed to HookReactionRouter is a noop
        (qualname confirms it is not the real escalate factory) when channel=None.
        """
        settings = _settings_with(["escalate"])

        captured_executors: dict[str, Any] = {}

        with patch("owlbear.core.hook_reaction_router.HookReactionRouter") as mock_cls:
            mock_cls.return_value.register = MagicMock()
            build_hooks(settings, channel=None)

        captured_executors = mock_cls.call_args.kwargs["executors"]
        escalate_fn = captured_executors["escalate"]

        # Real escalate executor wraps a channel — noop must NOT have channel in closure
        # The simplest contract: the escalate executor's qualname signals it is noop
        assert "_noop" in getattr(escalate_fn, "__qualname__", ""), (
            "When channel=None, escalate executor must be the noop, "
            f"but got: {escalate_fn!r} ({getattr(escalate_fn, '__qualname__', 'unknown')})"
        )

    def test_no_warning_when_channel_none_but_no_escalate_action(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC3 negative: no escalation warning emitted when channel=None but the
        configured reaction only uses 'notify' (no 'escalate' action present).
        The warning must be scoped to the escalate action, not fired for any
        non-empty hook_reactions value.
        """
        settings = _settings_with(["notify"])  # escalate action NOT configured

        with caplog.at_level(logging.WARNING, logger="owlbear.bootstrap.hooks"):
            build_hooks(settings, channel=None)

        escalate_warnings = [
            r
            for r in caplog.records
            if r.levelno >= logging.WARNING and "escalat" in r.getMessage().lower()
        ]
        assert not escalate_warnings, (
            "No escalation warning expected when escalate action is not configured, "
            f"but got: {[r.getMessage() for r in escalate_warnings]}"
        )


# ---------------------------------------------------------------------------
# AC6 + AC7 — build_hooks() real executor wiring
# ---------------------------------------------------------------------------


class TestFromAC_987_BuildHooksExecutorWiring:
    """build_hooks() must wire real executors for notify and escalate (AC6) and
    keep retry as noop (AC7) when settings.hook_reactions is non-empty.
    """

    def test_notify_executor_is_real_not_noop(self) -> None:
        """AC6: notify executor must not be the _noop placeholder when reactions configured."""
        settings = _settings_with(["notify"])

        with patch("owlbear.core.hook_reaction_router.HookReactionRouter") as mock_cls:
            mock_cls.return_value.register = MagicMock()
            build_hooks(settings)

        executors: dict[str, Any] = mock_cls.call_args.kwargs["executors"]
        notify_fn = executors["notify"]

        assert "_noop" not in getattr(notify_fn, "__qualname__", ""), (
            "notify executor must use the real _make_notify_executor factory, "
            f"but got noop: {getattr(notify_fn, '__qualname__', 'unknown')}"
        )

    def test_escalate_executor_is_real_with_channel(self) -> None:
        """AC6: escalate executor must not be the _noop placeholder when channel is provided."""
        settings = _settings_with(["escalate"])
        channel = AsyncMock()

        with patch("owlbear.core.hook_reaction_router.HookReactionRouter") as mock_cls:
            mock_cls.return_value.register = MagicMock()
            build_hooks(settings, channel=channel)

        executors: dict[str, Any] = mock_cls.call_args.kwargs["executors"]
        escalate_fn = executors["escalate"]

        assert "_noop" not in getattr(escalate_fn, "__qualname__", ""), (
            "escalate executor must use the real _make_escalate_executor factory "
            "when a channel is provided, "
            f"got: {getattr(escalate_fn, '__qualname__', 'unknown')}"
        )

    def test_retry_executor_remains_noop(self) -> None:
        """AC7: retry executor must remain the noop even when hook_reactions is non-empty."""
        settings = _settings_with(["notify", "retry", "escalate"])
        channel = AsyncMock()

        with patch("owlbear.core.hook_reaction_router.HookReactionRouter") as mock_cls:
            mock_cls.return_value.register = MagicMock()
            build_hooks(settings, channel=channel)

        executors: dict[str, Any] = mock_cls.call_args.kwargs["executors"]
        retry_fn = executors["retry"]

        assert "_noop" in getattr(retry_fn, "__qualname__", ""), (
            "retry executor must remain the internal _noop placeholder "
            f"(no real retry executor should be wired), "
            f"got: {getattr(retry_fn, '__qualname__', 'unknown')}"
        )

    @pytest.mark.asyncio
    async def test_wired_notify_executor_invokes_backend(self) -> None:
        """AC6 behavioral: the wired notify executor from build_hooks() actually
        calls a notification backend, proving the assembly wires a working
        factory output and not a noop-equivalent callable.
        """
        settings = _settings_with(["notify"])
        mock_backend = _make_backend(returns=True)

        with (
            patch("owlbear.bootstrap.hooks.ConsoleBellBackend", return_value=mock_backend),
            patch("owlbear.bootstrap.hooks.WinSoundBackend", return_value=MagicMock()),
        ):
            hooks_obj, _ = build_hooks(settings)
            notify_executor = hooks_obj.reaction_executors["notify"]

        await notify_executor({"_hook_event": HookEvent.TASK_COMPLETE})

        mock_backend.notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_wired_escalate_executor_calls_channel(self) -> None:
        """AC6 behavioral: the wired escalate executor from build_hooks() actually
        calls channel.send(), proving the assembly wires a working factory output
        and not a noop-equivalent callable.
        """
        settings = _settings_with(["escalate"])
        mock_channel = AsyncMock()

        hooks_obj, _ = build_hooks(settings, channel=mock_channel)
        escalate_executor = hooks_obj.reaction_executors["escalate"]

        await escalate_executor({"_hook_event": HookEvent.TASK_COMPLETE})

        mock_channel.send.assert_called_once()
