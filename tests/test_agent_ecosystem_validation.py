"""Behavioral tests for agent and skill ecosystem validators."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest
import yaml

_REPO_ROOT = Path(__file__).parent.parent
_AGENTS_ROOT = _REPO_ROOT / "share/agents"
_PROMPTS_ROOT = _REPO_ROOT / "share/prompts"
_SKILLS_ROOT = _REPO_ROOT / "share/skills"
_INSTRUCTIONS_ROOT = _REPO_ROOT / "share/instructions"
_AGENT_VALIDATOR_PATH = _REPO_ROOT / ".owlbear/scripts/validate_agents.py"
_SKILL_VALIDATOR_PATH = _REPO_ROOT / ".owlbear/scripts/validate_skills.py"

_EXPECTED_AGENTS = {
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
    "acceptor",
    "auditor",
    "builder-challenger",
    "collector",
    "shaper",
    "shaper-challenger",
    "verifier",
    "verifier-challenger",
}
_RETIRED_SKILLS = {
    "h-mcp-delivery",
    "r-pipeline-protocol",
    "w-spec-shaping",
    "w-task-decomposition",
    "w-task-repair",
    "w-node-acceptance",
    "w-whole-change-audit",
}
_GENERIC_TASK_TOOLS = {
    "owlbear-delivery/create_task",
    "owlbear-delivery/edit_task",
    "owlbear-delivery/end_work",
    "owlbear-delivery/list_tasks",
    "owlbear-delivery/move_task",
    "owlbear-delivery/pick_tasks",
    "owlbear-delivery/show_task",
    "owlbear-delivery/start_work",
}
_TARGET_ROLE_TOOLS = {
    "designer": {
        "create_design_session",
        "read_design_session",
        "revise_design_session",
        "publish_design_checkpoint",
        "derive_delivery_contract",
        "validate_delivery_contract",
        "admit_delivery_change",
    },
    "planner": {"show_plan_context", "publish_delivery_plan"},
    "builder": {
        "show_build_context",
        "show_integration_repair_context",
        "publish_delivery_result",
        "admit_reviewed_integration_repair",
    },
    "orchestrator": {
        "list_work_items",
        "acquire_frontier_work",
        "transition_delivery",
        "recover_claim",
        "recover_integration_repair_claim",
        "publish_integration_repair_authority_attention",
        "integrate_ready_change",
    },
}
_RETIRED_DELIVERY_TOOLS = {
    "arbitrate_attempt",
    "finish_assembly",
    "finish_build",
    "finish_plan",
    "list_frontier",
    "list_semantic_updates",
    "list_work_item_activity",
    "recover_interrupted_task",
    "respond_to_review",
    "show_attempt",
    "show_completion_summary",
    "show_job",
    "show_receipt",
    "start_job",
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


class _TargetApplicationDouble:
    def __getattr__(self, _name: str) -> object:
        def operation(*_args: object, **_kwargs: object) -> None:
            return None

        return operation


def test_agent_validator_accepts_valid_structure_and_known_mcp_server(tmp_path: Path) -> None:
    path = _write_agent(tmp_path, "reader", _agent_text("reader", tools="[owlbear-browser/acquire]"))

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

    conceptual = _write_agent(
        tmp_path,
        "conceptual-design-reviewer",
        _agent_text("conceptual-design-reviewer"),
    )
    assert any(
        "ND3 agent must have disable-model-invocation: false" in error
        for error in _AGENT_VALIDATOR.validate_agent(conceptual)
    )


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


@pytest.mark.asyncio
async def test_declared_mcp_tools_exist_in_live_registries() -> None:
    from owlbear_browser_mcp.server import mcp as browser_mcp
    from owlbear_delivery_mcp.server import mcp as delivery_mcp
    from owlbear_delivery_mcp.target_server import DELIVERY_OPERATION_NAMES, assemble_target_server
    from owlbear_knowledge_mcp.server import mcp as knowledge_mcp
    from owlbear_memory_mcp.server import mcp as memory_mcp

    target_mcp = assemble_target_server(_TargetApplicationDouble())  # type: ignore[arg-type]
    registries = {
        "owlbear-browser": {tool.name for tool in await browser_mcp.list_tools()},
        "owlbear-delivery": {tool.name for tool in await delivery_mcp.list_tools()},
        "owlbear-knowledge": {tool.name for tool in await knowledge_mcp.list_tools()},
        "owlbear-memory": {tool.name for tool in await memory_mcp.list_tools()},
    }
    target_registry = {tool.name for tool in await target_mcp.list_tools()}
    assert target_registry == set(DELIVERY_OPERATION_NAMES)
    assert target_registry.isdisjoint(_RETIRED_DELIVERY_TOOLS)

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
            available = (
                target_registry
                if server == "owlbear-delivery" and metadata["name"] in _TARGET_ROLE_TOOLS
                else registered
            )
            missing = declared - available
            assert not missing, f"{agent_path.name} has unavailable {server} tools: {sorted(missing)}"

    metadata = {path.stem.removesuffix(".agent"): _frontmatter(path) for path in _AGENTS_ROOT.glob("*.agent.md")}
    for role, expected in _TARGET_ROLE_TOOLS.items():
        declared = {
            tool.removeprefix("owlbear-delivery/")
            for tool in metadata[role]["tools"]
            if tool.startswith("owlbear-delivery/")
        }
        assert declared == expected


def test_installed_delivery_ecosystem_is_native_only() -> None:
    agents = {path.stem.removesuffix(".agent") for path in _AGENTS_ROOT.glob("*.agent.md")}
    assert agents == _EXPECTED_AGENTS
    assert agents.isdisjoint(_RETIRED_AGENTS)

    metadata = {path.stem.removesuffix(".agent"): _frontmatter(path) for path in _AGENTS_ROOT.glob("*.agent.md")}
    orchestrator = metadata["orchestrator"]
    assert orchestrator["agents"] == ["planner", "builder", "memory-curator", "Explore"]
    assert {
        tool.removeprefix("owlbear-delivery/") for tool in orchestrator["tools"] if tool.startswith("owlbear-delivery/")
    } == (_TARGET_ROLE_TOOLS["orchestrator"])
    assert metadata["builder"]["agents"] == ["build-reviewer"]
    assert metadata["designer"]["agents"] == ["conceptual-design-reviewer", "designer-challenger", "Explore"]

    declared_tools = {tool for agent in metadata.values() for tool in agent.get("tools", []) if isinstance(tool, str)}
    assert declared_tools.isdisjoint(_GENERIC_TASK_TOOLS)

    prompts = {path.stem.removesuffix(".prompt"): _frontmatter(path) for path in _PROMPTS_ROOT.glob("*.prompt.md")}
    assert "shape" not in prompts
    assert prompts["ideate"]["agent"] == "designer"
    assert prompts["design"]["agent"] == "designer"
    assert prompts["orchestrate"]["agent"] == "orchestrator"
    assert "integration-repair" not in prompts
    assert {prompt.get("agent") for prompt in prompts.values()}.isdisjoint(_RETIRED_AGENTS)

    skills = {path.parent.name for path in _SKILLS_ROOT.glob("*/SKILL.md")}
    assert _RETIRED_SKILLS.isdisjoint(skills)
    assert {
        "w-design-session",
        "w-frontier-planning",
        "w-packet-building",
        "w-orchestration",
        "w-integration-repair",
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


def test_target_role_write_and_lifecycle_guards_are_preserved() -> None:
    metadata = {path.stem.removesuffix(".agent"): _frontmatter(path) for path in _AGENTS_ROOT.glob("*.agent.md")}

    builder = metadata["builder"]
    assert builder["hooks"] == {
        "SessionStart": [{"type": "command", "command": "uv run python .owlbear/hooks/session-context.py"}],
        "PostToolUse": [{"type": "command", "command": "uv run python .owlbear/hooks/lint-changed.py"}],
    }
    assert not any(tool.startswith("owlbear-delivery/finish_") for tool in builder["tools"])

    assert metadata["planner"]["hooks"] == {
        "PreToolUse": [
            {
                "type": "command",
                "command": "uv run python .owlbear/hooks/deny-writes.py --terminal-read-only",
            }
        ]
    }
    assert metadata["designer"]["hooks"] == {
        "PreToolUse": [
            {
                "type": "command",
                "command": "uv run python .owlbear/hooks/deny-writes.py --allow-research --terminal-read-only",
            }
        ]
    }

    orchestrator_tools = set(metadata["orchestrator"]["tools"])
    assert not any(tool.startswith("edit/") for tool in orchestrator_tools)
    assert not any(tool.startswith("execute/") for tool in orchestrator_tools)
    assert metadata["build-reviewer"]["hooks"] == {
        "PreToolUse": [
            {
                "type": "command",
                "command": "uv run python .owlbear/hooks/deny-writes.py --terminal-read-only",
            }
        ]
    }
    assert "execute/runInTerminal" in metadata["build-reviewer"]["tools"]
    assert "execute/runInTerminal" not in metadata["planner-challenger"]["tools"]
    assert metadata["planner-challenger"]["hooks"] == {
        "PreToolUse": [{"type": "command", "command": "uv run python .owlbear/hooks/deny-writes.py"}]
    }


def test_design_entries_preserve_gate_order_and_warning_policy() -> None:
    ideate = (_PROMPTS_ROOT / "ideate.prompt.md").read_text(encoding="utf-8")
    design = (_PROMPTS_ROOT / "design.prompt.md").read_text(encoding="utf-8")
    designer = (_AGENTS_ROOT / "designer.agent.md").read_text(encoding="utf-8")
    workflow = (_SKILLS_ROOT / "w-design-session" / "SKILL.md").read_text(encoding="utf-8")

    assert "design, derivation, challenge, baseline, checkpoint,\nvalidation" in ideate
    assert "derivation, challenge,\nbaseline, checkpoint, validation, approval, and admission" in design
    assert "Derive, challenge, baseline, checkpoint,\n  and validate one unchanged package" in designer
    assert "An `error` or malformed challenge" in workflow
    assert "A non-pass challenge" not in workflow
    assert "Warnings must be visible in the complete review" in workflow


def test_planning_quality_reaches_author_and_independent_reviewer() -> None:
    workflow = (_SKILLS_ROOT / "w-frontier-planning" / "SKILL.md").read_text(encoding="utf-8")
    challenger = (_AGENTS_ROOT / "planner-challenger.agent.md").read_text(encoding="utf-8")

    assert "Load `h-codebase-orientation`, `h-module-design`, and `h-ac-quality`" in workflow
    assert "acceptance_observations" in workflow
    assert "proof_boundaries" in workflow
    assert "`h-ac-quality` - boundary-valid proof quality" in challenger


def test_decision_request_guidance_reaches_primary_workers() -> None:
    planning = (_SKILLS_ROOT / "w-frontier-planning" / "SKILL.md").read_text(encoding="utf-8")
    building = (_SKILLS_ROOT / "w-packet-building" / "SKILL.md").read_text(encoding="utf-8")
    handbook = (_SKILLS_ROOT / "h-decision-requests" / "SKILL.md").read_text(encoding="utf-8")

    for workflow in (planning, building):
        assert "If context contains a request or a request may be needed" in workflow
        assert "load `h-decision-requests`" in workflow
        assert "authority-equivalent" in workflow
    assert "Planner may choose decomposition" in planning
    assert "Builder may choose internal implementation details" in building
    assert "options: [{option_id:" in building
    assert "one concrete recommended proposal is valid" in handbook
    assert "Never invent a meaningless second option" in handbook


def test_target_delivery_workflows_enforce_review_and_remove_obsolete_controls() -> None:
    delivery_paths = (
        _AGENTS_ROOT / "orchestrator.agent.md",
        _AGENTS_ROOT / "builder.agent.md",
        _SKILLS_ROOT / "w-orchestration" / "SKILL.md",
        _SKILLS_ROOT / "w-frontier-planning" / "SKILL.md",
        _SKILLS_ROOT / "w-packet-building" / "SKILL.md",
    )
    content = "\n".join(path.read_text(encoding="utf-8") for path in delivery_paths)
    ecosystem_paths = (
        *sorted(_AGENTS_ROOT.glob("*.agent.md")),
        *sorted(_SKILLS_ROOT.glob("*/SKILL.md")),
        *sorted(_INSTRUCTIONS_ROOT.glob("*.instructions.md")),
        _REPO_ROOT / "share/WIRING.md",
        _REPO_ROOT / ".github/copilot-instructions.md",
    )
    ecosystem_content = "\n".join(path.read_text(encoding="utf-8") for path in ecosystem_paths)

    delivery_operations = {tool for role in ("planner", "builder", "orchestrator") for tool in _TARGET_ROLE_TOOLS[role]}
    for operation in delivery_operations:
        assert operation in content
    assert "deliverylaunchpackage" in content.lower()
    assert "deliverytransition" in content.lower()
    assert "kind: dispatch_failure" in content.lower()
    assert "failed_operation: show_build_context" in content.lower()
    assert "never forward this result to `transition_delivery`" in content.lower()
    assert "use that same exact `recover_claim` request" in content.lower()
    assert "byte-for-structure unchanged" in content.lower()
    assert "deliverybuildcontext.task_digest" in content.lower()
    assert "unblock_condition" in content
    assert "expected_evidence" in content
    assert "rejected `transition_delivery`" in content
    assert not {operation for operation in _RETIRED_DELIVERY_TOOLS if operation in content}

    obsolete = (
        "finish_accept",
        "reject_accept",
        "finish_audit",
        "reject_audit",
        "release_job",
        "pick_jobs",
        "shared writable worktree",
        "`dev` integration",
        "Priority",
        "Cancel",
    )
    assert not {term for term in obsolete if term in ecosystem_content}
    retired = ("accept job", "audit job", "acceptor", "auditor", "w-node-acceptance", "w-whole-change-audit")
    assert not {term for term in retired if term in ecosystem_content.lower()}
