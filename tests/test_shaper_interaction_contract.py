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
    instruction = _read("share/instructions/pipeline-agents.instructions.md")

    assert "Shaper is user-facing and is not dispatched by orchestrator" in protocol
    assert "does not expose a machine verdict as the user interface" in protocol
    assert "internal route recorded in task state" in protocol
    assert "user-facing human summary; route recorded in task state" in instruction
    assert "## Shape Notes" in instruction
