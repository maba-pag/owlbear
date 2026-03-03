"""Tests for owlbear.channels — ChannelPlugin Protocol + CLIChannel adapter."""

from __future__ import annotations

import asyncio
from io import StringIO
from pathlib import Path

import pytest

from owlbear.channels.base import ChannelPlugin
from owlbear.channels.cli import CLIChannel

# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestChannelPluginProtocol:
    """ChannelPlugin defines the expected interface."""

    def test_cli_channel_is_channel_plugin(self) -> None:
        """CLIChannel must satisfy the ChannelPlugin protocol."""
        channel: ChannelPlugin = CLIChannel()
        assert isinstance(channel, ChannelPlugin)

    def test_protocol_has_send(self) -> None:
        assert hasattr(ChannelPlugin, "send")

    def test_protocol_has_receive(self) -> None:
        assert hasattr(ChannelPlugin, "receive")

    def test_protocol_has_name(self) -> None:
        assert hasattr(ChannelPlugin, "name")


# ---------------------------------------------------------------------------
# CLIChannel
# ---------------------------------------------------------------------------


class TestCLIChannelName:
    """CLIChannel identifies itself."""

    def test_name_is_cli(self) -> None:
        assert CLIChannel().name == "cli"


class TestCLIChannelSend:
    """CLIChannel.send writes to stdout."""

    def test_send_writes_to_stdout(self) -> None:
        buf = StringIO()
        channel = CLIChannel(output=buf)
        asyncio.run(channel.send("hello world"))
        assert buf.getvalue() == "hello world\n"

    def test_send_multiple_messages(self) -> None:
        buf = StringIO()
        channel = CLIChannel(output=buf)
        asyncio.run(channel.send("first"))
        asyncio.run(channel.send("second"))
        assert buf.getvalue() == "first\nsecond\n"


class TestCLIChannelReceive:
    """CLIChannel.receive reads from stdin."""

    def test_receive_reads_line(self) -> None:
        buf = StringIO("user input\n")
        channel = CLIChannel(input=buf)
        result = asyncio.run(channel.receive())
        assert result == "user input"

    def test_receive_strips_trailing_newline(self) -> None:
        buf = StringIO("  spaces  \n")
        channel = CLIChannel(input=buf)
        result = asyncio.run(channel.receive())
        assert result == "  spaces  "

    def test_receive_empty_returns_none(self) -> None:
        """EOF / empty input returns None."""
        buf = StringIO("")
        channel = CLIChannel(input=buf)
        result = asyncio.run(channel.receive())
        assert result is None


class TestCLIChannelPrompt:
    """CLIChannel.receive with a prompt string."""

    def test_receive_with_prompt(self) -> None:
        in_buf = StringIO("answer\n")
        out_buf = StringIO()
        channel = CLIChannel(input=in_buf, output=out_buf)
        result = asyncio.run(channel.receive(prompt="> "))
        assert result == "answer"
        assert out_buf.getvalue() == "> "


# ---------------------------------------------------------------------------
# CLIChannel.send_file — task #395
# ---------------------------------------------------------------------------


class TestCLIChannelSendFile:
    """CLIChannel.send_file delivers file paths to the user."""

    def test_send_file_prints_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """send_file should print the file path to output."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        monkeypatch.setattr("os.startfile", lambda _p: None, raising=False)
        path = Path("screenshots/screenshot.png")
        asyncio.run(channel.send_file(path))
        assert str(path) in buf.getvalue()

    def test_send_file_prints_caption(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """send_file with caption should include caption in output."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        monkeypatch.setattr("os.startfile", lambda _p: None, raising=False)
        path = Path("screenshots/shot.png")
        asyncio.run(channel.send_file(path, caption="Error screenshot"))
        output = buf.getvalue()
        assert "Error screenshot" in output
        assert str(path) in output

    def test_send_file_no_caption(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """send_file without caption should still work."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        monkeypatch.setattr("os.startfile", lambda _p: None, raising=False)
        path = Path("screenshots/shot.png")
        asyncio.run(channel.send_file(path))
        assert str(path) in buf.getvalue()

    def test_send_file_calls_startfile_on_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On Windows, send_file should call os.startfile."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        opened: list[Path] = []
        monkeypatch.setattr("sys.platform", "win32")
        monkeypatch.setattr("os.startfile", opened.append, raising=False)
        asyncio.run(channel.send_file(Path("C:/screenshots/shot.png")))
        assert len(opened) == 1

    def test_send_file_no_startfile_on_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """On non-Windows, send_file should not call os.startfile."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        monkeypatch.setattr("sys.platform", "linux")
        path = Path("screenshots/shot.png")
        asyncio.run(channel.send_file(path))
        assert str(path) in buf.getvalue()
