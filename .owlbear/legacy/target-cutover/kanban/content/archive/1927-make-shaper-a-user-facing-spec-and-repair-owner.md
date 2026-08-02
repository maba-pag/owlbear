---
id: 1927
title: Make shaper a user-facing spec and repair owner
status: archived
priority: high
created: 2026-07-13T17:45:10.523540+02:00
updated: 2026-07-14T07:59:37.557072+02:00
tags:
  - scope:agent-config
  - feature
  - type:build
parent:
depends_on: []
ac:
  - The shaper exposes explicit spec-shaping and rejected-task-repair modes, 
    with staged user review and material decisions resolved before task graph 
    mutation.
  - Spec-derived task graphs are challenged and approved by the user before 
    Kanban creation, and accepted material planning changes update their owning 
    OpenSpec artifacts.
  - Rejected tasks with complete non-material follow-up are repaired 
    autonomously, while newly discovered material scope, architecture, behavior,
    or graph changes pause for interactive approval.
  - User-facing completion is a human summary, while existing task repairs still
    append required `## Shape Notes` history and focused agent ecosystem tests 
    pass.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Replace the shaper's pipeline-gate control flow with one user-facing agent that has explicit spec-shaping and rejected-task-repair workflows.

## Scope
In: shaper agent and prompt, new shaping workflow skills, task-decomposition/research/challenger/protocol alignment, wiring/docs needed for loading, and focused static contract tests.
Out: OpenSpec-supplied skills, orchestrator behavior, `pick_tasks` engine behavior, and dedicated raw-wish intake workflow.

User decisions from the shaping session are binding: OpenSpec output is an unreviewed draft; spec mode conducts a staged implementation review with architecture emphasis; accepted material changes update owning OpenSpec artifacts; challenger reviews a complete draft graph before user approval; Kanban writes follow approval; repair mode autonomously applies complete non-material instructions and escalates material expansion; `/shape` discovers pending shape work; final user output is human-readable while Channel B remains mandatory for task history.

Proof guidance: run agent validators and focused static tests covering review-before-write, pre-write challenge, repair classification, artifact revision, and human-summary behavior.

[[2026-07-13T23:02:59+02:00]]
## Builder Notes

### Change Envelope
- Reframed the existing shaper customization only; no Kanban runtime, orchestrator, `pick_tasks`, supplied OpenSpec skill, or sibling `../owlbear` file changed.
- Added explicit spec-shaping and rejected-task-repair workflows, with decomposition and research retained as subordinate capabilities.

### Implementation
- Added `w-spec-shaping`: staged product/scope, architecture/interface, and trade-off/completion review; accepted OpenSpec artifact reconciliation; complete provisional graph challenge; user approval before board writes; mechanical post-write audit; human summary.
- Added `w-task-repair`: mechanical reroute, local repair, prescribed split, material reshape, and insufficient-rejection classification; complete non-material instructions execute autonomously; material expansion stops before mutation and escalates interactively.
- Rewrote shaper agent and `/shape` around those modes, pending shape-task discovery, architecture-weighted dialogue, bounded research autonomy, and mandatory `## Shape Notes` history without visible machine verdicts.
- Changed task decomposition to `draft` and authorized `commit` phases; shaper-challenger now accepts complete provisional keys before user approval.
- Aligned ideation handoff to `/ideation` -> `/opsx:propose` -> `/shape`, protocol communication, research scope gate, inventory, and wiring.
- Added focused sequencing and repair regressions.

### Evidence
- Commit: `c5c49c6982ba4e3dad6310eb029df86c8816a4ad`.
- `uv run python .owlbear/scripts/validate_agents.py`: PASS, all 23 agents.
- `uv run python .owlbear/scripts/validate_skills.py`: PASS.
- Relevant regression scope: 81 passed.
- New shaper interaction module: 8 passed.
- Ruff check and format check for changed Python tests: PASS.
- Scoped `git diff --check`: PASS.
- VS Code diagnostics on changed files: none.
- `git -C ../owlbear status --short`: clean; sibling main-branch workspace untouched.
- builder-challenger: `decision: pass`; fresh 63-test subset, Ruff, and diff checks passed with no DONE blocker.

### Scope Notes
- Existing unrelated browser, board, memory, and generated-index changes were not staged or committed.
- Dedicated raw-wish shaping and `pick_tasks` exclusion remain intentionally outside this task.

[[2026-07-14T04:46:07+02:00]]
## Verify Notes

### Evidence reviewed
- Task intent and all four AC lines; Builder Notes and commit `c5c49c6982ba4e3dad6310eb029df86c8816a4ad`.
- Named authorities: `share/agents/shaper.agent.md`, `share/prompts/shape.prompt.md`, `share/skills/w-spec-shaping/SKILL.md`, `share/skills/w-task-repair/SKILL.md`, `share/skills/w-task-decomposition/SKILL.md`, and `share/agents/shaper-challenger.agent.md`.
- Change Module Map: changed agent/prompt/workflows, decomposition/challenger/protocol alignment, wiring, and focused static tests match the shaped scope. No deviation into orchestrator, Kanban engine, `pick_tasks`, or OpenSpec-supplied skills.

### Normal-path proof and checks
- `uv run pytest -q tests/test_shaper_interaction_contract.py tests/test_ideation_overhaul_static.py` -> `68 passed in 0.36s`.
- `uv run python .owlbear/scripts/validate_agents.py && uv run python .owlbear/scripts/validate_skills.py` -> agent validator passed all 23; combined command exited 0.
- `git diff --check c5c49c6^ c5c49c6` -> exit 0.
- The workflow preserves the intended pre-write sequence: staged review -> owning OpenSpec-artifact reconciliation -> complete provisional-graph challenge -> user approval -> board commit/audit. Repair classification permits autonomous mechanical/local/prescribed repairs and pauses material changes for interactive review.

### Finding
`w-spec-shaping` Step 7 requires `## Shape Notes` only on an aggregate task or existing parent. `w-task-decomposition` permits a standalone build task with neither. Therefore a valid single-task OpenSpec graph has no required durable task-history target, violating AC 4's requirement that existing task repairs retain mandatory `## Shape Notes` history and leaving the spec-shaping workflow's corresponding history contract incomplete.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Make the no-parent/no-aggregate spec-shaping path attach `## Shape Notes` to a concrete created task, preserving the approved graph and post-write audit; add a focused static assertion for this path, then rerun the focused shaper contracts and validators. | `share/skills/w-spec-shaping/SKILL.md`, `share/skills/w-task-decomposition/SKILL.md`, `tests/test_shaper_interaction_contract.py` | verifier-challenger failure: standalone graph can commit with no Shape Notes target |

### Verifier-challenger
- `decision: fail` — concrete standalone-graph history gap; no other AC or scope blocker reported.

### Final route
REJECT -> build. No verifier patch applied: the local workflow correction requires a durable regression assertion, which is builder-owned work.

[[2026-07-14T04:53:02+02:00]]
## Builder Notes

### Change Envelope
- Repair only the standalone spec-graph history gap identified by verification: a graph with no aggregate task or existing parent must still have a concrete `## Shape Notes` target.
- Expected owners: `w-spec-shaping`, `w-task-decomposition`, and the focused shaper interaction contract.

### Files Changed
- `share/skills/w-spec-shaping/SKILL.md`: direct standalone graphs to record Shape Notes in the created task representing the approved outcome.
- `share/skills/w-task-decomposition/SKILL.md`: return that created task as the task-history target to the calling workflow.
- `tests/test_shaper_interaction_contract.py`: added a static regression assertion for both sides of the standalone history handoff.

### Change Module Map
- No deviation. The repair remains inside the workflow owners and their existing focused static contract.

### Proof Selected
- Durable regression test added because this is an easy-to-miss workflow path whose failure removes required Kanban history; the existing contract suite did not cover it. The test is low-maintenance static protection of the cross-workflow requirement.

### Commands Run
- `uv run pytest -q tests/test_shaper_interaction_contract.py` — 14 passed.
- `uv run python .owlbear/scripts/validate_agents.py` — PASS, all 23 agent files conform.
- `uv run python .owlbear/scripts/validate_skills.py` — all checks passed.
- `uv run ruff check tests/test_shaper_interaction_contract.py` — passed.

### Builder-Challenger
- `decision: pass`. Confirmed concrete standalone Shape Notes target, coherent decomposition handoff, scoped regression coverage, and no change-envelope drift.

### Follow-up Risks
- This is a static workflow contract; runtime adherence still depends on the shaper following the documented commit flow.

[[2026-07-14T04:59:36+02:00]]
## Verify Notes

### Evidence Reviewed
- Acceptance criteria: explicit spec and repair modes; staged review plus material-decision gate; artifact reconciliation, challenger review, and user approval before Kanban writes; autonomous complete non-material repair with material escalation; human summary with required Shape Notes history.
- Named authorities checked: `share/agents/shaper.agent.md`, `share/prompts/shape.prompt.md`, `share/skills/w-spec-shaping/SKILL.md`, `share/skills/w-task-repair/SKILL.md`, `share/skills/w-task-decomposition/SKILL.md`, `share/skills/r-pipeline-protocol/SKILL.md`, and `share/instructions/pipeline-agents.instructions.md`.
- Change Module Map: the reviewed agent, prompt, workflows, decomposition/protocol alignment, wiring, and static-contract surfaces match the shaped scope. No Kanban runtime, orchestrator, or `pick_tasks` behavior was included.

### Boundary Verification
- Normal path exercised by static contract: `w-spec-shaping` orders artifact reconciliation, complete provisional-graph challenge, explicit user approval, then graph commit; draft phase prohibits Kanban mutation.
- The shaper agent and prompt require the selected workflow, stage user review, reconcile accepted OpenSpec decisions into their owning artifacts, and prohibit substantive board writes before approval.
- `w-task-repair` distinguishes mechanical/local/prescribed repairs from material reshape, permits autonomous complete non-material instructions, and stops before task or OpenSpec mutation for material expansion.
- User-facing summary and durable `## Shape Notes` history are both retained.

### Checks Run
- `uv run pytest tests/test_shaper_interaction_contract.py tests/test_skill_authority_wiring.py -q` - 18 passed in 0.29s.
- `uv run python .owlbear/scripts/validate_agents.py` - PASS, all 23 agent files conform to conventions.
- The initial validator lookup at `share/scripts/validate_agents.py` was stale; the current validator is `.owlbear/scripts/validate_agents.py`.
- `validate_skills.py` was invoked but the chained repository diff check reported pre-existing trailing whitespace in unrelated task records, including serialized task text; no workflow-structure defect was reported.

### Findings And Patches
- No defects found. No patch applied.

### Verifier Challenger
- `verifier-challenger`: decision `pass`; it confirmed AC coverage, sufficient focused proof, module-map alignment, and no concrete scope drift or unresolved criterion.

### Final Route
PASS: all acceptance criteria are satisfied; task advances to `collect`.

[[2026-07-14T07:59:37+02:00]]
## Collect Notes

### Classification
- `leaf`: no child tasks, no aggregate/EPIC title or tags, no aggregate intent section, and no parent dependency gate.

### Closure Evidence
- Verifier history contains a superseding PASS after the earlier rejection: the standalone spec-graph `## Shape Notes` target was repaired and the prior Required Follow-up was explicitly covered by later Builder and Verify Notes.
- Final verifier evidence: focused shaper interaction and skill-authority contracts passed (18 tests), agent validation passed for all 23 agent files, and verifier-challenger returned `decision: pass` with no unresolved AC or scope drift.
- Invariant coverage recorded upstream spans staged review before mutation, OpenSpec artifact reconciliation, complete graph challenge and user approval, repair classification, human-facing summary, and durable Shape Notes history.
- `list_tasks(parent=1927)` returned no children; `depends_on` is empty and `dep_status` is null.
- No pending Decision or Action Requests exist; task is unblocked and has no residual decision state.

### Rationale
ARCHIVED: verified leaf closure is complete. The later PASS supersedes the earlier rejected verification record, and no unresolved follow-up, dependency, child work, or decision remains.
