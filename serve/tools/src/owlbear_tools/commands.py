"""Central registry and help renderer for OwlBear workspace commands."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import textwrap
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TextIO

_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_RESET = "\033[0m"
_BOLD = "\033[1m"
_MAGENTA = "\033[35m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
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
_STAGED_SYMBOL = "ˢ"
_FIX_SYMBOL = "✚"
_UNSAFE_FIX_SYMBOL = "⚠"


@dataclass(frozen=True)
class Command:
    """One user-facing workspace command."""

    name: str
    usage: str
    summary: str
    group: str
    includes: tuple[str, ...] = ()
    development_only: bool = False
    topic_only: bool = False
    hidden: bool = False
    supports_staged: bool = False
    supports_safe_fixes: bool = False
    supports_unsafe_fixes: bool = False


@dataclass(frozen=True)
class _RenderLayout:
    summary_column: int
    capability_column: int | None
    terminal_width: int


def _internal_command(name: str, usage: str, summary: str, *, includes: tuple[str, ...] = ()) -> Command:
    return Command(
        name,
        usage,
        summary,
        "Internal",
        includes=includes,
        development_only=True,
        topic_only=True,
    )


COMMANDS = (
    Command("help", "uv run help [TOPIC]", "Command reference.", "Workspace"),
    Command("cockpit", "uv run cockpit [list] [OPTIONS]", "Start or list Cockpit instances.", "Workspace"),
    Command(
        "lint",
        "uv run lint",
        "Normal local lint.",
        "Quality",
        includes=(
            "lint-python",
            "lint-markdown",
            "lint-yaml",
            "lint-shell",
            "lint-actions",
            "lint-editorconfig",
            "lint-cockpit",
        ),
        supports_staged=True,
        supports_safe_fixes=True,
        supports_unsafe_fixes=True,
    ),
    Command(
        "lint-cockpit",
        "uv run lint-cockpit",
        "Cockpit frontend lint.",
        "Quality",
        includes=("lint-cockpit-code", "lint-cockpit-style", "lint-cockpit-html"),
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
        supports_unsafe_fixes=True,
    ),
    Command(
        "lint-python",
        "uv run lint-python",
        "Ruff Python lint.",
        "Quality",
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
        supports_unsafe_fixes=True,
    ),
    Command(
        "lint-markdown",
        "uv run lint-markdown",
        "Markdown lint.",
        "Quality",
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
    ),
    Command(
        "lint-yaml",
        "uv run lint-yaml",
        "Strict YAML lint.",
        "Quality",
        development_only=True,
        supports_staged=True,
    ),
    Command(
        "lint-shell",
        "uv run lint-shell",
        "ShellCheck.",
        "Quality",
        development_only=True,
        supports_staged=True,
    ),
    Command(
        "lint-actions",
        "uv run lint-actions",
        "GitHub Actions lint.",
        "Quality",
        development_only=True,
        supports_staged=True,
    ),
    Command(
        "lint-editorconfig",
        "uv run lint-editorconfig",
        "EditorConfig check.",
        "Quality",
        development_only=True,
        supports_staged=True,
    ),
    Command(
        "lint-cockpit-code",
        "uv run lint-cockpit-code",
        "Cockpit code lint.",
        "Quality",
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
    ),
    Command(
        "lint-cockpit-style",
        "uv run lint-cockpit-style",
        "Cockpit CSS lint.",
        "Quality",
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
        supports_unsafe_fixes=True,
    ),
    Command(
        "lint-cockpit-html",
        "uv run lint-cockpit-html",
        "Cockpit HTML lint.",
        "Quality",
        development_only=True,
        supports_staged=True,
    ),
    Command(
        "megalint",
        "uv run megalint",
        "MegaLinter across workspace.",
        "Quality",
        development_only=True,
        supports_safe_fixes=True,
        supports_unsafe_fixes=True,
    ),
    Command(
        "lint-full",
        "uv run lint-full",
        "All lint engines.",
        "Quality",
        includes=("lint", "megalint"),
        development_only=True,
        supports_safe_fixes=True,
        supports_unsafe_fixes=True,
    ),
    Command(
        "format-python",
        "uv run format-python",
        "Ruff Python format.",
        "Quality",
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
    ),
    Command(
        "format-whitespace",
        "uv run format-whitespace",
        "Trailing whitespace.",
        "Quality",
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
    ),
    Command(
        "format-eof",
        "uv run format-eof",
        "Final newline.",
        "Quality",
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
    ),
    Command(
        "format-full",
        "uv run format-full",
        "All formatters.",
        "Quality",
        includes=("format-python", "format-whitespace", "format-eof"),
        development_only=True,
        supports_staged=True,
        supports_safe_fixes=True,
    ),
    Command(
        "typecheck-cockpit",
        "uv run typecheck-cockpit",
        "Cockpit TypeScript.",
        "Quality",
        development_only=True,
    ),
    Command(
        "quality-full",
        "uv run quality-full",
        "Full quality sequence.",
        "Quality",
        includes=("format-full", "lint-full", "typecheck-cockpit", "todo"),
        development_only=True,
        supports_safe_fixes=True,
        supports_unsafe_fixes=True,
    ),
    Command(
        "todo",
        "uv run todo",
        "Scan for documentation TODO markers (advisory).",
        "Quality",
        development_only=True,
        hidden=True,
    ),
    Command(
        "indexes",
        "uv run indexes [PATH]",
        "Regenerate all workspace source indexes.",
        "Internal",
        includes=("doc-index", "py-index", "ts-index"),
        development_only=True,
        topic_only=True,
    ),
    _internal_command("doc-index", "uv run doc-index [PATH]", "Regenerate the documentation index."),
    _internal_command("py-index", "uv run py-index [PATH]", "Regenerate the Python source index."),
    _internal_command("ts-index", "uv run ts-index [PATH]", "Regenerate the TypeScript source index."),
    Command(
        "test",
        "uv run test [OPTIONS] [PATH ...]",
        "Run tests; paths select suites.",
        "Tests",
        development_only=True,
    ),
    Command(
        "test-e2e",
        "uv run test-e2e [OPTIONS] [SPEC ...]",
        "Fast Cockpit browser tests.",
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
        "target-branch",
        "uv run target-branch [BRANCH]",
        "Show or safely change the Delivery target branch.",
        "Setup",
        topic_only=True,
    ),
    Command(
        "dep-status",
        "uv run dep-status [OPTIONS]",
        "Report local dependency environment agreement without changing files.",
        "Maintenance",
        development_only=True,
        topic_only=True,
    ),
    Command(
        "dep-sync",
        "uv run dep-sync [OPTIONS]",
        "Synchronize local dependency environments from existing locks.",
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
    _internal_command(
        "test-curation-inventory",
        "uv run test-curation-inventory [--json] [--root PATH]",
        "Inventory task-looking tests and legacy provenance.",
    ),
    _internal_command(
        "migrate-delivery-state",
        "uv run migrate-delivery-state [PATH] [--apply]",
        "Preview or apply the one-way Delivery live-state migration.",
    ),
    _internal_command(
        "retire-delivery-integration",
        "uv run retire-delivery-integration [PATH] [--apply]",
        "Preview or apply terminal legacy Integration retirement.",
    ),
    _internal_command("semble", "uv run semble [OPTIONS]", "Run the assembly utility."),
)

_COMMANDS_BY_NAME = {command.name: command for command in COMMANDS}

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


def _visible(command: Command, *, development: bool, selected: str | None) -> bool:
    if command.hidden or (selected is None and command.topic_only):
        return False
    if selected is not None and command.group != selected:
        return False
    return development or not command.development_only


def _capabilities(command: Command, *, stream: TextIO) -> str:
    if not _capability_width(command):
        return ""
    slots = (
        _style(_STAGED_SYMBOL, _GREEN, stream=stream) if command.supports_staged else " ",
        _style(_FIX_SYMBOL, _RED, stream=stream) if command.supports_safe_fixes else " ",
        _style(_UNSAFE_FIX_SYMBOL, _YELLOW, stream=stream) if command.supports_unsafe_fixes else " ",
    )
    return " ".join(slots).rstrip()


def _capability_width(command: Command) -> int:
    return 5 if any((command.supports_staged, command.supports_safe_fixes, command.supports_unsafe_fixes)) else 0


def _expand_nested_commands(commands: list[Command], *, development: bool) -> list[Command]:
    """Pull every command reachable through the include graph into the rendered set."""
    resolved = {command.name: command for command in commands}
    pending = list(commands)
    while pending:
        command = pending.pop()
        for child_name in command.includes:
            child = _COMMANDS_BY_NAME[child_name]
            if child.group != command.group or child.name in resolved:
                continue
            if not development and child.development_only:
                continue
            resolved[child.name] = child
            pending.append(child)
    return [resolved[command.name] for command in COMMANDS if command.name in resolved]


def _tree_rows(commands: list[Command]) -> list[tuple[Command, int]]:
    by_name = {command.name: command for command in commands}
    child_names = {child_name for command in commands for child_name in command.includes if child_name in by_name}
    roots = [command for command in commands if command.name not in child_names]
    rows: list[tuple[Command, int]] = []

    def visit(command: Command, depth: int) -> None:
        rows.append((command, depth))
        for child_name in command.includes:
            child = by_name.get(child_name)
            if child is not None:
                visit(child, depth + 1)

    for root in roots:
        visit(root, 0)
    return rows


def _summary_column(rows: list[tuple[Command, int]]) -> int:
    return max(2 + depth * 2 + len(command.usage.removeprefix("uv run ")) + 2 for command, depth in rows)


def _wrap_summary(summary: str, *, width: int) -> list[str]:
    return textwrap.wrap(
        summary,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]


def _capability_column(
    rows: list[tuple[Command, int]],
    *,
    summary_column: int,
    terminal_width: int,
) -> int | None:
    positions = []
    for command, _ in rows:
        capability_width = _capability_width(command)
        if not capability_width:
            continue
        summary_width = max(20, terminal_width - summary_column - capability_width - 3)
        first_line = _wrap_summary(command.summary, width=summary_width)[0]
        positions.append(summary_column + len(first_line) + 2)
    return max(positions, default=None)


def _render_command(
    command: Command,
    *,
    stream: TextIO,
    layout: _RenderLayout,
    indent: str,
) -> None:
    display_usage = command.usage.removeprefix("uv run ")
    capabilities = _capabilities(command, stream=stream)
    capability_width = _capability_width(command)
    summary_column = layout.summary_column
    padding = " " * max(2, summary_column - len(indent) - len(display_usage))
    side_indent = " " * summary_column
    suffix = f"  {capabilities}" if capabilities else ""
    if capability_width and layout.capability_column is not None:
        summary_width = layout.capability_column - summary_column - 2
    else:
        summary_width = max(20, layout.terminal_width - summary_column - 1)
    summary_lines = _wrap_summary(command.summary, width=summary_width)
    if capability_width and layout.capability_column is not None:
        suffix = f"{' ' * max(2, layout.capability_column - summary_column - len(summary_lines[0]))}{capabilities}"
    print(  # noqa: T201
        f"{indent}{_style(display_usage, _GREEN, stream=stream)}{padding}{summary_lines[0]}{suffix}"
    )
    for line in summary_lines[1:]:
        print(f"{side_indent}{line}")  # noqa: T201


def _render_quality_legend(stream: TextIO, *, terminal_width: int) -> None:
    entries = (
        (_STAGED_SYMBOL, _GREEN, "staged files only (-s)"),
        (_FIX_SYMBOL, _RED, "disable safe fixes (-n)"),
        (_UNSAFE_FIX_SYMBOL, _YELLOW, "unsafe fixes (-u)"),
    )
    label = "  Available options:"
    styled = [f"{_style(symbol, color, stream=stream)} {text}" for symbol, color, text in entries]
    plain = f"{label}  " + "  ".join(f"{symbol} {text}" for symbol, _, text in entries)
    if len(plain) <= terminal_width:
        print(f"{label}  " + "  ".join(styled))  # noqa: T201
        return
    print(label)  # noqa: T201
    for entry in styled:
        print(f"    {entry}")  # noqa: T201


def _render_rows(
    rows: list[tuple[Command, int]],
    *,
    stream: TextIO,
    terminal_width: int,
) -> None:
    summary_column = _summary_column(rows)
    layout = _RenderLayout(
        summary_column=summary_column,
        capability_column=_capability_column(
            rows,
            summary_column=summary_column,
            terminal_width=terminal_width,
        ),
        terminal_width=terminal_width,
    )
    for command, depth in rows:
        _render_command(
            command,
            stream=stream,
            layout=layout,
            indent=" " * (2 + depth * 2),
        )


def _render_group(
    group: str,
    commands: list[Command],
    *,
    stream: TextIO,
    terminal_width: int,
) -> None:
    heading = _style(f"{group}:", _BOLD, _GROUP_STYLES[group], stream=stream)
    print(heading)  # noqa: T201
    _render_rows(_tree_rows(commands), stream=stream, terminal_width=terminal_width)
    if group == "Quality":
        _render_quality_legend(stream, terminal_width=terminal_width)
    print()  # noqa: T201


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
        command for command in COMMANDS if _visible(command, development=development, selected=selected)
    ]
    if selected is None:
        topics = "s, m, i" if development else "s"
        visible_commands = [
            replace(command, summary=f"Topics: {topics}.") if command.name == "help" else command
            for command in visible_commands
        ]
    visible_commands = _expand_nested_commands(visible_commands, development=development)
    terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns

    stream = sys.stdout
    print(_style(f"{_INFO} OwlBear commands", _BOLD, _MAGENTA, stream=stream) + "\n")  # noqa: T201
    for group in _GROUP_ORDER:
        if selected is not None and group != selected:
            continue
        group_commands = [command for command in visible_commands if command.group == group]
        if not group_commands:
            continue
        _render_group(
            group,
            group_commands,
            stream=stream,
            terminal_width=terminal_width,
        )
