"""Tests for the BearClaw CLI (bearclaw.cli)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


class TestCLIHelp:
    """Test --help output for all commands."""

    def test_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "BearClaw CLI" in result.output
        assert "auth" in result.output

    def test_auth_help(self) -> None:
        result = runner.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0
        assert "login" in result.output
        assert "status" in result.output


class TestCLIVersion:
    """Test --version flag."""

    def test_version_long_flag(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "owlbear 0.1.0" in result.output

    def test_version_short_flag(self) -> None:
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "owlbear 0.1.0" in result.output


class TestAuthCommands:
    """Test auth subcommands exist and are callable."""

    def test_auth_login_is_registered(self) -> None:
        result = runner.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0
        assert "login" in result.output

    def test_auth_status_is_registered(self) -> None:
        result = runner.invoke(app, ["auth", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output


class TestNoArgsShowsHelp:
    """Verify no-args behaviour."""

    def test_no_args_exits_zero(self) -> None:
        result = runner.invoke(app, [])
        # no_args_is_help=True causes Click to exit with code 2
        assert result.exit_code == 2
        assert "BearClaw CLI" in result.output


# ---------------------------------------------------------------------------
# Slack subcommand tests
# ---------------------------------------------------------------------------

# Env var names used by OwlBearSettings for Slack
_SLACK_ENV = {
    "OWLBEAR_SLACK_APP_TOKEN": "xapp-test-token",
    "OWLBEAR_SLACK_BOT_TOKEN": "xoxb-test-token",
    "OWLBEAR_SLACK_CHANNEL_ID": "C0123456789",
}


class TestSlackHelp:
    """Test slack subcommand help output."""

    def test_slack_help(self) -> None:
        result = runner.invoke(app, ["slack", "--help"])
        assert result.exit_code == 0
        assert "auth" in result.output
        assert "test" in result.output
        assert "status" in result.output


class TestSlackAuth:
    """Test bearclaw slack auth command."""

    def test_slack_auth_no_tokens(self, monkeypatch: MagicMock) -> None:
        """Missing tokens → error message and exit 1."""
        # Ensure no Slack env vars are set
        for key in _SLACK_ENV:
            monkeypatch.delenv(key, raising=False)
        result = runner.invoke(app, ["slack", "auth"])
        assert result.exit_code == 1
        assert "not configured" in result.output.lower()

    def test_slack_auth_success(self, monkeypatch: MagicMock) -> None:
        """Valid tokens + auth.test OK → success message."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "ok": True,
            "user": "owlbear-bot",
            "team": "test-workspace",
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("bearclaw.cli.httpx.post", return_value=mock_resp) as mock_post:
            result = runner.invoke(app, ["slack", "auth"])

        assert result.exit_code == 0
        assert "owlbear-bot" in result.output
        assert "test-workspace" in result.output
        mock_post.assert_called_once()

    def test_slack_auth_api_error(self, monkeypatch: MagicMock) -> None:
        """auth.test returns ok=false → error message and exit 1."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "error": "invalid_auth"}
        mock_resp.raise_for_status = MagicMock()

        with patch("bearclaw.cli.httpx.post", return_value=mock_resp):
            result = runner.invoke(app, ["slack", "auth"])

        assert result.exit_code == 1
        assert "invalid_auth" in result.output


class TestSlackTest:
    """Test bearclaw slack test command."""

    def test_slack_test_no_tokens(self, monkeypatch: MagicMock) -> None:
        """Missing tokens → error message and exit 1."""
        for key in _SLACK_ENV:
            monkeypatch.delenv(key, raising=False)
        result = runner.invoke(app, ["slack", "test"])
        assert result.exit_code == 1
        assert "not configured" in result.output.lower()

    def test_slack_test_success(self, monkeypatch: MagicMock) -> None:
        """Sends message successfully → success output."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_resp.raise_for_status = MagicMock()

        with patch("bearclaw.cli.httpx.post", return_value=mock_resp) as mock_post:
            result = runner.invoke(app, ["slack", "test"])

        assert result.exit_code == 0
        assert "C0123456789" in result.output
        mock_post.assert_called_once()

    def test_slack_test_api_error(self, monkeypatch: MagicMock) -> None:
        """chat.postMessage returns ok=false → error and exit 1."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "error": "channel_not_found"}
        mock_resp.raise_for_status = MagicMock()

        with patch("bearclaw.cli.httpx.post", return_value=mock_resp):
            result = runner.invoke(app, ["slack", "test"])

        assert result.exit_code == 1
        assert "channel_not_found" in result.output


class TestSlackStatus:
    """Test bearclaw slack status command."""

    def test_slack_status_no_tokens(self, monkeypatch: MagicMock) -> None:
        """No tokens configured → shows 'not configured'."""
        for key in _SLACK_ENV:
            monkeypatch.delenv(key, raising=False)
        result = runner.invoke(app, ["slack", "status"])
        assert result.exit_code == 0
        assert "not configured" in result.output.lower()

    def test_slack_status_configured_ok(self, monkeypatch: MagicMock) -> None:
        """All tokens set + auth.test OK → shows Connection: OK."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True, "user": "owlbear-bot", "team": "ws"}
        mock_resp.raise_for_status = MagicMock()

        with patch("bearclaw.cli.httpx.post", return_value=mock_resp):
            result = runner.invoke(app, ["slack", "status"])

        assert result.exit_code == 0
        assert "Connection: OK" in result.output
        assert "C0123456789" in result.output

    def test_slack_status_connection_failed(self, monkeypatch: MagicMock) -> None:
        """All tokens set but auth.test fails → shows Connection: Failed."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "error": "invalid_auth"}
        mock_resp.raise_for_status = MagicMock()

        with patch("bearclaw.cli.httpx.post", return_value=mock_resp):
            result = runner.invoke(app, ["slack", "status"])

        assert result.exit_code == 0
        assert "Connection: Failed" in result.output
