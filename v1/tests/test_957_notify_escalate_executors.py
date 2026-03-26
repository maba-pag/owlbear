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


# ---------------------------------------------------------------------------
# Retry additions (reviewer FAIL 2026-03-25)
# AC1 strengthened: call args + all-false warning
# AC2 strengthened: channel.receive guard
# AC6: export boundary guard
# ---------------------------------------------------------------------------


class TestFromAC_957_NotifyCallArgContract:
    """AC1 retry: backend.notify() arg contract and all-false-backends warning.

    The prior test suite called assert_called_once() but did not verify the
    positional args passed to notify() or check the pool-level warning that
    fires when every backend returns False without raising.
    """

    @pytest.mark.asyncio
    async def test_notify_called_with_message_as_first_arg(self) -> None:
        """AC1: first positional arg to backend.notify() must be a str message."""
        backend = _make_backend(returns=True)
        executor = _make_notify_executor([backend])
        await executor({"_hook_event": HookEvent.TASK_COMPLETE})

        args = backend.notify.call_args.args
        assert isinstance(args[0], str), (
            f"First arg to notify() must be a str, got {type(args[0])!r}"
        )

    @pytest.mark.asyncio
    async def test_notify_called_with_event_as_second_arg(self) -> None:
        """AC1: second positional arg to backend.notify() must be the hook event."""
        backend = _make_backend(returns=True)
        executor = _make_notify_executor([backend])
        event = HookEvent.TASK_COMPLETE
        await executor({"_hook_event": event})

        args = backend.notify.call_args.args
        assert len(args) >= 2, "notify() must receive at least two positional args"
        assert args[1] == event, f"Second arg to notify() must be the event object, got {args[1]!r}"

    @pytest.mark.asyncio
    async def test_all_false_backends_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """AC1 edge: a WARNING is logged when every backend returns False (none raise).

        This is the pool-level all-backends-failed warning, distinct from the
        per-backend exception warning covered by
        TestFromAC_987_NotifyExecutorFactory.test_warning_logged_on_backend_failure.
        """
        backends = [_make_backend(returns=False), _make_backend(returns=False)]
        executor = _make_notify_executor(backends)

        with caplog.at_level(logging.WARNING):
            await executor({"_hook_event": HookEvent.TASK_COMPLETE})

        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warnings, (
            "Expected at least one WARNING when all backends return False without raising"
        )


class TestFromAC_957_EscalateReceiveGuard:
    """AC2 retry: channel.receive must NEVER be called by the escalate executor.

    The escalate executor is send-only (AC2). The prior test suite verified
    send was called but never asserted receive was not called.
    """

    @pytest.mark.asyncio
    async def test_channel_receive_never_called(self) -> None:
        """AC2: escalate executor must not invoke channel.receive()."""
        channel = AsyncMock()
        executor = _make_escalate_executor(channel)
        await executor({"_hook_event": HookEvent.TASK_COMPLETE})

        channel.receive.assert_not_called()

    @pytest.mark.asyncio
    async def test_channel_receive_never_called_with_extra_payload(self) -> None:
        """AC2 edge: receive guard holds even when payload contains extra keys."""
        channel = AsyncMock()
        executor = _make_escalate_executor(channel)
        await executor({"_hook_event": HookEvent.ON_ERROR, "task_id": "99", "reason": "timeout"})

        channel.send.assert_called_once()
        channel.receive.assert_not_called()


class TestFromAC_957_ExportBoundary:
    """AC6: private factory functions must not appear in any public namespace.

    The reviewer noted that no test guards the private/export boundary.
    These tests will catch any future refactor that accidentally re-exports
    _make_notify_executor or _make_escalate_executor via __init__.py.
    """

    def test_make_notify_executor_not_on_bootstrap_package(self) -> None:
        """AC6: _make_notify_executor must not be re-exported from owlbear.bootstrap."""
        import owlbear.bootstrap as _bootstrap

        assert not hasattr(_bootstrap, "_make_notify_executor"), (
            "_make_notify_executor must not be accessible via owlbear.bootstrap"
        )

    def test_make_escalate_executor_not_on_bootstrap_package(self) -> None:
        """AC6: _make_escalate_executor must not be re-exported from owlbear.bootstrap."""
        import owlbear.bootstrap as _bootstrap

        assert not hasattr(_bootstrap, "_make_escalate_executor"), (
            "_make_escalate_executor must not be accessible via owlbear.bootstrap"
        )

    def test_make_notify_executor_not_on_top_level_package(self) -> None:
        """AC6: _make_notify_executor must not be accessible from the owlbear package."""
        import owlbear

        assert not hasattr(owlbear, "_make_notify_executor"), (
            "_make_notify_executor must not be re-exported from the owlbear top-level package"
        )

    def test_make_escalate_executor_not_on_top_level_package(self) -> None:
        """AC6: _make_escalate_executor must not be accessible from the owlbear package."""
        import owlbear

        assert not hasattr(owlbear, "_make_escalate_executor"), (
            "_make_escalate_executor must not be re-exported from the owlbear top-level package"
        )


# ---------------------------------------------------------------------------
# Retry-2 additions (reviewer FAIL 2026-03-26)
# AC1: notify message content — verifies payload message is forwarded, not a constant
# AC4: exc_info on backend-failure warning — verifies traceback is attached
# ---------------------------------------------------------------------------


class TestFromAC_957_NotifyDetailedContract:
    """AC1 + AC4 retry-2: message content derivation and exc_info traceback guard.

    The prior retry added type and position checks (is str, is the event object)
    but did not guard:
      - AC1 line 43: that the message forwarded to notify() actually comes from
        data["message"] when present, or from the event-derived default when absent.
        A constant string would satisfy the prior test but violate this contract.
      - AC4 line 54: that the per-backend warning record has exc_info attached,
        i.e. traceback data is preserved. Removing exc_info=True from the logger
        call would keep the prior suite green.
    """

    @pytest.mark.asyncio
    async def test_notify_forwards_data_message_key_verbatim(self) -> None:
        """AC1 gap: when data contains 'message', notify() must receive that exact string.

        Replacing the payload-derived message with any constant at hooks.py line 43
        would cause this test to fail.
        """
        backend = _make_backend(returns=True)
        sentinel = "unique-sentinel-payload-message-f7a2c9"
        executor = _make_notify_executor([backend])
        await executor({"_hook_event": HookEvent.TASK_COMPLETE, "message": sentinel})

        args = backend.notify.call_args.args
        assert args[0] == sentinel, (
            f"notify() must forward data['message'] verbatim, got {args[0]!r}"
        )

    @pytest.mark.asyncio
    async def test_notify_default_message_references_event_name(self) -> None:
        """AC1 gap: when data has no 'message' key, notify() receives an event-derived default.

        A constant string that does not reference the event name would fail this test.
        HookEvent.TASK_COMPLETE.value == "task_complete", so the default message must
        contain "task_complete".
        """
        backend = _make_backend(returns=True)
        executor = _make_notify_executor([backend])
        await executor({"_hook_event": HookEvent.TASK_COMPLETE})

        args = backend.notify.call_args.args
        sent_message: str = args[0]
        # HookEvent.TASK_COMPLETE.value is "task_complete"
        assert "task_complete" in sent_message, (
            "Default notify message must contain the event label 'task_complete', "
            f"got {sent_message!r}"
        )

    @pytest.mark.asyncio
    async def test_backend_failure_warning_has_exc_info_attached(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC4 gap: the per-backend WARNING must carry traceback info (exc_info=True).

        Removing exc_info=True from the logger.warning() call at hooks.py line 54
        would result in exc_info=(None, None, None) on the log record, which fails
        this assertion.
        """
        backend = _make_backend(returns=RuntimeError("test-exc-abc"))
        executor = _make_notify_executor([backend])

        with caplog.at_level(logging.WARNING):
            await executor({"_hook_event": HookEvent.TASK_COMPLETE})

        # Look for a WARNING record with a real exception attached (exc_info not None/falsy)
        exc_info_warnings = [
            r
            for r in caplog.records
            if r.levelno >= logging.WARNING and r.exc_info is not None and r.exc_info[1] is not None
        ]
        assert exc_info_warnings, (
            "Per-backend WARNING must include traceback info (exc_info=True). "
            "Found records: "
            + str(
                [
                    (r.getMessage(), r.exc_info)
                    for r in caplog.records
                    if r.levelno >= logging.WARNING
                ]
            )
        )
