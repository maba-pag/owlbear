"""Tests for Slack sender validation — allowlist checks in _handle_socket_event.

Task #801 (RED phase) for #795: sender validation with config allowlist,
subtype filtering, WARNING logging, and bootstrap wiring.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# AC 1 — Config field exists with default empty list
# ---------------------------------------------------------------------------


class TestFromAC_ConfigField:
    """AC 1: OwlBearSettings.slack_allowed_user_ids with default empty list."""

    def test_field_exists_on_settings(self, default_settings: object) -> None:
        """slack_allowed_user_ids must be an attribute of OwlBearSettings."""
        assert hasattr(default_settings, "slack_allowed_user_ids"), (
            "OwlBearSettings must have a slack_allowed_user_ids field"
        )

    def test_default_is_empty_list(self, default_settings: object) -> None:
        """Default value must be an empty list (backwards compatible)."""
        assert default_settings.slack_allowed_user_ids == []

    def test_field_type_is_list_of_str(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Field must accept a list of string user IDs via env var."""
        import os

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("OWLBEAR_SLACK_ALLOWED_USER_IDS", '["U111","U222"]')

        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert settings.slack_allowed_user_ids == ["U111", "U222"]


# ---------------------------------------------------------------------------
# AC 2 — SlackChannel.__init__ accepts allowed_user_ids kwarg
# ---------------------------------------------------------------------------


class TestFromAC_ConstructorKwarg:
    """AC 2: SlackChannel.__init__ accepts allowed_user_ids: frozenset[str]."""

    def test_init_accepts_allowed_user_ids_kwarg(self) -> None:
        """Constructor must accept allowed_user_ids as keyword-only arg."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U111", "U222"}),
        )
        assert hasattr(channel, "_allowed_user_ids")

    def test_allowed_user_ids_stored_as_frozenset(self) -> None:
        """Stored value must be a frozenset for O(1) lookup."""
        from owlbear.channels.slack import SlackChannel

        ids = frozenset({"U111"})
        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=ids,
        )
        assert channel._allowed_user_ids == ids
        assert isinstance(channel._allowed_user_ids, frozenset)

    def test_default_is_empty_frozenset(self) -> None:
        """Default allowed_user_ids must be an empty frozenset."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        assert channel._allowed_user_ids == frozenset()


# ---------------------------------------------------------------------------
# AC 3 — Messages with subtype dropped; event still ACK'd
# ---------------------------------------------------------------------------


class TestFromAC_SubtypeFilter:
    """AC 3: _handle_socket_event drops message events that have a subtype field."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_bot_message_subtype_dropped(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Message with subtype='bot_message' must NOT be enqueued."""
        from owlbear.channels.slack import SlackChannel

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
                "subtype": "bot_message",
                "text": "I am a bot",
            },
        }

        await handler(mock_socket_instance, fake_request)

        assert channel._message_queue.empty(), "Bot message should not be enqueued"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_message_changed_subtype_dropped(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Message with subtype='message_changed' must NOT be enqueued."""
        from owlbear.channels.slack import SlackChannel

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
                "subtype": "message_changed",
                "text": "edited text",
            },
        }

        await handler(mock_socket_instance, fake_request)

        assert channel._message_queue.empty(), "message_changed should not be enqueued"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_subtype_message_acked_but_not_enqueued(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Event envelope must be ACK'd even when the message is dropped.

        Both conditions must hold: ACK'd AND not enqueued.
        """
        from owlbear.channels.slack import SlackChannel

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
                "subtype": "bot_message",
                "text": "bot loop",
            },
        }

        await handler(mock_socket_instance, fake_request)

        # Must be ACK'd
        mock_socket_instance.send_socket_mode_response.assert_awaited_once()
        # Must NOT be enqueued
        assert channel._message_queue.empty(), "Subtype message must be dropped"


# ---------------------------------------------------------------------------
# AC 4 — Disallowed user dropped when allowlist non-empty
# ---------------------------------------------------------------------------


class TestFromAC_UserAllowlistFilter:
    """AC 4: Messages from disallowed users dropped when allowlist is non-empty."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_disallowed_user_message_dropped(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Message from user NOT in allowlist must NOT be enqueued."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALLOWED"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_ATTACKER",
                "text": "pwn the bot",
            },
        }

        await handler(mock_socket_instance, fake_request)

        assert channel._message_queue.empty(), "Disallowed user must be dropped"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_disallowed_user_still_acked(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Event envelope ACK'd even when sender is rejected."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALLOWED"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_BADGUY",
                "text": "sneaky",
            },
        }

        await handler(mock_socket_instance, fake_request)

        mock_socket_instance.send_socket_mode_response.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_message_without_user_field_dropped_when_allowlist_set(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Message with no 'user' field (e.g. subtypeless webhook) is dropped."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALLOWED"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "text": "no user field here",
                # Note: no 'user' key at all
            },
        }

        await handler(mock_socket_instance, fake_request)

        assert channel._message_queue.empty(), "Missing user field should be rejected"


# ---------------------------------------------------------------------------
# AC 5 — Rejected sender logged at WARNING with user_id, no content
# ---------------------------------------------------------------------------


class TestFromAC_RejectionLogging:
    """AC 5/6: Rejected senders logged at WARNING with user_id, no message content."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_rejection_logged_at_warning(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Rejected sender must produce a WARNING-level log message."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALLOWED"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_INTRUDER",
                "text": "TOP SECRET CONTENT",
            },
        }

        with caplog.at_level(logging.WARNING, logger="owlbear.channels.slack"):
            await handler(mock_socket_instance, fake_request)

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1, "Must log at WARNING level"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_rejection_log_contains_user_id(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """WARNING log must include the rejected user_id."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALLOWED"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_INTRUDER",
                "text": "secret payload",
            },
        }

        with caplog.at_level(logging.WARNING, logger="owlbear.channels.slack"):
            await handler(mock_socket_instance, fake_request)

        warning_messages = " ".join(
            r.getMessage() for r in caplog.records if r.levelno == logging.WARNING
        )
        assert "U_INTRUDER" in warning_messages, "Warning must include user_id"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_rejection_log_excludes_message_content(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """WARNING log must NOT contain message content (security requirement)."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALLOWED"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        secret_text = "MY_SUPER_SECRET_PAYLOAD_xyz123"
        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_INTRUDER",
                "text": secret_text,
            },
        }

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_instance, fake_request)

        all_log_text = " ".join(r.getMessage() for r in caplog.records)
        assert secret_text not in all_log_text, (
            "Message content MUST NOT appear in any log line"
        )


# ---------------------------------------------------------------------------
# AC 6 — Allowed user message enqueued
# ---------------------------------------------------------------------------


class TestFromAC_AllowedUserEnqueued:
    """AC 6: Message from an allowed user is enqueued normally."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_allowed_user_message_enqueued(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """An allowed user's message must be placed on the queue."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALLOWED"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_ALLOWED",
                "text": "hello from allowed user",
            },
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "hello from allowed user"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_allowed_user_among_multiple_still_passes(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """When multiple user IDs are allowed, any valid one passes."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALICE", "U_BOB", "U_CAROL"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_BOB",
                "text": "hello from Bob",
            },
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "hello from Bob"


# ---------------------------------------------------------------------------
# AC 7 — Empty allowlist accepts all senders
# ---------------------------------------------------------------------------


class TestFromAC_EmptyAllowlistAcceptsAll:
    """AC 7: Empty allowlist (default) accepts all senders."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_empty_allowlist_accepts_any_user(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """With default empty allowlist, any user_id is accepted.

        This requires the _allowed_user_ids attribute to exist (empty frozenset)
        AND for the handler to accept-all when it's empty.
        """
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            # No allowed_user_ids — default empty frozenset
        )
        # Must have the attribute (proves constructor change exists)
        assert hasattr(channel, "_allowed_user_ids")
        assert channel._allowed_user_ids == frozenset()

        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_RANDOM_USER",
                "text": "anyone can talk",
            },
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "anyone can talk"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_explicit_empty_frozenset_same_as_default(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Explicitly passing frozenset() behaves the same as the default."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset(),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_WHOEVER",
                "text": "open door",
            },
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "open door"


# ---------------------------------------------------------------------------
# AC 8 — Bootstrap wiring: create_channel passes frozenset
# ---------------------------------------------------------------------------


class TestFromAC_BootstrapWiring:
    """AC 8: create_channel() passes frozenset(settings.slack_allowed_user_ids)."""

    @patch("owlbear.channels.slack.SlackChannel")
    def test_create_channel_passes_allowed_user_ids(
        self, mock_slack_cls: MagicMock
    ) -> None:
        """create_channel must pass allowed_user_ids kwarg to SlackChannel."""
        from owlbear.bootstrap.channel import create_channel
        from owlbear.config import OwlBearSettings

        settings = MagicMock(spec=OwlBearSettings)
        settings.slack_app_token = MagicMock()
        settings.slack_app_token.get_secret_value.return_value = "xapp-test"
        settings.slack_bot_token = MagicMock()
        settings.slack_bot_token.get_secret_value.return_value = "xoxb-test"
        settings.slack_channel_id = "C12345"
        settings.slack_allowed_user_ids = ["U111", "U222"]
        settings.slack_rate_limit_per_minute = 30

        mock_slack_cls.return_value = MagicMock()
        create_channel(settings, "slack")

        call_kwargs = mock_slack_cls.call_args.kwargs
        assert "allowed_user_ids" in call_kwargs, (
            "create_channel must pass allowed_user_ids to SlackChannel"
        )
        assert call_kwargs["allowed_user_ids"] == frozenset({"U111", "U222"})
        assert isinstance(call_kwargs["allowed_user_ids"], frozenset)

    @patch("owlbear.channels.slack.SlackChannel")
    def test_create_channel_passes_empty_frozenset_for_empty_list(
        self, mock_slack_cls: MagicMock
    ) -> None:
        """Empty config list → empty frozenset passed to SlackChannel."""
        from owlbear.bootstrap.channel import create_channel
        from owlbear.config import OwlBearSettings

        settings = MagicMock(spec=OwlBearSettings)
        settings.slack_app_token = MagicMock()
        settings.slack_app_token.get_secret_value.return_value = "xapp-test"
        settings.slack_bot_token = MagicMock()
        settings.slack_bot_token.get_secret_value.return_value = "xoxb-test"
        settings.slack_channel_id = "C12345"
        settings.slack_allowed_user_ids = []
        settings.slack_rate_limit_per_minute = 30

        mock_slack_cls.return_value = MagicMock()
        create_channel(settings, "slack")

        call_kwargs = mock_slack_cls.call_args.kwargs
        assert call_kwargs["allowed_user_ids"] == frozenset()


# ---------------------------------------------------------------------------
# AC 5 supplement — Subtype check before user check (ordering)
# ---------------------------------------------------------------------------


class TestFromAC_CheckOrdering:
    """AC 5 (from #795): Subtype check runs BEFORE user check."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_subtype_filter_catches_before_user_check(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A bot_message (no user field) must be caught by subtype filter,
        not fall through to the user check where it would KeyError or
        produce a confusing 'unauthorized sender' warning.
        """
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            allowed_user_ids=frozenset({"U_ALLOWED"}),
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        # bot_message subtype — has NO user field
        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "subtype": "bot_message",
                "bot_id": "B12345",
                "text": "bot says hi",
            },
        }

        with caplog.at_level(logging.WARNING, logger="owlbear.channels.slack"):
            await handler(mock_socket_instance, fake_request)

        # Should be dropped by subtype filter (not user filter)
        assert channel._message_queue.empty()

        # Should NOT produce a "rejected sender" WARNING (that's the user check)
        sender_warnings = [
            r
            for r in caplog.records
            if r.levelno == logging.WARNING and "sender" in r.getMessage().lower()
        ]
        assert len(sender_warnings) == 0, (
            "Subtype filter must catch bot_message BEFORE user validation logs a warning"
        )


# ===========================================================================
# Task #802 — Slack message rate limiting (RED phase)
# ===========================================================================


# ---------------------------------------------------------------------------
# AC 1 — Config field: slack_rate_limit_per_minute on OwlBearSettings
# ---------------------------------------------------------------------------


class TestFromAC_RateLimitConfig:
    """Config + constructor wiring for rate limiting."""

    def test_settings_field_exists(self, default_settings: object) -> None:
        """OwlBearSettings must have slack_rate_limit_per_minute attribute."""
        assert hasattr(default_settings, "slack_rate_limit_per_minute"), (
            "OwlBearSettings must have a slack_rate_limit_per_minute field"
        )

    def test_settings_field_default_is_30(self, default_settings: object) -> None:
        """Default value must be 30."""
        assert default_settings.slack_rate_limit_per_minute == 30

    def test_settings_field_is_int(self, default_settings: object) -> None:
        """Field type must be int."""
        assert isinstance(default_settings.slack_rate_limit_per_minute, int)

    def test_init_accepts_rate_limit_per_minute_kwarg(self) -> None:
        """SlackChannel.__init__ must accept rate_limit_per_minute keyword-only arg."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=10,
        )
        assert channel._rate_limit_per_minute == 10

    def test_init_rate_limit_default_is_zero(self) -> None:
        """Default rate_limit_per_minute must be 0 (disabled)."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        assert channel._rate_limit_per_minute == 0

    def test_init_creates_empty_rate_windows(self) -> None:
        """__init__ must initialise self._rate_windows as an empty dict."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=5,
        )
        assert channel._rate_windows == {}
        assert isinstance(channel._rate_windows, dict)


# ---------------------------------------------------------------------------
# AC 2 — Rate limit enforcement
# ---------------------------------------------------------------------------


class TestFromAC_RateLimitEnforcement:
    """Enforcement of sliding-window rate limiting in _handle_socket_event."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_message_within_limit_enqueued(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Message from user within limit (< rate_limit_per_minute) is enqueued."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=5,
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_USER1",
                "text": "hello rate limit",
            },
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "hello rate limit"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_message_at_limit_dropped(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Message at limit (== rate_limit_per_minute in last 60s) is dropped."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=3,
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        # Send exactly 3 messages (== limit) — all should be accepted
        for i in range(3):
            fake_request = MagicMock()
            fake_request.type = "events_api"
            fake_request.payload = {
                "event": {
                    "type": "message",
                    "channel_type": "im",
                    "user": "U_SPAMMER",
                    "text": f"msg {i}",
                },
            }
            await handler(mock_socket_instance, fake_request)

        # 4th message should be dropped
        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_SPAMMER",
                "text": "this should be dropped",
            },
        }
        await handler(mock_socket_instance, fake_request)

        # Should have exactly 3 messages, not 4
        enqueued = []
        while not channel._message_queue.empty():
            enqueued.append(channel._message_queue.get_nowait())
        assert len(enqueued) == 3, (
            f"Expected 3 enqueued messages, got {len(enqueued)}"
        )
        assert "this should be dropped" not in enqueued

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_dropped_message_logs_warning_with_user_id(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Dropped message must log WARNING with user_id."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=1,
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        # First message accepted
        req1 = MagicMock()
        req1.type = "events_api"
        req1.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_FLOOD",
                "text": "msg 1",
            },
        }
        await handler(mock_socket_instance, req1)

        # Second message should be rate-limited
        req2 = MagicMock()
        req2.type = "events_api"
        req2.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_FLOOD",
                "text": "SUPER_SECRET_FLOOD_CONTENT",
            },
        }

        with caplog.at_level(logging.WARNING, logger="owlbear.channels.slack"):
            await handler(mock_socket_instance, req2)

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1, "Must log at WARNING level when rate limited"

        warning_text = " ".join(r.getMessage() for r in warning_records)
        assert "U_FLOOD" in warning_text, "WARNING must include user_id"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_dropped_message_log_excludes_content(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Rate-limit WARNING must NOT contain message content (security)."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=1,
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        # First message accepted
        req1 = MagicMock()
        req1.type = "events_api"
        req1.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_FLOOD",
                "text": "msg 1",
            },
        }
        await handler(mock_socket_instance, req1)

        secret_text = "TOP_SECRET_FLOOD_PAYLOAD_xyz789"
        req2 = MagicMock()
        req2.type = "events_api"
        req2.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_FLOOD",
                "text": secret_text,
            },
        }

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_instance, req2)

        all_log_text = " ".join(r.getMessage() for r in caplog.records)
        assert secret_text not in all_log_text, (
            "Message content MUST NOT appear in any log line"
        )

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_rate_limit_zero_disables_limiting(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """rate_limit_per_minute=0 disables rate limiting entirely."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=0,
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        # Send 100 messages rapidly — all should be accepted
        for i in range(100):
            fake_request = MagicMock()
            fake_request.type = "events_api"
            fake_request.payload = {
                "event": {
                    "type": "message",
                    "channel_type": "im",
                    "user": "U_UNLIMITED",
                    "text": f"msg {i}",
                },
            }
            await handler(mock_socket_instance, fake_request)

        enqueued = []
        while not channel._message_queue.empty():
            enqueued.append(channel._message_queue.get_nowait())
        assert len(enqueued) == 100, (
            f"With rate_limit=0, all 100 messages should be accepted, got {len(enqueued)}"
        )


# ---------------------------------------------------------------------------
# AC 3 — Sliding window: expiry and per-user isolation
# ---------------------------------------------------------------------------


class TestFromAC_SlidingWindow:
    """Sliding window behaviour: expiry pruning and per-user isolation."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_expired_entries_pruned_message_accepted(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """Expired entries (>60s old) are pruned; message accepted after window slides."""
        import time
        from collections import deque

        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=2,
        )

        # Pre-fill the rate window with 2 expired timestamps (>60s ago)
        old_time = time.monotonic() - 120.0  # 2 minutes ago
        channel._rate_windows["U_PATIENT"] = deque([old_time, old_time])

        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "events_api"
        fake_request.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_PATIENT",
                "text": "after window slides",
            },
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "after window slides"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_per_user_isolation(
        self, mock_socket_cls: MagicMock
    ) -> None:
        """User A at limit does not affect user B."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
            rate_limit_per_minute=2,
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        # User A sends 2 messages (hits limit)
        for i in range(2):
            req = MagicMock()
            req.type = "events_api"
            req.payload = {
                "event": {
                    "type": "message",
                    "channel_type": "im",
                    "user": "U_ALICE",
                    "text": f"alice msg {i}",
                },
            }
            await handler(mock_socket_instance, req)

        # User A's 3rd message should be dropped
        req_a3 = MagicMock()
        req_a3.type = "events_api"
        req_a3.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_ALICE",
                "text": "alice blocked",
            },
        }
        await handler(mock_socket_instance, req_a3)

        # User B should STILL be able to send
        req_b = MagicMock()
        req_b.type = "events_api"
        req_b.payload = {
            "event": {
                "type": "message",
                "channel_type": "im",
                "user": "U_BOB",
                "text": "bob is fine",
            },
        }
        await handler(mock_socket_instance, req_b)

        enqueued = []
        while not channel._message_queue.empty():
            enqueued.append(channel._message_queue.get_nowait())

        assert "bob is fine" in enqueued, "User B must not be affected by User A's limit"
        assert "alice blocked" not in enqueued, "User A's excess message must be dropped"
        assert len(enqueued) == 3, (
            f"Expected 3 messages (2 alice + 1 bob), got {len(enqueued)}"
        )


# ---------------------------------------------------------------------------
# AC 4 — Bootstrap wiring: create_channel passes rate_limit_per_minute
# ---------------------------------------------------------------------------


class TestFromAC_RateLimitBootstrap:
    """Bootstrap wiring: create_channel passes rate_limit_per_minute from settings."""

    @patch("owlbear.channels.slack.SlackChannel")
    def test_create_channel_passes_rate_limit(
        self, mock_slack_cls: MagicMock
    ) -> None:
        """create_channel must pass rate_limit_per_minute to SlackChannel."""
        from owlbear.bootstrap.channel import create_channel
        from owlbear.config import OwlBearSettings

        settings = MagicMock(spec=OwlBearSettings)
        settings.slack_app_token = MagicMock()
        settings.slack_app_token.get_secret_value.return_value = "xapp-test"
        settings.slack_bot_token = MagicMock()
        settings.slack_bot_token.get_secret_value.return_value = "xoxb-test"
        settings.slack_channel_id = "C12345"
        settings.slack_allowed_user_ids = []
        settings.slack_rate_limit_per_minute = 30

        mock_slack_cls.return_value = MagicMock()
        create_channel(settings, "slack")

        call_kwargs = mock_slack_cls.call_args.kwargs
        assert "rate_limit_per_minute" in call_kwargs, (
            "create_channel must pass rate_limit_per_minute to SlackChannel"
        )
        assert call_kwargs["rate_limit_per_minute"] == 30
