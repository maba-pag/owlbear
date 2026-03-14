"""Slack channel adapter — SocketMode + AsyncWebClient for Slack I/O."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

try:
    from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
    from slack_sdk.socket_mode.aiohttp import SocketModeClient
    from slack_sdk.socket_mode.response import SocketModeResponse
    from slack_sdk.web.async_client import AsyncWebClient
except ImportError:  # pragma: no cover
    RateLimitErrorRetryHandler = None  # type: ignore[assignment]
    SocketModeClient = None  # type: ignore[assignment]
    SocketModeResponse = None  # type: ignore[assignment]
    AsyncWebClient = None  # type: ignore[assignment]

from owlbear.channels.base import ChannelPlugin
from owlbear.channels.slack_mrkdwn import markdown_to_mrkdwn

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from slack_sdk.socket_mode.async_client import AsyncBaseSocketModeClient
    from slack_sdk.socket_mode.request import SocketModeRequest

logger = logging.getLogger(__name__)


class SlackChannel(ChannelPlugin):
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
    allowed_user_ids:
        Slack user IDs permitted to send messages.  When non-empty, messages
        from any other sender are silently dropped.  An empty set (default)
        allows all senders.
    """

    def __init__(
        self,
        app_token: str,
        bot_token: str,
        channel_id: str,
        *,
        receive_timeout: float = 30.0,
        allowed_user_ids: frozenset[str] = frozenset(),
    ) -> None:
        if AsyncWebClient is None:  # pragma: no cover
            msg = "slack_sdk is not installed. Install with: uv sync --extra slack"
            raise ImportError(msg)

        self._app_token = app_token
        self._bot_token = bot_token
        self._channel_id = channel_id
        self._receive_timeout = receive_timeout
        self._allowed_user_ids = allowed_user_ids

        self._web_client = AsyncWebClient(
            token=bot_token,
            retry_handlers=[RateLimitErrorRetryHandler(max_retry_count=1)],
        )
        self._socket_client: SocketModeClient | None = None
        self._message_queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._thread_registry: dict[str, str] = {}
        self._action_callbacks: dict[str, Callable[[dict], Awaitable[None]]] = {}

    def register_action(
        self,
        action_id: str,
        callback: Callable[[dict], Awaitable[None]],
    ) -> None:
        """Register a callback for a specific interactive action.

        When a ``block_actions`` payload contains an action whose
        ``action_id`` matches, *callback* is awaited with the full
        action dict instead of pushing the value to the message queue.
        """
        self._action_callbacks[action_id] = callback

    # -- ChannelPlugin interface ---------------------------------------------

    @property
    def name(self) -> str:
        """Channel identifier."""
        return "slack"

    @property
    def channel_id(self) -> str:
        """The Slack channel ID for outgoing messages."""
        return self._channel_id

    async def send(
        self,
        message: str,
        *,
        context_key: str | None = None,
    ) -> None:
        """Send *message* to the configured Slack channel.

        Parameters
        ----------
        message:
            Text to send (Markdown is converted to mrkdwn).
        context_key:
            Optional context identifier (e.g. ``"project_id:task_id"``).
            When provided, the first message creates a thread and subsequent
            messages with the same key auto-thread.
        """
        kwargs: dict[str, Any] = {
            "channel": self._channel_id,
            "text": markdown_to_mrkdwn(message),
        }
        if context_key is not None:
            thread_ts = self._thread_registry.get(context_key)
            if thread_ts is not None:
                kwargs["thread_ts"] = thread_ts

        response = await self._web_client.chat_postMessage(**kwargs)

        if context_key is not None and context_key not in self._thread_registry:
            self._thread_registry[context_key] = response["ts"]

    async def send_blocks(
        self,
        blocks: list[dict[str, Any]],
        text_fallback: str,
        *,
        thread_ts: str | None = None,
        context_key: str | None = None,
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
        elif context_key is not None:
            registry_ts = self._thread_registry.get(context_key)
            if registry_ts is not None:
                kwargs["thread_ts"] = registry_ts

        response = await self._web_client.chat_postMessage(**kwargs)

        if context_key is not None and context_key not in self._thread_registry:
            self._thread_registry[context_key] = response["ts"]

    async def send_image(
        self,
        file_or_bytes: str | Path | bytes,
        caption: str = "",
        *,
        thread_ts: str | None = None,
        context_key: str | None = None,
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
        context_key:
            Optional context identifier for automatic thread registry
            integration.  Explicit *thread_ts* takes precedence.
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
        elif context_key is not None:
            registry_ts = self._thread_registry.get(context_key)
            if registry_ts is not None:
                kwargs["thread_ts"] = registry_ts

        try:
            response = await self._web_client.files_upload_v2(**kwargs)
        except Exception:  # noqa: BLE001 — deliberate catch-all; fallback to plain text
            logger.warning(
                "files_upload_v2 failed, falling back to plain text",
                exc_info=True,
            )
            await self.send(caption or "[image upload failed]", context_key=context_key)
            return

        if context_key is not None and context_key not in self._thread_registry:
            # Extract ts from the files_upload_v2 response when available.
            ts = self._extract_upload_ts(response)
            if ts:
                self._thread_registry[context_key] = ts
            else:
                logger.debug(
                    "Could not extract ts from files_upload_v2 response"
                    " for context_key=%s; skipping thread registration",
                    context_key,
                )

    @staticmethod
    def _extract_upload_ts(response: dict[str, Any]) -> str | None:
        """Best-effort extraction of message ts from a files_upload_v2 response."""
        try:
            shares = response["file"]["shares"]
            # shares has "public" and/or "private" dicts keyed by channel id
            for visibility in ("public", "private"):
                channels = shares.get(visibility, {})
                for entries in channels.values():
                    if entries and entries[0].get("ts"):
                        return entries[0]["ts"]  # type: ignore[no-any-return]
        except (KeyError, TypeError, IndexError):
            pass
        return None

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        """Wait for the next incoming message from Slack.

        Loops internally on idle timeouts so the daemon stays alive.
        Returns ``None`` only when the disconnect sentinel is dequeued.
        The *prompt* parameter is accepted for protocol compliance but
        ignored (Slack has no prompt concept).
        """
        while True:
            try:
                return await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=self._receive_timeout,
                )
            except TimeoutError:
                continue

    def get_or_create_thread(self, context_key: str) -> str | None:
        """Return the thread timestamp for *context_key*, or ``None``.

        The thread is "created" implicitly when the first message is sent
        via :meth:`send` or :meth:`send_blocks` with the same *context_key*.
        """
        return self._thread_registry.get(context_key)

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
        Messages with a ``subtype`` (bot echoes, edits, deletes) are silently
        dropped.  When :attr:`_allowed_user_ids` is non-empty, messages from
        unlisted senders are dropped and logged at WARNING.

        All ``events_api`` envelopes are acknowledged regardless of filtering.
        """
        if request.type == "events_api":
            # Always acknowledge
            response = SocketModeResponse(envelope_id=request.envelope_id)
            await client.send_socket_mode_response(response)

            event = request.payload.get("event", {})
            if event.get("type") == "message" and event.get("channel_type") == "im":
                # AC 3/5: drop messages with a subtype (bot_message, message_changed, etc.)
                if event.get("subtype"):
                    return

                # AC 4/7: drop disallowed senders when allowlist is non-empty
                if self._allowed_user_ids:
                    sender = event.get("user")
                    if sender not in self._allowed_user_ids:
                        logger.warning(
                            "Rejected message from disallowed sender: %s",
                            sender,
                        )
                        return

                text = event.get("text", "")
                await self._message_queue.put(text)
                logger.debug("Enqueued Slack message: %s", text[:80])

        elif request.type == "interactive":
            # Always acknowledge interactive envelopes
            response = SocketModeResponse(envelope_id=request.envelope_id)
            await client.send_socket_mode_response(response)

            payload = request.payload
            if payload.get("type") == "block_actions":
                for action in payload.get("actions", []):
                    aid = action.get("action_id", "")
                    if aid in self._action_callbacks:
                        await self._action_callbacks[aid](action)
                        logger.debug("Routed action to callback: %s", aid)
                    else:
                        value = action.get("value") or aid
                        await self._message_queue.put(value)
                        logger.debug("Enqueued interactive action: %s", value[:80])
