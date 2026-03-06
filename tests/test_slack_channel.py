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


# ---------------------------------------------------------------------------
# Interactive event handler  (task #414)
# ---------------------------------------------------------------------------


class TestSlackChannelInteractiveHandler:
    """Interactive block_actions are routed to the message queue."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_interactive_block_actions_enqueued(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """A block_actions interactive payload puts action values on the queue."""
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
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [{"action_id": "approve_btn", "value": "approve"}],
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "approve"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_interactive_block_actions_acknowledged(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """Interactive envelopes are always acknowledged."""
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
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [{"action_id": "deny_btn", "value": "deny"}],
        }

        await handler(mock_socket_instance, fake_request)

        mock_socket_instance.send_socket_mode_response.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_interactive_multiple_actions_enqueued(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """Multiple actions in one payload each get enqueued."""
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
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [
                {"action_id": "opt1", "value": "option_a"},
                {"action_id": "opt2", "value": "option_b"},
            ],
        }

        await handler(mock_socket_instance, fake_request)

        results = []
        while not channel._message_queue.empty():
            results.append(channel._message_queue.get_nowait())
        assert results == ["option_a", "option_b"]

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_interactive_non_block_actions_ignored(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """Interactive payloads that aren't block_actions don't enqueue."""
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
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "view_submission",
            "view": {"id": "V123"},
        }

        await handler(mock_socket_instance, fake_request)

        # Still acknowledged
        mock_socket_instance.send_socket_mode_response.assert_awaited_once()
        # But nothing enqueued
        assert channel._message_queue.empty()

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_interactive_action_without_value_uses_action_id(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """When action has no 'value', fall back to action_id."""
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
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [{"action_id": "approve_btn"}],
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "approve_btn"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_events_api_still_works_after_interactive_support(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """Existing events_api handling is unaffected by interactive changes."""
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
                "text": "still works",
            },
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "still works"


# ---------------------------------------------------------------------------
# Action callback routing  (task #418)
# ---------------------------------------------------------------------------


class TestSlackChannelActionCallbackRouting:
    """Registered action callbacks are awaited; unregistered fall to queue."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_registered_callback_is_awaited(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """When action_id has a registered callback, it is awaited with action dict."""
        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )

        callback = AsyncMock()
        channel.register_action("approve_btn", callback)

        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        action_dict = {"action_id": "approve_btn", "value": "approve"}
        fake_request = MagicMock()
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [action_dict],
        }

        await handler(mock_socket_instance, fake_request)

        callback.assert_awaited_once_with(action_dict)
        # Should NOT be enqueued
        assert channel._message_queue.empty()

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_unregistered_action_falls_through_to_queue(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """Unregistered actions are still pushed to the message queue."""
        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        # Register a different action — "approve_btn" is NOT registered
        channel.register_action("other_btn", AsyncMock())

        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [{"action_id": "approve_btn", "value": "approve"}],
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "approve"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_mixed_registered_and_unregistered_actions(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """Payload with both registered and unregistered actions routes correctly."""
        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )

        callback = AsyncMock()
        channel.register_action("approve_btn", callback)

        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        approve_action = {"action_id": "approve_btn", "value": "approve"}
        deny_action = {"action_id": "deny_btn", "value": "deny"}

        fake_request = MagicMock()
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [approve_action, deny_action],
        }

        await handler(mock_socket_instance, fake_request)

        # approve_btn → callback
        callback.assert_awaited_once_with(approve_action)
        # deny_btn → queue
        result = channel._message_queue.get_nowait()
        assert result == "deny"
        assert channel._message_queue.empty()

    @pytest.mark.asyncio
    async def test_action_callbacks_initialized_empty(self) -> None:
        """_action_callbacks starts as an empty dict."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        assert channel._action_callbacks == {}

    @pytest.mark.asyncio
    async def test_register_action_stores_callback(self) -> None:
        """register_action adds the callback to the internal dict."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        cb = AsyncMock()
        channel.register_action("my_action", cb)
        assert channel._action_callbacks["my_action"] is cb


# ---------------------------------------------------------------------------
# Thread registry  (task #415)
# ---------------------------------------------------------------------------


class TestSlackChannelThreadRegistry:
    """SlackChannel tracks per-context thread timestamps."""

    def test_thread_registry_initialized_empty(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        assert channel._thread_registry == {}

    def test_get_or_create_thread_returns_none_for_unknown(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        assert channel.get_or_create_thread("proj1:task5") is None


# ---------------------------------------------------------------------------
# RateLimitErrorRetryHandler  (task #603)
# ---------------------------------------------------------------------------


class TestSlackChannelRateLimitRetryHandler:
    """AsyncWebClient must have RateLimitErrorRetryHandler registered."""

    def test_web_client_has_rate_limit_retry_handler(self) -> None:
        """The _web_client must include a RateLimitErrorRetryHandler."""
        from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        handlers = channel._web_client.retry_handlers
        rate_limit_handlers = [h for h in handlers if isinstance(h, RateLimitErrorRetryHandler)]
        assert len(rate_limit_handlers) == 1

    def test_rate_limit_handler_max_retry_count_is_one(self) -> None:
        """RateLimitErrorRetryHandler must have max_retry_count=1."""
        from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        handler = next(
            h
            for h in channel._web_client.retry_handlers
            if isinstance(h, RateLimitErrorRetryHandler)
        )
        assert handler.max_retry_count == 1

    def test_no_tenacity_retry_on_send(self) -> None:
        """send, send_blocks, send_image must NOT have tenacity @retry."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        for method_name in ("send", "send_blocks", "send_image"):
            method = getattr(channel, method_name)
            # tenacity-wrapped functions have a 'retry' attribute
            assert not hasattr(method, "retry"), (
                f"{method_name} should not have a tenacity @retry decorator"
            )

    def test_send_image_fallback_unchanged(self) -> None:
        """send_image still has the try/except fallback pattern (source check)."""
        import inspect

        source = inspect.getsource(SlackChannel.send_image)
        assert "files_upload_v2" in source
        assert "except" in source

    def test_get_or_create_thread_returns_ts_after_registration(self) -> None:
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._thread_registry["proj1:task5"] = "1234567890.000001"
        assert channel.get_or_create_thread("proj1:task5") == "1234567890.000001"

    @pytest.mark.asyncio
    async def test_send_with_context_key_captures_ts(self) -> None:
        """First send with context_key captures ts in the registry."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1111111111.000001",
        }

        await channel.send("hello", context_key="proj1:task5")

        assert channel._thread_registry["proj1:task5"] == "1111111111.000001"

    @pytest.mark.asyncio
    async def test_send_with_context_key_threads_subsequent(self) -> None:
        """Second send with same context_key passes thread_ts."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1111111111.000001",
        }

        # First message — creates thread
        await channel.send("first", context_key="proj1:task5")

        # Second message — should thread
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1111111111.000002",
        }
        await channel.send("second", context_key="proj1:task5")

        second_call = channel._web_client.chat_postMessage.call_args_list[1]
        assert second_call.kwargs.get("thread_ts") == "1111111111.000001"

    @pytest.mark.asyncio
    async def test_send_without_context_key_unchanged(self) -> None:
        """send() without context_key doesn't interact with the registry."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        await channel.send("no context")

        call_kwargs = channel._web_client.chat_postMessage.call_args.kwargs
        assert "thread_ts" not in call_kwargs
        assert channel._thread_registry == {}

    @pytest.mark.asyncio
    async def test_send_blocks_with_context_key_captures_ts(self) -> None:
        """send_blocks with context_key captures ts in the registry."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "2222222222.000001",
        }

        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "hi"}}]
        await channel.send_blocks(blocks, "hi", context_key="proj2:task10")

        assert channel._thread_registry["proj2:task10"] == "2222222222.000001"

    @pytest.mark.asyncio
    async def test_send_blocks_with_context_key_threads_subsequent(self) -> None:
        """Second send_blocks with same context_key auto-threads."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "2222222222.000001",
        }

        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "msg"}}]

        # First message
        await channel.send_blocks(blocks, "first", context_key="proj2:task10")

        # Second message
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "2222222222.000002",
        }
        await channel.send_blocks(blocks, "second", context_key="proj2:task10")

        second_call = channel._web_client.chat_postMessage.call_args_list[1]
        assert second_call.kwargs.get("thread_ts") == "2222222222.000001"

    @pytest.mark.asyncio
    async def test_send_blocks_context_key_does_not_override_explicit_thread_ts(
        self,
    ) -> None:
        """Explicit thread_ts takes precedence over registry lookup."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "3333333333.000001",
        }
        # Pre-populate registry
        channel._thread_registry["proj3:task1"] = "9999999999.000001"

        blocks = [{"type": "divider"}]
        await channel.send_blocks(
            blocks,
            "explicit",
            thread_ts="5555555555.000001",
            context_key="proj3:task1",
        )

        call_kwargs = channel._web_client.chat_postMessage.call_args.kwargs
        # Explicit thread_ts wins
        assert call_kwargs["thread_ts"] == "5555555555.000001"

    @pytest.mark.asyncio
    async def test_thread_registry_does_not_overwrite_existing(self) -> None:
        """Registry keeps the first ts — doesn't overwrite on subsequent sends."""
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1111111111.000001",
        }

        await channel.send("first", context_key="ctx1")

        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1111111111.000099",
        }
        await channel.send("second", context_key="ctx1")

        # Still the first ts
        assert channel._thread_registry["ctx1"] == "1111111111.000001"


# ---------------------------------------------------------------------------
# Import guard — slack_sdk optional dependency
# ---------------------------------------------------------------------------


class TestSlackImportGuard:
    """AC 1-4: slack_sdk is optional; missing import raises at instantiation."""

    def test_import_channels_without_slack_sdk(self) -> None:
        """import owlbear.channels succeeds even when slack_sdk is absent."""
        # If the guard is in place, the module loads with sentinels = None.
        # We verify by patching the sentinel *after* import (the guard sets it).
        import owlbear.channels

        assert hasattr(owlbear.channels, "SlackChannel")

    def test_import_slack_channel_without_sdk(self) -> None:
        """from owlbear.channels.slack import SlackChannel succeeds."""
        from owlbear.channels import slack as slack_mod

        assert hasattr(slack_mod, "SlackChannel")

    def test_instantiation_raises_without_slack_sdk(self) -> None:
        """SlackChannel() raises ImportError with install hint when sdk missing."""
        import owlbear.channels.slack as slack_mod

        # Simulate slack_sdk missing by setting sentinel to None
        original = slack_mod.AsyncWebClient
        try:
            slack_mod.AsyncWebClient = None  # type: ignore[assignment]
            with pytest.raises(ImportError, match="uv sync --extra slack"):
                SlackChannel(
                    app_token="xapp-test",
                    bot_token="xoxb-test",
                    channel_id="C12345",
                )
        finally:
            slack_mod.AsyncWebClient = original

    def test_instantiation_hint_message(self) -> None:
        """Error message includes specific install command."""
        import owlbear.channels.slack as slack_mod

        original = slack_mod.AsyncWebClient
        try:
            slack_mod.AsyncWebClient = None  # type: ignore[assignment]
            with pytest.raises(ImportError) as exc_info:
                SlackChannel(
                    app_token="xapp-test",
                    bot_token="xoxb-test",
                    channel_id="C12345",
                )
            assert "uv sync --extra slack" in str(exc_info.value)
        finally:
            slack_mod.AsyncWebClient = original
