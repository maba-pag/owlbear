"""Central registry and help renderer for OwlBear workspace commands."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """One user-facing workspace command."""

    name: str
    usage: str
    summary: str
    group: str


COMMANDS = (
    Command("help", "uv run help [TOPIC]", "Show this command reference.", "Everyday"),
    Command(
        "lint",
        "uv run lint [--no-fix | --unsafe-fixes] [--all | FILE ...]",
        "Lint staged, explicit, or all files; safe fixes default.",
        "Everyday",
    ),
    Command(
        "lint-full",
        "uv run lint-full [--no-fix | --unsafe-fixes]",
        "Run all local and full-project checks; safe fixes default.",
        "Everyday",
    ),
    Command("typecheck", "uv run typecheck", "Type-check the Cockpit frontend.", "Everyday"),
    Command(
        "megalint",
        "uv run megalint [--no-fix | --unsafe-fixes]",
        "Run MegaLinter; safe fixes default.",
        "Everyday",
    ),
    Command("cockpit", "uv run cockpit [list] [OPTIONS]", "Start or list Cockpit instances.", "Everyday"),
    Command("todo", "uv run todo", "Report documentation TODO markers.", "Everyday"),
    Command("hooks-install", "uv run hooks-install", "Install Git hooks and hook environments.", "Setup"),
    Command(
        "setup-project",
        "uv run setup-project [PATH] [--integration-target BRANCH]",
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
    Command("deps-status", "uv run deps-status", "Check locks and available dependency updates.", "Maintenance"),
    Command("deps-sync", "uv run deps-sync", "Install exactly the locked Python and npm dependencies.", "Maintenance"),
    Command("pds-sync", "uv run pds-sync", "Transactionally refresh self-hosted PDS assets.", "Maintenance"),
    Command(
        "megalint-clean",
        "uv run megalint-clean [--yes]",
        "Preview and remove obsolete MegaLinter images.",
        "Maintenance",
    ),
)

_TOPICS = {
    "everyday": "Everyday",
    "lint": "Everyday",
    "setup": "Setup",
    "maintenance": "Maintenance",
}


def command_footer() -> str:
    """Return the concise discovery hint printed by commands."""
    return "For the full command set, run `uv run help`."


def help_main() -> None:
    """Render the full command reference or one topic."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("topic", nargs="?", choices=sorted(_TOPICS))
    parser.add_argument("-h", "--help", action="help")
    args = parser.parse_args()
    selected = _TOPICS.get(args.topic) if args.topic else None

    print("OwlBear commands\n")  # noqa: T201
    for group in ("Everyday", "Setup", "Maintenance"):
        if selected is not None and group != selected:
            continue
        print(f"{group}:")  # noqa: T201
        for command in COMMANDS:
            if command.group == group:
                print(f"  {command.usage:<58} {command.summary}")  # noqa: T201
        print()  # noqa: T201
