"""Communication channel adapters (CLI, Slack, Teams, etc.)."""

from __future__ import annotations

from owlbear.channels.base import ChannelPlugin
from owlbear.channels.cli import CLIChannel
from owlbear.channels.slack import SlackChannel

__all__ = ["CLIChannel", "ChannelPlugin", "SlackChannel"]
