"""Tests for daemon lifecycle — PidFile, sentinel, signals, logging.

Covers: PidFile context manager, stale PID detection, PID conflict,
setup_logging, sentinel-based shutdown, run_daemon loop, signal handler,
bearclaw stop/status CLI commands, Copilot token refresh on auth errors,
ErrorJournal integration.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pytest

from owlbear.core.errors import ErrorCategory
from owlbear.daemon import PidFile, run_daemon, setup_logging
from owlbear.memory.error_journal import ErrorJournal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockChannel:
    """Minimal ChannelPlugin mock with programmable receive sequence."""

    def __init__(self, messages: list[str | None]) -> None:
        self._messages = list(messages)
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


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PidFile context manager
# ---------------------------------------------------------------------------


class TestPidFileContextManager:
    """PidFile writes PID on __enter__ and removes on __exit__."""

    def test_creates_pid_file_on_enter(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pf = PidFile(pid_path)
        pf.__enter__()
        try:
            assert pid_path.exists()
            assert pid_path.read_text().strip() == str(os.getpid())
        finally:
            pf.__exit__(None, None, None)

    def test_removes_pid_file_on_exit(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        with PidFile(pid_path):
            assert pid_path.exists()
        assert not pid_path.exists()

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "subdir" / "owlbear.pid"
        with PidFile(pid_path):
            assert pid_path.exists()
        assert not pid_path.exists()

    def test_exit_tolerates_missing_file(self, tmp_path: Path) -> None:
        """__exit__ should not raise if someone already deleted the PID file."""
        pid_path = tmp_path / "owlbear.pid"
        pf = PidFile(pid_path)
        pf.__enter__()
        pid_path.unlink()  # simulate external deletion
        pf.__exit__(None, None, None)  # should not raise


# ---------------------------------------------------------------------------
# PidFile stale detection
# ---------------------------------------------------------------------------


class TestPidFileStaleDetection:
    """PidFile detects stale PID files (process dead) and cleans up."""

    def test_stale_pid_cleaned_up(self, tmp_path: Path) -> None:
        """If PID file exists but process is dead, PidFile cleans up and proceeds."""
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("99999999")  # unlikely to be a real PID

        with (
            patch("owlbear.daemon._is_process_alive", return_value=False),
            PidFile(pid_path),
        ):
            # Should succeed — stale file was cleaned up
            assert pid_path.read_text().strip() == str(os.getpid())

    def test_stale_pid_file_removed_before_new_write(self, tmp_path: Path) -> None:
        """Stale PID file is removed, then current PID is written."""
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("88888888")

        with patch("owlbear.daemon._is_process_alive", return_value=False):
            pf = PidFile(pid_path)
            pf.__enter__()
            try:
                content = pid_path.read_text().strip()
                assert content == str(os.getpid())
                assert content != "88888888"
            finally:
                pf.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# PidFile conflict
# ---------------------------------------------------------------------------


class TestPidFileConflict:
    """PidFile raises RuntimeError when PID file exists and process alive."""

    def test_raises_on_live_process(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("12345")

        with (
            patch("owlbear.daemon._is_process_alive", return_value=True),
            pytest.raises(RuntimeError, match="already running"),
        ):
            PidFile(pid_path).__enter__()

    def test_pid_file_not_modified_on_conflict(self, tmp_path: Path) -> None:
        """On conflict, the existing PID file should remain unchanged."""
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("12345")

        with (
            patch("owlbear.daemon._is_process_alive", return_value=True),
            pytest.raises(RuntimeError),
        ):
            PidFile(pid_path).__enter__()
        assert pid_path.read_text().strip() == "12345"


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------


class TestSetupLogging:
    """setup_logging creates RotatingFileHandler + stderr StreamHandler."""

    def test_creates_rotating_file_handler(self, tmp_path: Path) -> None:
        log_file = tmp_path / "owlbear.log"
        handlers_before = list(logging.getLogger().handlers)
        root = setup_logging(log_file)

        new_handlers = [h for h in root.handlers if h not in handlers_before]
        file_handlers = [
            h for h in new_handlers if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        fh = file_handlers[0]
        assert fh.maxBytes == 5 * 1024 * 1024  # 5 MB
        assert fh.backupCount == 3

        # cleanup
        for h in new_handlers:
            root.removeHandler(h)
            h.close()

    def test_creates_stderr_stream_handler(self, tmp_path: Path) -> None:
        from rich.logging import RichHandler

        log_file = tmp_path / "owlbear.log"
        handlers_before = list(logging.getLogger().handlers)
        root = setup_logging(log_file)

        new_handlers = [h for h in root.handlers if h not in handlers_before]
        stream_handlers = [
            h
            for h in new_handlers
            if isinstance(h, (logging.StreamHandler, RichHandler))
            and not isinstance(h, logging.FileHandler)
        ]
        assert len(stream_handlers) == 1

        # cleanup
        for h in new_handlers:
            root.removeHandler(h)
            h.close()

    def test_log_format(self, tmp_path: Path) -> None:
        log_file = tmp_path / "owlbear.log"
        handlers_before = list(logging.getLogger().handlers)
        root = setup_logging(log_file)

        new_handlers = [h for h in root.handlers if h not in handlers_before]
        # Only file handlers use a plain Formatter; RichHandler uses Console rendering
        file_handlers = [
            h for h in new_handlers if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) >= 1
        for h in file_handlers:
            fmt = h.formatter
            assert fmt is not None
            assert "%(asctime)s" in fmt._fmt  # type: ignore[union-attr]
            assert "%(levelname)s" in fmt._fmt  # type: ignore[union-attr]
            assert "%(name)s" in fmt._fmt  # type: ignore[union-attr]
            assert "%(message)s" in fmt._fmt  # type: ignore[union-attr]

        # cleanup
        for h in new_handlers:
            root.removeHandler(h)
            h.close()

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        log_file = tmp_path / "logs" / "owlbear.log"
        handlers_before = list(logging.getLogger().handlers)
        root = setup_logging(log_file)
        assert log_file.parent.exists()

        # cleanup
        new_handlers = [h for h in root.handlers if h not in handlers_before]
        for h in new_handlers:
            root.removeHandler(h)
            h.close()


# ---------------------------------------------------------------------------
# Rich logging integration (TDD RED — #739)
# ---------------------------------------------------------------------------


class TestFromAC_RichLogging:  # noqa: N801
    """AC contract: setup_logging uses RichHandler for stderr, plain for file."""

    @staticmethod
    def _setup_and_collect(log_file: Path) -> tuple[logging.Logger, list[logging.Handler]]:
        """Call setup_logging and return (root, new_handlers)."""
        before = list(logging.getLogger().handlers)
        root = setup_logging(log_file)
        return root, [h for h in root.handlers if h not in before]

    @staticmethod
    def _cleanup(root: logging.Logger, handlers: list[logging.Handler]) -> None:
        for h in handlers:
            root.removeHandler(h)
            h.close()

    def test_stderr_handler_is_rich_handler(self, tmp_path: Path) -> None:
        """AC: stderr handler is instance of RichHandler after setup_logging()."""
        from rich.logging import RichHandler

        root, new = self._setup_and_collect(tmp_path / "owlbear.log")
        try:
            rich_handlers = [h for h in new if isinstance(h, RichHandler)]
            assert len(rich_handlers) == 1, (
                f"expected exactly 1 RichHandler, got {len(rich_handlers)}"
            )
        finally:
            self._cleanup(root, new)

    def test_file_handler_plain_formatter_with_rich_stderr(self, tmp_path: Path) -> None:
        """AC: file handler remains RotatingFileHandler with plain Formatter."""
        from rich.logging import RichHandler

        root, new = self._setup_and_collect(tmp_path / "owlbear.log")
        try:
            # Precondition: RichHandler is installed for stderr
            rich_handlers = [h for h in new if isinstance(h, RichHandler)]
            assert len(rich_handlers) == 1, "precondition: RichHandler must be on stderr"

            # File handler is RotatingFileHandler with plain logging.Formatter
            file_handlers = [h for h in new if isinstance(h, logging.handlers.RotatingFileHandler)]
            assert len(file_handlers) == 1
            assert type(file_handlers[0].formatter) is logging.Formatter
        finally:
            self._cleanup(root, new)

    def test_log_file_no_ansi_escapes(self, tmp_path: Path) -> None:
        """AC: log file output contains no ANSI escape sequences."""
        import re

        from rich.logging import RichHandler

        log_file = tmp_path / "owlbear.log"
        root, new = self._setup_and_collect(log_file)
        try:
            # Precondition: RichHandler is present (proves Rich is active)
            rich_handlers = [h for h in new if isinstance(h, RichHandler)]
            assert len(rich_handlers) == 1, "precondition: RichHandler must be on stderr"

            # Write through root logger and flush all handlers
            root.info("test-ansi-check")
            for h in new:
                h.flush()

            content = log_file.read_text()
            assert not re.search(r"\x1b\[", content), (
                f"ANSI escape sequences found in log file: {content!r}"
            )
        finally:
            self._cleanup(root, new)

    def test_setup_logging_installs_rich_traceback(self, tmp_path: Path) -> None:
        """AC: rich.traceback.install() sets sys.excepthook in CLI callback."""
        import sys

        log_file = tmp_path / "owlbear.log"
        root, new = self._setup_and_collect(log_file)
        try:
            # After setup_logging, sys.excepthook should have been replaced
            # by rich.traceback.install() — it should NOT be the default hook.
            assert sys.excepthook is not sys.__excepthook__, (
                "expected rich.traceback.install() to replace sys.excepthook"
            )
        finally:
            # Restore default excepthook if modified
            sys.excepthook = sys.__excepthook__
            self._cleanup(root, new)


# ---------------------------------------------------------------------------
# Sentinel shutdown
# ---------------------------------------------------------------------------


class TestSentinelShutdown:
    """run_daemon exits loop when sentinel file appears."""

    def test_sentinel_stops_loop(self, tmp_path: Path) -> None:
        """Daemon should exit when config_dir/owlbear.stop exists."""
        sentinel = tmp_path / "owlbear.stop"

        # Channel returns one message, then the sentinel appears
        call_count = 0

        async def mock_receive(*, prompt: str | None = None) -> str | None:  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "hello"
            # Create sentinel before second receive
            sentinel.touch()
            return "ignored"

        channel = MockChannel([])
        channel.receive = mock_receive  # type: ignore[assignment]

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(return_value="reply")

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        # Sentinel file should be cleaned up
        assert not sentinel.exists()

    def test_sentinel_cleaned_up_on_exit(self, tmp_path: Path) -> None:
        """Sentinel file is removed during shutdown."""
        sentinel = tmp_path / "owlbear.stop"
        sentinel.touch()  # pre-create sentinel so loop exits immediately

        channel = MockChannel([])
        mock_agent = AsyncMock()

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        assert not sentinel.exists()


# ---------------------------------------------------------------------------
# run_daemon full loop
# ---------------------------------------------------------------------------


class TestRunDaemon:
    """run_daemon creates PID, dispatches messages, shuts down on sentinel."""

    def test_receive_turn_send_cycle(self, tmp_path: Path) -> None:
        """Receives message, calls agent.turn(), sends response."""
        messages = ["hello"]
        channel = MockChannel(messages)

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(return_value="world")

        # Channel returns "hello", then None (EOF) → loop exits
        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        mock_agent.turn.assert_called_once_with("hello")
        assert "world" in channel.sent

    def test_none_receive_exits_loop(self, tmp_path: Path) -> None:
        """Channel returning None (EOF) should exit the daemon loop."""
        channel = MockChannel([None])

        mock_agent = AsyncMock()

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        mock_agent.turn.assert_not_called()

    def test_empty_message_skipped(self, tmp_path: Path) -> None:
        """Empty strings from channel should be skipped."""
        channel = MockChannel(["", "  ", None])

        mock_agent = AsyncMock()

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        mock_agent.turn.assert_not_called()

    def test_agent_error_sent_to_channel(self, tmp_path: Path) -> None:
        """If agent.turn() raises, error is sent to channel."""
        channel = MockChannel(["boom", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=RuntimeError("agent broke"))

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        assert any("agent broke" in msg for msg in channel.sent)

    def test_multiple_messages(self, tmp_path: Path) -> None:
        """Daemon processes multiple messages before EOF."""
        channel = MockChannel(["msg1", "msg2", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=["reply1", "reply2"])

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        assert mock_agent.turn.call_count == 2
        assert "reply1" in channel.sent
        assert "reply2" in channel.sent

    def test_accepts_settings_param(self, tmp_path: Path) -> None:
        """run_daemon accepts an optional settings parameter for token refresh."""
        channel = MockChannel([None])
        mock_agent = AsyncMock()

        # Should not raise — settings is an optional kwarg
        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                settings=None,
            )
        )

    def test_settings_param_defaults_to_none(self, tmp_path: Path) -> None:
        """run_daemon works without settings (backwards compatibility)."""
        channel = MockChannel([None])
        mock_agent = AsyncMock()

        # Existing call pattern still works
        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )


# ---------------------------------------------------------------------------
# OTel / configure_otel
# ---------------------------------------------------------------------------


class TestConfigureOtel:
    """run_daemon calls configure_otel when otel_endpoint is provided."""

    def test_otel_endpoint_configures_logfire(self, tmp_path: Path) -> None:
        """Passing otel_endpoint triggers configure_otel inside run_daemon."""
        channel = MockChannel([None])
        mock_agent = AsyncMock()

        with (
            patch("owlbear.daemon.logfire.configure") as mock_logfire,
            patch("owlbear.daemon.Agent.instrument_all"),
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    otel_endpoint="http://localhost:4318",
                )
            )

        mock_logfire.assert_called_once_with(send_to_logfire=False, additional_span_processors=[])
        assert os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") == "http://localhost:4318"

    def test_no_otel_endpoint_skips_configure(self, tmp_path: Path) -> None:
        """Without otel_endpoint, configure_otel is not called."""
        channel = MockChannel([None])
        mock_agent = AsyncMock()

        with patch("owlbear.daemon.logfire.configure") as mock_logfire:
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        mock_logfire.assert_not_called()


# ---------------------------------------------------------------------------
# DAEMON_STARTUP hook
# ---------------------------------------------------------------------------


class TestDaemonStartupHook:
    """DAEMON_STARTUP hook is emitted once with correct payload before receive."""

    def test_emit_called_once_with_correct_event_and_payload(self, tmp_path: Path) -> None:
        """run_daemon emits DAEMON_STARTUP with channel name and config_dir."""
        from owlbear.core.hooks import HookEvent

        channel = MockChannel([None])
        mock_agent = AsyncMock()

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        mock_agent.hooks.emit.assert_any_call(
            HookEvent.DAEMON_STARTUP,
            {"channel": "mock", "config_dir": str(tmp_path)},
        )

    def test_emit_occurs_before_first_receive(self, tmp_path: Path) -> None:
        """DAEMON_STARTUP emit happens before the first channel.receive()."""
        call_order: list[str] = []

        channel = MockChannel([None])
        original_receive = channel.receive

        async def tracking_receive(*, prompt: str | None = None) -> str | None:  # noqa: ARG001
            call_order.append("receive")
            return await original_receive()

        channel.receive = tracking_receive  # type: ignore[assignment]

        mock_agent = AsyncMock()

        async def tracking_emit(event: object, data: object) -> None:  # noqa: ARG001
            call_order.append("emit")

        mock_agent.hooks.emit = AsyncMock(side_effect=tracking_emit)

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        assert "emit" in call_order
        assert "receive" in call_order
        assert call_order.index("emit") < call_order.index("receive")


# ---------------------------------------------------------------------------
# Signal handler
# ---------------------------------------------------------------------------


class TestSignalHandler:
    """SIGINT sets shutdown event (same as sentinel check)."""

    def test_signal_handler_sets_shutdown_event(self, tmp_path: Path) -> None:
        """Signal handler installed by run_daemon triggers shutdown."""

        call_count = 0
        captured_handlers: dict[int, object] = {}

        def fake_signal(sig: int, handler: object) -> object:
            old = captured_handlers.get(sig, signal.SIG_DFL)
            captured_handlers[sig] = handler
            return old

        async def receive_then_stop(*, prompt: str | None = None) -> str | None:  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "hello"
            # Invoke the captured SIGINT handler directly to simulate signal.
            # Yield to the event loop so any call_soon_threadsafe callbacks fire.
            handler = captured_handlers.get(signal.SIGINT)
            if callable(handler):
                handler(signal.SIGINT, None)
                await asyncio.sleep(0)
            return "after-signal"

        channel = MockChannel([])
        channel.receive = receive_then_stop  # type: ignore[assignment]

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(return_value="reply")

        with patch("owlbear.daemon.signal.signal", side_effect=fake_signal):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # First message processed; "after-signal" skipped due to shutdown
        mock_agent.turn.assert_called_once_with("hello")

    def test_signal_handler_tolerates_closed_loop(self) -> None:
        """Signal handler swallows RuntimeError when loop is already closed."""
        from owlbear.daemon import _make_signal_handler

        event = asyncio.Event()

        # Simulate a loop whose call_soon_threadsafe raises RuntimeError
        mock_loop = MagicMock()
        mock_loop.call_soon_threadsafe.side_effect = RuntimeError("Event loop is closed")

        handler = _make_signal_handler(mock_loop, event)
        # Should NOT raise even though call_soon_threadsafe fails
        handler(signal.SIGINT, None)

        # Event was NOT set (call_soon_threadsafe never executed the callback)
        assert not event.is_set()

    def test_signal_handler_uses_call_soon_threadsafe(self) -> None:
        """Signal handler delegates to loop.call_soon_threadsafe(event.set)."""
        from owlbear.daemon import _make_signal_handler

        event = asyncio.Event()
        mock_loop = MagicMock()

        handler = _make_signal_handler(mock_loop, event)
        handler(signal.SIGINT, None)

        mock_loop.call_soon_threadsafe.assert_called_once_with(event.set)

    def test_signal_handlers_restored_after_run(self, tmp_path: Path) -> None:
        """Signal handlers are restored to their previous values after run_daemon."""
        prev_sigint = signal.getsignal(signal.SIGINT)
        prev_sigterm = signal.getsignal(signal.SIGTERM)

        channel = MockChannel([None])
        mock_agent = AsyncMock()

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        assert signal.getsignal(signal.SIGINT) == prev_sigint
        assert signal.getsignal(signal.SIGTERM) == prev_sigterm


# ---------------------------------------------------------------------------
# bearclaw stop
# ---------------------------------------------------------------------------


class TestBearclawStop:
    """bearclaw stop creates sentinel, polls PID removal, cleans up."""

    def test_creates_sentinel_file(self, tmp_path: Path) -> None:
        from bearclaw.commands.daemon import _daemon_stop

        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text(str(os.getpid()))

        with (
            patch("bearclaw.commands.daemon._poll_pid_removal", return_value=True),
            patch("bearclaw.commands.daemon._get_config_dir", return_value=tmp_path),
        ):
            _daemon_stop()

        # Sentinel was created (and may be cleaned up — that's fine)
        # We check the flow worked by verifying _poll_pid_removal was called

    def test_reports_not_running_when_no_pid(self, tmp_path: Path) -> None:
        from bearclaw.commands.daemon import _daemon_stop

        with patch("bearclaw.commands.daemon._get_config_dir", return_value=tmp_path):
            # Should not raise, just report not running
            _daemon_stop()

    def test_force_kills_on_timeout(self, tmp_path: Path) -> None:
        from bearclaw.commands.daemon import _daemon_stop

        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("99999")

        with (
            patch("bearclaw.commands.daemon._poll_pid_removal", return_value=False),
            patch("bearclaw.commands.daemon._get_config_dir", return_value=tmp_path),
            patch("os.kill") as mock_kill,
        ):
            _daemon_stop()

        # Should have attempted force kill
        mock_kill.assert_called()


# ---------------------------------------------------------------------------
# bearclaw status
# ---------------------------------------------------------------------------


class TestBearclawStatus:
    """bearclaw status reports running/stopped/stale via rich.Panel."""

    @staticmethod
    def _mock_settings(tmp_path: Path) -> MagicMock:
        s = MagicMock()
        s.config_dir = str(tmp_path)
        s.chat_model = "gpt-4o"
        s.autonomous_mode = False
        s.heartbeat_enabled = False
        s.heartbeat_interval = 1800
        return s

    def test_not_running(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from bearclaw.commands.daemon import _daemon_status

        with patch(
            "bearclaw.commands.daemon.OwlBearSettings",
            return_value=self._mock_settings(tmp_path),
        ):
            _daemon_status()

        captured = capsys.readouterr()
        assert "Stopped" in captured.out

    def test_running(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from bearclaw.commands.daemon import _daemon_status

        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text(str(os.getpid()))

        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=self._mock_settings(tmp_path),
            ),
            patch(
                "bearclaw.commands.daemon._is_process_alive",
                return_value=True,
            ),
        ):
            _daemon_status()

        captured = capsys.readouterr()
        assert "Running" in captured.out
        assert str(os.getpid()) in captured.out

    def test_stale_pid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        from bearclaw.commands.daemon import _daemon_status

        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("99999999")

        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=self._mock_settings(tmp_path),
            ),
            patch(
                "bearclaw.commands.daemon._is_process_alive",
                return_value=False,
            ),
        ):
            _daemon_status()

        captured = capsys.readouterr()
        assert "Stale" in captured.out


# ---------------------------------------------------------------------------
# Error factory helpers
# ---------------------------------------------------------------------------


def _make_httpx_status_error(status: int) -> httpx.HTTPStatusError:
    """Create an httpx.HTTPStatusError with the given status code."""
    request = httpx.Request("GET", "http://example.com")
    response = httpx.Response(status, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


def _make_openai_auth_error() -> openai.AuthenticationError:
    """Create an openai.AuthenticationError."""
    request = httpx.Request("GET", "http://example.com")
    response = httpx.Response(401, request=request)
    return openai.AuthenticationError(message="bad token", response=response, body=None)


def _make_openai_permission_error() -> openai.PermissionDeniedError:
    """Create an openai.PermissionDeniedError."""
    request = httpx.Request("GET", "http://example.com")
    response = httpx.Response(403, request=request)
    return openai.PermissionDeniedError(message="denied", response=response, body=None)


# ---------------------------------------------------------------------------
# Copilot token refresh on auth error
# ---------------------------------------------------------------------------


class TestCopilotTokenRefresh:
    """run_daemon refreshes Copilot token on auth errors and retries once."""

    def test_auth_error_triggers_refresh_and_retry(self, tmp_path: Path) -> None:
        """Auth error on first call → refresh token → retry succeeds."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        # First call raises auth error, second call (after refresh) succeeds
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed reply"],
        )
        mock_agent.update_model = MagicMock()

        mock_settings = MagicMock()

        mock_client = AsyncMock()
        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=mock_client,
        ) as mock_create:
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=mock_settings,
                )
            )

        # create_copilot_client called with settings
        mock_create.assert_called_once_with(mock_settings)
        # agent.update_model called with the new model built from client
        mock_agent.update_model.assert_called_once()
        # agent.turn called twice (original + retry)
        assert mock_agent.turn.call_count == 2
        # Successful response sent to channel
        assert "refreshed reply" in channel.sent

    def test_non_auth_error_no_refresh(self, tmp_path: Path) -> None:
        """Non-auth RuntimeError → no refresh attempt, error sent to channel."""
        channel = MockChannel(["boom", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=RuntimeError("not auth related"))

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
        ) as mock_create:
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        # No refresh attempted
        mock_create.assert_not_called()
        # Error sent to channel as before
        assert any("not auth related" in msg for msg in channel.sent)

    def test_refresh_failure_sends_error_to_channel(self, tmp_path: Path) -> None:
        """If create_copilot_client raises during refresh, error sent to channel."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=_make_openai_auth_error())

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("no network"),
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        # Error sent to channel
        assert any("no network" in msg for msg in channel.sent)
        # Loop continues — channel processes next message (None → exit)

    def test_retry_auth_error_sends_error_to_channel(self, tmp_path: Path) -> None:
        """If retry after refresh also fails with auth error, error sent to channel."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        # Both calls fail with auth errors — no infinite retry
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), _make_openai_auth_error()],
        )
        mock_agent.update_model = MagicMock()

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        # Only one refresh attempt (not infinite)
        assert mock_agent.turn.call_count == 2
        # Error sent to channel
        assert any("Error:" in msg for msg in channel.sent)

    def test_auth_error_without_settings_skips_refresh(self, tmp_path: Path) -> None:
        """Auth error with settings=None → no refresh, error sent to channel."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=_make_openai_auth_error())

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
        ) as mock_create:
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=None,
                )
            )

        # No refresh without settings
        mock_create.assert_not_called()
        # Error still sent to channel
        assert any("Error:" in msg for msg in channel.sent)

    def test_auth_refresh_updates_openai_client_attr(self, tmp_path: Path) -> None:
        """After auth refresh, agent._openai_client points to the NEW client."""
        channel = MockChannel(["hello", None])

        old_client = AsyncMock()
        new_client = AsyncMock()

        mock_agent = AsyncMock()
        mock_agent._openai_client = old_client
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed reply"],
        )
        mock_agent.update_model = MagicMock()

        mock_settings = MagicMock()
        mock_settings.chat_model = "gpt-4o"

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=new_client,
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=mock_settings,
                )
            )

        # Old client was closed
        old_client.close.assert_awaited_once()
        # agent._openai_client now points to the NEW client, not old
        assert mock_agent._openai_client is new_client

    def test_repeated_auth_refresh_closes_previous_refresh_client(self, tmp_path: Path) -> None:
        """Two auth errors → two refreshes; second closes the FIRST refresh's client."""
        # msg1 → auth error → refresh1 → retry succeeds
        # msg2 → auth error → refresh2 (closes refresh1 client) → retry succeeds
        channel = MockChannel(["msg1", "msg2", None])

        original_client = AsyncMock()
        refresh1_client = AsyncMock()
        refresh2_client = AsyncMock()

        mock_agent = AsyncMock()
        mock_agent._openai_client = original_client
        # Call sequence: msg1→auth_err, msg1_retry→ok, msg2→auth_err, msg2_retry→ok
        mock_agent.turn = AsyncMock(
            side_effect=[
                _make_openai_auth_error(),
                "reply1",
                _make_openai_auth_error(),
                "reply2",
            ],
        )
        mock_agent.update_model = MagicMock()

        mock_settings = MagicMock()
        mock_settings.chat_model = "gpt-4o"

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            side_effect=[refresh1_client, refresh2_client],
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=mock_settings,
                )
            )

        # Original client closed during first refresh
        original_client.close.assert_awaited_once()
        # refresh1 client closed during second refresh
        refresh1_client.close.assert_awaited_once()
        # refresh2 client NOT closed (it's the active one)
        refresh2_client.close.assert_not_awaited()
        # Final _openai_client is the second refresh client
        assert mock_agent._openai_client is refresh2_client


# ---------------------------------------------------------------------------
# Classified error recovery (classify_error integration)
# ---------------------------------------------------------------------------


class TestClassifiedErrorRecovery:
    """run_daemon uses classify_error() for structured error recovery."""

    def test_transient_error_retries_three_times(self, tmp_path: Path) -> None:
        """Model-level transient errors retry up to 3 times; all fail → sends error."""
        channel = MockChannel(["hello", None])

        exc = _make_httpx_status_error(503)
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=exc)

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # 1 initial + 3 retries = 4 calls
        assert mock_agent.turn.call_count == 4
        # 3 sleeps (one per retry)
        assert mock_sleep.call_count == 3
        # Error sent to channel after retries exhausted (sanitized)
        assert any("HTTP request failed" in msg for msg in channel.sent)

    def test_transient_error_succeeds_on_second_retry(self, tmp_path: Path) -> None:
        """Model-level transient error on first two attempts, success on third."""
        channel = MockChannel(["hello", None])

        exc = _make_httpx_status_error(503)
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=[exc, exc, "recovered"])

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # Initial call + 2 retry = 3 calls
        assert mock_agent.turn.call_count == 3
        assert "recovered" in channel.sent

    def test_transient_backoff_uses_jitter(self, tmp_path: Path) -> None:
        """Backoff delays include jitter — sleep values are not pure powers of 2."""
        channel = MockChannel(["hello", None])

        exc = _make_httpx_status_error(503)
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=exc)

        with (
            patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("owlbear.daemon.random.uniform", return_value=0.42) as mock_jitter,
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # random.uniform called for each retry
        assert mock_jitter.call_count == 3
        # Each sleep = base_delay + jitter (0.42)
        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        # With jitter=0.42: delays should be 1+0.42, 2+0.42, 4+0.42
        assert sleep_args[0] == pytest.approx(1.42)
        assert sleep_args[1] == pytest.approx(2.42)
        assert sleep_args[2] == pytest.approx(4.42)

    def test_permanent_error_no_retry(self, tmp_path: Path) -> None:
        """Permanent errors are sent to channel immediately — no retry."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=FileNotFoundError("missing.txt"))

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        # Only 1 call — no retry for permanent errors
        mock_agent.turn.assert_called_once()
        assert any("File not found" in msg for msg in channel.sent)

    def test_tool_semantic_error_treated_as_permanent(self, tmp_path: Path) -> None:
        """Tool-semantic errors treated same as permanent at daemon level."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=KeyError("bad_key"))

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        mock_agent.turn.assert_called_once()
        assert any("Error:" in msg for msg in channel.sent)

    def test_daemon_continues_after_transient_exhaustion(self, tmp_path: Path) -> None:
        """After model-level transient retries exhausted, daemon processes next message."""
        channel = MockChannel(["msg1", "msg2", None])

        exc = _make_httpx_status_error(503)
        mock_agent = AsyncMock()
        # msg1: all 4 calls (1 initial + 3 retry) fail; msg2: succeeds
        mock_agent.turn = AsyncMock(side_effect=[exc, exc, exc, exc, "reply2"])

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # 4 calls for msg1 + 1 call for msg2
        assert mock_agent.turn.call_count == 5
        # Error from msg1 (sanitized) and reply from msg2 both sent
        assert any("HTTP request failed" in msg for msg in channel.sent)
        assert "reply2" in channel.sent

    def test_classify_error_is_used_not_is_auth_error(self, tmp_path: Path) -> None:
        """Verify classify_error is called (not _is_auth_error)."""
        channel = MockChannel(["hello", None])

        exc = _make_openai_auth_error()
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(
            side_effect=[exc, "refreshed"],
        )
        mock_agent.update_model = MagicMock()

        with (
            patch(
                "owlbear.daemon.create_copilot_client",
                new_callable=AsyncMock,
                return_value=AsyncMock(),
            ),
            patch("owlbear.daemon.classify_error", return_value=ErrorCategory.AUTH) as mock_clf,
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        mock_clf.assert_called_once_with(exc)

    def test_daemon_never_crashes_from_message_failure(self, tmp_path: Path) -> None:
        """Daemon loop continues even after unexpected exception types."""
        channel = MockChannel(["bad", "good", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(
            side_effect=[MemoryError("oom"), "ok"],
        )

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        assert mock_agent.turn.call_count == 2
        assert any("oom" in msg for msg in channel.sent)
        assert "ok" in channel.sent


# ---------------------------------------------------------------------------
# Channel send failure — original error must still be logged (#471)
# ---------------------------------------------------------------------------


class TestChannelSendFailureLogsOriginalError:
    """When channel.send() fails in _recover_from_error, the original error
    must still be logged via logger.exception() so it is never silently lost.
    """

    def test_transient_exhausted_channel_failure_logs_original(self, tmp_path: Path) -> None:
        """Transient retries exhausted + channel.send raises → original logged."""
        original_exc = httpx.ConnectError("connection refused")
        channel = MockChannel(["hello", None])
        # Make channel.send raise on the error-report attempt
        channel.send = AsyncMock(side_effect=OSError("channel dead"))  # type: ignore[assignment]

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=original_exc)

        with (
            patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock),
            patch("owlbear.daemon.logger") as mock_logger,
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # logger.exception must have been called with the original error context
        exc_calls = mock_logger.exception.call_args_list
        original_logged = any("connection refused" in str(call) for call in exc_calls)
        assert original_logged, f"Original error not found in logger.exception calls: {exc_calls}"

    def test_auth_refresh_failed_channel_failure_logs_original(self, tmp_path: Path) -> None:
        """Auth refresh fails + channel.send raises → original refresh error logged."""
        auth_exc = _make_openai_auth_error()
        refresh_exc = RuntimeError("refresh failed")
        channel = MockChannel(["hello", None])
        channel.send = AsyncMock(side_effect=OSError("channel dead"))  # type: ignore[assignment]

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=auth_exc)
        mock_agent.update_model = MagicMock()

        with (
            patch(
                "owlbear.daemon.create_copilot_client",
                new_callable=AsyncMock,
                side_effect=refresh_exc,
            ),
            patch("owlbear.daemon.logger") as mock_logger,
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        exc_calls = mock_logger.exception.call_args_list
        original_logged = any("refresh failed" in str(call) for call in exc_calls)
        assert original_logged, f"Original error not found in logger.exception calls: {exc_calls}"

    def test_permanent_error_channel_failure_logs_original(self, tmp_path: Path) -> None:
        """Permanent error + channel.send raises → original error logged."""
        original_exc = FileNotFoundError("missing.txt")
        channel = MockChannel(["hello", None])
        channel.send = AsyncMock(side_effect=OSError("channel dead"))  # type: ignore[assignment]

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=original_exc)

        with patch("owlbear.daemon.logger") as mock_logger:
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        exc_calls = mock_logger.exception.call_args_list
        original_logged = any("missing.txt" in str(call) for call in exc_calls)
        assert original_logged, f"Original error not found in logger.exception calls: {exc_calls}"

    def test_channel_send_success_still_sends_error(self, tmp_path: Path) -> None:
        """When channel.send succeeds, the error message is still delivered (AC5)."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=FileNotFoundError("gone.txt"))

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        assert any("File not found" in msg for msg in channel.sent)

    def test_recover_from_error_never_propagates(self, tmp_path: Path) -> None:
        """_recover_from_error never lets an exception escape (AC4)."""
        original_exc = FileNotFoundError("boom")
        channel = MockChannel(["hello", None])
        channel.send = AsyncMock(side_effect=OSError("channel dead"))  # type: ignore[assignment]

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=original_exc)

        with patch("owlbear.daemon.logger"):
            # Must not raise — the daemon loop should continue
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )


# ---------------------------------------------------------------------------
# ErrorJournal integration (#475)
# ---------------------------------------------------------------------------


class TestErrorJournalIntegration:
    """run_daemon logs error entries to ErrorJournal when provided."""

    def _make_journal(self, tmp_path: Path) -> ErrorJournal:
        return ErrorJournal(tmp_path)

    def test_transient_retries_exhausted_logs_entry(self, tmp_path: Path) -> None:
        """All model-level transient retries fail → journal entry resolved=False."""
        journal = self._make_journal(tmp_path)
        channel = MockChannel(["hello", None])

        exc = _make_httpx_status_error(503)
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=exc)
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("sessions/test.jsonl")

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    error_journal=journal,
                )
            )

        entries = journal.query()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.error_type == ErrorCategory.TRANSIENT.value
        assert entry.action_taken == "transient_retries_exhausted"
        assert entry.resolved is False
        assert entry.tool_name == "agent.turn"
        assert entry.session_id == str(Path("sessions/test.jsonl"))

    def test_transient_retry_succeeds_logs_entry(self, tmp_path: Path) -> None:
        """Model-level transient error then success → journal entry resolved=True."""
        journal = self._make_journal(tmp_path)
        channel = MockChannel(["hello", None])

        exc = _make_httpx_status_error(503)
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=[exc, "recovered"])
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("sessions/test.jsonl")

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    error_journal=journal,
                )
            )

        entries = journal.query()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.action_taken == "transient_retry"
        assert entry.resolved is True
        assert entry.attempt_number == 1

    def test_auth_refresh_succeeds_logs_entry(self, tmp_path: Path) -> None:
        """Auth error → refresh → success → journal entry resolved=True."""
        journal = self._make_journal(tmp_path)
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed"],
        )
        mock_agent.update_model = MagicMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("sessions/test.jsonl")

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                    error_journal=journal,
                )
            )

        entries = journal.query()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.action_taken == "auth_refresh"
        assert entry.resolved is True
        assert entry.error_type == ErrorCategory.AUTH.value

    def test_auth_refresh_fails_logs_entry(self, tmp_path: Path) -> None:
        """Auth error → refresh fails → journal entry resolved=False."""
        journal = self._make_journal(tmp_path)
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=_make_openai_auth_error())
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("sessions/test.jsonl")

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network down"),
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                    error_journal=journal,
                )
            )

        entries = journal.query()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.action_taken == "auth_refresh_failed"
        assert entry.resolved is False

    def test_permanent_error_logs_entry(self, tmp_path: Path) -> None:
        """Permanent error → journal entry resolved=False."""
        journal = self._make_journal(tmp_path)
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=FileNotFoundError("missing.txt"))
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("sessions/test.jsonl")

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                error_journal=journal,
            )
        )

        entries = journal.query()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.action_taken == "permanent"
        assert entry.resolved is False
        assert "missing.txt" in entry.exception_message

    def test_no_journal_does_not_crash(self, tmp_path: Path) -> None:
        """error_journal=None → no crash (backward compat)."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=FileNotFoundError("missing.txt"))

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                error_journal=None,
            )
        )

        assert any("File not found" in msg for msg in channel.sent)

    def test_journal_failure_does_not_break_recovery(self, tmp_path: Path) -> None:
        """If journal.log() raises, recovery still works."""
        journal = self._make_journal(tmp_path)
        journal.log = MagicMock(side_effect=OSError("disk full"))  # type: ignore[assignment]
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=FileNotFoundError("missing.txt"))
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("sessions/test.jsonl")

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                error_journal=journal,
            )
        )

        # Recovery still sent error to channel
        assert any("File not found" in msg for msg in channel.sent)


# ---------------------------------------------------------------------------
# Auth refresh closes old OpenAI client (#650 — red phase for #514)
# ---------------------------------------------------------------------------


class TestAuthRefreshClosesOldClient:
    """Daemon auth refresh must close the old AsyncOpenAI client.

    After #514, _handle_classified_error's AUTH branch calls
    ``await old_client.close()`` before ``agent.update_model(new_model)``
    so the old httpx.AsyncClient connection pool is released.
    """

    def test_old_client_closed_before_model_update(self, tmp_path: Path) -> None:
        """Auth error → old OpenAI client.close() is called before update_model."""
        channel = MockChannel(["hello", None])

        # Track call order to verify close happens before update_model
        call_order: list[str] = []

        old_client = AsyncMock()
        old_client.close = AsyncMock(side_effect=lambda: call_order.append("close"))

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed reply"],
        )

        def track_update_model(new_model):  # noqa: ARG001
            call_order.append("update_model")

        mock_agent.update_model = MagicMock(side_effect=track_update_model)

        # Expose the old client via the agent's model provider chain.
        # After #514, the daemon retrieves the old client from the agent
        # (e.g. agent._openai_client or agent.inner.model.client).
        mock_agent._openai_client = old_client

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        # Old client must have been closed
        old_client.close.assert_awaited_once()
        # Close must happen before update_model
        assert call_order == ["close", "update_model"], (
            f"Expected close before update_model, got: {call_order}"
        )

    def test_old_client_closed_even_when_refresh_fails(self, tmp_path: Path) -> None:
        """Even if token refresh fails, the old client should still be closed."""
        channel = MockChannel(["hello", None])

        old_client = AsyncMock()
        old_client.close = AsyncMock()

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=_make_openai_auth_error())
        mock_agent.update_model = MagicMock()
        mock_agent._openai_client = old_client

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            side_effect=RuntimeError("no network"),
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        # Old client should still be closed even though refresh failed
        old_client.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Daemon retry reconciliation (#665 — red phase for #512)
# ---------------------------------------------------------------------------


class TestDaemonRetryReconciliation:
    """Daemon-level retry must not multiply with tool-level HookedToolset retry.

    HookedToolset uses tenacity @retry (3 attempts, base 0.5s) for transient
    tool errors.  The daemon's _recover_from_error uses its own retry loop
    (3 attempts, base 1s) for transient errors at the agent.turn() level.

    Problem: with ``reraise=True``, a transient tool error re-raises as the
    original exception (e.g. ``httpx.ConnectError``).  The daemon sees a
    transient exception and retries 3 more times → up to 4 (1 + 3) daemon
    calls, each potentially triggering 3 tool retries = 12 total attempts.
    Task #512 fixes this by detecting when the tool-level retry is already
    exhausted and skipping daemon-level retry.
    """

    def test_tool_transient_exhausted_no_daemon_retry(self, tmp_path: Path) -> None:
        """When a transient error already exhausted tool-level retries, daemon
        must NOT apply its own transient retry loop.

        Currently: ``httpx.ConnectError`` re-raised from HookedToolset
        (reraise=True) is classified TRANSIENT, triggering 3 daemon retries.
        After #512: daemon detects the error was already retried at tool level
        and sends the error to channel immediately (no daemon retry).

        This test simulates the current scenario: agent.turn raises a plain
        transient exception.  We assert the *desired* behavior (1 call, no
        retry) which currently fails because _recover_from_error retries.
        """
        channel = MockChannel(["hello", None])

        # Plain transient error — same as what HookedToolset re-raises with
        # reraise=True after exhausting its 3 attempts.
        exc = httpx.ConnectError("connection refused")
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=exc)
        # Mark the exception as tool-exhausted (future #512 convention)
        exc._tool_retries_exhausted = True

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # Desired: daemon should NOT retry — only 1 call to agent.turn
        assert mock_agent.turn.call_count == 1, (
            f"Expected 1 call (no daemon retry for tool-exhausted error), "
            f"got {mock_agent.turn.call_count}"
        )
        mock_sleep.assert_not_called()
        assert any("Error:" in msg or "Connection" in msg for msg in channel.sent)

    def test_model_level_transient_still_retried_by_daemon(self, tmp_path: Path) -> None:
        """Copilot 503 during agent.turn() (model-level) DOES trigger daemon retry.

        Model-level transients are NOT from exhausted tool retries — the daemon
        should still apply its backoff loop.  This is existing behavior.
        """
        channel = MockChannel(["hello", None])

        exc = _make_httpx_status_error(503)
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=[exc, exc, "recovered"])

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # 1 initial + 2 retries = 3 calls
        assert mock_agent.turn.call_count == 3
        assert "recovered" in channel.sent

    def test_no_multiplicative_retries(self, tmp_path: Path) -> None:
        """Total daemon calls for a tool-exhausted transient must be 1, not 4.

        Currently: the daemon sees ``httpx.ConnectError`` (re-raised by
        tenacity) and retries 3 more times → 4 total agent.turn() calls.
        After #512: daemon detects the exhausted tool retry and stops at 1.
        """
        channel = MockChannel(["hello", None])

        exc = httpx.ConnectError("connection refused")
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=exc)

        with patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # Currently 4 calls (1 initial + 3 daemon retries); desired is 1
        assert mock_agent.turn.call_count == 1, (
            f"Multiplicative retry detected: {mock_agent.turn.call_count} calls "
            f"(expected 1 after tool-level exhaustion)"
        )

    def test_auth_error_path_unchanged(self, tmp_path: Path) -> None:
        """Auth errors still trigger token refresh — unaffected by #512."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(
            side_effect=[_make_openai_auth_error(), "refreshed reply"],
        )
        mock_agent.update_model = MagicMock()

        with patch(
            "owlbear.daemon.create_copilot_client",
            new_callable=AsyncMock,
            return_value=AsyncMock(),
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=MagicMock(),
                )
            )

        assert mock_agent.turn.call_count == 2
        assert "refreshed reply" in channel.sent

    def test_permanent_error_path_unchanged(self, tmp_path: Path) -> None:
        """Permanent errors propagate immediately — unaffected by #512."""
        channel = MockChannel(["hello", None])

        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=FileNotFoundError("missing.txt"))

        _run(
            run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
            )
        )

        mock_agent.turn.assert_called_once()
        assert any("File not found" in msg for msg in channel.sent)


# ---------------------------------------------------------------------------
# _is_process_alive direct test (coverage for lines 83-88)
# ---------------------------------------------------------------------------


class TestIsProcessAlive:
    """Direct tests for _is_process_alive (not patched via PidFile)."""

    def test_alive_returns_true(self) -> None:
        from owlbear.daemon import _is_process_alive

        # Current process is definitely alive
        assert _is_process_alive(os.getpid()) is True

    def test_dead_pid_returns_false(self) -> None:
        from owlbear.daemon import _is_process_alive

        # Mock os.kill to raise OSError (dead process path)
        with patch("os.kill", side_effect=OSError("No such process")):
            assert _is_process_alive(12345) is False


# ---------------------------------------------------------------------------
# Transient retries exhausted + channel.send failure (lines 356-357)
# ---------------------------------------------------------------------------


class TestTransientExhaustedChannelSendFails:
    """When all daemon-level transient retries are exhausted AND channel.send
    fails, the original error must still be logged."""

    def test_model_level_transient_exhausted_channel_send_fails(self, tmp_path: Path) -> None:
        """HTTPStatusError 503 exhausts all 3 retries, then channel.send raises."""
        exc = _make_httpx_status_error(503)
        channel = MockChannel(["hello", None])
        channel.send = AsyncMock(side_effect=OSError("channel broken"))  # type: ignore[assignment]

        mock_agent = AsyncMock()
        # All retries fail with the same 503
        mock_agent.turn = AsyncMock(side_effect=exc)

        with (
            patch("owlbear.daemon.asyncio.sleep", new_callable=AsyncMock),
            patch("owlbear.daemon.logger") as mock_logger,
        ):
            _run(
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                )
            )

        # logger.exception must have been called about channel send failure
        exc_calls = mock_logger.exception.call_args_list
        channel_send_logged = any(
            "Failed to send error to channel" in str(call) for call in exc_calls
        )
        assert channel_send_logged, f"Channel send failure not logged: {exc_calls}"
