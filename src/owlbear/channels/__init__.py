"""Communication channel adapters (CLI, Teams, etc.)."""

from __future__ import annotations

from owlbear.channels.base import ChannelPlugin
from owlbear.channels.cli import CLIChannel

__all__ = ["CLIChannel", "ChannelPlugin"]
