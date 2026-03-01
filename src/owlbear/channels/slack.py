"""Slack channel adapter — SocketMode + AsyncWebClient for Slack I/O."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient

from owlbear.channels.slack_mrkdwn import markdown_to_mrkdwn

if TYPE_CHECKING:
    from pathlib import Path

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
            text=markdown_to_mrkdwn(message),
        )

    async def send_blocks(
        self,
        blocks: list[dict[str, Any]],
        text_fallback: str,
        *,
        thread_ts: str | None = None,
    ) -> None:
        """Send a Block Kit structured message to the configured Slack channel.

        Parameters
        ----------
        blocks:
            Non-empty list of Block Kit block dicts.
        text_fallback:
            Plain-text fallback — Slack uses it for notifications and
            accessibility readers.
        thread_ts:
            Optional thread timestamp to reply in a thread.

        Raises
        ------
        ValueError
            If *blocks* is empty.
        """
        if not blocks:
            msg = "blocks must be non-empty"
            raise ValueError(msg)

        kwargs: dict[str, Any] = {
            "channel": self._channel_id,
            "blocks": blocks,
            "text": text_fallback,
        }
        if thread_ts is not None:
            kwargs["thread_ts"] = thread_ts

        await self._web_client.chat_postMessage(**kwargs)

    async def send_image(
        self,
        file_or_bytes: str | Path | bytes,
        caption: str = "",
        *,
        thread_ts: str | None = None,
    ) -> None:
        """Upload an image file to the configured Slack channel.

        Accepts a file path (``str`` or :class:`~pathlib.Path`) or raw
        ``bytes``.  On upload failure the method logs a warning and falls
        back to :meth:`send` with the *caption* as plain text.

        Requires the ``files:write`` bot scope.

        Parameters
        ----------
        file_or_bytes:
            Path to the image file or raw image bytes.
        caption:
            Optional caption used as both ``title`` and ``initial_comment``.
        thread_ts:
            Optional thread timestamp to reply in a thread.
        """
        kwargs: dict[str, Any] = {
            "file": file_or_bytes,
            "channel": self._channel_id,
        }
        if caption:
            kwargs["title"] = caption
            kwargs["initial_comment"] = caption
        else:
            kwargs["title"] = "image"
        if thread_ts is not None:
            kwargs["thread_ts"] = thread_ts

        try:
            await self._web_client.files_upload_v2(**kwargs)
        except Exception:  # noqa: BLE001 — deliberate catch-all; fallback to plain text
            logger.warning(
                "files_upload_v2 failed, falling back to plain text",
                exc_info=True,
            )
            await self.send(caption or "[image upload failed]")

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
