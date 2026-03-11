"""Tests for BearClaw browser CLI subcommands (bearclaw browser)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# bearclaw browser start
# ---------------------------------------------------------------------------


class TestBrowserStart:
    """Tests for ``bearclaw browser start``."""

    @patch("bearclaw.commands.browser.launch_edge_cdp", return_value=12345)
    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_start_default_port(
        self, mock_settings: object, mock_launch: object, tmp_path: Path
    ) -> None:
        """Calls launch_edge_cdp with default port 9222."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        result = runner.invoke(app, ["browser", "start"])
        assert result.exit_code == 0
        mock_launch.assert_called_once_with(port=9222)  # type: ignore[union-attr]

    @patch("bearclaw.commands.browser.launch_edge_cdp", return_value=12345)
    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_start_custom_port(
        self, mock_settings: object, mock_launch: object, tmp_path: Path
    ) -> None:
        """Calls launch_edge_cdp with --port flag when provided."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        result = runner.invoke(app, ["browser", "start", "--port", "9333"])
        assert result.exit_code == 0
        mock_launch.assert_called_once_with(port=9333)  # type: ignore[union-attr]

    @patch("bearclaw.commands.browser.launch_edge_cdp", return_value=12345)
    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_start_writes_pid_file(
        self, mock_settings: object, _mock_launch: object, tmp_path: Path
    ) -> None:
        """Writes PID file to config dir."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        runner.invoke(app, ["browser", "start"])
        pid_file = tmp_path / "browser.pid"
        assert pid_file.exists()
        assert pid_file.read_text() == "12345"

    @patch("bearclaw.commands.browser.launch_edge_cdp", return_value=12345)
    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_start_outputs_success_message(
        self, mock_settings: object, _mock_launch: object, tmp_path: Path
    ) -> None:
        """Outputs success message with port number."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        result = runner.invoke(app, ["browser", "start"])
        assert result.exit_code == 0
        assert "Edge started on port 9222 (PID 12345)" in result.output

    @patch(
        "bearclaw.commands.browser.launch_edge_cdp",
        side_effect=FileNotFoundError("Microsoft Edge executable not found"),
    )
    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_start_exit_1_when_edge_not_found(
        self, mock_settings: object, _mock_launch: object, tmp_path: Path
    ) -> None:
        """Exit code 1 and error message when Edge not found."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        result = runner.invoke(app, ["browser", "start"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# bearclaw browser stop
# ---------------------------------------------------------------------------


class TestBrowserStop:
    """Tests for ``bearclaw browser stop``."""

    @patch("bearclaw.commands.browser.kill_edge")
    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_stop_reads_pid_and_kills(
        self, mock_settings: object, mock_kill: object, tmp_path: Path
    ) -> None:
        """Reads PID from PID file and calls kill_edge with correct PID."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        (tmp_path / "browser.pid").write_text("12345")
        result = runner.invoke(app, ["browser", "stop"])
        assert result.exit_code == 0
        mock_kill.assert_called_once_with(12345)  # type: ignore[union-attr]

    @patch("bearclaw.commands.browser.kill_edge")
    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_stop_removes_pid_file(
        self, mock_settings: object, _mock_kill: object, tmp_path: Path
    ) -> None:
        """Removes PID file after killing."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        pid_file = tmp_path / "browser.pid"
        pid_file.write_text("12345")
        runner.invoke(app, ["browser", "stop"])
        assert not pid_file.exists()

    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_stop_exit_1_when_not_running(self, mock_settings: object, tmp_path: Path) -> None:
        """Exit code 1 and error message when no PID file exists."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        result = runner.invoke(app, ["browser", "stop"])
        assert result.exit_code == 1
        assert "not running" in result.output.lower()

    @patch("bearclaw.commands.browser.kill_edge")
    @patch("bearclaw.commands.browser.OwlBearSettings")
    def test_stop_outputs_success_message(
        self, mock_settings: object, _mock_kill: object, tmp_path: Path
    ) -> None:
        """Prints 'Edge stopped' on success."""
        mock_settings.return_value.config_dir = tmp_path  # type: ignore[union-attr]
        (tmp_path / "browser.pid").write_text("99")
        result = runner.invoke(app, ["browser", "stop"])
        assert result.exit_code == 0
        assert "Edge stopped" in result.output


# ---------------------------------------------------------------------------
# bearclaw browser status
# ---------------------------------------------------------------------------


class TestBrowserStatus:
    """Tests for ``bearclaw browser status``."""

    @patch(
        "bearclaw.commands.browser.is_cdp_available",
        new_callable=AsyncMock,
        return_value=True,
    )
    def test_status_connected(self, _mock_available: object) -> None:
        """Shows 'Connected' when is_cdp_available returns True."""
        result = runner.invoke(app, ["browser", "status"])
        assert result.exit_code == 0
        assert "Connected" in result.output

    @patch(
        "bearclaw.commands.browser.is_cdp_available",
        new_callable=AsyncMock,
        return_value=False,
    )
    def test_status_not_connected(self, _mock_available: object) -> None:
        """Shows 'Not connected' when is_cdp_available returns False."""
        result = runner.invoke(app, ["browser", "status"])
        assert result.exit_code == 0
        assert "Not connected" in result.output

    @patch(
        "bearclaw.commands.browser.is_cdp_available",
        new_callable=AsyncMock,
        return_value=True,
    )
    def test_status_custom_port(self, mock_available: object) -> None:
        """Accepts --port flag."""
        result = runner.invoke(app, ["browser", "status", "--port", "9333"])
        assert result.exit_code == 0
        mock_available.assert_called_once_with(port=9333)  # type: ignore[union-attr]
        assert "9333" in result.output
