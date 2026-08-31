"""Behavioral tests for agent and skill ecosystem validators."""

from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).parent.parent
_AGENTS_ROOT = _REPO_ROOT / "share/agents"
_PROMPTS_ROOT = _REPO_ROOT / "share/prompts"
_SKILLS_ROOT = _REPO_ROOT / "share/skills"
_INSTRUCTIONS_ROOT = _REPO_ROOT / "share/instructions"
_LOCAL_INSTRUCTIONS_ROOT = _REPO_ROOT / ".owlbear/instructions"
_AGENT_VALIDATOR_PATH = _REPO_ROOT / ".owlbear/scripts/validate_agents.py"
_SKILL_VALIDATOR_PATH = _REPO_ROOT / ".owlbear/scripts/validate_skills.py"
_PROMPT_VALIDATOR_PATH = _REPO_ROOT / ".owlbear/scripts/validate_prompts.py"
_AGENT_WORKFLOW_PATH = _REPO_ROOT / ".github/workflows/agent-ecosystem.yml"

_EXPECTED_AGENTS = {
    "build-reviewer",
    "builder",
    "conceptual-design-reviewer",
    "designer",
    "designer-challenger",
    "finalizer",
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
    "w-integration-repair",
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
        "publish_delivery_result",
    },
    "orchestrator": {
        "list_work_items",
        "acquire_frontier_work",
        "transition_delivery",
        "recover_claim",
        "recover_integration_repair_claim",
    },
    "finalizer": {
        "show_finalization_context",
        "finalize_change",
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
    "list_integration_ready_changes",
    "integrate_ready_change",
    "prepare_external_completion",
    "show_integration_repair_context",
    "create_integration_repair_candidate",
    "admit_reviewed_integration_repair",
    "publish_integration_repair_authority_attention",
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
_PROMPT_VALIDATOR = _load_module(_PROMPT_VALIDATOR_PATH, "prompt_validator")


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


def _write_prompt(tmp_path: Path, name: str, content: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"{name}.prompt.md"
    path.write_text(content, encoding="utf-8")
    return path


def _frontmatter(path: Path) -> dict[str, object]:
    _, raw, _ = path.read_text(encoding="utf-8").split("---", maxsplit=2)
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict)
    return parsed


def test_agent_workflow_covers_its_contract_tests_without_duplicate_paths() -> None:
    document = yaml.safe_load(_AGENT_WORKFLOW_PATH.read_text(encoding="utf-8"))
    trigger = document.get("on", document.get(True))
    pull_request = trigger["pull_request"]
    job = document["jobs"]["validate-agent-ecosystem"]
    pytest_run = next(str(step["run"]) for step in job["steps"] if "pytest" in str(step.get("run", "")))

    assert set(trigger) == {"pull_request"}
    assert pull_request["branches"] == ["dev"]
    assert len(pull_request["paths"]) == len(set(pull_request["paths"]))
    assert {
        ".github/workflows/dependency-verification.yml",
        ".owlbear/instructions/**",
        "serve/tools/src/owlbear_tools/dependency_ci.py",
        "share/instructions/**",
        "tests/test_dependency_verification_workflow.py",
    } <= set(pull_request["paths"])
    assert job["timeout-minutes"] == 5
    assert "if" not in job
    assert all(
        path in pytest_run
        for path in (
            "tests/test_agent_ecosystem_validation.py",
            "tests/test_write_guard_hooks.py",
            "tests/test_knowledge_ops_contract.py",
            "tests/test_dependency_verification_workflow.py",
        )
    )


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


def test_agent_validator_requires_declared_role_hooks(tmp_path: Path) -> None:
    path = _write_agent(tmp_path, "builder", _agent_text("builder"))

    errors = _AGENT_VALIDATOR.validate_agent(path)

    assert any("missing required SessionStart hook" in error for error in errors)
    assert any("missing required PostToolUse hook" in error for error in errors)


def test_agent_validator_rejects_missing_hook_scripts(tmp_path: Path) -> None:
    content = _agent_text("reader").replace(
        "agents: []\n---",
        """agents: []
hooks:
  PreToolUse:
    - type: command
      command: uv run python .owlbear/hooks/missing.py
---""",
    )
    path = _write_agent(tmp_path, "reader", content)

    errors = _AGENT_VALIDATOR.validate_agent(path)

    assert any("hook script does not exist" in error for error in errors)


def test_agent_validator_discovers_project_local_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_root = tmp_path / ".owlbear/agents"
    path = _write_agent(local_root, "local-agent", _agent_text("local-agent"))
    monkeypatch.setattr(_AGENT_VALIDATOR, "_AGENT_ROOTS", (local_root,))

    assert _AGENT_VALIDATOR._discover_agent_files() == [path]  # noqa: SLF001


def test_prompt_validator_accepts_current_prompt_roots() -> None:
    prompt_files = _PROMPT_VALIDATOR._discover_prompt_files()  # noqa: SLF001

    assert prompt_files
    assert all(_PROMPT_VALIDATOR.validate_prompt(path) == [] for path in prompt_files)


def test_prompt_validator_rejects_unresolved_agent_and_skill(tmp_path: Path) -> None:
    path = _write_prompt(
        tmp_path / "prompts",
        "broken",
        """---
description: Broken prompt
agent: missing-agent
---

Read `h-missing` and `../skills/h-missing/SKILL.md`.
""",
    )

    errors = _PROMPT_VALIDATOR.validate_prompt(path)

    assert any("prompt agent does not resolve" in error for error in errors)
    assert any("referenced skill file does not exist" in error for error in errors)
    assert any("referenced skill does not exist" in error for error in errors)


def test_skill_validator_discovers_project_local_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_root = tmp_path / ".owlbear/skills"
    skill_dir = local_root / "h-local"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: h-local
description: "Handbook: Local"
---

# Local
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(_SKILL_VALIDATOR, "_SKILL_ROOTS", (local_root,))

    assert _SKILL_VALIDATOR.main([]) == 0


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
    from owlbear_browser_mcp.server import mcp as browser_mcp  # noqa: PLC0415
    from owlbear_delivery_mcp.server import mcp as delivery_mcp  # noqa: PLC0415
    from owlbear_delivery_mcp.target_server import DELIVERY_OPERATION_NAMES, assemble_target_server  # noqa: PLC0415
    from owlbear_knowledge_mcp.server import mcp as knowledge_mcp  # noqa: PLC0415
    from owlbear_memory_mcp.server import mcp as memory_mcp  # noqa: PLC0415

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


def test_retired_delivery_operations_are_absent_from_agent_prose() -> None:
    """Retired MCP mutations must not survive in agent instructions or examples."""
    for agent_path in _AGENTS_ROOT.glob("*.agent.md"):
        content = agent_path.read_text(encoding="utf-8")
        for operation in _RETIRED_DELIVERY_TOOLS:
            assert operation not in content, f"{agent_path.name} mentions retired Delivery operation {operation}"

    orchestrator = (_AGENTS_ROOT / "orchestrator.agent.md").read_text(encoding="utf-8")
    assert "repair result" not in orchestrator
    assert "repair-authority attention" not in orchestrator


def test_retired_skills_are_absent_from_active_customization_prose() -> None:
    """Retired skill names must not survive in active customization sources."""
    roots = (
        _REPO_ROOT / "share/agents",
        _REPO_ROOT / "share/instructions",
        _REPO_ROOT / "share/prompts",
        _REPO_ROOT / "share/skills",
        _REPO_ROOT / ".owlbear/agents",
        _REPO_ROOT / ".owlbear/instructions",
        _REPO_ROOT / ".owlbear/prompts",
        _REPO_ROOT / ".owlbear/skills",
    )
    active_files = [path for root in roots if root.is_dir() for path in root.rglob("*") if path.is_file()]
    active_files.append(_REPO_ROOT / ".github/copilot-instructions.md")

    for path in active_files:
        content = path.read_text(encoding="utf-8")
        for skill in _RETIRED_SKILLS:
            assert re.search(rf"(?<![a-z0-9-]){re.escape(skill)}(?![a-z0-9-])", content) is None, (
                f"{path.relative_to(_REPO_ROOT)} mentions retired skill {skill}"
            )


def test_project_doc_instruction_declares_local_standard_route() -> None:
    """The local doc wiring declares its scope and standards route; runtime loading is separate."""
    path = _LOCAL_INSTRUCTIONS_ROOT / "doc-types.instructions.md"
    content = path.read_text(encoding="utf-8")
    _, raw_frontmatter, _ = content.split("---", maxsplit=2)
    metadata = yaml.safe_load(raw_frontmatter)
    assert isinstance(metadata, dict)

    apply_to = metadata["applyTo"]
    assert isinstance(apply_to, str)
    assert {
        ".github/README-automation.md",
        ".owlbear/README.md",
        "store/README.md",
        "tests/README.md",
    } <= set(apply_to.split(","))
    assert "Before applying these project-specific document-type rules, read `r-doc-standards`" in content


def test_memory_curator_identity_deferral_reporting_split() -> None:
    """Periodic curation keeps identity-only uncertainty pending without reporting it."""
    workflow = (_SKILLS_ROOT / "w-mem-curation/SKILL.md").read_text(encoding="utf-8")
    curator = (_AGENTS_ROOT / "memory-curator.agent.md").read_text(encoding="utf-8")
    structure = (_SKILLS_ROOT / "h-memory-structure/SKILL.md").read_text(encoding="utf-8")

    content = " ".join(f"{workflow}\n{curator}\n{structure}".split())

    assert "Classify content before provenance or scope." in content
    assert "`*` is anonymous provenance" in content
    assert (
        "Identity-only uncertainty remains pending and is omitted from periodic defer and conflict summaries."
        in content
    )
    assert "Conflicts and ordinary content or scope uncertainty remain reportable." in content
    assert "another reviewed non-pending entry or a readable local definition" in content


def test_memory_curator_required_skill_falls_back_to_shared_root() -> None:
    """The curator's logical workflow resolves when no project-local override exists."""
    agent = (_AGENTS_ROOT / "memory-curator.agent.md").read_text(encoding="utf-8")
    skill = _SKILLS_ROOT / "w-mem-curation/SKILL.md"

    assert "fall back to `share/skills` when no local override exists" in agent
    assert skill.is_file()
    assert "owlbear-memory/list_memories" in agent
    assert "owlbear-memory/commit_memory_batch" in agent


def test_memory_audit_rescoping_requires_corroborated_agent_names() -> None:
    """Manual review cannot infer named scope from an entry's own provenance."""
    prompt = (_PROMPTS_ROOT / "memory-audit.prompt.md").read_text(encoding="utf-8")
    guidance = (_SKILLS_ROOT / "h-mcp-memory/SKILL.md").read_text(encoding="utf-8")
    system = (_INSTRUCTIONS_ROOT / "owlbear-system.instructions.md").read_text(encoding="utf-8")

    content = " ".join(f"{prompt}\n{guidance}\n{system}".split())

    assert "another reviewed non-pending memory, a readable local `.agent.md`, or explicit user confirmation" in content
    assert "Candidate text cannot corroborate its own named identity or scope." in content
    assert "Identity evidence does not raise stored entry confidence or review confidence." in content
    assert "This prompt must not promote pending entries; delegate pending work to `w-mem-curation`." in content
