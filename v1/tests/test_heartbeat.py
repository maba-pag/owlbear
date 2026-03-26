"""Tests for HeartbeatRunner — proactive agent wakeups via HEARTBEAT.md.

Covers: timer tick, HEARTBEAT_OK suppression, non-OK channel delivery,
active-hours skip, overnight wrap-around, missing file, shutdown mid-sleep,
exception resilience, config validation, disabled-config guard.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from owlbear.heartbeat import HeartbeatRunner, _is_active_hour

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_runner(  # noqa: PLR0913
    *,
    agent: AsyncMock | None = None,
    channel: AsyncMock | None = None,
    heartbeat_path: Path | None = None,
    interval: float = 0.05,
    active_hours: tuple[int, int] = (0, 24),
    shutdown_event: asyncio.Event | None = None,
) -> tuple[HeartbeatRunner, asyncio.Event]:
    """Build a HeartbeatRunner with sensible defaults for testing."""
    if agent is None:
        agent = AsyncMock()
        agent.turn = AsyncMock(return_value="HEARTBEAT_OK")
    if channel is None:
        channel = AsyncMock()
        channel.send = AsyncMock()
    if shutdown_event is None:
        shutdown_event = asyncio.Event()
    runner = HeartbeatRunner(
        agent=agent,
        channel=channel,
        interval_seconds=interval,
        active_hours=active_hours,
        shutdown_event=shutdown_event,
        heartbeat_path=heartbeat_path or Path("HEARTBEAT.md"),
    )
    return runner, shutdown_event


# ---------------------------------------------------------------------------
# Timer tick calls agent.turn
# ---------------------------------------------------------------------------


class TestHeartbeatTick:
    """HeartbeatRunner reads HEARTBEAT.md and calls agent.turn()."""

    async def test_heartbeat_tick_calls_agent_turn(self, tmp_path: Path) -> None:
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("- [ ] Check stale tasks\n")

        agent = AsyncMock()
        agent.turn = AsyncMock(return_value="HEARTBEAT_OK")

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            heartbeat_path=hb_file,
            shutdown_event=shutdown,
        )

        async def _stop() -> None:
            await asyncio.sleep(0.02)
            shutdown.set()

        await asyncio.gather(runner.run(), _stop())
        agent.turn.assert_called_once_with("- [ ] Check stale tasks\n")


# ---------------------------------------------------------------------------
# HEARTBEAT_OK suppresses channel.send
# ---------------------------------------------------------------------------


class TestHeartbeatOkSuppression:
    """When agent returns HEARTBEAT_OK, channel.send() must NOT be called."""

    async def test_heartbeat_ok_suppresses_channel_send(self, tmp_path: Path) -> None:
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("check tasks\n")

        agent = AsyncMock()
        agent.turn = AsyncMock(return_value="All clear — HEARTBEAT_OK")
        channel = AsyncMock()
        channel.send = AsyncMock()

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            channel=channel,
            heartbeat_path=hb_file,
            shutdown_event=shutdown,
        )

        async def _stop() -> None:
            await asyncio.sleep(0.02)
            shutdown.set()

        await asyncio.gather(runner.run(), _stop())
        channel.send.assert_not_called()


# ---------------------------------------------------------------------------
# Non-OK response sends to channel
# ---------------------------------------------------------------------------


class TestHeartbeatNonOk:
    """When agent returns findings (no HEARTBEAT_OK), channel.send() called."""

    async def test_heartbeat_non_ok_sends_to_channel(self, tmp_path: Path) -> None:
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("check tasks\n")

        findings = "Found 3 stale tasks in backlog"
        agent = AsyncMock()
        agent.turn = AsyncMock(return_value=findings)
        channel = AsyncMock()
        channel.send = AsyncMock()

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            channel=channel,
            heartbeat_path=hb_file,
            shutdown_event=shutdown,
        )

        async def _stop() -> None:
            await asyncio.sleep(0.02)
            shutdown.set()

        await asyncio.gather(runner.run(), _stop())
        channel.send.assert_called_once_with(findings)


# ---------------------------------------------------------------------------
# Active hours — skip when outside window
# ---------------------------------------------------------------------------


class TestActiveHoursSkip:
    """agent.turn() NOT called when current UTC hour is outside active_hours."""

    async def test_heartbeat_active_hours_skip(self, tmp_path: Path) -> None:
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("check tasks\n")

        agent = AsyncMock()
        agent.turn = AsyncMock(return_value="HEARTBEAT_OK")

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            heartbeat_path=hb_file,
            active_hours=(8, 22),
            shutdown_event=shutdown,
        )

        # Hour 3 is outside (8, 22)
        with patch("owlbear.heartbeat._utc_hour", return_value=3):

            async def _stop() -> None:
                await asyncio.sleep(0.02)
                shutdown.set()

            await asyncio.gather(runner.run(), _stop())

        agent.turn.assert_not_called()


# ---------------------------------------------------------------------------
# Active hours — wrap-around (overnight window)
# ---------------------------------------------------------------------------


class TestActiveHoursWraparound:
    """active_hours=(22, 6) means overnight: 22-23, 0-5 are inside."""

    async def test_hour_inside_overnight_window(self, tmp_path: Path) -> None:
        """Hour 2 is inside (22, 6) window — agent.turn() should be called."""
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("- [ ] Nightly review\n")

        agent = AsyncMock()
        agent.turn = AsyncMock(return_value="HEARTBEAT_OK")

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            heartbeat_path=hb_file,
            active_hours=(22, 6),
            shutdown_event=shutdown,
        )

        with patch("owlbear.heartbeat._utc_hour", return_value=2):

            async def _stop() -> None:
                await asyncio.sleep(0.02)
                shutdown.set()

            await asyncio.gather(runner.run(), _stop())

        agent.turn.assert_called_once()

    async def test_hour_outside_overnight_window(self, tmp_path: Path) -> None:
        """Hour 10 is outside (22, 6) window — agent.turn() NOT called."""
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("- [ ] Nightly review\n")

        agent = AsyncMock()
        agent.turn = AsyncMock(return_value="HEARTBEAT_OK")

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            heartbeat_path=hb_file,
            active_hours=(22, 6),
            shutdown_event=shutdown,
        )

        with patch("owlbear.heartbeat._utc_hour", return_value=10):

            async def _stop() -> None:
                await asyncio.sleep(0.02)
                shutdown.set()

            await asyncio.gather(runner.run(), _stop())

        agent.turn.assert_not_called()

    def test_is_active_hour_normal_range(self) -> None:
        """_is_active_hour for non-wrapping ranges."""
        assert _is_active_hour(10, (8, 22)) is True
        assert _is_active_hour(3, (8, 22)) is False
        assert _is_active_hour(8, (8, 22)) is True
        assert _is_active_hour(22, (8, 22)) is False

    def test_is_active_hour_overnight(self) -> None:
        """_is_active_hour for overnight wrap-around."""
        assert _is_active_hour(2, (22, 6)) is True
        assert _is_active_hour(23, (22, 6)) is True
        assert _is_active_hour(10, (22, 6)) is False
        assert _is_active_hour(6, (22, 6)) is False


# ---------------------------------------------------------------------------
# Missing HEARTBEAT.md — graceful skip
# ---------------------------------------------------------------------------


class TestMissingFile:
    """Missing HEARTBEAT.md should skip tick without crashing."""

    async def test_heartbeat_missing_file_skips(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "HEARTBEAT.md"
        assert not nonexistent.exists()

        agent = AsyncMock()
        agent.turn = AsyncMock(return_value="HEARTBEAT_OK")

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            heartbeat_path=nonexistent,
            shutdown_event=shutdown,
        )

        async def _stop() -> None:
            await asyncio.sleep(0.02)
            shutdown.set()

        await asyncio.gather(runner.run(), _stop())
        agent.turn.assert_not_called()


# ---------------------------------------------------------------------------
# Shutdown mid-sleep — clean exit via wait_for pattern
# ---------------------------------------------------------------------------


class TestShutdownMidSleep:
    """Setting shutdown_event during sleep causes clean exit."""

    async def test_heartbeat_shutdown_mid_sleep(self, tmp_path: Path) -> None:
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("check tasks\n")

        agent = AsyncMock()
        agent.turn = AsyncMock(return_value="HEARTBEAT_OK")

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            heartbeat_path=hb_file,
            interval=3600,
            shutdown_event=shutdown,
        )

        async def _trigger() -> None:
            await asyncio.sleep(0.05)
            shutdown.set()

        # Must complete without TimeoutError — shutdown interrupted the sleep
        await asyncio.wait_for(
            asyncio.gather(runner.run(), _trigger()),
            timeout=2.0,
        )


# ---------------------------------------------------------------------------
# Exception in agent.turn() — log and continue
# ---------------------------------------------------------------------------


class TestAgentException:
    """agent.turn() raising should be logged; runner continues next tick."""

    async def test_heartbeat_agent_exception_continues(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        hb_file = tmp_path / "HEARTBEAT.md"
        hb_file.write_text("check tasks\n")

        agent = AsyncMock()
        agent.turn = AsyncMock(side_effect=[RuntimeError("boom"), "HEARTBEAT_OK"])
        channel = AsyncMock()
        channel.send = AsyncMock()

        shutdown = asyncio.Event()
        runner, _ = _make_runner(
            agent=agent,
            channel=channel,
            heartbeat_path=hb_file,
            shutdown_event=shutdown,
        )

        async def _stop() -> None:
            await asyncio.sleep(0.12)
            shutdown.set()

        with caplog.at_level(logging.ERROR):
            await asyncio.gather(runner.run(), _stop())

        assert agent.turn.call_count >= 2
        assert any("Heartbeat agent.turn() failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


class TestHeartbeatConfig:
    """Config field validation for heartbeat settings."""

    def test_heartbeat_defaults(self) -> None:
        from owlbear.config import OwlBearSettings

        s = OwlBearSettings()
        assert s.heartbeat_enabled is False
        assert s.heartbeat_interval == 1800
        assert s.heartbeat_active_hours == (8, 22)

    def test_heartbeat_interval_positive(self) -> None:
        from owlbear.config import OwlBearSettings

        with pytest.raises(ValueError, match="heartbeat_interval"):
            OwlBearSettings(heartbeat_interval=0)

    def test_heartbeat_interval_negative(self) -> None:
        from owlbear.config import OwlBearSettings

        with pytest.raises(ValueError, match="heartbeat_interval"):
            OwlBearSettings(heartbeat_interval=-10)
