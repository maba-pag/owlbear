"""Tests for owlbear.channels.slack — SlackChannel adapter (ChannelPlugin)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.channels.base import ChannelPlugin
from owlbear.channels.slack import SlackChannel

# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestSlackChannelProtocol:
    """SlackChannel must satisfy the ChannelPlugin protocol."""

    def test_isinstance_channel_plugin(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        assert isinstance(channel, ChannelPlugin)


# ---------------------------------------------------------------------------
# Name property
# ---------------------------------------------------------------------------


class TestSlackChannelName:
    """SlackChannel.name returns 'slack'."""

    def test_name_is_slack(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        assert channel.name == "slack"


# ---------------------------------------------------------------------------
# send()
# ---------------------------------------------------------------------------


class TestSlackChannelSend:
    """SlackChannel.send calls chat_postMessage with correct args."""

    @pytest.mark.asyncio
    async def test_send_calls_chat_post_message(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        await channel.send("hello slack")

        channel._web_client.chat_postMessage.assert_awaited_once_with(
            channel="C12345",
            text="hello slack",
        )

    @pytest.mark.asyncio
    async def test_send_multiple_messages(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        await channel.send("first")
        await channel.send("second")

        assert channel._web_client.chat_postMessage.await_count == 2


# ---------------------------------------------------------------------------
# receive()
# ---------------------------------------------------------------------------


class TestSlackChannelReceive:
    """SlackChannel.receive returns text from queued message events."""

    @pytest.mark.asyncio
    async def test_receive_returns_message_text(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        # Simulate a message being placed on the internal queue
        await channel._message_queue.put("hi from user")

        result = await channel.receive()
        assert result == "hi from user"

    @pytest.mark.asyncio
    async def test_receive_returns_none_on_timeout(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            receive_timeout=0.05,
        )
        # Queue is empty — should timeout and return None
        result = await channel.receive(prompt="say something")
        assert result is None

    @pytest.mark.asyncio
    async def test_receive_returns_none_on_disconnect_sentinel(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        # Put None sentinel to signal disconnect
        await channel._message_queue.put(None)

        result = await channel.receive()
        assert result is None


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


class TestSlackChannelConnect:
    """SlackChannel.connect creates SocketModeClient and connects."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_connect_creates_socket_client(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        await channel.connect()

        mock_socket_cls.assert_called_once()
        mock_socket_instance.connect.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_connect_registers_event_handler(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        await channel.connect()

        # socket_mode_request_listeners should have been appended to
        assert len(mock_socket_instance.socket_mode_request_listeners) > 0


# ---------------------------------------------------------------------------
# disconnect()
# ---------------------------------------------------------------------------


class TestSlackChannelDisconnect:
    """SlackChannel.disconnect closes SocketModeClient."""

    @pytest.mark.asyncio
    async def test_disconnect_closes_socket_client(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        mock_socket = AsyncMock()
        channel._socket_client = mock_socket

        await channel.disconnect()

        mock_socket.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_sends_none_sentinel(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._socket_client = AsyncMock()

        await channel.disconnect()

        # Queue should contain the None sentinel for receive() to return None
        result = channel._message_queue.get_nowait()
        assert result is None

    @pytest.mark.asyncio
    async def test_disconnect_noop_when_not_connected(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        # No socket client set — should not raise
        await channel.disconnect()


# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------


class TestSlackChannelEventHandler:
    """The internal event handler enqueues message text."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_message_event_enqueued(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        await channel.connect()

        # Grab the registered handler
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        # Simulate a message.im event
        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "text": "hello from DM",
            },
        }

        await handler(mock_socket_instance, fake_request)

        # The message text should be on the queue
        result = channel._message_queue.get_nowait()
        assert result == "hello from DM"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_non_message_event_ignored(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        await channel.connect()

        handler = mock_socket_instance.socket_mode_request_listeners[0]

        # Simulate an event that is NOT a message
        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "reaction_added",
            },
        }

        await handler(mock_socket_instance, fake_request)

        # Queue should be empty — event was ignored
        assert channel._message_queue.empty()

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_handler_sends_ack(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        await channel.connect()

        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "text": "ack me",
            },
        }

        await handler(mock_socket_instance, fake_request)

        # Handler should acknowledge the request
        mock_socket_instance.send_socket_mode_response.assert_awaited_once()


# ---------------------------------------------------------------------------
# send_blocks()  (task #326)
# ---------------------------------------------------------------------------


class TestSlackChannelSendBlocks:
    """SlackChannel.send_blocks sends Block Kit messages via chat_postMessage."""

    @pytest.mark.asyncio
    async def test_send_blocks_calls_chat_post_message_with_blocks(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Hello"}},
        ]
        await channel.send_blocks(blocks, text_fallback="Hello")

        channel._web_client.chat_postMessage.assert_awaited_once_with(
            channel="C12345",
            blocks=blocks,
            text="Hello",
        )

    @pytest.mark.asyncio
    async def test_send_blocks_passes_block_kit_structure(self) -> None:
        """Blocks must be passed as a list[dict] matching Block Kit format."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        blocks: list[dict] = [
            {"type": "header", "text": {"type": "plain_text", "text": "Title"}},
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Option 1*"},
            },
        ]
        await channel.send_blocks(blocks, text_fallback="Title")

        call_kwargs = channel._web_client.chat_postMessage.call_args.kwargs
        sent_blocks = call_kwargs["blocks"]
        assert isinstance(sent_blocks, list)
        assert all(isinstance(b, dict) for b in sent_blocks)
        assert sent_blocks[0]["type"] == "header"
        assert sent_blocks[1]["type"] == "divider"
        assert sent_blocks[2]["type"] == "section"

    @pytest.mark.asyncio
    async def test_send_blocks_forwards_thread_ts(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "reply"}},
        ]
        await channel.send_blocks(
            blocks,
            text_fallback="reply",
            thread_ts="1234567890.123456",
        )

        channel._web_client.chat_postMessage.assert_awaited_once_with(
            channel="C12345",
            blocks=blocks,
            text="reply",
            thread_ts="1234567890.123456",
        )

    @pytest.mark.asyncio
    async def test_send_blocks_without_thread_ts_omits_it(self) -> None:
        """When thread_ts is None, it should NOT appear in the API call."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        blocks = [{"type": "divider"}]
        await channel.send_blocks(blocks, text_fallback="divider")

        call_kwargs = channel._web_client.chat_postMessage.call_args.kwargs
        assert "thread_ts" not in call_kwargs

    @pytest.mark.asyncio
    async def test_send_blocks_empty_blocks_raises_value_error(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        with pytest.raises(ValueError, match=r"[Bb]locks"):
            await channel.send_blocks([], text_fallback="empty")

        # chat_postMessage should NOT have been called
        channel._web_client.chat_postMessage.assert_not_awaited()


# ---------------------------------------------------------------------------
# send_image()  (task #328)
# ---------------------------------------------------------------------------


class TestSlackChannelSendImage:
    """SlackChannel.send_image uploads files via files_upload_v2."""

    @pytest.mark.asyncio
    async def test_send_image_path_calls_files_upload_v2(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        await channel.send_image("/images/chart.png", caption="Chart")

        channel._web_client.files_upload_v2.assert_awaited_once_with(
            file="/images/chart.png",
            channel="C12345",
            title="Chart",
            initial_comment="Chart",
        )

    @pytest.mark.asyncio
    async def test_send_image_bytes_calls_files_upload_v2(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        image_data = b"\x89PNG\r\n\x1a\nfake-image-bytes"
        await channel.send_image(image_data, caption="Screenshot")

        channel._web_client.files_upload_v2.assert_awaited_once_with(
            file=image_data,
            channel="C12345",
            title="Screenshot",
            initial_comment="Screenshot",
        )

    @pytest.mark.asyncio
    async def test_send_image_forwards_thread_ts(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        await channel.send_image(
            "/images/img.png",
            caption="Threaded",
            thread_ts="9876543210.654321",
        )

        channel._web_client.files_upload_v2.assert_awaited_once_with(
            file="/images/img.png",
            channel="C12345",
            title="Threaded",
            initial_comment="Threaded",
            thread_ts="9876543210.654321",
        )

    @pytest.mark.asyncio
    async def test_send_image_caption_becomes_initial_comment_and_title(self) -> None:
        """The caption param must map to both initial_comment and title."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        await channel.send_image(b"data", caption="My caption text")

        call_kwargs = channel._web_client.files_upload_v2.call_args.kwargs
        assert call_kwargs["initial_comment"] == "My caption text"
        assert call_kwargs["title"] == "My caption text"

    @pytest.mark.asyncio
    async def test_send_image_without_caption_uses_defaults(self) -> None:
        """When caption is None, title defaults to 'image' and no initial_comment."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        await channel.send_image(b"data")

        call_kwargs = channel._web_client.files_upload_v2.call_args.kwargs
        assert call_kwargs["title"] == "image"
        assert "initial_comment" not in call_kwargs or call_kwargs["initial_comment"] is None

    @pytest.mark.asyncio
    async def test_send_image_error_fallback_sends_caption_as_text(self) -> None:
        """When files_upload_v2 raises, fall back to send(caption)."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.side_effect = Exception("upload failed")

        await channel.send_image("/images/pic.png", caption="Fallback text")

        # files_upload_v2 was attempted
        channel._web_client.files_upload_v2.assert_awaited_once()
        # Fell back to chat_postMessage with the caption
        channel._web_client.chat_postMessage.assert_awaited_once_with(
            channel="C12345",
            text="Fallback text",
        )

    @pytest.mark.asyncio
    async def test_send_image_error_without_caption_sends_generic(self) -> None:
        """Fallback with no caption sends a generic failure notice."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.side_effect = Exception("upload failed")

        await channel.send_image("/images/pic.png")

        channel._web_client.chat_postMessage.assert_awaited_once()
        call_kwargs = channel._web_client.chat_postMessage.call_args.kwargs
        assert "text" in call_kwargs
        # Should contain some indication of failure, not be empty
        assert call_kwargs["text"]
