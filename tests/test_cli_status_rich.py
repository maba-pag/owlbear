"""RED tests for enhanced bearclaw status rich.Panel display (#643).

These tests describe the TARGET interface — rich.Panel output with styled
status, uptime, project, and detail fields.  They should FAIL against the
current typer.echo-based implementation.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bearclaw.cli import app
from bearclaw.commands.daemon import _daemon_status

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_settings(tmp_path: Path, **overrides: object) -> MagicMock:
    """Build a mock OwlBearSettings pointing at *tmp_path*."""
    s = MagicMock()
    s.config_dir = str(tmp_path)
    s.chat_model = overrides.get("chat_model", "gpt-4o")
    s.autonomous_mode = overrides.get("autonomous_mode", False)
    s.heartbeat_enabled = overrides.get("heartbeat_enabled", False)
    s.heartbeat_interval = overrides.get("heartbeat_interval", 1800)
    s.slack_channel_id = overrides.get("slack_channel_id")
    return s


# ---------------------------------------------------------------------------
# No PID file → Stopped (red border)
# ---------------------------------------------------------------------------


class TestStatusStopped:
    """When no PID file exists, the panel should say 'Stopped'."""

    def test_output_contains_stopped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with patch(
            "bearclaw.commands.daemon.OwlBearSettings",
            return_value=_mock_settings(tmp_path),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        assert "Stopped" in out


# ---------------------------------------------------------------------------
# PID alive → Running (green border) with uptime
# ---------------------------------------------------------------------------


class TestStatusRunning:
    """When the PID file exists and the process is alive."""

    def test_output_contains_running(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        # Set mtime ~1h 1m ago so uptime is computed from pid file mtime
        mtime = time.time() - 3661
        os.utime(pid_path, (mtime, mtime))
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        assert "Running" in out

    def test_output_contains_pid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        assert "42" in out

    def test_output_contains_uptime(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        # Set mtime 90s ago — uptime from pid file mtime
        mtime = time.time() - 90
        os.utime(pid_path, (mtime, mtime))
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        # Uptime should show a human-readable duration (not the em-dash placeholder)
        assert "Uptime" in out
        assert "0h 1m" in out

    def test_uptime_days_format(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        # Set mtime 1 day + 3 hours ago
        mtime = time.time() - (86400 + 10800)
        os.utime(pid_path, (mtime, mtime))
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        assert "1d 3h" in out


# ---------------------------------------------------------------------------
# PID stale → Stale (yellow border), no uptime
# ---------------------------------------------------------------------------


class TestStatusStale:
    """When the PID file exists but process is dead."""

    def test_output_contains_stale(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("99999")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=False),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        assert "Stale" in out

    def test_output_contains_pid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("99999")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=False),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        assert "99999" in out

    def test_output_no_uptime(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("99999")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=False),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        # Stale process should NOT report uptime
        assert "Uptime" not in out


# ---------------------------------------------------------------------------
# --detail flag shows config labels
# ---------------------------------------------------------------------------


class TestStatusDetail:
    """--detail flag should include Model, Autonomous, Heartbeat labels."""

    def test_detail_shows_model(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path, chat_model="claude-sonnet-4"),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            result = runner.invoke(app, ["status", "--detail"])
        assert result.exit_code == 0
        assert "Model" in result.output
        assert "claude-sonnet-4" in result.output

    def test_detail_shows_autonomous(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path, autonomous_mode=True),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            result = runner.invoke(app, ["status", "--detail"])
        assert result.exit_code == 0
        assert "Autonomous" in result.output

    def test_detail_shows_heartbeat(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path, heartbeat_enabled=True),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            result = runner.invoke(app, ["status", "--detail"])
        assert result.exit_code == 0
        assert "Heartbeat" in result.output

    def test_detail_shows_slack_channel(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path, slack_channel_id="C12345"),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            result = runner.invoke(app, ["status", "--detail"])
        assert result.exit_code == 0
        assert "Slack Channel" in result.output
        assert "C12345" in result.output

    def test_detail_shows_slack_channel_dash_when_none(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path, slack_channel_id=None),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            result = runner.invoke(app, ["status", "--detail"])
        assert result.exit_code == 0
        assert "Slack Channel" in result.output


# ---------------------------------------------------------------------------
# Active project display
# ---------------------------------------------------------------------------


class TestStatusProject:
    """Project name should appear in status output."""

    def test_active_project_shown(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("42")
        active_path = tmp_path / "active_project"
        active_path.write_text("my-cool-project", encoding="utf-8")
        with (
            patch(
                "bearclaw.commands.daemon.OwlBearSettings",
                return_value=_mock_settings(tmp_path),
            ),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        assert "my-cool-project" in out

    def test_no_active_project_shows_none(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # No active_project file → should display "None"
        with patch(
            "bearclaw.commands.daemon.OwlBearSettings",
            return_value=_mock_settings(tmp_path),
        ):
            _daemon_status()
        out = capsys.readouterr().out
        assert "None" in out


# ---------------------------------------------------------------------------
# CLI runner: bearclaw status exits 0
# ---------------------------------------------------------------------------


class TestStatusCliRunner:
    """CliRunner invocation of 'bearclaw status' returns exit code 0."""

    def test_cli_status_exits_zero(self, tmp_path: Path) -> None:
        with patch(
            "bearclaw.commands.daemon.OwlBearSettings",
            return_value=_mock_settings(tmp_path),
        ):
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
