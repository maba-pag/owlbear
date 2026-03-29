"""Validate OwlBear agent files against known tool-name regressions.

Checks each agents/*.agent.md file for:
  - Bare 'todo' (not 'todos') on the tools: line (word-boundary matched)
  - Presence of 'resolveMemoryFileUri' anywhere in the file

Usage:
    python scripts/validate_agents.py <agent_file> [<agent_file> ...]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_BARE_TODO_RE = re.compile(r"\btodo\b")
_RESOLVE_URI = "resolveMemoryFileUri"


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


def validate_agent(agent_file: Path) -> list[str]:
    """Validate a single agent file.

    Args:
        agent_file: Path to the .agent.md file to check.

    Returns:
        List of validation error messages.  Empty list means valid.
    """
    content = Path(agent_file).read_text(encoding="utf-8")
    errors: list[str] = []

    # AC2: full-file check for deprecated tool name
    if _RESOLVE_URI in content:
        errors.append(f"{agent_file}: contains '{_RESOLVE_URI}'")

    # AC1: tools: line — word-boundary check for bare 'todo'
    tools = _tools_text(_frontmatter_lines(content))
    if tools and _BARE_TODO_RE.search(tools):
        errors.append(f"{agent_file}: tools: contains bare 'todo' (should be 'todos')")

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
