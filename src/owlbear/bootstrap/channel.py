"""Bootstrap channel factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear.channels.cli import CLIChannel

if TYPE_CHECKING:
    from owlbear.channels.base import ChannelPlugin
    from owlbear.config import OwlBearSettings


def create_channel(settings: OwlBearSettings, channel_name: str) -> ChannelPlugin:
    """Dispatch to the correct channel adapter.

    Raises
    ------
    ValueError
        If *channel_name* is not recognized.
    """
    if channel_name == "cli":
        return CLIChannel()

    if channel_name == "slack":
        from owlbear.channels.slack import SlackChannel  # noqa: PLC0415

        has_all_slack = (
            settings.slack_app_token and settings.slack_bot_token and settings.slack_channel_id
        )
        if not has_all_slack:
            msg = "Slack channel requires slack_app_token, slack_bot_token, and slack_channel_id"
            raise ValueError(msg)
        return SlackChannel(
            app_token=settings.slack_app_token.get_secret_value(),
            bot_token=settings.slack_bot_token.get_secret_value(),
            channel_id=settings.slack_channel_id,
            allowed_user_ids=frozenset(settings.slack_allowed_user_ids),
            rate_limit_per_minute=settings.slack_rate_limit_per_minute,
        )

    if channel_name == "voice":
        from owlbear.voice import VoiceChannel  # noqa: PLC0415

        return VoiceChannel()

    msg = f"Unknown channel: {channel_name!r}"
    raise ValueError(msg)
