---
id: 1927
title: Make shaper a user-facing spec and repair owner
status: verify
priority: high
created: 2026-07-13T17:45:10.523540+02:00
updated: 2026-07-13T23:02:59.846746+02:00
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
archival_reason:
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
