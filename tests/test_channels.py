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

    def test_protocol_has_send_file(self) -> None:
        assert hasattr(ChannelPlugin, "send_file")

    def test_protocol_has_send_blocks(self) -> None:
        assert hasattr(ChannelPlugin, "send_blocks")

    def test_protocol_has_send_image(self) -> None:
        assert hasattr(ChannelPlugin, "send_image")


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
# CLIChannel.receive() EOF regression guard (#667)
# ---------------------------------------------------------------------------


class TestCLIChannelReceiveEofRegression:
    """CLIChannel.receive() must still return None on EOF (no regression from #513)."""

    def test_receive_returns_none_on_eof(self) -> None:
        """Empty stdin ⇒ None (EOF sentinel)."""
        buf = StringIO("")
        channel = CLIChannel(input=buf)
        result = asyncio.run(channel.receive())
        assert result is None

    def test_receive_returns_none_after_all_lines_consumed(self) -> None:
        """After reading all available lines, next receive returns None."""
        buf = StringIO("only line\n")
        channel = CLIChannel(input=buf)
        first = asyncio.run(channel.receive())
        assert first == "only line"
        second = asyncio.run(channel.receive())
        assert second is None


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


# ---------------------------------------------------------------------------
# Default protocol methods — send_blocks / send_image on CLIChannel (#675)
# ---------------------------------------------------------------------------


class TestCLIChannelDefaultSendBlocks:
    """CLIChannel inherits default send_blocks from ChannelPlugin."""

    def test_send_blocks_delegates_to_send(self) -> None:
        """Default send_blocks sends text_fallback via send()."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Hi"}}]
        asyncio.run(channel.send_blocks(blocks, "Plain fallback"))
        assert "Plain fallback" in buf.getvalue()

    def test_send_blocks_ignores_block_content(self) -> None:
        """Default send_blocks does not render block structure."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        blocks = [{"type": "header", "text": {"type": "plain_text", "text": "Title"}}]
        asyncio.run(channel.send_blocks(blocks, "Fallback text"))
        assert "Fallback text" in buf.getvalue()
        assert "Title" not in buf.getvalue()


class TestCLIChannelSendImage:
    """CLIChannel.send_image delegates to send_file for Path inputs."""

    def test_send_image_path_includes_file_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """send_image(Path) should include the file path in output (via send_file)."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        monkeypatch.setattr("os.startfile", lambda _p: None, raising=False)
        asyncio.run(channel.send_image(Path("shot.png"), caption="Screenshot"))
        output = buf.getvalue()
        assert "shot.png" in output
        assert "Screenshot" in output

    def test_send_image_path_calls_startfile_on_windows(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """send_image(Path) on Windows should open the file via os.startfile."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        opened: list[Path] = []
        monkeypatch.setattr("sys.platform", "win32")
        monkeypatch.setattr("os.startfile", opened.append, raising=False)
        asyncio.run(channel.send_image(Path("shot.png"), caption="Cap"))
        assert len(opened) == 1

    def test_send_image_bytes_sends_caption(self) -> None:
        """send_image(bytes) should send caption text (no file path)."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        asyncio.run(channel.send_image(b"fake-image", caption="Bytes img"))
        assert "Bytes img" in buf.getvalue()

    def test_send_image_bytes_no_caption(self) -> None:
        """send_image(bytes) without caption sends '[image]'."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        asyncio.run(channel.send_image(b"\x89PNG"))
        assert "[image]" in buf.getvalue()


# ---------------------------------------------------------------------------
# _BareChannel — minimal protocol stub for testing ChannelPlugin defaults (#677)
# ---------------------------------------------------------------------------


class _BareChannel(ChannelPlugin):
    """Minimal ChannelPlugin implementation — only ``name``, ``send``, ``receive``.

    All three default methods (``send_file``, ``send_blocks``, ``send_image``)
    should be inherited from :class:`ChannelPlugin` and delegate to ``send()``.
    """

    def __init__(self) -> None:
        self.sent: list[str] = []

    @property
    def name(self) -> str:
        return "bare"

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        return None


class TestBareChannelProtocolCompliance:
    """_BareChannel satisfies the runtime-checkable ChannelPlugin protocol (AC #6)."""

    def test_bare_channel_is_channel_plugin(self) -> None:
        assert isinstance(_BareChannel(), ChannelPlugin)


class TestChannelPluginSendFileDefault:
    """ChannelPlugin.send_file default delegates to send() (AC #1)."""

    def test_send_file_delegates_with_caption(self) -> None:
        ch = _BareChannel()
        asyncio.run(ch.send_file(Path("report.pdf"), caption="Report"))
        assert ch.sent == ["[Report] report.pdf"]

    def test_send_file_delegates_without_caption(self) -> None:
        ch = _BareChannel()
        asyncio.run(ch.send_file(Path("data.csv")))
        assert ch.sent == ["data.csv"]


class TestChannelPluginSendBlocksDefault:
    """ChannelPlugin.send_blocks default delegates to send() (AC #2)."""

    def test_send_blocks_sends_text_fallback(self) -> None:
        ch = _BareChannel()
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Hi"}}]
        asyncio.run(ch.send_blocks(blocks, "Plain fallback"))
        assert ch.sent == ["Plain fallback"]

    def test_send_blocks_ignores_block_content(self) -> None:
        ch = _BareChannel()
        blocks = [{"type": "header", "text": {"type": "plain_text", "text": "Title"}}]
        asyncio.run(ch.send_blocks(blocks, "Fallback only"))
        assert ch.sent == ["Fallback only"]
        assert "Title" not in ch.sent[0]


class TestChannelPluginSendImageDefault:
    """ChannelPlugin.send_image default delegates to send() (AC #3)."""

    def test_send_image_with_caption(self) -> None:
        ch = _BareChannel()
        asyncio.run(ch.send_image(Path("shot.png"), caption="Screenshot"))
        assert ch.sent == ["Screenshot"]

    def test_send_image_without_caption_sends_placeholder(self) -> None:
        ch = _BareChannel()
        asyncio.run(ch.send_image(b"\x89PNG"))
        assert ch.sent == ["[image]"]

    def test_send_image_bytes_with_caption(self) -> None:
        ch = _BareChannel()
        asyncio.run(ch.send_image(b"fake-img", caption="Diagram"))
        assert ch.sent == ["Diagram"]


class TestCLIChannelOverridesSendFile:
    """CLIChannel.send_file uses its own override, not the default (AC #4)."""

    def test_send_file_uses_write_not_send(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLIChannel.send_file writes directly to _output, not via send()."""
        buf = StringIO()
        channel = CLIChannel(output=buf)
        monkeypatch.setattr("os.startfile", lambda _p: None, raising=False)
        asyncio.run(channel.send_file(Path("file.txt"), caption="Note"))
        # CLIChannel override formats as "[caption] path\n" written directly
        assert buf.getvalue() == "[Note] file.txt\n"

    def test_send_file_override_differs_from_default(self) -> None:
        """CLIChannel.send_file output differs from what ChannelPlugin.send_file
        would produce (the default goes through send(), CLIChannel writes directly)."""
        bare = _BareChannel()
        # Both produce similar text, but CLIChannel bypasses send() entirely
        asyncio.run(bare.send_file(Path("x.txt"), caption="C"))
        assert bare.sent == ["[C] x.txt"]
        # CLIChannel.send_file is a different method (not inherited)
        assert CLIChannel.send_file is not ChannelPlugin.send_file


# ---------------------------------------------------------------------------
# SlackChannel overrides — send_blocks / send_image (AC #5)
# ---------------------------------------------------------------------------

try:
    from owlbear.channels.slack import SlackChannel

    _has_slack = True
except ImportError:
    _has_slack = False


@pytest.mark.skipif(not _has_slack, reason="slack_sdk not installed")
class TestSlackChannelOverrides:
    """SlackChannel.send_blocks and send_image are overrides, not defaults (AC #5)."""

    def test_send_blocks_is_own_override(self) -> None:
        """SlackChannel.send_blocks differs from the ChannelPlugin default."""
        assert SlackChannel.send_blocks is not ChannelPlugin.send_blocks

    def test_send_image_is_own_override(self) -> None:
        """SlackChannel.send_image differs from the ChannelPlugin default."""
        assert SlackChannel.send_image is not ChannelPlugin.send_image
