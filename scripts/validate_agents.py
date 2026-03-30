"""Validate OwlBear agent files against known tool-name regressions.

Checks each agents/*.agent.md file for:
  - Bare 'todo' on the tools: line (word-boundary matched) — tool is disabled for subagents
  - 'todos' on the tools: line — tool is disabled for subagents
  - Presence of 'manage_todo_list' anywhere in the file — tool is disabled for subagents
  - Presence of 'resolveMemoryFileUri' anywhere in the file

Usage:
    python scripts/validate_agents.py <agent_file> [<agent_file> ...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_BARE_TODO_RE = re.compile(r"\btodo\b")
_TODOS_RE = re.compile(r"\btodos\b")
_RESOLVE_URI = "resolveMemoryFileUri"
_MANAGE_TODO_LIST = "manage_todo_list"

# Canonical VS Code built-in toolset prefixes.
# Source: VS Code Copilot cheat sheet 2026-03-25 + docs/research/stale-tool-names.md
# Update this set when VS Code adds new toolsets.
KNOWN_TOOLSETS: frozenset[str] = frozenset(
    {"agent", "browser", "edit", "execute", "read", "search", "web", "vscode"}
)

# Standalone tool names not under any toolset prefix.
# Source: VS Code Copilot cheat sheet 2026-03-25 + docs/research/stale-tool-names.md
# Update this set when VS Code adds new standalone tools.
KNOWN_STANDALONE_TOOLS: frozenset[str] = frozenset({"newWorkspace", "selection"})

# Tool names that already produce specific ban errors — skip in unknown-tool check
# to avoid double-reporting the same tool with two different error messages.
_BANNED_TOOL_NAMES: frozenset[str] = frozenset(
    {"todos", "todo", "manage_todo_list", "resolveMemoryFileUri"}
)


def _frontmatter_lines(content: str) -> list[str]:
    """Return lines inside the leading --- ... --- block, or empty list."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:i]
    return []


def _tools_text(fm_lines: list[str]) -> str:
    """Concatenate the tools: line and any following indented continuation lines."""
    result: list[str] = []
    in_tools = False
    for line in fm_lines:
        if re.match(r"^tools:", line):
            result.append(line)
            in_tools = True
        elif in_tools:
            if line.startswith((" ", "\t")):
                result.append(line)
            else:
                break
    return " ".join(result)


def _is_valid_tool(name: str) -> bool:
    """Return True if name matches any recognized VS Code built-in or MCP server pattern."""
    # (a) exact match in KNOWN_TOOLSETS — toolset shorthand like 'search'
    if name in KNOWN_TOOLSETS:
        return True
    # (b) prefix before first '/' is in KNOWN_TOOLSETS — e.g. 'execute/runInTerminal'
    if "/" in name:
        prefix = name.split("/", 1)[0]
        if prefix in KNOWN_TOOLSETS:
            return True
    # (c) exact match in KNOWN_STANDALONE_TOOLS
    if name in KNOWN_STANDALONE_TOOLS:
        return True
    # (d) MCP server wildcard pattern — e.g. 'owlbear-kanban/*'
    return bool(name.endswith("/*"))


def _check_unknown_tools(fm_lines: list[str], agent_file: Path) -> list[str]:
    """Return error messages for tool names not in the canonical registry.

    Skips names already covered by specific ban checks to avoid double errors.
    """
    tools = _tools_text(fm_lines)
    if not tools:
        return []
    bracket_match = re.search(r"\[([^\]]*)\]", tools)
    if not bracket_match:
        return []
    errors: list[str] = []
    for raw in bracket_match.group(1).split(","):
        name = raw.strip().strip("'\"")
        if not name:
            continue
        if name in _BANNED_TOOL_NAMES:
            continue
        if not _is_valid_tool(name):
            errors.append(
                f"{agent_file}: tools: unknown tool '{name}'"
                f" — not a recognized VS Code built-in or MCP server pattern"
            )
    return errors


def validate_agent(agent_file: Path) -> list[str]:
    """Validate a single agent file.

    Args:
        agent_file: Path to the .agent.md file to check.

    Returns:
        List of validation error messages.  Empty list means valid.
    """
    content = Path(agent_file).read_text(encoding="utf-8")
    errors: list[str] = []

    # Full-file checks for disabled tools
    if _RESOLVE_URI in content:
        errors.append(f"{agent_file}: contains '{_RESOLVE_URI}'")
    if _MANAGE_TODO_LIST in content:
        errors.append(
            f"{agent_file}: contains 'manage_todo_list' — tool is disabled for subagents"
        )

    # tools: line checks — word-boundary checks for banned tool names
    tools = _tools_text(_frontmatter_lines(content))
    if tools and _TODOS_RE.search(tools):
        errors.append(
            f"{agent_file}: tools: contains 'todos' — tool is disabled for subagents"
        )
    if tools and _BARE_TODO_RE.search(tools):
        errors.append(
            f"{agent_file}: tools: contains bare 'todo' — tool is disabled for subagents"
        )

    # Unknown-tool check — runs after ban checks so banned tools are not double-reported
    errors.extend(_check_unknown_tools(_frontmatter_lines(content), agent_file))

    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Accepts agent file paths as positional arguments."""
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        sys.stderr.write(
            "Usage: validate_agents.py <agent_file> [<agent_file> ...]\n"
        )
        return 1

    has_errors = False
    for raw_path in args:
        agent_file = Path(raw_path)
        errors = validate_agent(agent_file)
        if errors:
            has_errors = True
            for error in errors:
                sys.stderr.write(f"{error}\n")

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
