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
