"""Tests for bearclaw chat — interactive CLI REPL (tasks #122, #270).

Mocks ``bootstrap()`` return value (:class:`BootstrapResult` with mock
agent/channel) instead of mocking individual toolset constructors.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()

# Fake paths that never touch the real filesystem (not /tmp — avoids S108).
_FAKE_CONFIG = PurePosixPath("/fake/.owlbear")


def _make_mocks(
    *,
    model: str = "gpt-4o",
    session_name: str = "s",
    turn_results: list[str | Exception] | None = None,
    history: list[object] | None = None,
) -> tuple[MagicMock, MagicMock, AsyncMock, MagicMock]:
    """Return ``(settings_cls, session_cls, bootstrap_fn, agent)`` pre-configured mocks.

    The *bootstrap_fn* is an :class:`AsyncMock` whose side-effect lazily creates
    a real :class:`CLIChannel` (so ``CliRunner``'s stdin redirection is active)
    and attaches the pre-built *agent* mock.
    """
    settings = MagicMock()
    settings.chat_model = model
    settings.config_dir = _FAKE_CONFIG
    settings_cls = MagicMock(return_value=settings)

    session = MagicMock()
    session.load.return_value = history or []
    session.path = _FAKE_CONFIG / "sessions" / f"{session_name}.jsonl"
    session_cls = MagicMock(return_value=session)

    effects = turn_results or []
    side: list[str | Exception] = list(effects) if effects else ["ok"]
    agent = MagicMock()
    agent.turn = AsyncMock(side_effect=side)

    async def _fake_bootstrap(*_args: object, **_kwargs: object) -> MagicMock:
        from owlbear.channels.cli import CLIChannel

        result = MagicMock()
        result.agent = agent
        result.channel = CLIChannel()
        return result

    bootstrap_fn = AsyncMock(side_effect=_fake_bootstrap)

    return settings_cls, session_cls, bootstrap_fn, agent


def _invoke_chat(input_text: str, extra_args: list[str] | None = None) -> object:
    """Run ``bearclaw chat`` with piped *input_text* via CliRunner."""
    args = ["chat", *(extra_args or [])]
    return runner.invoke(app, args, input=input_text)


def _patch_and_run(  # noqa: PLR0913
    input_text: str,
    *,
    extra_args: list[str] | None = None,
    model: str = "gpt-4o",
    session_name: str = "s",
    turn_results: list[str | Exception] | None = None,
    history: list[object] | None = None,
) -> tuple[object, MagicMock, MagicMock, MagicMock]:
    """Patch chat dependencies, invoke the CLI, return (result, settings, session, agent)."""
    s_cls, ss_cls, boot_fn, agent = _make_mocks(
        model=model,
        session_name=session_name,
        turn_results=turn_results,
        history=history,
    )
    with (
        patch("owlbear.config.OwlBearSettings", s_cls),
        patch("bearclaw.commands.chat.SessionStore", ss_cls),
        patch("bearclaw.commands.chat.bootstrap", boot_fn),
    ):
        result = _invoke_chat(input_text, extra_args=extra_args)
    return result, s_cls.return_value, ss_cls.return_value, agent


# ---------------------------------------------------------------------------
# Startup banner
# ---------------------------------------------------------------------------


class TestChatBanner:
    """Test that startup prints a banner with model and session info."""

    def test_banner_shows_model_and_session(self) -> None:
        result, *_ = _patch_and_run("exit\n", session_name="test", extra_args=["--session", "test"])
        assert result.exit_code == 0
        assert "gpt-4o" in result.output
        assert "test" in result.output


# ---------------------------------------------------------------------------
# Message round-trip
# ---------------------------------------------------------------------------


class TestChatRoundTrip:
    """Test user input -> agent.turn() -> response printed."""

    def test_user_message_calls_turn_and_prints_response(self) -> None:
        result, _, _, agent = _patch_and_run(
            "hello there\nexit\n",
            turn_results=["I am OwlBear!"],
        )
        assert result.exit_code == 0
        agent.turn.assert_called_once_with("hello there")
        assert "I am OwlBear!" in result.output


# ---------------------------------------------------------------------------
# Multi-line input
# ---------------------------------------------------------------------------


class TestChatMultiLine:
    """Test !multi + lines + !end -> single concatenated prompt."""

    def test_multi_line_joins_input(self) -> None:
        result, _, _, agent = _patch_and_run(
            "!multi\nline one\nline two\n!end\nexit\n",
            turn_results=["got it"],
        )
        assert result.exit_code == 0
        agent.turn.assert_called_once_with("line one\nline two")
        assert "got it" in result.output


# ---------------------------------------------------------------------------
# Exit keywords
# ---------------------------------------------------------------------------


class TestChatExit:
    """Test exit/quit triggers graceful shutdown."""

    def test_exit_keyword(self) -> None:
        result, _, _, agent = _patch_and_run("exit\n")
        assert result.exit_code == 0
        assert "Goodbye" in result.output
        agent.turn.assert_not_called()

    def test_quit_keyword(self) -> None:
        result, _, _, agent = _patch_and_run("quit\n")
        assert result.exit_code == 0
        assert "Goodbye" in result.output
        agent.turn.assert_not_called()


# ---------------------------------------------------------------------------
# EOF (receive returns None)
# ---------------------------------------------------------------------------


class TestChatEOF:
    """Test EOF (empty input / Ctrl+D) triggers graceful shutdown."""

    def test_eof_exits_gracefully(self) -> None:
        result, *_ = _patch_and_run("")
        assert result.exit_code == 0
        assert "Goodbye" in result.output


# ---------------------------------------------------------------------------
# Session loaded on startup
# ---------------------------------------------------------------------------


class TestChatSessionLoad:
    """Test that session history is loaded on startup."""

    def test_session_loaded_on_startup(self) -> None:
        result, _, session, _ = _patch_and_run("exit\n", history=["fake-msg"])
        assert result.exit_code == 0
        session.load.assert_called_once()


# ---------------------------------------------------------------------------
# Agent error during turn (don't crash)
# ---------------------------------------------------------------------------


class TestChatAgentError:
    """Test that agent errors during turn don't crash the REPL."""

    def test_agent_error_prints_and_continues(self) -> None:
        result, _, _, _ = _patch_and_run(
            "first\nsecond\nexit\n",
            turn_results=[RuntimeError("LLM down"), "recovered"],
        )
        assert result.exit_code == 0
        assert "Error" in result.output
        assert "recovered" in result.output


# ---------------------------------------------------------------------------
# --model flag
# ---------------------------------------------------------------------------


class TestChatModelFlag:
    """Test that --model flag overrides the default."""

    def test_model_flag_calls_update_model(self) -> None:
        s_cls, ss_cls, boot_fn, agent = _make_mocks()
        with (
            patch("owlbear.config.OwlBearSettings", s_cls),
            patch("bearclaw.commands.chat.SessionStore", ss_cls),
            patch("bearclaw.commands.chat.bootstrap", boot_fn),
        ):
            result = _invoke_chat("exit\n", extra_args=["--model", "claude-sonnet"])
        assert result.exit_code == 0
        agent.update_model.assert_called_once_with("claude-sonnet")
        assert "claude-sonnet" in result.output

    def test_no_model_flag_skips_update(self) -> None:
        result, _, _, agent = _patch_and_run("exit\n")
        assert result.exit_code == 0
        agent.update_model.assert_not_called()


# ---------------------------------------------------------------------------
# Help text in banner
# ---------------------------------------------------------------------------


class TestChatHelp:
    """Test that the help subcommand exists and banner mentions !multi."""

    def test_chat_in_help(self) -> None:
        result = runner.invoke(app, ["chat", "--help"])
        assert result.exit_code == 0
        assert "chat" in result.output.lower()

    def test_banner_mentions_multi_and_exit(self) -> None:
        result, *_ = _patch_and_run("exit\n")
        assert "!multi" in result.output
        assert "exit" in result.output.lower()


# ---------------------------------------------------------------------------
# bootstrap() called with correct arguments (#270)
# ---------------------------------------------------------------------------


class TestBootstrapIntegration:
    """Verify _chat_async calls bootstrap() and wires session/model overrides."""

    def test_bootstrap_called_with_settings_and_cli_channel(self) -> None:
        s_cls, ss_cls, boot_fn, _agent = _make_mocks()
        with (
            patch("owlbear.config.OwlBearSettings", s_cls),
            patch("bearclaw.commands.chat.SessionStore", ss_cls),
            patch("bearclaw.commands.chat.bootstrap", boot_fn),
        ):
            result = _invoke_chat("exit\n")

        assert result.exit_code == 0
        boot_fn.assert_awaited_once()
        call_kwargs = boot_fn.call_args.kwargs
        assert call_kwargs["channel_name"] == "cli"
        assert "workspace_root" in call_kwargs

    def test_session_overridden_on_agent(self) -> None:
        """After bootstrap, agent.session must be the user-specified store."""
        s_cls, ss_cls, boot_fn, agent = _make_mocks(session_name="my-sess")
        with (
            patch("owlbear.config.OwlBearSettings", s_cls),
            patch("bearclaw.commands.chat.SessionStore", ss_cls),
            patch("bearclaw.commands.chat.bootstrap", boot_fn),
        ):
            result = _invoke_chat("exit\n", extra_args=["--session", "my-sess"])

        assert result.exit_code == 0
        # The session store created by _build_chat_session should be assigned
        assert agent.session == ss_cls.return_value


# ---------------------------------------------------------------------------
# _detect_github_remote
# ---------------------------------------------------------------------------


class TestDetectGitHubRemote:
    """Unit tests for _detect_github_remote."""

    def test_ssh_remote_parsed(self, tmp_path: Path) -> None:
        """SSH-style remote → (owner, repo) tuple."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        from bearclaw.commands.chat import _detect_github_remote

        mock_result = make_completed_process(returncode=0, stdout="git@github.com:owner/repo.git\n")

        with patch("bearclaw.commands.chat.subprocess.run", return_value=mock_result):
            result = _detect_github_remote(tmp_path)

        assert result == ("owner", "repo")

    def test_https_remote_parsed(self, tmp_path: Path) -> None:
        """HTTPS-style remote → (owner, repo) tuple."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        from bearclaw.commands.chat import _detect_github_remote

        mock_result = make_completed_process(returncode=0, stdout="https://github.com/owner/repo.git\n")

        with patch("bearclaw.commands.chat.subprocess.run", return_value=mock_result):
            result = _detect_github_remote(tmp_path)

        assert result == ("owner", "repo")

    def test_git_failure_returns_none(self, tmp_path: Path) -> None:
        """Non-zero git exit code → None."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        from bearclaw.commands.chat import _detect_github_remote

        mock_result = make_completed_process(returncode=128, stdout="")

        with patch("bearclaw.commands.chat.subprocess.run", return_value=mock_result):
            result = _detect_github_remote(tmp_path)

        assert result is None

    def test_invalid_remote_returns_none(self, tmp_path: Path) -> None:
        """Unparseable remote URL → None (ValueError caught)."""
        from conftest import make_completed_process  # type: ignore[import-untyped]

        from bearclaw.commands.chat import _detect_github_remote

        mock_result = make_completed_process(returncode=0, stdout="not-a-valid-url\n")

        with patch("bearclaw.commands.chat.subprocess.run", return_value=mock_result):
            result = _detect_github_remote(tmp_path)

        assert result is None
