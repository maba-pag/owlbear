"""Tests for the BearClaw CLI (bearclaw.cli)."""

from __future__ import annotations

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
    """Test auth subcommands."""

    def test_auth_login(self) -> None:
        result = runner.invoke(app, ["auth", "login"])
        assert result.exit_code == 0
        assert "Not yet implemented" in result.output
        assert "device flow" in result.output

    def test_auth_status(self) -> None:
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "Not yet implemented" in result.output
        assert "token status" in result.output


class TestNoArgsShowsHelp:
    """Verify no-args behaviour."""

    def test_no_args_exits_zero(self) -> None:
        result = runner.invoke(app, [])
        # no_args_is_help=True causes Click to exit with code 2
        assert result.exit_code == 2
        assert "BearClaw CLI" in result.output
