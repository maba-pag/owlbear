"""Validate OwlBear agent files against conventions.

Checks each agents/*.agent.md file for:
  - Bare 'todo' on the tools: line — tool is disabled for subagents
  - 'todos' on the tools: line — tool is disabled for subagents
  - Presence of 'manage_todo_list' anywhere — tool is disabled for subagents
  - Presence of 'resolveMemoryFileUri' anywhere
  - Unknown tool names not in the canonical registry
  - Frontmatter agents: ↔ body <agents> table alignment
  - ND3 agents have disable-model-invocation: false

Usage:
    python .owlbear/scripts/validate_agents.py [<agent_file> ...]
    # No args = discover and validate all agents in share/agents/
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
KNOWN_TOOLSETS: frozenset[str] = frozenset({"agent", "browser", "edit", "execute", "read", "search", "web", "vscode"})

# Standalone tool names not under any toolset prefix.
# Source: VS Code Copilot cheat sheet 2026-03-25 + docs/research/stale-tool-names.md
# Update this set when VS Code adds new standalone tools.
KNOWN_STANDALONE_TOOLS: frozenset[str] = frozenset({"newWorkspace", "selection"})

# MCP server names whose tools may appear as 'server/tool_name' or 'server/*'.
# Update this set when a new MCP server is added to the workspace.
KNOWN_MCP_SERVERS: frozenset[str] = frozenset({"ob-kanban", "ob-knowledge", "ob-memory", "ddgs", "markitdown"})

# Tool names that already produce specific ban errors — skip in unknown-tool check
# to avoid double-reporting the same tool with two different error messages.
_BANNED_TOOL_NAMES: frozenset[str] = frozenset({"todos", "todo", "manage_todo_list", "resolveMemoryFileUri"})

_AGENTS_DIR = Path(__file__).resolve().parents[2] / "share" / "agents"

# Known ND3 agents — must have disable-model-invocation: false.
# See share/WIRING.md § "Nesting Depth" for the canonical list.
ND3_AGENTS: frozenset[str] = frozenset(
    {
        "shaper-challenger",
        "builder-challenger",
        "verifier-challenger",
        "ideation-critic",
    }
)

_BUILTINS = frozenset({"Explore", "General Purpose"})
_AGENT_TABLE_MIN_CELLS = 2


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
        # (e) prefix is a known MCP server — e.g. 'ob-kanban/start_work'
        if prefix in KNOWN_MCP_SERVERS:
            return True
    # (c) exact match in KNOWN_STANDALONE_TOOLS
    if name in KNOWN_STANDALONE_TOOLS:
        return True
    # (d) MCP server wildcard pattern — e.g. 'ob-kanban/*'
    return bool(name.endswith("/*"))


def _fm_scalar(fm_lines: list[str], key: str) -> str | None:
    """Get a scalar frontmatter value by key."""
    for line in fm_lines:
        if line.startswith(f"{key}:"):
            _, _, val = line.partition(":")
            return val.strip()
    return None


def _fm_agents(fm_lines: list[str]) -> list[str]:
    """Extract the agents: array from frontmatter lines (inline or multi-line)."""
    agents: list[str] = []
    in_agents = False
    for line in fm_lines:
        if in_agents:
            stripped = line.strip()
            if stripped.startswith("- "):
                agents.append(stripped[2:].strip())
                continue
            in_agents = False
        if line.startswith("agents:"):
            _, _, val = line.partition(":")
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                return [a.strip() for a in inner.split(",") if a.strip()]
            if val == "[]":
                return []
            in_agents = True
    return agents


def _body_agents_table(content: str) -> list[str]:
    """Extract agent names from the <agents> body section table."""
    m = re.search(r"<agents>(.*?)</agents>", content, re.DOTALL)
    if not m:
        return []
    agents: list[str] = []
    for raw_line in m.group(1).splitlines():
        line = raw_line.strip()
        if line.startswith("|") and not line.startswith("| Agent") and not line.startswith("|---"):
            cells = [c.strip() for c in line.split("|")]
            if len(cells) >= _AGENT_TABLE_MIN_CELLS and cells[1] and cells[1] != "Agent":
                agents.append(cells[1])
    return agents


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
                f"{agent_file}: tools: unknown tool '{name}' — not a recognized VS Code built-in or MCP server pattern"
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
    fm_lines = _frontmatter_lines(content)

    # Full-file checks for disabled tools
    if _RESOLVE_URI in content:
        errors.append(f"{agent_file}: contains '{_RESOLVE_URI}'")
    if _MANAGE_TODO_LIST in content:
        errors.append(f"{agent_file}: contains 'manage_todo_list' — tool is disabled for subagents")

    # tools: line checks — word-boundary checks for banned tool names
    tools = _tools_text(fm_lines)
    if tools and _TODOS_RE.search(tools):
        errors.append(f"{agent_file}: tools: contains 'todos' — tool is disabled for subagents")
    if tools and _BARE_TODO_RE.search(tools):
        errors.append(f"{agent_file}: tools: contains bare 'todo' — tool is disabled for subagents")

    # Unknown-tool check — runs after ban checks so banned tools are not double-reported
    errors.extend(_check_unknown_tools(fm_lines, agent_file))

    # --- Agent table alignment ---
    name = agent_file.stem.replace(".agent", "")
    fm_agents = set(_fm_agents(fm_lines))
    body_agents = set(_body_agents_table(content))
    fm_custom = fm_agents - _BUILTINS
    body_custom = body_agents - _BUILTINS

    if fm_custom and not body_agents:
        has_section = "<agents>" in content and "</agents>" in content
        if not has_section:
            errors.append(f"{agent_file}: has agents: {sorted(fm_custom)} in frontmatter but no <agents> body section")

    in_fm_not_body = fm_custom - body_custom
    if in_fm_not_body:
        errors.append(f"{agent_file}: in frontmatter agents: but missing from <agents> table: {sorted(in_fm_not_body)}")

    in_body_not_fm = body_custom - fm_custom
    if in_body_not_fm:
        errors.append(f"{agent_file}: in <agents> table but missing from frontmatter agents:: {sorted(in_body_not_fm)}")

    # --- ND3 DMI rule ---
    dmi = _fm_scalar(fm_lines, "disable-model-invocation")
    if name in ND3_AGENTS and dmi != "false":
        errors.append(f"{agent_file}: ND3 agent must have disable-model-invocation: false (currently: {dmi})")

    return errors


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Accepts agent file paths; no args = all agents."""
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        if not _AGENTS_DIR.is_dir():
            sys.stderr.write(f"Agent directory not found: {_AGENTS_DIR}\n")
            return 1
        agent_files = sorted(_AGENTS_DIR.glob("*.agent.md"))
    else:
        agent_files = [Path(p) for p in args]

    has_errors = False
    for agent_file in agent_files:
        errors = validate_agent(agent_file)
        if errors:
            has_errors = True
            for error in errors:
                sys.stderr.write(f"{error}\n")

    if not has_errors and not args:
        print(f"PASS — all {len(agent_files)} agent files conform to conventions")

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
