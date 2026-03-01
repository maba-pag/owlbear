"""Tests for owlbear.core.progress — ProgressReporter periodic updates.

TDD red-phase tests for task #335.  The module ``owlbear.core.progress``
does not exist yet — all tests are expected to fail on import until the
implementation task (#336) is completed.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest
from owlbear.core.progress import ProgressReporter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeChannel:
    """Mock channel using asyncio.Queue to verify message cadence."""

    def __init__(self) -> None:
        self.messages: asyncio.Queue[str] = asyncio.Queue()
        self._send = AsyncMock(side_effect=self._enqueue)

    @property
    def name(self) -> str:
        return "fake"

    async def send(self, message: str) -> None:
        await self._send(message)

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        return None

    async def _enqueue(self, message: str) -> None:
        await self.messages.put(message)


class FailingChannel:
    """Channel whose send() always raises."""

    @property
    def name(self) -> str:
        return "failing"

    async def send(self, message: str) -> None:  # noqa: ARG002
        msg = "channel down"
        raise ConnectionError(msg)

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        return None


# ---------------------------------------------------------------------------
# on_tool_complete hook
# ---------------------------------------------------------------------------


class TestOnToolComplete:
    """Test on_tool_complete() hook callback increments counter + records tool."""

    def test_increments_tool_count(self) -> None:
        """on_tool_complete increments internal tool counter."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=30.0, detail="brief")
        assert reporter.tool_count == 0
        reporter.on_tool_complete({"tool_name": "read_file", "args": {}})
        assert reporter.tool_count == 1

    def test_records_last_tool_name(self) -> None:
        """on_tool_complete records the most recent tool name."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=30.0, detail="brief")
        reporter.on_tool_complete({"tool_name": "read_file", "args": {}})
        reporter.on_tool_complete({"tool_name": "run_command", "args": {}})
        assert reporter.last_tool == "run_command"

    def test_records_last_tool_args(self) -> None:
        """on_tool_complete records the most recent tool args."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=30.0, detail="detailed")
        reporter.on_tool_complete({"tool_name": "run_command", "args": {"command": "pytest"}})
        assert reporter.last_tool_args == {"command": "pytest"}

    def test_increments_multiple_calls(self) -> None:
        """Counter increments for each tool completion."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=30.0, detail="brief")
        for i in range(5):
            reporter.on_tool_complete({"tool_name": f"tool_{i}", "args": {}})
        assert reporter.tool_count == 5


# ---------------------------------------------------------------------------
# Brief format
# ---------------------------------------------------------------------------


class TestBriefFormat:
    """Test brief format: contains tool count, last tool name, elapsed time."""

    def test_contains_tool_count(self) -> None:
        """Brief message includes the number of tools called."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=30.0, detail="brief")
        for _ in range(3):
            reporter.on_tool_complete({"tool_name": "read_file", "args": {}})
        msg = reporter.format_message()
        assert "3" in msg

    def test_contains_last_tool_name(self) -> None:
        """Brief message includes the name of the last tool called."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=30.0, detail="brief")
        reporter.on_tool_complete({"tool_name": "run_command", "args": {}})
        msg = reporter.format_message()
        assert "run_command" in msg

    def test_contains_elapsed_time(self) -> None:
        """Brief message includes elapsed seconds."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=30.0, detail="brief")
        reporter.on_tool_complete({"tool_name": "read_file", "args": {}})
        # Patch the start time to simulate elapsed time
        with patch.object(reporter, "_start_time", reporter._start_time - 45.0):
            msg = reporter.format_message()
        assert "45" in msg or "45s" in msg


# ---------------------------------------------------------------------------
# Detailed format
# ---------------------------------------------------------------------------


class TestDetailedFormat:
    """Test detailed format: includes agent name, session id, tool args."""

    def test_includes_agent_name(self) -> None:
        """Detailed message includes agent_name when set."""
        ch = FakeChannel()
        reporter = ProgressReporter(
            channel=ch, interval=30.0, detail="detailed",
            agent_name="coder", session_id="abc123",
        )
        reporter.on_tool_complete({"tool_name": "read_file", "args": {"path": "x.py"}})
        msg = reporter.format_message()
        assert "coder" in msg

    def test_includes_session_id(self) -> None:
        """Detailed message includes session_id when set."""
        ch = FakeChannel()
        reporter = ProgressReporter(
            channel=ch, interval=30.0, detail="detailed",
            agent_name="coder", session_id="abc123",
        )
        reporter.on_tool_complete({"tool_name": "read_file", "args": {"path": "x.py"}})
        msg = reporter.format_message()
        assert "abc123" in msg

    def test_includes_tool_args(self) -> None:
        """Detailed message includes last tool arguments."""
        ch = FakeChannel()
        reporter = ProgressReporter(
            channel=ch, interval=30.0, detail="detailed",
        )
        reporter.on_tool_complete(
            {"tool_name": "run_command", "args": {"command": "pytest tests/"}},
        )
        msg = reporter.format_message()
        assert "pytest tests/" in msg


# ---------------------------------------------------------------------------
# Activity gate
# ---------------------------------------------------------------------------


class TestActivityGate:
    """Test activity gate: no update if no tools executed since last update."""

    @pytest.mark.asyncio
    async def test_no_update_when_idle(self) -> None:
        """Timer tick with no tool activity since last update sends nothing."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=0.05, detail="brief")
        # Start, but do NOT call on_tool_complete
        await reporter.start()
        # Wait enough for one tick
        await asyncio.sleep(0.15)
        await reporter.stop()
        # Channel should not have been called — no activity
        ch._send.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_sent_after_tool_activity(self) -> None:
        """Timer tick after tool activity sends an update."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=0.05, detail="brief")
        await reporter.start()
        reporter.on_tool_complete({"tool_name": "read_file", "args": {}})
        # Wait for at least one tick
        await asyncio.sleep(0.15)
        await reporter.stop()
        assert ch._send.call_count >= 1

    @pytest.mark.asyncio
    async def test_no_duplicate_update_without_new_activity(self) -> None:
        """After sending one update, no further updates without new tool activity."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=0.05, detail="brief")
        await reporter.start()
        reporter.on_tool_complete({"tool_name": "read_file", "args": {}})
        # Wait for first tick
        await asyncio.sleep(0.1)
        first_count = ch._send.call_count
        assert first_count >= 1
        # Wait for more ticks — no new activity
        await asyncio.sleep(0.15)
        await reporter.stop()
        # Should NOT have sent additional updates
        assert ch._send.call_count == first_count


# ---------------------------------------------------------------------------
# Start / Stop lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Test start()/stop() lifecycle: timer starts on start(), cancelled on stop()."""

    @pytest.mark.asyncio
    async def test_start_creates_timer_task(self) -> None:
        """start() spawns a background asyncio task."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=1.0, detail="brief")
        await reporter.start()
        assert reporter._timer_task is not None
        assert not reporter._timer_task.done()
        await reporter.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_timer_task(self) -> None:
        """stop() cancels the background timer task."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=1.0, detail="brief")
        await reporter.start()
        task = reporter._timer_task
        await reporter.stop()
        assert task is not None
        assert task.done()

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(self) -> None:
        """Calling stop() multiple times does not raise."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=1.0, detail="brief")
        await reporter.start()
        await reporter.stop()
        # Second stop — should be no-op
        await reporter.stop()

    @pytest.mark.asyncio
    async def test_stop_before_start_is_noop(self) -> None:
        """Calling stop() without start() does not raise."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=1.0, detail="brief")
        await reporter.stop()  # Should not raise


# ---------------------------------------------------------------------------
# Channel send failure
# ---------------------------------------------------------------------------


class TestChannelSendFailure:
    """Test channel.send() failure logged and swallowed."""

    @pytest.mark.asyncio
    async def test_send_error_logged_and_swallowed(self, caplog: pytest.LogCaptureFixture) -> None:
        """If channel.send() raises, the error is logged but does not crash."""
        ch = FailingChannel()
        reporter = ProgressReporter(channel=ch, interval=0.05, detail="brief")
        await reporter.start()
        reporter.on_tool_complete({"tool_name": "read_file", "args": {}})
        # Wait for a tick to trigger send
        await asyncio.sleep(0.15)
        await reporter.stop()
        # Should have logged the error, not raised
        assert any(
            "channel down" in record.message or "send" in record.message.lower()
            for record in caplog.records
            if record.levelno >= logging.WARNING
        )


# ---------------------------------------------------------------------------
# Message cadence via Queue
# ---------------------------------------------------------------------------


class TestMessageCadence:
    """Mock channel with asyncio.Queue to verify message cadence."""

    @pytest.mark.asyncio
    async def test_messages_arrive_at_interval(self) -> None:
        """Updates should arrive roughly at the configured interval."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=0.05, detail="brief")
        await reporter.start()
        # Generate continuous activity
        for i in range(10):
            reporter.on_tool_complete({"tool_name": f"tool_{i}", "args": {}})
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.1)
        await reporter.stop()
        # Should have received at least 2 messages given ~0.3s window with 0.05s interval
        assert ch.messages.qsize() >= 2

    @pytest.mark.asyncio
    async def test_update_message_format_is_string(self) -> None:
        """Each message sent to the channel is a non-empty string."""
        ch = FakeChannel()
        reporter = ProgressReporter(channel=ch, interval=0.05, detail="brief")
        await reporter.start()
        reporter.on_tool_complete({"tool_name": "read_file", "args": {}})
        await asyncio.sleep(0.15)
        await reporter.stop()
        assert ch.messages.qsize() >= 1
        msg = ch.messages.get_nowait()
        assert isinstance(msg, str)
        assert len(msg) > 0
