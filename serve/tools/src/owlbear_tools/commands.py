"""Central registry and help renderer for OwlBear workspace commands."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TextIO

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_RESET = "\033[0m"
_BOLD = "\033[1m"
_MAGENTA = "\033[35m"
_GREEN = "\033[32m"
_INFO = "\N{INFORMATION SOURCE}"
_GROUP_STYLES = {
    "Workspace": "\033[36m",
    "Quality": "\033[32m",
    "Tests": "\033[35m",
    "Setup": "\033[34m",
    "Maintenance": "\033[33m",
    "Internal": "\033[90m",
}
_GROUP_ORDER = ("Workspace", "Quality", "Tests", "Setup", "Maintenance", "Internal")


@dataclass(frozen=True)
class Command:
    """One user-facing workspace command."""

    name: str
    usage: str
    summary: str
    group: str
    development_only: bool = False
    topic_only: bool = False


def _internal_command(name: str, usage: str, summary: str) -> Command:
    return Command(name, usage, summary, "Internal", development_only=True, topic_only=True)


COMMANDS = (
    Command("help", "uv run help [TOPIC]", "Show this command reference.", "Workspace"),
    Command("cockpit", "uv run cockpit [list] [OPTIONS]", "Start or list Cockpit instances.", "Workspace"),
    Command(
        "lint",
        "uv run lint [OPTIONS] [FILE ...]",
        "Staged or explicit files; --all selects repository; safe fixes default.",
        "Quality",
    ),
    Command("todo", "uv run todo", "Report documentation TODO markers.", "Quality"),
    Command(
        "lint-full",
        "uv run lint-full [OPTIONS]",
        "lint --all plus frontend and MegaLinter checks; safe fixes default.",
        "Quality",
        development_only=True,
    ),
    Command(
        "typecheck",
        "uv run typecheck",
        "Type-check the Cockpit frontend.",
        "Quality",
        development_only=True,
    ),
    Command(
        "test",
        "uv run test [OPTIONS] [PATH ...]",
        "Run tests for staged or explicit paths; --all runs every suite.",
        development_only=True,
        group="Tests",
    ),
    Command(
        "test-e2e",
        "uv run test-e2e [OPTIONS] [SPEC ...]",
        "Run Cockpit's fast Playwright gate; --all runs every spec.",
        "Tests",
        development_only=True,
    ),
    Command(
        "hooks-install",
        "uv run hooks-install",
        "Install Git hooks and hook environments.",
        "Setup",
        topic_only=True,
    ),
    Command(
        "setup-project",
        "uv run setup-project [OPTIONS] [PATH]",
        "Initialize an OwlBear project.",
        "Setup",
        topic_only=True,
    ),
    Command(
        "doctor",
        "uv run doctor [PATH]",
        "Check an OwlBear project without changing it.",
        "Setup",
        topic_only=True,
    ),
    Command(
        "integration-target",
        "uv run integration-target [BRANCH]",
        "Show or safely change the Delivery target branch.",
        "Setup",
        topic_only=True,
    ),
    Command(
        "deps-status",
        "uv run deps-status",
        "Report installed, allowed, and latest versions without updating locks.",
        "Maintenance",
        development_only=True,
        topic_only=True,
    ),
    Command(
        "deps-sync",
        "uv run deps-sync",
        "Install existing locks exactly; do not update versions or ranges.",
        "Maintenance",
        development_only=True,
        topic_only=True,
    ),
    Command(
        "pds-sync",
        "uv run pds-sync",
        "Transactionally refresh self-hosted PDS assets.",
        "Maintenance",
        development_only=True,
        topic_only=True,
    ),
    Command(
        "megalint",
        "uv run megalint [OPTIONS]",
        "Run MegaLinter; safe fixes default.",
        "Maintenance",
        development_only=True,
        topic_only=True,
    ),
    Command(
        "megalint-clean",
        "uv run megalint-clean [--yes]",
        "Preview and remove obsolete MegaLinter images.",
        "Maintenance",
        development_only=True,
        topic_only=True,
    ),
    _internal_command("commit-owned", "uv run commit-owned [OPTIONS] -- PATH ...", "Create a scoped commit."),
    _internal_command("test-root", "uv run test-root PATH ...", "Resolve test toolchains and working directories."),
    _internal_command("indexes", "uv run indexes [PATH]", "Regenerate all workspace source indexes."),
    _internal_command("doc-index", "uv run doc-index [PATH]", "Regenerate the documentation index."),
    _internal_command("py-index", "uv run py-index [PATH]", "Regenerate the Python source index."),
    _internal_command("ts-index", "uv run ts-index [PATH]", "Regenerate the TypeScript source index."),
    _internal_command("semble", "uv run semble [OPTIONS]", "Run the assembly utility."),
    _internal_command("eslint-fix", "uv run eslint-fix [OPTIONS]", "Run the Cockpit ESLint hook."),
    _internal_command("megalint-hook", "uv run megalint-hook", "Run the MegaLinter hook implementation."),
    _internal_command(
        "text-hygiene-check",
        "uv run text-hygiene-check [PATH ...]",
        "Run non-mutating text hygiene checks.",
    ),
)

_TOPICS = {
    "workspace": "Workspace",
    "w": "Workspace",
    "quality": "Quality",
    "lint": "Quality",
    "q": "Quality",
    "tests": "Tests",
    "test": "Tests",
    "t": "Tests",
    "setup": "Setup",
    "s": "Setup",
    "maintenance": "Maintenance",
    "m": "Maintenance",
    "internal": "Internal",
    "i": "Internal",
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
    development = _is_development_checkout()
    available_topics = {
        topic for topic, group in _TOPICS.items() if development or group not in {"Tests", "Maintenance", "Internal"}
    }
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("topic", nargs="?", choices=sorted(available_topics))
    parser.add_argument("-h", "--help", action="help")
    args = parser.parse_args()
    selected = _TOPICS.get(args.topic) if args.topic else None
    visible_commands = [
        command
        for command in COMMANDS
        if (selected == command.group or (selected is None and not command.topic_only))
        and (development or not command.development_only)
    ]
    if selected is None:
        topics = "setup (s), maintenance (m), internal (i)" if development else "setup (s)"
        visible_commands = [
            replace(command, summary=f"Show commands; topics: {topics}.") if command.name == "help" else command
            for command in visible_commands
        ]
    usage_width = max(len(command.usage) for command in visible_commands)
    terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns
    stacked = any(2 + usage_width + 1 + len(command.summary) > terminal_width for command in visible_commands)

    stream = sys.stdout
    print(_style(f"{_INFO} OwlBear commands", _BOLD, _MAGENTA, stream=stream) + "\n")  # noqa: T201
    for group in _GROUP_ORDER:
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
