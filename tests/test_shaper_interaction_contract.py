"""Static contracts for user-facing spec shaping and rejected-task repair."""

from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _flat(relative_path: str) -> str:
    return " ".join(_read(relative_path).split())


def test_shaper_has_explicit_spec_and_repair_modes() -> None:
    agent = _read("share/agents/shaper.agent.md")
    prompt = _read("share/prompts/shape.prompt.md")
    flat_agent = " ".join(agent.split())
    flat_prompt = " ".join(prompt.split())

    for workflow in ("w-spec-shaping", "w-task-repair"):
        assert workflow in agent
        assert workflow in prompt

    assert "use a pipeline verdict as the user interface" in flat_agent
    assert "append `## Shape Notes`" in prompt
    assert "Do not involve, notify, or modify the orchestrator" in flat_prompt


def test_shaper_loads_only_the_selected_mode_and_triggered_companions() -> None:
    agent = _read("share/agents/shaper.agent.md")
    required = agent.split("<required_reading>", 1)[1].split("</required_reading>", 1)[0]
    flat_agent = " ".join(agent.split())

    assert "`r-pipeline-protocol`" in required
    assert "`w-spec-shaping`" not in required
    assert "`w-task-repair`" not in required
    assert "`h-codebase-orientation`" not in required
    assert "`h-module-design`" not in required
    assert "After classifying the input, immediately load `w-spec-shaping`" in flat_agent


def test_orientation_is_read_only_and_memory_uses_universal_gate() -> None:
    orientation = _read("share/skills/h-codebase-orientation/SKILL.md")
    decomposition = _read("share/skills/w-task-decomposition/SKILL.md")
    flat_orientation = " ".join(orientation.split())
    flat_decomposition = " ".join(decomposition.split())

    assert "Do not regenerate indexes during ordinary orientation" in flat_orientation
    assert "Regenerate all indexes before orienting" not in orientation
    assert "specific, non-obvious, reusable fact" in flat_decomposition
    assert "write 3-5 bullets" not in decomposition
    assert "confidence=0.8" not in decomposition


def test_spec_shaping_challenges_and_gets_approval_before_writes() -> None:
    workflow = _read("share/skills/w-spec-shaping/SKILL.md")
    flat_workflow = _flat("share/skills/w-spec-shaping/SKILL.md")

    reconcile = workflow.index("## Step 4 - Reconcile The OpenSpec Artifacts")
    challenge = workflow.index("## Step 5 - Draft And Challenge The Graph")
    approval = workflow.index("## Step 6 - Obtain Graph Approval")
    commit = workflow.index("## Step 7 - Commit And Audit The Graph")

    assert reconcile < challenge < approval < commit
    assert "without creating or editing Kanban tasks" in flat_workflow
    assert "Call `shaper-challenger` on this complete pre-write graph" in workflow
    assert "After approval" in workflow
    assert "This post-write audit is mechanical" in workflow


def test_spec_review_is_staged_and_architecture_weighted() -> None:
    workflow = _read("share/skills/w-spec-shaping/SKILL.md")

    for stage in (
        "### Stage A - Product And Scope",
        "### Stage B - Architecture And Interfaces",
        "### Stage C - Trade-offs And Completion",
    ):
        assert stage in workflow

    assert "Explain at high, adaptive depth" in workflow
    assert "exposed command, tool, endpoint, and schema details" in workflow
    assert "Take an opinionated evidence-based position" in workflow


def test_accepted_changes_update_owning_openspec_artifacts() -> None:
    workflow = _read("share/skills/w-spec-shaping/SKILL.md")

    for owner in ("Proposal", "Spec", "Design"):
        assert f"| {owner}" in workflow or f"| Product outcome" in workflow
    assert "Do not bury an accepted departure only in Shape Notes" in workflow
    assert "Validate the reconciled change with the OpenSpec CLI" in workflow


def test_task_repair_distinguishes_autonomous_and_material_work() -> None:
    workflow = _read("share/skills/w-task-repair/SKILL.md")
    flat_workflow = _flat("share/skills/w-task-repair/SKILL.md")

    for repair_class in (
        "Mechanical reroute",
        "Local task repair",
        "Prescribed split",
        "Material reshape",
        "Insufficient rejection",
    ):
        assert repair_class in workflow

    assert "Do not ask the user to confirm a complete non-material repair" in workflow
    assert "stop before task or OpenSpec mutation" in flat_workflow
    assert "Strong source evidence is grounds for a recommendation" in workflow
    assert "Channel B is mandatory for repaired existing tasks" in workflow


def test_decomposition_drafts_without_mutation_then_commits_authorized_graph() -> None:
    workflow = _read("share/skills/w-task-decomposition/SKILL.md")

    draft = workflow.index("### Step 5b — Return The Provisional Graph")
    commit = workflow.index("## Step 6 — Commit An Approved Graph")
    audit = workflow.index("## Step 8 — Return The Board Audit")

    assert draft < commit < audit
    assert "Do not create or edit Kanban tasks in draft phase" in workflow
    assert "the user-approved graph from `w-spec-shaping`" in workflow
    assert "Do not run a second substantive shaper-challenger review after creation" in workflow


def test_challenger_accepts_complete_provisional_graph() -> None:
    challenger = _read("share/agents/shaper-challenger.agent.md")

    assert "Review before board mutation" in challenger
    assert "Provisional keys are sufficient" in challenger
    assert "Do not require concrete task IDs" in challenger


def test_shaper_human_output_does_not_remove_channel_b_history() -> None:
    protocol = _read("share/skills/r-pipeline-protocol/SKILL.md")

    assert "Shaper is user-facing and is not dispatched by orchestrator" in protocol
    assert "does not expose a machine verdict as the user interface" in protocol
    assert "internal route recorded in task state" in protocol
    assert "`## Shape Notes`" in protocol


def test_standalone_spec_graph_has_a_shape_notes_target() -> None:
    shaping = _read("share/skills/w-spec-shaping/SKILL.md")
    decomposition = _read("share/skills/w-task-decomposition/SKILL.md")

    assert "For a standalone graph, record\nthem in the created task" in shaping
    assert "standalone graph, identify the created task" in decomposition


def test_shaper_can_own_one_explicit_connected_mutation_set() -> None:
    protocol = _read("share/skills/r-pipeline-protocol/SKILL.md")
    prompt = _read("share/prompts/shape.prompt.md")
    repair = _read("share/skills/w-task-repair/SKILL.md")
    flat_protocol = " ".join(protocol.split())
    flat_repair = " ".join(repair.split())

    assert "Builder, verifier, and collector handle one task per invocation" in protocol
    assert "Shaper handles one shaping subject per invocation" in protocol
    assert "claim every existing task in deterministic ID order" in flat_protocol
    assert "release the claims acquired in this invocation and stop without mutation" in flat_protocol
    assert "Do not add tasks to the mutation set after approval or after writes begin" in flat_protocol
    assert "Existing task number or explicit connected set" in prompt
    assert "mere proximity or shared topic is insufficient" in flat_repair
    assert "claim every existing task before the first write" in flat_repair


def test_research_returns_evidence_without_owning_shaper_routing() -> None:
    research = _read("share/skills/w-research/SKILL.md")
    flat_research = " ".join(research.split())

    assert "Use the smallest source set that can support or falsify the claim" in flat_research
    assert "Write `.owlbear/research/{slug}.md` only when" in research
    assert "Do not create or edit Kanban tasks, invoke `shaper-challenger`, request approval" in flat_research
    assert "Return Channel A signal" not in research
    assert "APPROVED -> build" not in research


def test_user_facing_agent_output_is_a_structural_exception() -> None:
    structure = _read("share/skills/h-agent-structure/SKILL.md")
    flat_structure = " ".join(structure.split())

    assert "A user-facing pipeline agent may define a human summary" in flat_structure
    assert "internal route is recorded in task state" in flat_structure
