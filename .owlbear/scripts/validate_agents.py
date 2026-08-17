"""Validate OwlBear agent files against conventions.

Checks each agents/*.agent.md file for:
  - Bare 'todo' on the tools: line — tool is disabled for subagents
  - 'todos' on the tools: line — tool is disabled for subagents
  - Presence of 'manage_todo_list' anywhere — tool is disabled for subagents
  - Presence of 'resolveMemoryFileUri' anywhere
  - Unknown tool names not in the canonical registry
  - Frontmatter agents: ↔ body <agents> table alignment
    - Hook declaration shape, script paths, and required role contracts
  - ND3 agents have disable-model-invocation: false

Usage:
    python .owlbear/scripts/validate_agents.py [<agent_file> ...]
        # No args = discover and validate all agents in share/ and .owlbear/
"""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

import yaml

_BARE_TODO_RE = re.compile(r"\btodo\b")
_TODOS_RE = re.compile(r"\btodos\b")
_RESOLVE_URI = "resolveMemoryFileUri"
_MANAGE_TODO_LIST = "manage_todo_list"

# Canonical VS Code built-in toolset prefixes.
# Source: VS Code Copilot cheat sheet 2026-03-25 + docs/research/stale-tool-names.md
# Update this set when VS Code adds new toolsets.
KNOWN_TOOLSETS: frozenset[str] = frozenset(
    {
        "agent",
        "browser",
        "edit",
        "execute",
        "read",
        "search",
        "web",
        "vscode",
        "vscodeGeneral",
        "vscodeTasks",
    }
)

# Standalone tool names not under any toolset prefix.
# Source: VS Code Copilot cheat sheet 2026-03-25 + docs/research/stale-tool-names.md
# Update this set when VS Code adds new standalone tools.
KNOWN_STANDALONE_TOOLS: frozenset[str] = frozenset({"newWorkspace", "selection", "vscode.mermaid-markdown-features"})

# MCP server names whose tools may appear as 'server/tool_name' or 'server/*'.
# Update this set when a new MCP server is added to the workspace.
KNOWN_MCP_SERVERS: frozenset[str] = frozenset(
    {"owlbear-browser", "owlbear-delivery", "owlbear-knowledge", "owlbear-memory", "ddgs", "markitdown"}
)

# Tool names that already produce specific ban errors — skip in unknown-tool check
# to avoid double-reporting the same tool with two different error messages.
_BANNED_TOOL_NAMES: frozenset[str] = frozenset({"todos", "todo", "manage_todo_list", "resolveMemoryFileUri"})

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENT_ROOTS = (_REPO_ROOT / "share" / "agents", _REPO_ROOT / ".owlbear" / "agents")
_SKILL_ROOTS = (_REPO_ROOT / "share" / "skills", _REPO_ROOT / ".owlbear" / "skills")
_HOOK_EVENTS = frozenset({"SessionStart", "PreToolUse", "PostToolUse"})
_REQUIRED_HOOKS: dict[str, dict[str, frozenset[str]]] = {
    "build-reviewer": {
        "PreToolUse": frozenset({"uv run python .owlbear/hooks/deny-writes.py --terminal-read-only"}),
    },
    "builder": {
        "SessionStart": frozenset({"uv run python .owlbear/hooks/session-context.py"}),
        "PostToolUse": frozenset({"uv run python .owlbear/hooks/lint-changed.py"}),
    },
    "conceptual-design-reviewer": {
        "PreToolUse": frozenset({"uv run python .owlbear/hooks/deny-writes.py"}),
    },
    "designer": {
        "PreToolUse": frozenset({"uv run python .owlbear/hooks/deny-writes.py --allow-research --terminal-read-only"}),
    },
    "designer-challenger": {
        "PreToolUse": frozenset({"uv run python .owlbear/hooks/deny-writes.py"}),
    },
    "finalizer": {
        "PreToolUse": frozenset({"uv run python .owlbear/hooks/deny-writes.py --terminal-read-only"}),
    },
    "planner": {
        "PreToolUse": frozenset({"uv run python .owlbear/hooks/deny-writes.py --terminal-read-only"}),
    },
    "planner-challenger": {
        "PreToolUse": frozenset({"uv run python .owlbear/hooks/deny-writes.py"}),
    },
    "test-curator": {
        "PreToolUse": frozenset({"uv run python .owlbear/hooks/deny-src-writes.py"}),
    },
}

# Known ND3 agents — must have disable-model-invocation: false.
# See share/WIRING.md § "Nesting Depth" for the canonical list.
ND3_AGENTS: frozenset[str] = frozenset(
    {
        "build-reviewer",
        "conceptual-design-reviewer",
        "planner-challenger",
    }
)

_BUILTINS = frozenset({"Explore", "General Purpose"})
_AGENT_TABLE_MIN_CELLS = 2
_REQUIRED_FRONTMATTER = frozenset(
    {
        "name",
        "description",
        "user-invocable",
        "disable-model-invocation",
        "model",
        "tools",
    }
)
_REQUIRED_SECTIONS = (
    "persona",
    "required_reading",
    "critical_rules",
    "output_format",
    "boundaries",
    "examples",
)


def _frontmatter_data(fm_lines: list[str]) -> dict[str, object]:
    """Return parsed frontmatter when it is a mapping, otherwise an empty mapping."""
    if not fm_lines:
        return {}
    try:
        parsed = yaml.safe_load("\n".join(fm_lines))
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


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
        # (e) prefix is a known MCP server — e.g. 'owlbear-delivery/transition_delivery'
        if prefix in KNOWN_MCP_SERVERS:
            return True
    # (c) exact match in KNOWN_STANDALONE_TOOLS
    return name in KNOWN_STANDALONE_TOOLS


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
        if not line.startswith("|") or line.startswith("| Agent"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if (
            len(cells) >= _AGENT_TABLE_MIN_CELLS
            and cells[1]
            and cells[1] != "Agent"
            and not re.fullmatch(r":?-+:?", cells[1])
        ):
            agents.append(cells[1])
    return agents


def _hook_entry_command(
    event: str,
    index: int,
    entry: object,
    agent_file: Path,
) -> tuple[str | None, list[str]]:
    """Validate one hook entry and return its command plus any diagnostics."""
    if not isinstance(entry, dict):
        return None, [f"{agent_file}: hooks.{event}[{index}] must be a mapping"]

    errors: list[str] = []
    if entry.get("type") != "command":
        errors.append(f"{agent_file}: hooks.{event}[{index}] must use type: command")
    command = entry.get("command")
    if not isinstance(command, str) or not command.strip():
        errors.append(f"{agent_file}: hooks.{event}[{index}] needs a non-empty command")
        return None, errors

    command = command.strip()
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        errors.append(f"{agent_file}: hooks.{event}[{index}] command is not shell-parseable: {exc}")
        return command, errors
    errors.extend(
        f"{agent_file}: hook script does not exist: {token}"
        for token in tokens
        if token.startswith(".owlbear/hooks/") and not (_REPO_ROOT / token).is_file()
    )
    return command, errors


def _hook_commands(fm_lines: list[str], agent_file: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Parse hook commands and validate their declaration shape and local script paths."""
    hooks = _frontmatter_data(fm_lines).get("hooks")
    if hooks is None:
        return {}, []
    if not isinstance(hooks, dict):
        return {}, [f"{agent_file}: hooks must be a mapping of lifecycle event to command entries"]

    commands: dict[str, list[str]] = {}
    errors: list[str] = []
    for event, entries in hooks.items():
        if event not in _HOOK_EVENTS:
            errors.append(f"{agent_file}: hooks contains unsupported lifecycle event '{event}'")
        if not isinstance(entries, list):
            errors.append(f"{agent_file}: hooks.{event} must be a list")
            continue

        event_commands: list[str] = []
        for index, entry in enumerate(entries):
            command, entry_errors = _hook_entry_command(event, index, entry, agent_file)
            errors.extend(entry_errors)
            if command is not None:
                event_commands.append(command)
        commands[event] = event_commands

    return commands, errors


def _check_hooks(fm_lines: list[str], agent_file: Path) -> list[str]:
    """Validate declared hooks and enforce the current safety-hook contracts."""
    commands, errors = _hook_commands(fm_lines, agent_file)
    expected = _REQUIRED_HOOKS.get(agent_file.stem.replace(".agent", ""), {})
    for event, required_commands in expected.items():
        declared = set(commands.get(event, []))
        missing = sorted(required_commands - declared)
        if missing:
            errors.append(f"{agent_file}: missing required {event} hook(s): {missing}")
    return errors


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


def _check_structure(content: str, fm_lines: list[str], agent_file: Path) -> list[str]:
    """Validate frontmatter identity and required body sections."""
    errors: list[str] = []
    if not fm_lines:
        errors.append(f"{agent_file}: missing or unterminated YAML frontmatter")
        metadata: dict[str, object] = {}
    else:
        try:
            parsed = yaml.safe_load("\n".join(fm_lines))
        except yaml.YAMLError as exc:
            errors.append(f"{agent_file}: invalid YAML frontmatter: {exc}")
            metadata = {}
        else:
            if not isinstance(parsed, dict):
                errors.append(f"{agent_file}: YAML frontmatter must be a mapping")
                metadata = {}
            else:
                metadata = parsed

    missing_keys = sorted(_REQUIRED_FRONTMATTER - metadata.keys())
    if missing_keys:
        errors.append(f"{agent_file}: missing required frontmatter fields: {missing_keys}")

    name = agent_file.stem.replace(".agent", "")
    declared_name = metadata.get("name")
    if declared_name is not None and declared_name != name:
        errors.append(f"{agent_file}: frontmatter name '{declared_name}' must match filename '{name}'")

    for section in _REQUIRED_SECTIONS:
        opening = f"<{section}>"
        closing = f"</{section}>"
        if opening not in content or closing not in content:
            errors.append(f"{agent_file}: missing required <{section}> section")
    return errors


def _check_tool_policy(content: str, fm_lines: list[str], agent_file: Path) -> list[str]:
    """Validate banned and unknown tool declarations."""
    errors: list[str] = []

    if _RESOLVE_URI in content:
        errors.append(f"{agent_file}: contains '{_RESOLVE_URI}'")
    if _MANAGE_TODO_LIST in content:
        errors.append(f"{agent_file}: contains 'manage_todo_list' — tool is disabled for subagents")

    tools = _tools_text(fm_lines)
    if tools and _TODOS_RE.search(tools):
        errors.append(f"{agent_file}: tools: contains 'todos' — tool is disabled for subagents")
    if tools and _BARE_TODO_RE.search(tools):
        errors.append(f"{agent_file}: tools: contains bare 'todo' — tool is disabled for subagents")

    errors.extend(_check_unknown_tools(fm_lines, agent_file))
    return errors


def _check_delegation(content: str, fm_lines: list[str], agent_file: Path) -> list[str]:
    """Validate delegated-agent discovery and resolution."""
    errors: list[str] = []

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

    agent_roots = (agent_file.parent, *_AGENT_ROOTS)
    unresolved = sorted(
        agent for agent in fm_custom if not any((root / f"{agent}.agent.md").is_file() for root in agent_roots)
    )
    if unresolved:
        errors.append(f"{agent_file}: delegated agents do not resolve beside caller: {unresolved}")
    return errors


def _check_required_reading(content: str, agent_file: Path) -> list[str]:
    """Validate that directly required skills resolve in the shared skill tree."""
    match = re.search(r"<required_reading>(.*?)</required_reading>", content, re.DOTALL)
    if match is None:
        return []
    skill_names = set(re.findall(r"`([hwr]-[a-z0-9-]+)`", match.group(1)))
    skill_roots = (agent_file.parent.parent / "skills", *_SKILL_ROOTS)
    unresolved = sorted(
        name for name in skill_names if not any((root / name / "SKILL.md").is_file() for root in skill_roots)
    )
    if not unresolved:
        return []
    return [f"{agent_file}: required skills do not resolve beside agent tree: {unresolved}"]


def validate_agent(agent_file: Path) -> list[str]:
    """Validate one agent's structure, tools, delegation, and nesting metadata."""
    content = Path(agent_file).read_text(encoding="utf-8")
    fm_lines = _frontmatter_lines(content)
    errors = [
        *_check_structure(content, fm_lines, agent_file),
        *_check_tool_policy(content, fm_lines, agent_file),
        *_check_hooks(fm_lines, agent_file),
        *_check_delegation(content, fm_lines, agent_file),
        *_check_required_reading(content, agent_file),
    ]

    name = agent_file.stem.replace(".agent", "")
    dmi = _fm_scalar(fm_lines, "disable-model-invocation")
    if name in ND3_AGENTS and dmi != "false":
        errors.append(f"{agent_file}: ND3 agent must have disable-model-invocation: false (currently: {dmi})")

    return errors


def _discover_agent_files() -> list[Path]:
    """Discover agents from every active project customization root."""
    return sorted({agent_file for root in _AGENT_ROOTS if root.is_dir() for agent_file in root.glob("*.agent.md")})


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Accepts agent file paths; no args = all agents."""
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        agent_files = _discover_agent_files()
        if not agent_files:
            roots = ", ".join(str(root) for root in _AGENT_ROOTS)
            sys.stderr.write(f"No agent files found in active roots: {roots}\n")
            return 1
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
