"""Slack channel adapter — SocketMode + AsyncWebClient for Slack I/O."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient

if TYPE_CHECKING:
    from slack_sdk.socket_mode.async_client import AsyncBaseSocketModeClient
    from slack_sdk.socket_mode.request import SocketModeRequest

logger = logging.getLogger(__name__)


class SlackChannel:
    """Slack channel adapter implementing the :class:`ChannelPlugin` protocol.

    Uses ``AsyncWebClient`` for sending messages and ``SocketModeClient``
    for receiving real-time events via Socket Mode.

    Parameters
    ----------
    app_token:
        Slack app-level token (``xapp-...``) for Socket Mode.
    bot_token:
        Slack bot token (``xoxb-...``) for Web API calls.
    channel_id:
        Default Slack channel ID for outgoing messages.
    receive_timeout:
        Seconds to wait for an incoming message before returning ``None``.
    """

    def __init__(
        self,
        app_token: str,
        bot_token: str,
        channel_id: str,
        *,
        receive_timeout: float = 30.0,
    ) -> None:
        self._app_token = app_token
        self._bot_token = bot_token
        self._channel_id = channel_id
        self._receive_timeout = receive_timeout

        self._web_client = AsyncWebClient(token=bot_token)
        self._socket_client: SocketModeClient | None = None
        self._message_queue: asyncio.Queue[str | None] = asyncio.Queue()

    # -- ChannelPlugin interface ---------------------------------------------

    @property
    def name(self) -> str:
        """Channel identifier."""
        return "slack"

    @property
    def channel_id(self) -> str:
        """The Slack channel ID for outgoing messages."""
        return self._channel_id

    async def send(self, message: str) -> None:
        """Send *message* to the configured Slack channel."""
        await self._web_client.chat_postMessage(
            channel=self._channel_id,
            text=message,
        )

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        """Wait for the next incoming message from Slack.

        Returns ``None`` on timeout or disconnect.  The *prompt* parameter
        is accepted for protocol compliance but ignored (Slack has no
        prompt concept).
        """
        try:
            return await asyncio.wait_for(
                self._message_queue.get(),
                timeout=self._receive_timeout,
            )
        except TimeoutError:
            return None

    # -- Lifecycle -----------------------------------------------------------

    async def connect(self) -> None:
        """Create and connect the SocketModeClient."""
        self._socket_client = SocketModeClient(
            app_token=self._app_token,
            web_client=self._web_client,
        )
        self._socket_client.socket_mode_request_listeners.append(
            self._handle_socket_event,
        )
        await self._socket_client.connect()
        logger.info("SlackChannel connected via Socket Mode")

    async def disconnect(self) -> None:
        """Close the SocketModeClient and signal the receive queue."""
        if self._socket_client is not None:
            await self._socket_client.close()
            logger.info("SlackChannel disconnected")
        # Sentinel so any pending receive() returns None
        await self._message_queue.put(None)

    # -- Internal ------------------------------------------------------------

    async def _handle_socket_event(
        self,
        client: AsyncBaseSocketModeClient,
        request: SocketModeRequest,
    ) -> None:
        """Process incoming Socket Mode events.

        Only ``message`` events with ``channel_type == 'im'`` are enqueued.
        All ``events_api`` requests are acknowledged.
        """
        if request.type == "events_api":
            # Always acknowledge
            response = SocketModeResponse(envelope_id=request.envelope_id)
            await client.send_socket_mode_response(response)

            event = request.payload.get("event", {})
            if event.get("type") == "message" and event.get("channel_type") == "im":
                text = event.get("text", "")
                await self._message_queue.put(text)
                logger.debug("Enqueued Slack message: %s", text[:80])
