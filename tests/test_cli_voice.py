"""Tests for BearClaw voice CLI subcommands (Tasks #96, #244)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from bearclaw.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Command registration
# ---------------------------------------------------------------------------


class TestVoiceCommandRegistration:
    """voice subcommands are registered on the main app."""

    def test_voice_help(self) -> None:
        result = runner.invoke(app, ["voice", "--help"])
        assert result.exit_code == 0
        assert "listen" in result.output
        assert "speak" in result.output

    def test_voice_appears_in_main_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "voice" in result.output


# ---------------------------------------------------------------------------
# bearclaw voice listen
# ---------------------------------------------------------------------------


class TestVoiceListen:
    """Tests for ``bearclaw voice listen``."""

    @patch("bearclaw.cli._make_voice_channel")
    def test_listen_prints_transcription(self, mock_make: MagicMock) -> None:
        mock_ch = MagicMock()
        mock_ch.receive = AsyncMock(return_value="hello world")
        mock_make.return_value = mock_ch

        result = runner.invoke(app, ["voice", "listen"])

        assert result.exit_code == 0
        assert "hello world" in result.output

    @patch("bearclaw.cli._make_voice_channel")
    def test_listen_default_duration(self, mock_make: MagicMock) -> None:
        mock_ch = MagicMock()
        mock_ch.receive = AsyncMock(return_value="text")
        mock_make.return_value = mock_ch

        runner.invoke(app, ["voice", "listen"])

        # receive is called; duration is passed to recorder at construction
        mock_ch.receive.assert_awaited_once()

    @patch("bearclaw.cli._make_voice_channel")
    def test_listen_custom_duration(self, mock_make: MagicMock) -> None:
        mock_ch = MagicMock()
        mock_ch.receive = AsyncMock(return_value="text")
        mock_make.return_value = mock_ch

        result = runner.invoke(app, ["voice", "listen", "--duration", "10.0"])

        assert result.exit_code == 0

    @patch("bearclaw.cli._make_voice_channel")
    def test_listen_silence_message(self, mock_make: MagicMock) -> None:
        """When no speech is detected, print a helpful message."""
        mock_ch = MagicMock()
        mock_ch.receive = AsyncMock(return_value=None)
        mock_make.return_value = mock_ch

        result = runner.invoke(app, ["voice", "listen"])

        assert result.exit_code == 0
        assert "No speech detected" in result.output


# ---------------------------------------------------------------------------
# bearclaw voice speak
# ---------------------------------------------------------------------------


class TestVoiceSpeak:
    """Tests for ``bearclaw voice speak``."""

    @patch("bearclaw.cli._make_voice_channel")
    def test_speak_sends_text(self, mock_make: MagicMock) -> None:
        mock_ch = MagicMock()
        mock_ch.send = AsyncMock()
        mock_make.return_value = mock_ch

        result = runner.invoke(app, ["voice", "speak", "hello there"])

        assert result.exit_code == 0
        mock_ch.send.assert_awaited_once_with("hello there")


# ---------------------------------------------------------------------------
# ImportError handling
# ---------------------------------------------------------------------------


class TestVoiceImportError:
    """Graceful error when [voice] extras are not installed."""

    @patch(
        "bearclaw.cli._make_voice_channel",
        side_effect=ImportError("Install with: uv sync --extra voice"),
    )
    def test_listen_import_error(self, _mock: MagicMock) -> None:
        result = runner.invoke(app, ["voice", "listen"])
        assert result.exit_code == 1
        assert "uv sync --extra voice" in result.output

    @patch(
        "bearclaw.cli._make_voice_channel",
        side_effect=ImportError("Install with: uv sync --extra voice"),
    )
    def test_speak_import_error(self, _mock: MagicMock) -> None:
        result = runner.invoke(app, ["voice", "speak", "hello"])
        assert result.exit_code == 1
        assert "uv sync --extra voice" in result.output


# ---------------------------------------------------------------------------
# bearclaw voice brainstorm
# ---------------------------------------------------------------------------


class TestVoiceBrainstorm:
    """Tests for ``bearclaw voice brainstorm``."""

    def test_brainstorm_appears_in_help(self) -> None:
        result = runner.invoke(app, ["voice", "--help"])
        assert result.exit_code == 0
        assert "brainstorm" in result.output

    @patch("bearclaw.cli._make_voice_channel")
    def test_brainstorm_default_options(self, mock_make: MagicMock) -> None:
        mock_ch = MagicMock()
        mock_ch.brainstorm = AsyncMock(return_value="brainstorm transcript")
        mock_make.return_value = mock_ch

        result = runner.invoke(app, ["voice", "brainstorm"])

        assert result.exit_code == 0
        assert "brainstorm transcript" in result.output
        mock_ch.brainstorm.assert_awaited_once()

    @patch("bearclaw.cli._make_voice_channel")
    def test_brainstorm_custom_duration(self, mock_make: MagicMock) -> None:
        mock_ch = MagicMock()
        mock_ch.brainstorm = AsyncMock(return_value="text")
        mock_make.return_value = mock_ch

        result = runner.invoke(
            app,
            ["voice", "brainstorm", "--duration", "60"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_ch.brainstorm.call_args[1]
        assert call_kwargs["duration"] == 60.0

    @patch("bearclaw.cli._make_voice_channel")
    def test_brainstorm_custom_idle_timeout(self, mock_make: MagicMock) -> None:
        mock_ch = MagicMock()
        mock_ch.brainstorm = AsyncMock(return_value="text")
        mock_make.return_value = mock_ch

        result = runner.invoke(
            app,
            ["voice", "brainstorm", "--idle-timeout", "5"],
        )

        assert result.exit_code == 0
        call_kwargs = mock_ch.brainstorm.call_args[1]
        assert call_kwargs["idle_timeout"] == 5.0

    @patch("bearclaw.cli._make_voice_channel")
    def test_brainstorm_prints_live_updates(self, mock_make: MagicMock) -> None:
        """on_update callback is passed and prints partial text."""
        mock_ch = MagicMock()
        mock_ch.brainstorm = AsyncMock(return_value="final text")
        mock_make.return_value = mock_ch

        result = runner.invoke(app, ["voice", "brainstorm"])

        assert result.exit_code == 0
        # Verify on_update was passed as a keyword argument
        call_kwargs = mock_ch.brainstorm.call_args[1]
        assert "on_update" in call_kwargs

    @patch(
        "bearclaw.cli._make_voice_channel",
        side_effect=ImportError("Install with: uv sync --extra voice"),
    )
    def test_brainstorm_import_error(self, _mock: MagicMock) -> None:
        result = runner.invoke(app, ["voice", "brainstorm"])
        assert result.exit_code == 1
        assert "uv sync --extra voice" in result.output
