"""Behavioral tests for agent and skill ecosystem validators."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import yaml

_REPO_ROOT = Path(__file__).parent.parent
_AGENTS_ROOT = _REPO_ROOT / "share/agents"
_PROMPTS_ROOT = _REPO_ROOT / "share/prompts"
_SKILLS_ROOT = _REPO_ROOT / "share/skills"
_INSTRUCTIONS_ROOT = _REPO_ROOT / "share/instructions"
_AGENT_VALIDATOR_PATH = _REPO_ROOT / ".owlbear/scripts/validate_agents.py"
_SKILL_VALIDATOR_PATH = _REPO_ROOT / ".owlbear/scripts/validate_skills.py"

_EXPECTED_AGENTS = {
    "acceptor",
    "auditor",
    "build-reviewer",
    "builder",
    "conceptual-design-reviewer",
    "designer",
    "designer-challenger",
    "knowledge-enricher",
    "knowledge-ingestor",
    "memory-curator",
    "orchestrator",
    "planner",
    "planner-challenger",
    "test-curator",
}
_RETIRED_AGENTS = {
    "builder-challenger",
    "collector",
    "shaper",
    "shaper-challenger",
    "verifier",
    "verifier-challenger",
}
_RETIRED_SKILLS = {
    "h-mcp-kanban",
    "r-pipeline-protocol",
    "w-spec-shaping",
    "w-task-decomposition",
    "w-task-repair",
}
_GENERIC_TASK_TOOLS = {
    "ob-kanban/create_task",
    "ob-kanban/edit_task",
    "ob-kanban/end_work",
    "ob-kanban/list_tasks",
    "ob-kanban/move_task",
    "ob-kanban/pick_tasks",
    "ob-kanban/show_task",
    "ob-kanban/start_work",
}


def _load_module(path: Path, name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


_AGENT_VALIDATOR = _load_module(_AGENT_VALIDATOR_PATH, "agent_validator")
_SKILL_VALIDATOR = _load_module(_SKILL_VALIDATOR_PATH, "skill_validator")


def _agent_text(
    name: str,
    *,
    tools: str = "[search]",
    agents: str = "[]",
    agent_rows: str = "",
    disable_model_invocation: str = "true",
) -> str:
    return f"""---
name: {name}
description: "Test agent"
user-invocable: false
disable-model-invocation: {disable_model_invocation}
model: test-model
tools: {tools}
agents: {agents}
---

<persona>Test role.</persona>
<required_reading>None.</required_reading>
<critical_rules>Validate structure.</critical_rules>
<agents>
| Agent | When |
|-------|------|
{agent_rows}</agents>
<output_format>Text.</output_format>
<boundaries>None.</boundaries>
<examples>Example.</examples>
"""


def _write_agent(tmp_path: Path, name: str, content: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"{name}.agent.md"
    path.write_text(content, encoding="utf-8")
    return path


def _frontmatter(path: Path) -> dict[str, object]:
    _, raw, _ = path.read_text(encoding="utf-8").split("---", maxsplit=2)
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict)
    return parsed


def test_agent_validator_accepts_valid_structure_and_known_mcp_server(tmp_path: Path) -> None:
    path = _write_agent(tmp_path, "reader", _agent_text("reader", tools="[ob-browser/acquire]"))

    assert _AGENT_VALIDATOR.validate_agent(path) == []


def test_agent_validator_rejects_malformed_frontmatter_and_missing_sections(tmp_path: Path) -> None:
    path = _write_agent(tmp_path, "broken", "---\nname: broken\ntools: [search\n")

    errors = _AGENT_VALIDATOR.validate_agent(path)

    assert any("missing or unterminated YAML frontmatter" in error for error in errors)
    assert any("missing required frontmatter fields" in error for error in errors)
    assert any("missing required <persona> section" in error for error in errors)


def test_agent_validator_rejects_unknown_and_banned_tools(tmp_path: Path) -> None:
    path = _write_agent(
        tmp_path,
        "broken",
        _agent_text("broken", tools="[unknown/run, unknown/*, manage_todo_list]"),
    )

    errors = _AGENT_VALIDATOR.validate_agent(path)

    assert any("unknown tool 'unknown/run'" in error for error in errors)
    assert any("unknown tool 'unknown/*'" in error for error in errors)
    assert any("manage_todo_list" in error for error in errors)


def test_agent_validator_rejects_unresolved_or_misaligned_delegates(tmp_path: Path) -> None:
    path = _write_agent(
        tmp_path,
        "caller",
        _agent_text("caller", agents="[missing]", agent_rows="| other | Review |\n"),
    )

    errors = _AGENT_VALIDATOR.validate_agent(path)

    assert any("missing from <agents> table" in error for error in errors)
    assert any("missing from frontmatter agents" in error for error in errors)
    assert any("delegated agents do not resolve" in error for error in errors)


def test_agent_validator_enforces_filename_and_nd3_invocation(tmp_path: Path) -> None:
    path = _write_agent(tmp_path, "planner-challenger", _agent_text("wrong-name"))

    errors = _AGENT_VALIDATOR.validate_agent(path)

    assert any("must match filename 'planner-challenger'" in error for error in errors)
    assert any("ND3 agent must have disable-model-invocation: false" in error for error in errors)


def test_agent_validator_rejects_unresolved_required_skills(tmp_path: Path) -> None:
    path = _write_agent(
        tmp_path / "share/agents",
        "reader",
        _agent_text("reader").replace(
            "<required_reading>None.</required_reading>", "<required_reading>`h-missing`</required_reading>"
        ),
    )

    errors = _AGENT_VALIDATOR.validate_agent(path)

    assert any("required skills do not resolve" in error for error in errors)


def test_skill_validator_accepts_vendor_fields_and_rejects_missing_metadata(tmp_path: Path) -> None:
    valid_dir = tmp_path / "h-example"
    valid_dir.mkdir()
    (valid_dir / "SKILL.md").write_text(
        """---
name: h-example
description: "Handbook: Example"
user-invocable: false
---

# Example
""",
        encoding="utf-8",
    )
    invalid_dir = tmp_path / "h-invalid"
    invalid_dir.mkdir()
    (invalid_dir / "SKILL.md").write_text("---\nname: h-invalid\n---\n", encoding="utf-8")

    assert _SKILL_VALIDATOR.validate_skill(valid_dir) == []
    assert _SKILL_VALIDATOR.validate_skill(invalid_dir)


def test_declared_owlbear_mcp_tools_exist_in_live_registries() -> None:
    from owlbear_mcp_browser.server import mcp_app as browser_mcp
    from owlbear_mcp_kanban.server import mcp as kanban_mcp
    from owlbear_mcp_knowledge.server import mcp as knowledge_mcp
    from owlbear_mcp_memory.server import mcp as memory_mcp

    registries = {
        "ob-browser": {tool.name for tool in browser_mcp.list_tools()},
        "ob-kanban": {tool.name for tool in kanban_mcp._tool_manager.list_tools()},  # noqa: SLF001
        "ob-knowledge": {tool.name for tool in knowledge_mcp._tool_manager.list_tools()},  # noqa: SLF001
        "ob-memory": {tool.name for tool in memory_mcp._tool_manager.list_tools()},  # noqa: SLF001
    }

    for agent_path in _AGENTS_ROOT.glob("*.agent.md"):
        metadata = _frontmatter(agent_path)
        tools = metadata.get("tools", [])
        assert isinstance(tools, list)
        for server, registered in registries.items():
            declared = {
                tool.removeprefix(f"{server}/")
                for tool in tools
                if isinstance(tool, str) and tool.startswith(f"{server}/") and not tool.endswith("/*")
            }
            missing = declared - registered
            assert not missing, f"{agent_path.name} has unavailable {server} tools: {sorted(missing)}"


def test_installed_delivery_ecosystem_is_native_only() -> None:
    agents = {path.stem.removesuffix(".agent") for path in _AGENTS_ROOT.glob("*.agent.md")}
    assert agents == _EXPECTED_AGENTS
    assert agents.isdisjoint(_RETIRED_AGENTS)

    metadata = {path.stem.removesuffix(".agent"): _frontmatter(path) for path in _AGENTS_ROOT.glob("*.agent.md")}
    orchestrator = metadata["orchestrator"]
    assert orchestrator["agents"] == ["planner", "builder", "acceptor", "auditor", "memory-curator", "Explore"]
    assert {
        "ob-kanban/pick_jobs",
        "ob-kanban/start_job",
        "ob-kanban/finish_plan",
        "ob-kanban/finish_build",
        "ob-kanban/finish_accept",
        "ob-kanban/finish_audit",
    } <= set(orchestrator["tools"])
    assert metadata["builder"]["agents"] == ["build-reviewer"]
    assert metadata["designer"]["agents"] == ["conceptual-design-reviewer", "designer-challenger", "Explore"]

    declared_tools = {tool for agent in metadata.values() for tool in agent.get("tools", []) if isinstance(tool, str)}
    assert declared_tools.isdisjoint(_GENERIC_TASK_TOOLS)

    prompts = {path.stem.removesuffix(".prompt"): _frontmatter(path) for path in _PROMPTS_ROOT.glob("*.prompt.md")}
    assert "shape" not in prompts
    assert prompts["ideate"]["agent"] == "designer"
    assert prompts["design"]["agent"] == "designer"
    assert prompts["orchestrate"]["agent"] == "orchestrator"
    assert {prompt.get("agent") for prompt in prompts.values()}.isdisjoint(_RETIRED_AGENTS)

    skills = {path.parent.name for path in _SKILLS_ROOT.glob("*/SKILL.md")}
    assert _RETIRED_SKILLS.isdisjoint(skills)
    assert {
        "w-design-session",
        "w-frontier-planning",
        "w-packet-building",
        "w-node-acceptance",
        "w-whole-change-audit",
        "w-orchestration",
    } <= skills

    instructions = {path.stem.removesuffix(".instructions") for path in _INSTRUCTIONS_ROOT.glob("*.instructions.md")}
    assert instructions == {
        "agent-ecosystem",
        "doc-standards",
        "frontend",
        "owlbear-system",
        "python",
        "research-docs",
    }


def test_native_role_write_and_lifecycle_guards_are_preserved() -> None:
    metadata = {path.stem.removesuffix(".agent"): _frontmatter(path) for path in _AGENTS_ROOT.glob("*.agent.md")}

    builder = metadata["builder"]
    assert builder["hooks"] == {
        "SessionStart": [{"type": "command", "command": "uv run python .owlbear/hooks/session-context.py"}],
        "PostToolUse": [{"type": "command", "command": "uv run python .owlbear/hooks/lint-changed.py"}],
    }
    assert not any(tool.startswith("ob-kanban/finish_") for tool in builder["tools"])

    for role in ("acceptor", "auditor"):
        assert metadata[role]["hooks"] == {
            "PreToolUse": [
                {
                    "type": "command",
                    "command": "uv run python .owlbear/hooks/deny-writes.py --terminal-read-only",
                }
            ]
        }
        assert not any(tool.startswith("edit/") for tool in metadata[role]["tools"])

    orchestrator_tools = set(metadata["orchestrator"]["tools"])
    assert not any(tool.startswith("edit/") for tool in orchestrator_tools)
    assert not any(tool.startswith("execute/") for tool in orchestrator_tools)
    assert metadata["build-reviewer"]["hooks"] == {
        "PreToolUse": [{"type": "command", "command": "uv run python .owlbear/hooks/deny-writes.py"}]
    }
