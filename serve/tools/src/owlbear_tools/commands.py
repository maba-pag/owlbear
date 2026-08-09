"""Central registry and help renderer for OwlBear workspace commands."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_RESET = "\033[0m"
_BOLD = "\033[1m"
_MAGENTA = "\033[35m"
_GREEN = "\033[32m"
_INFO = "\N{INFORMATION SOURCE}"
_GROUP_STYLES = {
    "Everyday": "\033[36m",
    "Setup": "\033[34m",
    "Maintenance": "\033[33m",
}


@dataclass(frozen=True)
class Command:
    """One user-facing workspace command."""

    name: str
    usage: str
    summary: str
    group: str
    development_only: bool = False


COMMANDS = (
    Command("help", "uv run help [TOPIC]", "Show this command reference.", "Everyday"),
    Command(
        "lint",
        "uv run lint [OPTIONS] [FILE ...]",
        "Staged or explicit files; --all selects repository; safe fixes default.",
        "Everyday",
    ),
    Command(
        "lint-full",
        "uv run lint-full [OPTIONS]",
        "lint --all plus frontend and MegaLinter checks; safe fixes default.",
        "Everyday",
        development_only=True,
    ),
    Command(
        "typecheck",
        "uv run typecheck",
        "Type-check the Cockpit frontend.",
        "Everyday",
        development_only=True,
    ),
    Command(
        "megalint",
        "uv run megalint [OPTIONS]",
        "Run MegaLinter; safe fixes default.",
        "Everyday",
        development_only=True,
    ),
    Command("cockpit", "uv run cockpit [list] [OPTIONS]", "Start or list Cockpit instances.", "Everyday"),
    Command("todo", "uv run todo", "Report documentation TODO markers.", "Everyday"),
    Command("hooks-install", "uv run hooks-install", "Install Git hooks and hook environments.", "Setup"),
    Command(
        "setup-project",
        "uv run setup-project [OPTIONS] [PATH]",
        "Initialize an OwlBear project.",
        "Setup",
    ),
    Command("doctor", "uv run doctor [PATH]", "Check an OwlBear project without changing it.", "Setup"),
    Command(
        "integration-target",
        "uv run integration-target [BRANCH]",
        "Show or safely change the Delivery target branch.",
        "Setup",
    ),
    Command(
        "deps-status",
        "uv run deps-status",
        "Report installed, allowed, and latest versions without updating locks.",
        "Maintenance",
        development_only=True,
    ),
    Command(
        "deps-sync",
        "uv run deps-sync",
        "Install existing locks exactly; do not update versions or ranges.",
        "Maintenance",
        development_only=True,
    ),
    Command(
        "pds-sync",
        "uv run pds-sync",
        "Transactionally refresh self-hosted PDS assets.",
        "Maintenance",
        development_only=True,
    ),
    Command(
        "megalint-clean",
        "uv run megalint-clean [--yes]",
        "Preview and remove obsolete MegaLinter images.",
        "Maintenance",
        development_only=True,
    ),
)

_TOPICS = {
    "everyday": "Everyday",
    "lint": "Everyday",
    "setup": "Setup",
    "maintenance": "Maintenance",
}


def _supports_color(stream: TextIO) -> bool:
    return "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb" and stream.isatty()


def _style(text: str, *codes: str, stream: TextIO) -> str:
    if not _supports_color(stream):
        return text
    return f"{''.join(codes)}{text}{_RESET}"


def command_footer(stream: TextIO | None = None) -> str:
    """Return the concise discovery hint printed by commands."""
    output = stream or sys.stderr
    icon = _style(_INFO, _BOLD, _MAGENTA, stream=output)
    command = _style("uv run help", _BOLD, _GREEN, stream=output)
    return f"{icon} More commands and options: {command}"


def _is_development_checkout() -> bool:
    root = Path.cwd()
    return root.resolve() == _REPOSITORY_ROOT and (root / ".pre-commit-config.yaml").is_file()


def help_main() -> None:
    """Render the full command reference or one topic."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("topic", nargs="?", choices=sorted(_TOPICS))
    parser.add_argument("-h", "--help", action="help")
    args = parser.parse_args()
    selected = _TOPICS.get(args.topic) if args.topic else None
    development = _is_development_checkout()
    visible_commands = [
        command
        for command in COMMANDS
        if (selected is None or command.group == selected) and (development or not command.development_only)
    ]
    usage_width = max(len(command.usage) for command in visible_commands)
    terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
    stacked = any(2 + usage_width + 1 + len(command.summary) > terminal_width for command in visible_commands)

    stream = sys.stdout
    print(_style(f"{_INFO} OwlBear commands", _BOLD, _MAGENTA, stream=stream) + "\n")  # noqa: T201
    for group in ("Everyday", "Setup", "Maintenance"):
        if selected is not None and group != selected:
            continue
        commands = [command for command in visible_commands if command.group == group]
        if not commands:
            continue
        heading = _style(f"{group}:", _BOLD, _GROUP_STYLES[group], stream=stream)
        print(heading)  # noqa: T201
        for command in commands:
            if stacked:
                usage = _style(command.usage, _GREEN, stream=stream)
                print(f"  {usage}\n      {command.summary}")  # noqa: T201
                continue
            usage = _style(f"{command.usage:<{usage_width}}", _GREEN, stream=stream)
            print(f"  {usage} {command.summary}")  # noqa: T201
        print()  # noqa: T201
