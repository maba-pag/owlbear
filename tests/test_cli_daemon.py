"""Tests for BearClaw daemon CLI helpers — stop, status, PID management."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bearclaw.cli import app
from bearclaw.commands.daemon import (
    _daemon_status,
    _daemon_stop,
    _get_config_dir,
    _poll_pid_removal,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# _poll_pid_removal
# ---------------------------------------------------------------------------


class TestPollPidRemoval:
    """Unit tests for _poll_pid_removal."""

    def test_no_file_returns_true_immediately(self, tmp_path: Path) -> None:
        missing = tmp_path / "missing.pid"
        assert _poll_pid_removal(missing, timeout=0.5) is True

    def test_file_exists_returns_false_on_timeout(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("12345")
        assert _poll_pid_removal(pid_path, timeout=0.3) is False

    def test_file_removed_mid_poll_returns_true(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("12345")

        call_count = 0
        original_exists = pid_path.exists

        def _fake_exists() -> bool:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                pid_path.unlink(missing_ok=True)
            return original_exists()

        with patch.object(type(pid_path), "exists", side_effect=_fake_exists):
            assert _poll_pid_removal(pid_path, timeout=5.0) is True


# ---------------------------------------------------------------------------
# _get_config_dir
# ---------------------------------------------------------------------------


class TestGetConfigDir:
    """Unit test for _get_config_dir."""

    def test_returns_settings_config_dir(self) -> None:
        mock_settings = MagicMock()
        mock_settings.config_dir = "/fake/.owlbear"
        with patch("bearclaw.commands.daemon.OwlBearSettings", return_value=mock_settings):
            result = _get_config_dir()
        assert result == Path("/fake/.owlbear")


# ---------------------------------------------------------------------------
# _daemon_stop
# ---------------------------------------------------------------------------


class TestDaemonStop:
    """Tests for _daemon_stop logic."""

    def test_no_pid_file_prints_not_running(self, tmp_path: Path) -> None:
        mock_settings = MagicMock()
        mock_settings.config_dir = str(tmp_path)
        with patch("bearclaw.commands.daemon.OwlBearSettings", return_value=mock_settings):
            _daemon_stop()
        # No PID file → should not crash (prints "not running")

    def test_graceful_stop(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("12345")
        mock_settings = MagicMock()
        mock_settings.config_dir = str(tmp_path)
        with (
            patch("bearclaw.commands.daemon.OwlBearSettings", return_value=mock_settings),
            patch("bearclaw.commands.daemon._poll_pid_removal", return_value=True),
        ):
            _daemon_stop()
        # Sentinel should be created then cleaned up
        assert not (tmp_path / "owlbear.stop").exists()

    def test_force_kill_fallback(self, tmp_path: Path) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("12345")
        mock_settings = MagicMock()
        mock_settings.config_dir = str(tmp_path)
        with (
            patch("bearclaw.commands.daemon.OwlBearSettings", return_value=mock_settings),
            patch("bearclaw.commands.daemon._poll_pid_removal", return_value=False),
            patch("bearclaw.commands.daemon.os.kill") as mock_kill,
        ):
            _daemon_stop()
        mock_kill.assert_called_once_with(12345, 9)


# ---------------------------------------------------------------------------
# _daemon_status
# ---------------------------------------------------------------------------


class TestDaemonStatus:
    """Tests for _daemon_status logic."""

    def test_no_pid_file_reports_not_running(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_settings = MagicMock()
        mock_settings.config_dir = str(tmp_path)
        with patch("bearclaw.commands.daemon.OwlBearSettings", return_value=mock_settings):
            _daemon_status()
        captured = capsys.readouterr()
        assert "Stopped" in captured.out

    def test_alive_pid_reports_running(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("12345")
        mock_settings = MagicMock()
        mock_settings.config_dir = str(tmp_path)
        with (
            patch("bearclaw.commands.daemon.OwlBearSettings", return_value=mock_settings),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=True),
        ):
            _daemon_status()
        captured = capsys.readouterr()
        assert "Running" in captured.out
        assert "12345" in captured.out

    def test_dead_pid_reports_stale(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pid_path = tmp_path / "owlbear.pid"
        pid_path.write_text("12345")
        mock_settings = MagicMock()
        mock_settings.config_dir = str(tmp_path)
        with (
            patch("bearclaw.commands.daemon.OwlBearSettings", return_value=mock_settings),
            patch("bearclaw.commands.daemon.is_process_alive", return_value=False),
        ):
            _daemon_status()
        captured = capsys.readouterr()
        assert "Stale" in captured.out


# ---------------------------------------------------------------------------
# CLI wrappers: stop_cmd and status_cmd
# ---------------------------------------------------------------------------


class TestStopCmd:
    """Test ``bearclaw stop`` invocation via CliRunner."""

    def test_stop_cmd_calls_daemon_stop(self) -> None:
        with patch("bearclaw.commands.daemon._daemon_stop") as mock_stop:
            result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        mock_stop.assert_called_once()


class TestStatusCmd:
    """Test ``bearclaw status`` invocation via CliRunner."""

    def test_status_cmd_calls_daemon_status(self) -> None:
        with patch("bearclaw.commands.daemon._daemon_status") as mock_status:
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        mock_status.assert_called_once()
