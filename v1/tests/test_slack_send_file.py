"""Tests for SlackChannel.send_file delegation to send_image."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from owlbear.channels.slack import SlackChannel


def _make_channel() -> SlackChannel:
    """Create a SlackChannel with mocked internals for unit testing."""
    channel = SlackChannel(
        app_token="xapp-test",
        bot_token="xoxb-test",
        channel_id="C12345",
    )
    channel._web_client = AsyncMock()
    return channel


# ---------------------------------------------------------------------------
# Happy path: delegation with explicit caption
# ---------------------------------------------------------------------------


class TestFromAC_SendFileDelegation:  # noqa: N801
    """send_file delegates to send_image with correct arguments."""

    @pytest.mark.asyncio
    async def test_send_file_delegates_to_send_image_with_caption(self) -> None:
        """send_file(Path('report.pdf'), caption='Report') calls send_image."""
        channel = _make_channel()
        with patch.object(channel, "send_image", new_callable=AsyncMock) as mock_si:
            await channel.send_file(Path("report.pdf"), caption="Report")

            mock_si.assert_awaited_once_with(Path("report.pdf"), caption="Report")

    @pytest.mark.asyncio
    async def test_send_file_caption_forwarded_to_send_image(self) -> None:
        """The caption kwarg is forwarded verbatim to send_image."""
        channel = _make_channel()
        with patch.object(channel, "send_image", new_callable=AsyncMock) as mock_si:
            await channel.send_file(Path("chart.png"), caption="Weekly chart")

            call_kwargs = mock_si.call_args
            assert call_kwargs.kwargs.get("caption") == "Weekly chart" or (
                len(call_kwargs.args) > 1 and call_kwargs.args[1] == "Weekly chart"
            )


# ---------------------------------------------------------------------------
# No-caption default: path.name used as caption
# ---------------------------------------------------------------------------


class TestFromAC_SendFileNoCaptionDefault:  # noqa: N801
    """When caption is omitted, send_file uses path.name as caption."""

    @pytest.mark.asyncio
    async def test_no_caption_uses_path_name(self) -> None:
        """send_file(Path('data.csv')) delegates with caption='data.csv'."""
        channel = _make_channel()
        with patch.object(channel, "send_image", new_callable=AsyncMock) as mock_si:
            await channel.send_file(Path("data.csv"))

            mock_si.assert_awaited_once_with(Path("data.csv"), caption="data.csv")

    @pytest.mark.asyncio
    async def test_no_caption_nested_path_uses_filename_only(self) -> None:
        """Path('/tmp/reports/summary.xlsx').name should yield 'summary.xlsx'."""
        channel = _make_channel()
        with patch.object(channel, "send_image", new_callable=AsyncMock) as mock_si:
            await channel.send_file(Path("reports/summary.xlsx"))

            # caption should be the filename only, not the full path
            call_kwargs = mock_si.call_args
            caption_arg = call_kwargs.kwargs.get("caption") or (
                call_kwargs.args[1] if len(call_kwargs.args) > 1 else None
            )
            assert caption_arg == "summary.xlsx"

    @pytest.mark.asyncio
    async def test_explicit_none_caption_uses_path_name(self) -> None:
        """send_file(path, caption=None) should still use path.name."""
        channel = _make_channel()
        with patch.object(channel, "send_image", new_callable=AsyncMock) as mock_si:
            await channel.send_file(Path("output.json"), caption=None)

            mock_si.assert_awaited_once_with(Path("output.json"), caption="output.json")


# ---------------------------------------------------------------------------
# Error fallback: send_image raises → send_file propagates
# ---------------------------------------------------------------------------


class TestFromAC_SendFileErrorPropagation:  # noqa: N801
    """When send_image raises, send_file propagates the exception (no double fallback)."""

    @pytest.mark.asyncio
    async def test_send_image_error_propagates(self) -> None:
        """send_file must not swallow exceptions from send_image."""
        channel = _make_channel()
        with patch.object(
            channel, "send_image", new_callable=AsyncMock
        ) as mock_si:
            mock_si.side_effect = RuntimeError("upload failed")

            with pytest.raises(RuntimeError, match="upload failed"):
                await channel.send_file(Path("broken.pdf"), caption="Report")

    @pytest.mark.asyncio
    async def test_no_fallback_to_send_on_error(self) -> None:
        """send_file must NOT fall back to send() when send_image raises."""
        channel = _make_channel()
        with patch.object(
            channel, "send_image", new_callable=AsyncMock
        ) as mock_si, patch.object(
            channel, "send", new_callable=AsyncMock
        ) as mock_send:
            mock_si.side_effect = RuntimeError("upload failed")

            with pytest.raises(RuntimeError):
                await channel.send_file(Path("broken.pdf"), caption="Report")

            # send() must NOT be called — no double fallback
            mock_send.assert_not_awaited()


# ---------------------------------------------------------------------------
# Signature match
# ---------------------------------------------------------------------------


class TestFromAC_SendFileSignature:  # noqa: N801
    """send_file signature matches the ChannelPlugin protocol."""

    def test_send_file_is_overridden_on_slack_channel(self) -> None:
        """SlackChannel must define its own send_file, not just inherit the default."""
        assert "send_file" in SlackChannel.__dict__, (
            "SlackChannel must override send_file (not rely on ChannelPlugin default)"
        )

    def test_send_file_signature_has_path_param(self) -> None:
        """First positional param after self should be 'path' of type Path."""
        # Only valid once SlackChannel defines its own send_file
        assert "send_file" in SlackChannel.__dict__
        sig = inspect.signature(SlackChannel.__dict__["send_file"])
        params = list(sig.parameters.values())
        # params[0] is 'self', params[1] is 'path'
        assert params[1].name == "path"

    def test_send_file_signature_has_keyword_only_caption(self) -> None:
        """caption must be keyword-only with default None."""
        assert "send_file" in SlackChannel.__dict__
        sig = inspect.signature(SlackChannel.__dict__["send_file"])
        param = sig.parameters["caption"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY
        assert param.default is None
