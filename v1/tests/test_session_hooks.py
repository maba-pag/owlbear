"""Tests for SESSION_START and SESSION_END hook emission in run_daemon.

TDD RED phase for task #711 (test task #713).  All tests must FAIL until
the builder adds SESSION_START / SESSION_END emission to ``run_daemon()``.

Tests verify the contract:
- SESSION_START emitted with {session_id, workspace_root} after DAEMON_STARTUP
- SESSION_END emitted with {session_id, messages} in the finally block
- SESSION_END fires even on exception
- Empty/missing session -> messages falls back to []
- ContextInjectionHook fires on SESSION_START and populates data['context']
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.daemon import run_daemon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockChannel:
    """Minimal ChannelPlugin mock that returns a pre-set message sequence."""

    def __init__(self, messages: list[str | None] | None = None) -> None:
        self._messages = list(messages) if messages is not None else [None]
        self._index = 0
        self.sent: list[str] = []

    @property
    def name(self) -> str:
        return "mock"

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        if self._index >= len(self._messages):
            return None
        msg = self._messages[self._index]
        self._index += 1
        return msg


def _make_mock_agent(
    *,
    session_path: Path = Path("sessions/test.jsonl"),
    session_load_result: list[object] | None = None,
    hooks: HookRegistry | None = None,
) -> AsyncMock:
    """Create a mock OwlBearAgent with session and hooks attributes."""
    agent = AsyncMock()
    agent.session.path = session_path
    agent.session.load.return_value = session_load_result if session_load_result is not None else []
    if hooks is not None:
        agent.hooks = hooks
    return agent


# ---------------------------------------------------------------------------
# TestFromAC_SessionStart -- SESSION_START emission
# ---------------------------------------------------------------------------


class TestFromAC_SessionStart:
    """SESSION_START hook is emitted by run_daemon with correct payload."""

    @pytest.mark.asyncio
    async def test_session_start_emitted(self, tmp_path: Path) -> None:
        """run_daemon emits SESSION_START with {session_id, workspace_root}."""
        channel = _MockChannel([None])
        mock_agent = _make_mock_agent(session_path=tmp_path / "session.jsonl")

        await (
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                workspace_root=tmp_path,
            )
        )

        calls = mock_agent.hooks.emit.call_args_list
        session_start_calls = [c for c in calls if c.args[0] == HookEvent.SESSION_START]
        assert len(session_start_calls) == 1, "SESSION_START should be emitted exactly once"

        payload = session_start_calls[0].args[1]
        assert "session_id" in payload
        assert "workspace_root" in payload
        assert payload["session_id"] == str(tmp_path / "session.jsonl")
        assert payload["workspace_root"] == str(tmp_path)

    @pytest.mark.asyncio
    async def test_session_start_after_daemon_startup(self, tmp_path: Path) -> None:
        """SESSION_START is emitted after DAEMON_STARTUP (ordering)."""
        channel = _MockChannel([None])
        emit_order: list[str] = []

        hooks = HookRegistry()

        def track_daemon_startup(data: object) -> None:  # noqa: ARG001
            emit_order.append("DAEMON_STARTUP")

        def track_session_start(data: object) -> None:  # noqa: ARG001
            emit_order.append("SESSION_START")

        hooks.register(HookEvent.DAEMON_STARTUP, track_daemon_startup)
        hooks.register(HookEvent.SESSION_START, track_session_start)

        mock_agent = _make_mock_agent(
            session_path=tmp_path / "session.jsonl",
            hooks=hooks,
        )

        await (
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                workspace_root=tmp_path,
            )
        )

        assert "DAEMON_STARTUP" in emit_order, "DAEMON_STARTUP should be emitted"
        assert "SESSION_START" in emit_order, "SESSION_START should be emitted"
        assert emit_order.index("DAEMON_STARTUP") < emit_order.index("SESSION_START"), (
            "DAEMON_STARTUP must come before SESSION_START"
        )


# ---------------------------------------------------------------------------
# TestFromAC_SessionEnd -- SESSION_END emission
# ---------------------------------------------------------------------------


class TestFromAC_SessionEnd:
    """SESSION_END hook is emitted by run_daemon with correct payload."""

    @pytest.mark.asyncio
    async def test_session_end_emitted_on_normal_exit(self, tmp_path: Path) -> None:
        """run_daemon emits SESSION_END with {session_id, messages} on normal exit."""
        channel = _MockChannel([None])
        mock_agent = _make_mock_agent(
            session_path=tmp_path / "session.jsonl",
            session_load_result=["msg1", "msg2"],
        )

        await (
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                workspace_root=tmp_path,
            )
        )

        calls = mock_agent.hooks.emit.call_args_list
        session_end_calls = [c for c in calls if c.args[0] == HookEvent.SESSION_END]
        assert len(session_end_calls) == 1, "SESSION_END should be emitted exactly once"

        payload = session_end_calls[0].args[1]
        assert "session_id" in payload
        assert "messages" in payload
        assert payload["session_id"] == str(tmp_path / "session.jsonl")
        assert payload["messages"] == ["msg1", "msg2"]

    @pytest.mark.asyncio
    async def test_session_end_emitted_on_exception(self, tmp_path: Path) -> None:
        """SESSION_END is emitted in finally block even when channel_loop raises."""
        channel = _MockChannel([])

        async def exploding_receive(
            *,
            prompt: str | None = None,  # noqa: ARG001
        ) -> str | None:
            msg = "boom in channel"
            raise RuntimeError(msg)

        channel.receive = exploding_receive  # type: ignore[assignment]

        mock_agent = _make_mock_agent(session_path=tmp_path / "session.jsonl")

        # run_daemon may propagate the exception; we only care SESSION_END was emitted
        with pytest.raises((RuntimeError, ExceptionGroup)):
            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    workspace_root=tmp_path,
                )
            )

        calls = mock_agent.hooks.emit.call_args_list
        session_end_calls = [c for c in calls if c.args[0] == HookEvent.SESSION_END]
        assert len(session_end_calls) == 1, (
            "SESSION_END must be emitted even when an exception occurs"
        )

    @pytest.mark.asyncio
    async def test_session_end_empty_session(self, tmp_path: Path) -> None:
        """SESSION_END with missing session file falls back to empty messages list."""
        channel = _MockChannel([None])
        mock_agent = _make_mock_agent(session_path=tmp_path / "nonexistent.jsonl")
        # Simulate load() raising because session file doesn't exist
        mock_agent.session.load.side_effect = FileNotFoundError("no session file")

        await (
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                workspace_root=tmp_path,
            )
        )

        calls = mock_agent.hooks.emit.call_args_list
        session_end_calls = [c for c in calls if c.args[0] == HookEvent.SESSION_END]
        assert len(session_end_calls) == 1, "SESSION_END should be emitted"

        payload = session_end_calls[0].args[1]
        assert payload["messages"] == [], (
            "messages should fall back to empty list when session.load() fails"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ContextInjection -- ContextInjectionHook integration
# ---------------------------------------------------------------------------


class TestFromAC_ContextInjection:
    """ContextInjectionHook fires on SESSION_START and populates data['context']."""

    @pytest.mark.asyncio
    async def test_context_injection_hook_fires(self, tmp_path: Path) -> None:
        """Register ContextInjectionHook, run run_daemon, verify data['context']."""
        from owlbear.core.context_hook import ContextInjectionHook

        channel = _MockChannel([None])
        captured_data: list[dict[str, object]] = []

        hooks = HookRegistry()

        # ContextInjectionHook with a real instructions file and harmless command
        instructions_file = tmp_path / "instructions.md"
        instructions_file.write_text("# Test instructions", encoding="utf-8")

        hook = ContextInjectionHook(
            instructions_path=instructions_file,
            kanban_cmd=["echo", "test"],
        )
        hook.register(hooks)

        # Spy to capture SESSION_START payload after ContextInjectionHook runs
        async def capture_payload(data: object) -> None:
            if isinstance(data, dict):
                captured_data.append(dict(data))

        hooks.register(HookEvent.SESSION_START, capture_payload)

        mock_agent = _make_mock_agent(
            session_path=tmp_path / "session.jsonl",
            hooks=hooks,
        )

        await (
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                workspace_root=tmp_path,
            )
        )

        # SESSION_START should have been emitted through run_daemon
        assert len(captured_data) >= 1, "SESSION_START payload should have been captured"
        payload = captured_data[0]
        assert "context" in payload, "ContextInjectionHook should populate data['context']"
        assert "instructions" in payload["context"]
        assert "kanban_summary" in payload["context"]
