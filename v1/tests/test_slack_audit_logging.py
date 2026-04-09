"""Tests for Slack message audit logging — structured INFO log, content purge.

Task #804 (RED phase) for #797: accepted-message INFO log, content-leak
removal, subtype-drop DEBUG log, and rejection-warning regression guard.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_channel(*, allowed_user_ids: frozenset[str] = frozenset()) -> object:
    """Create a SlackChannel with sensible test defaults."""
    from owlbear.channels.slack import SlackChannel

    return SlackChannel(
        app_token="xapp-test",
        bot_token="xoxb-test",
        channel_id="C12345",
        allowed_user_ids=allowed_user_ids,
    )


def _make_message_request(
    *,
    user: str = "U_SENDER",
    text: str = "hello world",
    subtype: str | None = None,
) -> MagicMock:
    """Build a fake SocketModeRequest for a DM message event."""
    fake = MagicMock()
    fake.type = "events_api"
    event: dict[str, object] = {
        "type": "message",
        "channel_type": "im",
        "user": user,
        "text": text,
    }
    if subtype is not None:
        event["subtype"] = subtype
    fake.payload = {"event": event}
    return fake


async def _connect_and_get_handler(
    channel: object, mock_socket_cls: MagicMock
) -> object:
    """Wire a mock SocketModeClient and return the event handler."""
    mock_instance = AsyncMock()
    mock_instance.socket_mode_request_listeners = []
    mock_socket_cls.return_value = mock_instance
    await channel.connect()  # type: ignore[attr-defined]
    return mock_instance.socket_mode_request_listeners[0]


# ===========================================================================
# AC 2 — Accepted message logged at INFO with user_id + len(text), NOT content
# ===========================================================================


class TestFromAC_AcceptedMessageInfoLog:
    """AC 2: accepted message produces INFO log with user_id and text length."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_accepted_message_logged_at_info(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An accepted DM must produce at least one INFO-level log record."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        request = _make_message_request(user="U_ALICE", text="greetings")

        with caplog.at_level(logging.INFO, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_records) >= 1, "Accepted message must produce an INFO log"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_info_log_contains_user_id(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """INFO log for accepted message must include the sender's user_id."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        request = _make_message_request(user="U_BOB42", text="hey")

        with caplog.at_level(logging.INFO, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        info_text = " ".join(
            r.getMessage() for r in caplog.records if r.levelno == logging.INFO
        )
        assert "U_BOB42" in info_text, "INFO log must contain the sender user_id"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_info_log_contains_text_length(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """INFO log must include len(text), not the text itself."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        msg = "a" * 42
        request = _make_message_request(user="U_X", text=msg)

        with caplog.at_level(logging.INFO, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        info_text = " ".join(
            r.getMessage() for r in caplog.records if r.levelno == logging.INFO
        )
        assert "42" in info_text, "INFO log must contain the text length (42)"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_info_log_excludes_message_content(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """INFO log for accepted message must exist AND NOT contain content."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        secret = "SUPER_SECRET_PAYLOAD_xyz789"
        request = _make_message_request(user="U_X", text=secret)

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_records) >= 1, "INFO log must be emitted for accepted message"
        info_text = " ".join(r.getMessage() for r in info_records)
        assert secret not in info_text, (
            "INFO log must NOT contain message content"
        )


# ===========================================================================
# AC 3 — No log line contains message text (security invariant)
# ===========================================================================


class TestFromAC_ContentNeverLogged:
    """AC 3: no log emitted by _handle_socket_event contains event text."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_accepted_message_content_absent_from_all_logs(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """For an accepted message, text must not appear in ANY log line."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        secret = "PRIVATE_CONVERSATION_CONTENT_abc123"
        request = _make_message_request(user="U_A", text=secret)

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        all_log_text = " ".join(r.getMessage() for r in caplog.records)
        assert secret not in all_log_text, (
            "Message content must NEVER appear in any log line (accepted path)"
        )

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_rejected_message_content_absent_from_all_logs(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """For a rejected message, text must not appear in ANY log line."""
        channel = _make_channel(allowed_user_ids=frozenset({"U_ALLOWED"}))
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        secret = "REJECTED_USER_PRIVATE_MSG_def456"
        request = _make_message_request(user="U_INTRUDER", text=secret)

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        all_log_text = " ".join(r.getMessage() for r in caplog.records)
        assert secret not in all_log_text, (
            "Message content must NEVER appear in any log line (rejected path)"
        )

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_subtype_filtered_message_content_absent_from_all_logs(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """For a subtype-filtered message, text must not appear in ANY log line."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        secret = "BOT_LOOP_SECRET_CONTENT_ghi789"
        request = _make_message_request(
            user="U_BOT", text=secret, subtype="bot_message"
        )

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        all_log_text = " ".join(r.getMessage() for r in caplog.records)
        assert secret not in all_log_text, (
            "Message content must NEVER appear in any log line (subtype-filtered path)"
        )


# ===========================================================================
# AC 4 — Old content-leaking debug log removed
# ===========================================================================


class TestFromAC_DebugLineRemoved:
    """AC 4: 'Enqueued Slack message: ...' debug log pattern no longer emitted."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_no_enqueued_slack_message_debug_pattern(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The old 'Enqueued Slack message:' debug log must not appear."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        request = _make_message_request(user="U_X", text="some text here")

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        debug_messages = [
            r.getMessage()
            for r in caplog.records
            if r.levelno == logging.DEBUG
        ]
        for msg in debug_messages:
            assert "Enqueued Slack message" not in msg, (
                "Old content-leaking debug pattern must be removed"
            )

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_no_text_prefix_in_any_debug_log(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """No debug log should contain a prefix of the message text."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        text = "IDENTIFIABLE_PREFIX_TEXT_FOR_THIS_TEST"
        request = _make_message_request(user="U_X", text=text)

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        all_debug_text = " ".join(
            r.getMessage()
            for r in caplog.records
            if r.levelno == logging.DEBUG
        )
        assert text not in all_debug_text, (
            "Message text must not appear in debug logs"
        )


# ===========================================================================
# AC 5 — Subtype-filtered drops produce DEBUG log with subtype value
# ===========================================================================


class TestFromAC_SubtypeDropLogged:
    """AC 5: subtype-filtered drops produce a DEBUG log with the subtype value."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_bot_message_drop_produces_debug_log(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Dropping a bot_message subtype must log at DEBUG level."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        request = _make_message_request(
            user="U_BOT", text="bot content", subtype="bot_message"
        )

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        debug_text = " ".join(r.getMessage() for r in debug_records)
        assert "bot_message" in debug_text, (
            "DEBUG log must contain the subtype value 'bot_message'"
        )

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_message_changed_drop_produces_debug_log(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Dropping a message_changed subtype must log at DEBUG with value."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        request = _make_message_request(
            user="U_X", text="edit content", subtype="message_changed"
        )

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        debug_text = " ".join(
            r.getMessage()
            for r in caplog.records
            if r.levelno == logging.DEBUG
        )
        assert "message_changed" in debug_text, (
            "DEBUG log must contain the subtype value 'message_changed'"
        )

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_subtype_drop_debug_log_excludes_content(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """DEBUG log for subtype drop must exist AND NOT contain content."""
        channel = _make_channel()
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        secret = "SUBTYPE_SECRET_PAYLOAD_jkl012"
        request = _make_message_request(
            user="U_BOT", text=secret, subtype="bot_message"
        )

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 1, "Subtype drop must produce a DEBUG log"
        all_log_text = " ".join(r.getMessage() for r in debug_records)
        assert secret not in all_log_text, (
            "Subtype-drop DEBUG log must NOT contain message content"
        )


# ===========================================================================
# AC 6 — Rejection WARNING log unchanged (regression guard)
# ===========================================================================


class TestFromAC_RejectionLogUnchanged:
    """AC 6: existing #795 rejection WARNING is still present and correct."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_rejection_warning_still_present(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Rejected sender must still produce a WARNING-level log."""
        channel = _make_channel(allowed_user_ids=frozenset({"U_ALLOWED"}))
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        request = _make_message_request(user="U_INTRUDER", text="blocked msg")

        with caplog.at_level(logging.WARNING, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1, "Rejection WARNING must still be emitted"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_rejection_warning_contains_user_id(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Rejection WARNING must include the rejected user_id."""
        channel = _make_channel(allowed_user_ids=frozenset({"U_ALLOWED"}))
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        request = _make_message_request(user="U_BADACTOR", text="nope")

        with caplog.at_level(logging.WARNING, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        warning_text = " ".join(
            r.getMessage() for r in caplog.records if r.levelno == logging.WARNING
        )
        assert "U_BADACTOR" in warning_text, (
            "Rejection WARNING must contain the rejected user_id"
        )

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_rejection_warning_excludes_content(
        self, mock_socket_cls: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Rejection WARNING must NOT contain message content."""
        channel = _make_channel(allowed_user_ids=frozenset({"U_ALLOWED"}))
        handler = await _connect_and_get_handler(channel, mock_socket_cls)
        secret = "REJECTION_SECRET_CONTENT_mno345"
        request = _make_message_request(user="U_INTRUDER", text=secret)

        with caplog.at_level(logging.DEBUG, logger="owlbear.channels.slack"):
            await handler(mock_socket_cls.return_value, request)

        all_log_text = " ".join(r.getMessage() for r in caplog.records)
        assert secret not in all_log_text, (
            "Rejection WARNING must NOT contain message content"
        )
