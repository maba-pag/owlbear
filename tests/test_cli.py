"""Tests for the BearClaw CLI (bearclaw.cli)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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

        with patch("bearclaw.commands.slack.httpx.post", return_value=mock_resp) as mock_post:
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

        with patch("bearclaw.commands.slack.httpx.post", return_value=mock_resp):
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

        with patch("bearclaw.commands.slack.httpx.post", return_value=mock_resp) as mock_post:
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

        with patch("bearclaw.commands.slack.httpx.post", return_value=mock_resp):
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

        with patch("bearclaw.commands.slack.httpx.post", return_value=mock_resp):
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

        with patch("bearclaw.commands.slack.httpx.post", return_value=mock_resp):
            result = runner.invoke(app, ["slack", "status"])

        assert result.exit_code == 0
        assert "Connection: Failed" in result.output

    def test_slack_status_http_error(self, monkeypatch: MagicMock) -> None:
        """All tokens set but httpx raises → shows Connection: Failed (request error)."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        with patch("bearclaw.commands.slack.httpx.post", side_effect=httpx.HTTPError("timeout")):
            result = runner.invoke(app, ["slack", "status"])

        assert result.exit_code == 0
        assert "request error" in result.output.lower()


class TestSlackAuthHttpError:
    """Test bearclaw slack auth when httpx raises."""

    def test_slack_auth_http_error(self, monkeypatch: MagicMock) -> None:
        """HTTP error during auth.test → error message and exit 1."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        with patch(
            "bearclaw.commands.slack.httpx.post",
            side_effect=httpx.HTTPError("connection failed"),
        ):
            result = runner.invoke(app, ["slack", "auth"])

        assert result.exit_code == 1
        assert "failed" in result.output.lower()


class TestSlackTestHttpError:
    """Test bearclaw slack test when httpx raises."""

    def test_slack_test_http_error(self, monkeypatch: MagicMock) -> None:
        """HTTP error during chat.postMessage → error message and exit 1."""
        for key, val in _SLACK_ENV.items():
            monkeypatch.setenv(key, val)

        with patch(
            "bearclaw.commands.slack.httpx.post",
            side_effect=httpx.HTTPError("connection failed"),
        ):
            result = runner.invoke(app, ["slack", "test"])

        assert result.exit_code == 1
        assert "failed" in result.output.lower()


# ---------------------------------------------------------------------------
# bearclaw run — run_cmd integration tests
# ---------------------------------------------------------------------------


def _make_bootstrap_result() -> MagicMock:
    """Create a mock BootstrapResult with all required attributes."""
    result = MagicMock()
    result.agent = MagicMock()
    result.channel = MagicMock()
    result.mcp_registry = None
    result.cleanup = []
    return result


def _pid_context_manager() -> MagicMock:
    """Create a MagicMock that acts as a sync context manager."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


class TestRunCmd:
    """Test bearclaw run command wired through bootstrap()."""

    def test_calls_bootstrap_with_channel_name(self, tmp_path: Path) -> None:
        """run_cmd passes --channel value to bootstrap(channel_name=...)."""
        mock_result = _make_bootstrap_result()
        captured_channel: list[str] = []

        async def fake_bootstrap(settings, *, channel_name="cli", workspace_root=None):  # noqa: ARG001
            captured_channel.append(channel_name)
            return mock_result

        async def fake_run_daemon(**kwargs):
            pass

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.setup_logging"),
            patch("owlbear.daemon.PidFile", return_value=_pid_context_manager()),
        ):
            mock_settings_cls.return_value.config_dir = str(tmp_path)
            result = runner.invoke(app, ["run", "--channel", "cli"])

        assert result.exit_code == 0
        assert captured_channel == ["cli"]

    def test_model_override_calls_update_model(self, tmp_path: Path) -> None:
        """When --model is provided, result.agent.update_model() is called."""
        mock_result = _make_bootstrap_result()

        async def fake_bootstrap(settings, *, channel_name="cli", workspace_root=None):  # noqa: ARG001
            return mock_result

        async def fake_run_daemon(**kwargs):
            pass

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.setup_logging"),
            patch("owlbear.daemon.PidFile", return_value=_pid_context_manager()),
        ):
            mock_settings_cls.return_value.config_dir = str(tmp_path)
            runner.invoke(app, ["run", "--model", "gpt-4o"])

        mock_result.agent.update_model.assert_called_once_with("gpt-4o")

    def test_mcp_lifecycle_managed(self, tmp_path: Path) -> None:
        """MCP registry __aenter__/__aexit__ called around run_daemon."""
        mock_result = _make_bootstrap_result()
        mock_mcp = MagicMock()
        mock_mcp.__aenter__ = AsyncMock(return_value=mock_mcp)
        mock_mcp.__aexit__ = AsyncMock(return_value=None)
        mock_result.mcp_registry = mock_mcp

        async def fake_bootstrap(settings, *, channel_name="cli", workspace_root=None):  # noqa: ARG001
            return mock_result

        async def fake_run_daemon(**kwargs):
            pass

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.setup_logging"),
            patch("owlbear.daemon.PidFile", return_value=_pid_context_manager()),
        ):
            mock_settings_cls.return_value.config_dir = str(tmp_path)
            runner.invoke(app, ["run"])

        mock_mcp.__aenter__.assert_called_once()
        mock_mcp.__aexit__.assert_called_once()

    def test_cleanup_callbacks_invoked(self, tmp_path: Path) -> None:
        """result.cleanup callbacks are invoked in finally block."""
        mock_result = _make_bootstrap_result()
        cb1 = MagicMock()
        cb2 = MagicMock()
        mock_result.cleanup = [cb1, cb2]

        async def fake_bootstrap(settings, *, channel_name="cli", workspace_root=None):  # noqa: ARG001
            return mock_result

        async def fake_run_daemon(**kwargs):
            pass

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.setup_logging"),
            patch("owlbear.daemon.PidFile", return_value=_pid_context_manager()),
        ):
            mock_settings_cls.return_value.config_dir = str(tmp_path)
            runner.invoke(app, ["run"])

        cb1.assert_called_once()
        cb2.assert_called_once()

    def test_cleanup_runs_even_on_error(self, tmp_path: Path) -> None:
        """Cleanup callbacks run even when run_daemon raises."""
        mock_result = _make_bootstrap_result()
        cb = MagicMock()
        mock_result.cleanup = [cb]

        async def fake_bootstrap(settings, *, channel_name="cli", workspace_root=None):  # noqa: ARG001
            return mock_result

        async def fake_run_daemon(**_kwargs):
            msg = "daemon crashed"
            raise RuntimeError(msg)

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.setup_logging"),
            patch("owlbear.daemon.PidFile", return_value=_pid_context_manager()),
        ):
            mock_settings_cls.return_value.config_dir = str(tmp_path)
            runner.invoke(app, ["run"])

        # Cleanup should still be called despite the error
        cb.assert_called_once()

    def test_pidfile_still_managed(self, tmp_path: Path) -> None:
        """run_cmd still owns PidFile (not bootstrap)."""
        mock_result = _make_bootstrap_result()

        async def fake_bootstrap(settings, *, channel_name="cli", workspace_root=None):  # noqa: ARG001
            return mock_result

        async def fake_run_daemon(**kwargs):
            pass

        pid_cm = _pid_context_manager()

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.setup_logging"),
            patch("owlbear.daemon.PidFile", return_value=pid_cm) as mock_pid_cls,
        ):
            mock_settings_cls.return_value.config_dir = str(tmp_path)
            runner.invoke(app, ["run"])

        # PidFile was constructed and used as context manager
        mock_pid_cls.assert_called_once()
        pid_cm.__enter__.assert_called_once()
        pid_cm.__exit__.assert_called_once()

    def test_run_daemon_receives_settings(self, tmp_path: Path) -> None:
        """run_daemon is called with settings parameter."""
        mock_result = _make_bootstrap_result()
        captured_kwargs: dict = {}

        async def fake_bootstrap(settings, *, channel_name="cli", workspace_root=None):  # noqa: ARG001
            return mock_result

        async def fake_run_daemon(**kwargs):
            captured_kwargs.update(kwargs)

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.setup_logging"),
            patch("owlbear.daemon.PidFile", return_value=_pid_context_manager()),
        ):
            mock_settings_cls.return_value.config_dir = str(tmp_path)
            runner.invoke(app, ["run"])

        assert "settings" in captured_kwargs


# ---------------------------------------------------------------------------
# Cleanup loop awaits async callables (#650 — red phase for #514)
# ---------------------------------------------------------------------------


class TestCleanupLoopAwaitsAsync:
    """The cleanup loop in _run() must await async callables.

    After #514, the loop uses ``inspect.isawaitable()`` on the return
    value of each callback so that ``AsyncOpenAI.close()`` (a coroutine)
    is properly awaited instead of silently discarded.
    """

    def test_async_cleanup_callable_is_awaited(self, tmp_path: Path) -> None:
        """An async cleanup callable should be awaited, not just called."""
        mock_result = _make_bootstrap_result()
        async_cb = AsyncMock()
        mock_result.cleanup = [async_cb]

        async def fake_bootstrap(settings, *, channel_name="cli", workspace_root=None):  # noqa: ARG001
            return mock_result

        async def fake_run_daemon(**kwargs):
            pass

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch("owlbear.bootstrap.bootstrap", new=fake_bootstrap),
            patch("owlbear.daemon.run_daemon", new=fake_run_daemon),
            patch("owlbear.daemon.setup_logging"),
            patch("owlbear.daemon.PidFile", return_value=_pid_context_manager()),
        ):
            mock_settings_cls.return_value.config_dir = str(tmp_path)
            runner.invoke(app, ["run"])

        # AsyncMock tracks await calls separately from regular calls.
        # If the loop awaits the result, await_count will be >= 1.
        assert async_cb.await_count >= 1, (
            f"Async cleanup callable was called but not awaited "
            f"(call_count={async_cb.call_count}, await_count={async_cb.await_count})"
        )


class TestChatAsyncRunsCleanup:
    """_chat_async must run result.cleanup on exit.

    After #514, _chat_async wraps its body in try/finally and invokes
    all cleanup callables (including async ones) when the chat loop ends.
    Currently _chat_async has no cleanup handling at all — second leak vector.
    """

    def test_chat_cleanup_invoked_on_exit(self, tmp_path: Path) -> None:
        """Cleanup callbacks are called when _chat_async finishes."""
        cleanup_cb = MagicMock()
        mock_result = _make_bootstrap_result()
        mock_result.cleanup = [cleanup_cb]
        # Make channel.receive return None to exit immediately
        mock_result.channel.receive = AsyncMock(return_value=None)
        mock_result.channel.send = AsyncMock()
        mock_result.agent.session = MagicMock()
        mock_result.agent.session.load = MagicMock()

        with (
            patch("owlbear.config.OwlBearSettings") as mock_settings_cls,
            patch(
                "bearclaw.commands.chat.bootstrap",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
        ):
            mock_settings_cls.return_value = MagicMock(
                config_dir=str(tmp_path),
                chat_model="test-model",
            )
            import asyncio

            from bearclaw.commands.chat import _chat_async

            asyncio.run(
                _chat_async(
                    model=None,
                    session=None,
                    workspace_root=tmp_path,
                )
            )

        cleanup_cb.assert_called_once()


# ---------------------------------------------------------------------------
# Rich traceback in CLI callback (TDD RED — #632)
# ---------------------------------------------------------------------------


class TestFromAC_RichTracebackCli:  # noqa: N801
    """AC#1: rich.traceback.install(show_locals=False, suppress=[typer, click]) in cli.py main().

    The rich traceback handler must be installed at the CLI app callback level
    so ALL commands (auth, chat, daemon, project, etc.) get rich tracebacks,
    not just the daemon.
    """

    def test_main_callback_calls_rich_traceback_install(self) -> None:
        """CLI app callback calls install_rich_traceback with correct params."""
        import click as click_mod
        import typer as typer_mod

        with patch("bearclaw.cli.install_rich_traceback") as mock_install:
            runner.invoke(app, ["--help"])
            mock_install.assert_called_once_with(
                show_locals=False,
                suppress=[typer_mod, click_mod],
            )

    def test_rich_traceback_covers_non_daemon_commands(self) -> None:
        """Rich traceback fires for non-daemon commands (e.g. auth --help)."""
        with patch("bearclaw.cli.install_rich_traceback") as mock_install:
            runner.invoke(app, ["auth", "--help"])
            assert mock_install.called, "rich.traceback.install() must fire for non-daemon commands"
