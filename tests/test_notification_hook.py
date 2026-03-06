"""Tests for NotificationHook and NotificationBackend protocol.

Covers: protocol structure, backend priority dispatch, event filtering,
error isolation, graceful degradation, and individual backend behavior.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.notification_hook import (
    ConsoleBellBackend,
    NotificationBackend,
    NotificationHook,
    WinSoundBackend,
)


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _mock_backend(name: str, *, success: bool = True) -> MagicMock:
    """Create a mock NotificationBackend."""
    b = MagicMock()
    b.name = name
    b.notify = AsyncMock(return_value=success)
    return b


# ---------------------------------------------------------------------------
# NotificationBackend Protocol
# ---------------------------------------------------------------------------


class TestNotificationBackendProtocol:
    """NotificationBackend protocol defines the expected interface."""

    def test_conforming_class_satisfies_protocol(self) -> None:
        """A class with name property + async notify satisfies the protocol."""

        class _Good:
            @property
            def name(self) -> str:
                return "good"

            async def notify(self, message: str, event: HookEvent) -> bool:  # noqa: ARG002
                return True

        assert isinstance(_Good(), NotificationBackend)

    def test_missing_notify_rejects_protocol(self) -> None:
        """A class without notify does not satisfy NotificationBackend."""

        class _Bad:
            @property
            def name(self) -> str:
                return "bad"

        assert not isinstance(_Bad(), NotificationBackend)


# ---------------------------------------------------------------------------
# NotificationHook dispatch
# ---------------------------------------------------------------------------


class TestNotificationHookDispatch:
    """NotificationHook.__call__ dispatches to backends correctly."""

    def test_dispatches_in_priority_order(self) -> None:
        """Backends are tried in the order they appear in the list."""
        order: list[str] = []

        b1, b2 = MagicMock(), MagicMock()
        b1.name, b2.name = "first", "second"

        async def _b1(_msg: str, _ev: HookEvent) -> bool:
            order.append("first")
            return False

        async def _b2(_msg: str, _ev: HookEvent) -> bool:
            order.append("second")
            return False

        b1.notify, b2.notify = _b1, _b2

        hook = NotificationHook(backends=[b1, b2], notification_events=["task_complete"])
        _run(hook({"_hook_event": HookEvent.TASK_COMPLETE, "message": "done"}))
        assert order == ["first", "second"]

    def test_stops_at_first_successful_backend(self) -> None:
        """When a backend returns True, remaining backends are skipped."""
        b1 = _mock_backend("first", success=True)
        b2 = _mock_backend("second", success=True)

        hook = NotificationHook(backends=[b1, b2], notification_events=["task_complete"])
        _run(hook({"_hook_event": HookEvent.TASK_COMPLETE, "message": "done"}))

        b1.notify.assert_called_once()
        b2.notify.assert_not_called()

    def test_skips_events_not_in_notification_events(self) -> None:
        """Events outside the configured list are silently ignored."""
        b1 = _mock_backend("b1")

        hook = NotificationHook(backends=[b1], notification_events=["task_complete"])
        _run(hook({"_hook_event": HookEvent.SESSION_START}))

        b1.notify.assert_not_called()

    def test_backend_failure_falls_through_to_next(self) -> None:
        """An exception in one backend falls through to the next."""
        b1 = _mock_backend("first")
        b1.notify = AsyncMock(side_effect=RuntimeError("boom"))
        b2 = _mock_backend("second", success=True)

        hook = NotificationHook(backends=[b1, b2], notification_events=["task_complete"])
        _run(hook({"_hook_event": HookEvent.TASK_COMPLETE, "message": "done"}))

        b2.notify.assert_called_once()

    def test_all_backends_fail_logs_warning_no_exception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When every backend fails, a warning is logged but no exception."""
        b1 = _mock_backend("b1", success=False)
        b2 = _mock_backend("b2", success=False)

        hook = NotificationHook(backends=[b1, b2], notification_events=["task_complete"])
        with caplog.at_level(logging.WARNING):
            _run(hook({"_hook_event": HookEvent.TASK_COMPLETE, "message": "done"}))

        assert any(
            "all notification backends failed" in rec.message.lower() for rec in caplog.records
        )


# ---------------------------------------------------------------------------
# NotificationHook.register
# ---------------------------------------------------------------------------


class TestNotificationHookRegister:
    """NotificationHook.register() hooks into the event system."""

    def test_registers_on_all_configured_events(self) -> None:
        """register() adds a handler for each event in notification_events."""
        hook = NotificationHook(
            backends=[_mock_backend("b1")],
            notification_events=["task_complete", "question_pending"],
        )
        registry = HookRegistry()
        hook.register(registry)

        assert HookEvent.TASK_COMPLETE in registry.handlers
        assert HookEvent.QUESTION_PENDING in registry.handlers
        assert len(registry.handlers[HookEvent.TASK_COMPLETE]) == 1
        assert len(registry.handlers[HookEvent.QUESTION_PENDING]) == 1

    def test_register_skips_unknown_events(self, caplog: pytest.LogCaptureFixture) -> None:
        """Unknown event names in notification_events are logged and skipped."""
        hook = NotificationHook(
            backends=[_mock_backend("b1")],
            notification_events=["task_complete", "no_such_event"],
        )
        registry = HookRegistry()
        with caplog.at_level(logging.WARNING):
            hook.register(registry)

        assert HookEvent.TASK_COMPLETE in registry.handlers
        assert any("no_such_event" in rec.message for rec in caplog.records)

    def test_registered_handler_dispatches_via_emit(self) -> None:
        """A handler created by register() dispatches through the hook."""
        b1 = _mock_backend("b1", success=True)
        hook = NotificationHook(backends=[b1], notification_events=["task_complete"])
        registry = HookRegistry()
        hook.register(registry)

        _run(registry.emit(HookEvent.TASK_COMPLETE, {"message": "done"}))
        b1.notify.assert_called_once()


# ---------------------------------------------------------------------------
# ConsoleBellBackend
# ---------------------------------------------------------------------------


class TestConsoleBellBackend:
    """ConsoleBellBackend writes \\a to stdout."""

    def test_writes_bell_to_stdout(self) -> None:
        """Bell backend writes the bell character and flushes stdout."""
        backend = ConsoleBellBackend()
        with patch("owlbear.core.notification_hook.sys") as mock_sys:
            result = _run(backend.notify("hello", HookEvent.TASK_COMPLETE))

        mock_sys.stdout.write.assert_called_once_with("\a")
        mock_sys.stdout.flush.assert_called_once()
        assert result is True

    def test_name_is_bell(self) -> None:
        """ConsoleBellBackend.name returns 'bell'."""
        assert ConsoleBellBackend().name == "bell"


# ---------------------------------------------------------------------------
# WinSoundBackend
# ---------------------------------------------------------------------------


class TestWinSoundBackend:
    """WinSoundBackend calls winsound.MessageBeep."""

    def test_calls_messagebeep(self) -> None:
        """Sound backend invokes winsound.MessageBeep (mocked)."""
        mock_winsound = MagicMock()
        with patch.dict("sys.modules", {"winsound": mock_winsound}):
            backend = WinSoundBackend()
            result = _run(backend.notify("hello", HookEvent.TASK_COMPLETE))

        mock_winsound.MessageBeep.assert_called_once_with(
            mock_winsound.MB_ICONINFORMATION,
        )
        assert result is True

    def test_name_is_sound(self) -> None:
        """WinSoundBackend.name returns 'sound'."""
        assert WinSoundBackend().name == "sound"

    def test_returns_false_when_winsound_unavailable(self) -> None:
        """On non-Windows (no winsound), notify returns False."""
        import sys as _sys

        original = _sys.modules.get("winsound")
        _sys.modules["winsound"] = None  # type: ignore[assignment]
        try:
            backend = WinSoundBackend()
            result = _run(backend.notify("hello", HookEvent.TASK_COMPLETE))
        finally:
            if original is not None:
                _sys.modules["winsound"] = original
            else:
                _sys.modules.pop("winsound", None)
        assert result is False

    def test_returns_false_on_messagebeep_failure(self) -> None:
        """When MessageBeep raises, notify returns False."""
        mock_winsound = MagicMock()
        mock_winsound.MessageBeep.side_effect = RuntimeError("speaker off")
        with patch.dict("sys.modules", {"winsound": mock_winsound}):
            backend = WinSoundBackend()
            result = _run(backend.notify("hello", HookEvent.TASK_COMPLETE))
        assert result is False
