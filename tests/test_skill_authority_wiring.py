"""Regression tests for intentional agent loading of shared project authorities."""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENTS_ROOT = _REPO_ROOT / "share/agents"
_SHARE_ROOT = _REPO_ROOT / "share"

_EXPECTED_REQUIRED_READERS = {
    "h-codebase-orientation": {"builder", "verifier"},
    "h-module-design": {"shaper-challenger"},
    "r-workspace-governance": {
        "builder",
        "collector",
        "shaper",
        "verifier",
    },
}


def _required_skills(path: Path) -> set[str]:
    content = path.read_text(encoding="utf-8")
    match = re.search(r"<required_reading>(.*?)</required_reading>", content, re.DOTALL)
    assert match is not None, f"Missing required_reading in {path.name}"
    return set(re.findall(r"`([hwr]-[a-z0-9-]+)`", match.group(1)))


def test_authorities_have_intentional_regular_agent_readers() -> None:
    """Regular loading stays limited to roles that need an authority in nearly every session."""
    actual = {skill: set() for skill in _EXPECTED_REQUIRED_READERS}
    for agent_path in _AGENTS_ROOT.glob("*.agent.md"):
        for skill in _required_skills(agent_path):
            if skill in actual:
                actual[skill].add(agent_path.name.removesuffix(".agent.md"))

    assert actual == _EXPECTED_REQUIRED_READERS


def test_on_demand_authority_paths_are_declared() -> None:
    """Roles with situational needs can discover the authority without regular loading."""
    orientation = (_REPO_ROOT / "share/skills/h-codebase-orientation/SKILL.md").read_text(encoding="utf-8")
    protocol = (_REPO_ROOT / "share/skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    spec_shaping = (_REPO_ROOT / "share/skills/w-spec-shaping/SKILL.md").read_text(encoding="utf-8")
    task_repair = (_REPO_ROOT / "share/skills/w-task-repair/SKILL.md").read_text(encoding="utf-8")

    assert "`h-module-design`" in orientation
    assert "`r-workspace-governance`" in protocol
    assert "`h-codebase-orientation`" in spec_shaping
    assert "`h-module-design`" in spec_shaping
    assert "`h-codebase-orientation`" in task_repair


def test_memory_tools_follow_exact_role_profiles() -> None:
    """Every memory grant belongs to one complete, documented capability profile."""
    expected = {
        "builder": {"assess_memories", "recall_memory", "save_memory"},
        "collector": {"assess_memories", "recall_memory", "save_memory"},
        "memory-curator": {"curate_memory", "delete_memory", "list_memories", "read_memory"},
        "shaper": {"assess_memories", "recall_memory", "save_memory"},
        "test-curator": {"save_memory"},
        "verifier": {"assess_memories", "recall_memory", "save_memory"},
    }
    actual: dict[str, set[str]] = {}
    for agent_path in _AGENTS_ROOT.glob("*.agent.md"):
        content = agent_path.read_text(encoding="utf-8")
        tools = set(re.findall(r"ob-memory/([a-z_]+)", content))
        if tools:
            actual[agent_path.name.removesuffix(".agent.md")] = tools

    assert actual == expected


def test_memory_tool_profiles_have_reachable_instructions() -> None:
    """Granted tools are introduced by guaranteed context before the operation is required."""
    task_owners = {"builder", "collector", "shaper", "verifier"}
    for agent_name in task_owners:
        assert "r-pipeline-protocol" in _required_skills(_AGENTS_ROOT / f"{agent_name}.agent.md")

    protocol = (_SHARE_ROOT / "skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    system = (_SHARE_ROOT / "instructions/owlbear-system.instructions.md").read_text(encoding="utf-8")
    structure = (_SHARE_ROOT / "skills/h-memory-structure/SKILL.md").read_text(encoding="utf-8")
    handbook = (_SHARE_ROOT / "skills/h-mcp-memory/SKILL.md").read_text(encoding="utf-8")
    curation = (_SHARE_ROOT / "skills/w-mem-curation/SKILL.md").read_text(encoding="utf-8")

    assert "| `h-mcp-memory` | `recall_memory` returned entries" in protocol
    assert "load `h-mcp-memory` and call `assess_memories`" in protocol
    assert re.search(r"Include every returned\s+entry in one assessment batch", protocol)
    assert re.search(r"including entries you did\s+not apply or reference", protocol)
    assert "Challengers do not recall or assess memory" in protocol

    assert "If `save_memory` is available and an insight qualifies" in system
    assert "load `h-memory-structure`" in system
    assert "`h-mcp-memory` for tool syntax" in system
    assert "the memory curator owns deduplication" in system
    assert "Ordinary writers do not need `list_memories` or\n`read_memory`" in structure
    assert "Candidate producer | test-curator | `save_memory`" in handbook

    for tool in ("list_memories", "read_memory", "curate_memory", "delete_memory"):
        assert f"`{tool}" in curation


def test_declared_mcp_tools_are_registered_at_runtime() -> None:
    """Every explicitly granted Kanban and memory tool exists in its live MCP registry."""
    from owlbear_mcp_kanban.server import mcp as kanban_mcp  # noqa: PLC0415
    from owlbear_mcp_memory.server import mcp as memory_mcp  # noqa: PLC0415

    registries = {
        "ob-kanban": {tool.name for tool in kanban_mcp._tool_manager.list_tools()},  # noqa: SLF001
        "ob-memory": {tool.name for tool in memory_mcp._tool_manager.list_tools()},  # noqa: SLF001
    }
    for agent_path in _AGENTS_ROOT.glob("*.agent.md"):
        content = agent_path.read_text(encoding="utf-8")
        for server, registered in registries.items():
            declared = set(re.findall(rf"{server}/([a-z_]+)", content))
            assert declared <= registered, f"{agent_path.name} has unavailable {server} tools: {declared - registered}"


def test_mcp_capable_agents_can_load_deferred_tools() -> None:
    """Every agent granted an MCP operation can invoke the documented deferred-tool loader."""
    for agent_path in _AGENTS_ROOT.glob("*.agent.md"):
        content = agent_path.read_text(encoding="utf-8")
        if re.search(r"ob-(?:kanban|memory)/", content):
            assert "vscode/toolSearch" in content, f"{agent_path.name} cannot load deferred MCP tools"

    system = (_SHARE_ROOT / "instructions/owlbear-system.instructions.md").read_text(encoding="utf-8")
    assert "| OwlBear Kanban | `ob-kanban/*`" in system
    assert "| OwlBear Memory | `ob-memory/*`" in system
    assert '"kanban"' in system
    assert '"memory"' in system


def test_pipeline_kanban_tools_follow_role_boundaries() -> None:
    """Pipeline roles receive the exact Kanban mutations and reads their workflows require."""
    expected = {
        "builder": {
            "create_request",
            "edit_task",
            "end_work",
            "list_requests",
            "list_tasks",
            "show_request",
            "show_task",
            "start_work",
        },
        "collector": {
            "edit_task",
            "end_work",
            "list_requests",
            "list_tasks",
            "show_request",
            "show_task",
            "start_work",
        },
        "orchestrator": {"edit_task", "end_work", "pick_tasks"},
        "shaper": {
            "create_request",
            "create_task",
            "edit_task",
            "end_work",
            "list_requests",
            "list_tasks",
            "move_task",
            "show_request",
            "show_task",
            "start_work",
        },
        "verifier": {
            "create_request",
            "edit_task",
            "end_work",
            "list_requests",
            "list_tasks",
            "show_request",
            "show_task",
            "start_work",
        },
    }
    for agent_name, expected_tools in expected.items():
        content = (_AGENTS_ROOT / f"{agent_name}.agent.md").read_text(encoding="utf-8")
        actual = set(re.findall(r"ob-kanban/([a-z_]+)", content))
        assert actual == expected_tools

    collector = (_AGENTS_ROOT / "collector.agent.md").read_text(encoding="utf-8")
    assert "ob-kanban/create_request" not in collector
    protocol = (_SHARE_ROOT / "skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    assert "Collector | Never create requests" in protocol


def test_pipeline_commit_gate_includes_final_task_state() -> None:
    """Pipeline closure commits after end_work and includes archive moves explicitly."""
    governance = (_REPO_ROOT / "share/skills/r-workspace-governance/SKILL.md").read_text(encoding="utf-8")
    protocol = (_REPO_ROOT / "share/skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")

    assert "call `end_work` first" in governance
    assert "Do not return `DONE`, `PASS`, or `ARCHIVED`" in governance
    assert "### After `end_work`" in protocol
    assert "Include the final task record in every pipeline commit" in protocol
    assert "both its former task path and final archive path" in protocol
    assert 'block_reason="COMMIT_FAILED:' in governance
    assert "filesystem block prevents orchestrator" in governance
    assert 'block_reason=""' in governance
    assert re.search(r"archived\s+tasks are already off-board", protocol, re.IGNORECASE)


def test_pipeline_agents_bound_repair_and_prove_returned_work() -> None:
    """Runtime context forces early routing, bounded repair, and explicit finding closure."""
    protocol = (_SHARE_ROOT / "skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    repair = (_SHARE_ROOT / "skills/w-task-repair/SKILL.md").read_text(encoding="utf-8")
    builder = (_AGENTS_ROOT / "builder.agent.md").read_text(encoding="utf-8")
    builder_challenger = (_AGENTS_ROOT / "builder-challenger.agent.md").read_text(encoding="utf-8")
    verifier = (_AGENTS_ROOT / "verifier.agent.md").read_text(encoding="utf-8")
    verifier_challenger = (_AGENTS_ROOT / "verifier-challenger.agent.md").read_text(encoding="utf-8")

    assert "### Early Routing And Bounded Repair" in protocol
    assert "one grounded repair and rerun for the same failure" in protocol
    assert "This is not a one-edit\nlimit" in protocol
    assert "map every AC to the command or observation that proves it" in protocol
    assert "| # | Failure Key | Target Agent |" in protocol

    assert "Close returned work first" in builder
    assert "every AC and current failure key to direct evidence" in builder
    assert "every current follow-up failure key" in builder_challenger
    assert "missing caller\n  context is itself a concrete DONE defect" in builder_challenger

    assert "Patch once within a concrete local budget" in verifier
    assert "same failure key" in verifier
    assert "current follow-up failure key lacks explicit resolution evidence" in verifier_challenger

    assert "Treat each failure key in the latest follow-up as the repair identity" in repair
    assert "each current failure key and the authority" in repair


def test_retired_authority_names_are_absent_from_shared_ecosystem() -> None:
    """Shared consumers use one current name for each authority."""
    retired = {"h-project-orientation", "r-project-standards", "r-architecture-standards"}
    offenders: list[str] = []
    for path in _SHARE_ROOT.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        if any(name in content for name in retired):
            offenders.append(str(path.relative_to(_REPO_ROOT)))

    assert not offenders, f"Retired authority references remain: {offenders}"


def test_pipeline_requests_have_one_lifecycle_authority() -> None:
    """Request blocking uses create-request then release, with no shadow instruction."""
    protocol = (_SHARE_ROOT / "skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    requests = (_SHARE_ROOT / "skills/h-decision-requests/SKILL.md").read_text(encoding="utf-8")

    assert not (_SHARE_ROOT / "instructions/pipeline-agents.instructions.md").exists()
    assert "`create_request` atomically creates the pending record and blocks the task" in protocol
    assert 'end_work(outcome="release")' in protocol
    assert 'Do not call `end_work(outcome="block")`' in requests
    assert "It does not\nreturn a block reason" in requests


def test_task_agent_request_routes_are_executable() -> None:
    """Request owners have create/read tools; collector remains a read-only consumer."""
    builder = (_AGENTS_ROOT / "builder.agent.md").read_text(encoding="utf-8")
    verifier = (_AGENTS_ROOT / "verifier.agent.md").read_text(encoding="utf-8")
    collector = (_AGENTS_ROOT / "collector.agent.md").read_text(encoding="utf-8")
    shaper = (_AGENTS_ROOT / "shaper.agent.md").read_text(encoding="utf-8")

    for agent in (builder, verifier, shaper):
        assert "ob-kanban/create_request" in agent
        assert "ob-kanban/list_requests" in agent
        assert "ob-kanban/show_request" in agent
    for agent in (builder, verifier):
        assert "| Block | `BLOCK" in agent

    assert "ob-kanban/create_request" not in collector
    assert "ob-kanban/list_requests" in collector
    assert "ob-kanban/show_request" in collector

    for agent_name in ("builder", "collector", "shaper", "verifier"):
        assert "r-pipeline-protocol" in _required_skills(_AGENTS_ROOT / f"{agent_name}.agent.md")

    protocol = (_SHARE_ROOT / "skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    requests = (_SHARE_ROOT / "skills/h-decision-requests/SKILL.md").read_text(encoding="utf-8")
    assert "Load `h-decision-requests` before creating or consuming one" in protocol
    assert "Call `list_requests" in requests
    assert "Call `show_request" in requests


def test_pipeline_signal_producers_match_orchestration_consumers() -> None:
    """Every dispatched lifecycle signal is declared by agents and recognized by orchestration."""
    protocol = (_SHARE_ROOT / "skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    orchestration = (_SHARE_ROOT / "skills/w-orchestration/SKILL.md").read_text(encoding="utf-8")

    assert "No generic `FAIL` Channel A signal exists" in protocol
    assert "`FAIL`" not in orchestration
    assert "`agent` capability's\n`runSubagent(agentName=agent, prompt=str(task_id)" in orchestration
    assert 'end_work(id={task_id}, outcome="release"' in orchestration
    assert 'end_work(id={task_id}, outcome="block"' in orchestration
    assert "If that returns `ERR_NOT_CLAIMED`, call\n   `edit_task" in orchestration
    for signal in ("TOOL_UNAVAILABLE", "COMMIT_FAILED"):
        assert signal in orchestration
        for agent_name in ("builder", "verifier", "collector"):
            agent = (_AGENTS_ROOT / f"{agent_name}.agent.md").read_text(encoding="utf-8")
            assert signal in agent


def test_pipeline_uses_current_stage_evidence_and_breaks_repeat_cycles() -> None:
    """Leaf collection and verification use bounded current lifecycle evidence."""
    protocol = (_SHARE_ROOT / "skills/r-pipeline-protocol/SKILL.md").read_text(encoding="utf-8")
    collector = (_AGENTS_ROOT / "collector.agent.md").read_text(encoding="utf-8")
    verifier = (_AGENTS_ROOT / "verifier.agent.md").read_text(encoding="utf-8")

    assert "### Current Lifecycle Evidence" in protocol
    assert "latest occurrence for the current stage" in protocol
    assert "do not fund a third build/verify cycle" in protocol
    assert "Use the latest Verify Notes occurrence" in collector
    assert "without re-reviewing code" in collector
    assert "Use `Explore` only for aggregate" in collector
    assert "Break repeated repair cycles" in verifier
    assert "never authorize a third build/verify" in verifier


def test_shaping_rejects_ownerless_execution() -> None:
    """Planned operations must fit agent authority or have an explicit user-action owner."""
    decomposition = (_SHARE_ROOT / "skills/w-task-decomposition/SKILL.md").read_text(encoding="utf-8")
    challenger = (_AGENTS_ROOT / "shaper-challenger.agent.md").read_text(encoding="utf-8")

    assert "Reject ownerless execution" in decomposition
    assert "`type:user-action` with a planned Action Request" in decomposition
    assert "required executor lacks\n  authority" in challenger
