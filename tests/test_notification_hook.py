"""Tests for NotificationHook and NotificationBackend protocol.

Covers: protocol structure, backend priority dispatch, event filtering,
error isolation, graceful degradation, and individual backend behavior.
"""

from __future__ import annotations

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

    @pytest.mark.asyncio
    async def test_dispatches_in_priority_order(self) -> None:
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
        await hook({"_hook_event": HookEvent.TASK_COMPLETE, "message": "done"})
        assert order == ["first", "second"]

    @pytest.mark.asyncio
    async def test_stops_at_first_successful_backend(self) -> None:
        """When a backend returns True, remaining backends are skipped."""
        b1 = _mock_backend("first", success=True)
        b2 = _mock_backend("second", success=True)

        hook = NotificationHook(backends=[b1, b2], notification_events=["task_complete"])
        await hook({"_hook_event": HookEvent.TASK_COMPLETE, "message": "done"})

        b1.notify.assert_called_once()
        b2.notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_events_not_in_notification_events(self) -> None:
        """Events outside the configured list are silently ignored."""
        b1 = _mock_backend("b1")

        hook = NotificationHook(backends=[b1], notification_events=["task_complete"])
        await hook({"_hook_event": HookEvent.SESSION_START})

        b1.notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_backend_failure_falls_through_to_next(self) -> None:
        """An exception in one backend falls through to the next."""
        b1 = _mock_backend("first")
        b1.notify = AsyncMock(side_effect=RuntimeError("boom"))
        b2 = _mock_backend("second", success=True)

        hook = NotificationHook(backends=[b1, b2], notification_events=["task_complete"])
        await hook({"_hook_event": HookEvent.TASK_COMPLETE, "message": "done"})

        b2.notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_backends_fail_logs_warning_no_exception(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When every backend fails, a warning is logged but no exception."""
        b1 = _mock_backend("b1", success=False)
        b2 = _mock_backend("b2", success=False)

        hook = NotificationHook(backends=[b1, b2], notification_events=["task_complete"])
        with caplog.at_level(logging.WARNING):
            await hook({"_hook_event": HookEvent.TASK_COMPLETE, "message": "done"})

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

    @pytest.mark.asyncio
    async def test_registered_handler_dispatches_via_emit(self) -> None:
        """A handler created by register() dispatches through the hook."""
        b1 = _mock_backend("b1", success=True)
        hook = NotificationHook(backends=[b1], notification_events=["task_complete"])
        registry = HookRegistry()
        hook.register(registry)

        await registry.emit(HookEvent.TASK_COMPLETE, {"message": "done"})
        b1.notify.assert_called_once()


# ---------------------------------------------------------------------------
# ConsoleBellBackend
# ---------------------------------------------------------------------------


class TestConsoleBellBackend:
    """ConsoleBellBackend writes \\a to stdout."""

    @pytest.mark.asyncio
    async def test_writes_bell_to_stdout(self) -> None:
        """Bell backend writes the bell character and flushes stdout."""
        backend = ConsoleBellBackend()
        with patch("owlbear.core.notification_hook.sys") as mock_sys:
            result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

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

    @pytest.mark.asyncio
    async def test_calls_messagebeep(self) -> None:
        """Sound backend invokes winsound.MessageBeep (mocked)."""
        mock_winsound = MagicMock()
        with patch.dict("sys.modules", {"winsound": mock_winsound}):
            backend = WinSoundBackend()
            result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        mock_winsound.MessageBeep.assert_called_once_with(
            mock_winsound.MB_ICONINFORMATION,
        )
        assert result is True

    def test_name_is_sound(self) -> None:
        """WinSoundBackend.name returns 'sound'."""
        assert WinSoundBackend().name == "sound"

    @pytest.mark.asyncio
    async def test_returns_false_when_winsound_unavailable(self) -> None:
        """On non-Windows (no winsound), notify returns False."""
        import sys as _sys

        original = _sys.modules.get("winsound")
        _sys.modules["winsound"] = None  # type: ignore[assignment]
        try:
            backend = WinSoundBackend()
            result = await backend.notify("hello", HookEvent.TASK_COMPLETE)
        finally:
            if original is not None:
                _sys.modules["winsound"] = original
            else:
                _sys.modules.pop("winsound", None)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_messagebeep_failure(self) -> None:
        """When MessageBeep raises, notify returns False."""
        mock_winsound = MagicMock()
        mock_winsound.MessageBeep.side_effect = RuntimeError("speaker off")
        with patch.dict("sys.modules", {"winsound": mock_winsound}):
            backend = WinSoundBackend()
            result = await backend.notify("hello", HookEvent.TASK_COMPLETE)
        assert result is False


# ---------------------------------------------------------------------------
# SlackNotificationBackend (TDD RED — task #980)
# ---------------------------------------------------------------------------


class TestFromAC_SlackNotificationBackend:
    """TDD RED tests for SlackNotificationBackend (task #980, implements #978).

    All tests import SlackNotificationBackend inside each method so that
    existing tests in this file remain passing while this class fails RED.
    """

    # ------------------------------------------------------------------
    # AC1 — Protocol conformance
    # ------------------------------------------------------------------

    def test_isinstance_notification_backend(self) -> None:
        """SlackNotificationBackend satisfies the NotificationBackend protocol."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        assert isinstance(SlackNotificationBackend("tok", "chan"), NotificationBackend)

    # ------------------------------------------------------------------
    # AC1 — name property
    # ------------------------------------------------------------------

    def test_name_returns_slack(self) -> None:
        """name property returns 'slack'."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        assert SlackNotificationBackend("tok", "chan").name == "slack"

    # ------------------------------------------------------------------
    # AC1 — Happy path: returns True on success
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_returns_true_on_success(self) -> None:
        """notify() returns True when chat_postMessage succeeds."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        mock_client_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.chat_postMessage = AsyncMock(return_value={"ok": True})
        mock_client_cls.return_value = mock_instance

        with patch("owlbear.core.notification_hook.AsyncWebClient", mock_client_cls):
            backend = SlackNotificationBackend("mytoken", "mychannel")
            result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        assert result is True
        mock_client_cls.assert_called_once_with(token="mytoken")
        mock_instance.chat_postMessage.assert_called_once()

    # ------------------------------------------------------------------
    # AC1 — Guard: bot_token is None → returns False
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_returns_false_when_bot_token_is_none(self) -> None:
        """notify() returns False immediately when bot_token is None."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        backend = SlackNotificationBackend(None, "mychannel")
        result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        assert result is False

    # ------------------------------------------------------------------
    # AC1 — Guard: channel_id is None → returns False
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_returns_false_when_channel_id_is_none(self) -> None:
        """notify() returns False immediately when channel_id is None."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        backend = SlackNotificationBackend("mytoken", None)
        result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        assert result is False

    # ------------------------------------------------------------------
    # AC1 — Import guard: AsyncWebClient is None → returns False
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_returns_false_when_asyncwebclient_unavailable(self) -> None:
        """notify() returns False when slack_sdk is not installed (AsyncWebClient is None)."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        with patch("owlbear.core.notification_hook.AsyncWebClient", None):
            backend = SlackNotificationBackend("mytoken", "mychannel")
            result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        assert result is False

    # ------------------------------------------------------------------
    # AC1 — Exception handling: logs warning, returns False, no propagation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_returns_false_and_logs_warning_on_exception(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """notify() catches exceptions from chat_postMessage, logs a warning, returns False."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        mock_client_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.chat_postMessage = AsyncMock(side_effect=RuntimeError("network error"))
        mock_client_cls.return_value = mock_instance

        with patch("owlbear.core.notification_hook.AsyncWebClient", mock_client_cls):
            backend = SlackNotificationBackend("mytoken", "mychannel")
            with caplog.at_level(logging.WARNING):
                result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        assert result is False
        assert any(rec.levelno >= logging.WARNING for rec in caplog.records)

    # ------------------------------------------------------------------
    # AC1 — Message format: *{event.value}*: {message}
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_formats_message_with_event_value(self) -> None:
        """notify() posts *{event.value}*: {message} to chat_postMessage."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        mock_client_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.chat_postMessage = AsyncMock(return_value={"ok": True})
        mock_client_cls.return_value = mock_instance

        with patch("owlbear.core.notification_hook.AsyncWebClient", mock_client_cls):
            backend = SlackNotificationBackend("mytoken", "mychannel")
            await backend.notify("task done", HookEvent.TASK_COMPLETE)

        call_kwargs = mock_instance.chat_postMessage.call_args.kwargs
        assert call_kwargs.get("channel") == "mychannel"
        assert call_kwargs.get("text") == f"*{HookEvent.TASK_COMPLETE.value}*: task done"

    # ------------------------------------------------------------------
    # AC1 — Message format: *notification*: {message} when event is None
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_formats_message_with_none_event(self) -> None:
        """notify() posts *notification*: {message} when event is None (defensive fallback)."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        mock_client_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.chat_postMessage = AsyncMock(return_value={"ok": True})
        mock_client_cls.return_value = mock_instance

        with patch("owlbear.core.notification_hook.AsyncWebClient", mock_client_cls):
            backend = SlackNotificationBackend("mytoken", "mychannel")
            await backend.notify("some message", None)  # type: ignore[arg-type]

        call_kwargs = mock_instance.chat_postMessage.call_args.kwargs
        assert call_kwargs.get("text") == "*notification*: some message"

    # ------------------------------------------------------------------
    # AC1 — Structural guard: no imports from owlbear.channels
    # ------------------------------------------------------------------

    def test_no_owlbear_channels_import(self) -> None:
        """notification_hook.py must not import from owlbear.channels."""
        import ast
        import pathlib

        from owlbear.core.notification_hook import SlackNotificationBackend

        _ = SlackNotificationBackend  # referenced to trigger ImportError at RED phase

        source = pathlib.Path("src/owlbear/core/notification_hook.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and "owlbear.channels" in node.module
            ):
                pytest.fail(
                    f"Found forbidden import in notification_hook.py: from {node.module} import ..."
                )

    def test_no_owlbear_channels_plain_import(self) -> None:
        """notification_hook.py must not use plain `import owlbear.channels[.*]` statements."""
        import ast
        import pathlib

        source = pathlib.Path("src/owlbear/core/notification_hook.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "owlbear.channels" in alias.name:
                        pytest.fail(
                            "Found forbidden plain import in notification_hook.py:"
                            f" import {alias.name}"
                        )

    # ------------------------------------------------------------------
    # AC5 — Short-circuit: guard exits BEFORE constructing AsyncWebClient
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_bot_token_none_never_constructs_client(self) -> None:
        """When bot_token is None, returns False without constructing AsyncWebClient."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        mock_client_cls = MagicMock()
        with patch("owlbear.core.notification_hook.AsyncWebClient", mock_client_cls):
            backend = SlackNotificationBackend(None, "mychannel")
            result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        assert result is False
        mock_client_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_notify_channel_id_none_never_constructs_client(self) -> None:
        """When channel_id is None, returns False without constructing AsyncWebClient."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        mock_client_cls = MagicMock()
        with patch("owlbear.core.notification_hook.AsyncWebClient", mock_client_cls):
            backend = SlackNotificationBackend("mytoken", None)
            result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        assert result is False
        mock_client_cls.assert_not_called()

    # ------------------------------------------------------------------
    # AC3 — Structural guard: no owlbear.config / settings imports
    # ------------------------------------------------------------------

    def test_no_config_settings_import(self) -> None:
        """notification_hook.py must not import from owlbear.config or reference OwlBearSettings."""
        import ast
        import pathlib

        source = pathlib.Path("src/owlbear/core/notification_hook.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "owlbear.config" in node.module or "settings" in node.module.lower():
                    pytest.fail(
                        f"Found forbidden config/settings import in notification_hook.py: "
                        f"from {node.module} import ..."
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "owlbear.config" in alias.name or "settings" in alias.name.lower():
                        pytest.fail(
                            f"Found forbidden config/settings import in notification_hook.py: "
                            f"import {alias.name}"
                        )

    # ------------------------------------------------------------------
    # AC3 — Constructor signature: exactly bot_token and channel_id, nothing else
    # ------------------------------------------------------------------

    def test_constructor_signature_exact_two_params(self) -> None:
        """SlackNotificationBackend.__init__ accepts exactly bot_token and channel_id."""
        import inspect

        from owlbear.core.notification_hook import SlackNotificationBackend

        sig = inspect.signature(SlackNotificationBackend.__init__)
        params = [p for p in sig.parameters if p != "self"]
        assert params == ["bot_token", "channel_id"], (
            f"Expected __init__ params ['bot_token', 'channel_id'], got {params}"
        )

    # ------------------------------------------------------------------
    # AC5 — AsyncWebClient None guard exits BEFORE the exception handler
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_notify_asyncwebclient_none_exits_before_exception_handler(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """When AsyncWebClient is None, returns False without entering the exception handler."""
        from owlbear.core.notification_hook import SlackNotificationBackend

        with patch("owlbear.core.notification_hook.AsyncWebClient", None):
            backend = SlackNotificationBackend("mytoken", "mychannel")
            with caplog.at_level(logging.WARNING):
                result = await backend.notify("hello", HookEvent.TASK_COMPLETE)

        assert result is False
        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert not warning_records, (
            "Warning was logged — notify() entered the exception handler instead of "
            "short-circuiting at 'if AsyncWebClient is None'"
        )

    # ------------------------------------------------------------------
    # AC4 — Import-guard shape: try/except ImportError around AsyncWebClient
    # ------------------------------------------------------------------

    def test_asyncwebclient_import_guard_exists(self) -> None:
        """notification_hook.py must guard the AsyncWebClient import with try/except ImportError."""
        import ast
        import pathlib

        source = pathlib.Path("src/owlbear/core/notification_hook.py").read_text()
        tree = ast.parse(source)

        found_guard = False
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            # Body must import AsyncWebClient from slack_sdk
            for stmt in node.body:
                if not isinstance(stmt, ast.ImportFrom):
                    continue
                if "slack_sdk" not in (stmt.module or ""):
                    continue
                if not any(alias.name == "AsyncWebClient" for alias in stmt.names):
                    continue
                # Handler must catch ImportError (or bare except)
                for handler in node.handlers:
                    if handler.type is None or (
                        isinstance(handler.type, ast.Name) and handler.type.id == "ImportError"
                    ):
                        found_guard = True

        assert found_guard, (
            "notification_hook.py must guard "
            "'from slack_sdk.web.async_client import AsyncWebClient' "
            "with a try/except ImportError block"
        )
