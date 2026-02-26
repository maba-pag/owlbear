"""Tests for owlbear.core.hooks — HookRegistry and HookEvent."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from owlbear.core.hooks import HookEvent, HookRegistry


class TestHookEvent:
    """HookEvent enum has the expected members."""

    def test_has_session_start(self) -> None:
        assert HookEvent.SESSION_START == "session_start"

    def test_has_session_end(self) -> None:
        assert HookEvent.SESSION_END == "session_end"

    def test_has_pre_tool_use(self) -> None:
        assert HookEvent.PRE_TOOL_USE == "pre_tool_use"

    def test_has_post_tool_use(self) -> None:
        assert HookEvent.POST_TOOL_USE == "post_tool_use"

    def test_has_on_message(self) -> None:
        assert HookEvent.ON_MESSAGE == "on_message"

    def test_has_on_error(self) -> None:
        assert HookEvent.ON_ERROR == "on_error"


class TestHookRegistrySync:
    """Synchronous handler registration and emission."""

    def test_register_and_emit(self) -> None:
        registry = HookRegistry()
        handler = MagicMock()
        registry.register(HookEvent.ON_MESSAGE, handler)
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {"text": "hi"}))
        handler.assert_called_once_with({"text": "hi"})

    def test_emit_no_handlers(self) -> None:
        """Emitting an event with no handlers should not raise."""
        registry = HookRegistry()
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {}))

    def test_multiple_handlers_called_in_order(self) -> None:
        registry = HookRegistry()
        call_order: list[int] = []
        registry.register(HookEvent.ON_MESSAGE, lambda _: call_order.append(1))
        registry.register(HookEvent.ON_MESSAGE, lambda _: call_order.append(2))
        registry.register(HookEvent.ON_MESSAGE, lambda _: call_order.append(3))
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {}))
        assert call_order == [1, 2, 3]

    def test_different_events_isolated(self) -> None:
        registry = HookRegistry()
        msg_handler = MagicMock()
        err_handler = MagicMock()
        registry.register(HookEvent.ON_MESSAGE, msg_handler)
        registry.register(HookEvent.ON_ERROR, err_handler)
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {"text": "hi"}))
        msg_handler.assert_called_once()
        err_handler.assert_not_called()


class TestHookRegistryAsync:
    """Async handler registration and emission."""

    def test_async_handler_called(self) -> None:
        registry = HookRegistry()
        handler = AsyncMock()
        registry.register(HookEvent.ON_MESSAGE, handler)
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {"text": "hi"}))
        handler.assert_called_once_with({"text": "hi"})

    def test_mixed_sync_async_handlers(self) -> None:
        registry = HookRegistry()
        results: list[str] = []
        sync_handler = MagicMock(side_effect=lambda _: results.append("sync"))

        async def async_handler(_: Any) -> None:
            results.append("async")

        registry.register(HookEvent.ON_MESSAGE, sync_handler)
        registry.register(HookEvent.ON_MESSAGE, async_handler)
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {}))
        assert results == ["sync", "async"]


class TestHookRegistryErrorIsolation:
    """One failing handler must not prevent others from running."""

    def test_error_isolation_sync(self) -> None:
        registry = HookRegistry()
        results: list[str] = []
        registry.register(HookEvent.ON_MESSAGE, lambda _: results.append("first"))
        registry.register(
            HookEvent.ON_MESSAGE,
            MagicMock(side_effect=RuntimeError("boom")),
        )
        registry.register(HookEvent.ON_MESSAGE, lambda _: results.append("third"))
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {}))
        assert results == ["first", "third"]

    def test_error_isolation_async(self) -> None:
        registry = HookRegistry()
        results: list[str] = []

        async def good_before(_: Any) -> None:
            results.append("before")

        async def bad(_: Any) -> None:
            msg = "async boom"
            raise RuntimeError(msg)

        async def good_after(_: Any) -> None:
            results.append("after")

        registry.register(HookEvent.ON_MESSAGE, good_before)
        registry.register(HookEvent.ON_MESSAGE, bad)
        registry.register(HookEvent.ON_MESSAGE, good_after)
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {}))
        assert results == ["before", "after"]


class TestHookRegistryUnregister:
    """Handlers can be unregistered."""

    def test_unregister(self) -> None:
        registry = HookRegistry()
        handler = MagicMock()
        registry.register(HookEvent.ON_MESSAGE, handler)
        registry.unregister(HookEvent.ON_MESSAGE, handler)
        asyncio.run(registry.emit(HookEvent.ON_MESSAGE, {}))
        handler.assert_not_called()

    def test_unregister_nonexistent(self) -> None:
        """Unregistering a handler that was never registered should not raise."""
        registry = HookRegistry()
        handler = MagicMock()
        registry.unregister(HookEvent.ON_MESSAGE, handler)  # no-op


class TestHookRegistryClear:
    """Clear all handlers."""

    def test_clear(self) -> None:
        registry = HookRegistry()
        registry.register(HookEvent.ON_MESSAGE, MagicMock())
        registry.register(HookEvent.ON_ERROR, MagicMock())
        registry.clear()
        assert registry.handlers == {}
