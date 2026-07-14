---
id: 1928
title: Align shaper companions and graph ownership
status: collect
priority: high
created: 2026-07-14T00:10:46.227791+02:00
updated: 2026-07-14T05:00:31.984017+02:00
tags:
  - scope:agent-config
  - type:build
  - fix
parent:
depends_on: []
ac:
  - A shaper invocation can safely reshape an explicit connected set of existing
    tasks while preserving claims and leaving the strict one-task rule unchanged
    for execution agents.
  - The shaper loads only common protocol eagerly, then loads exactly the 
    selected mode and triggered companions.
  - Research returns proportional evidence to its caller without independently 
    challenging graphs, creating follow-up tasks, routing board work, or 
    emitting a shaper machine verdict.
  - Codebase orientation does not regenerate committed indexes during ordinary 
    discovery, and task decomposition uses the universal memory qualification 
    gate without quotas or fixed confidence.
  - Wiring and focused static contracts encode the intended authorities, and 
    ecosystem validators pass.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Remove active contradictions that still make the user-facing shaper behave like an isolated pipeline worker or let subordinate companions preempt its decisions.

## Scope
In: role-scoped connected-task ownership, mode-dependent shaper loading, evidence-only research, read-only orientation guidance, universal memory qualification, wiring, and focused static contracts.
Out: Kanban runtime/API changes, atomic batch tooling, terminal sandboxing, generated-index implementation, and unrelated pipeline-agent behavior.

Observed value basis: an old-world one-task rule refused a real connected reshape; research still routes and emits machine verdicts independently; required reading eagerly loads mutually exclusive modes and architecture context; orientation mandates writes to committed indexes; decomposition conflicts with universal memory quality.

Proof guidance: run agent/skill validators and focused tests for shaper interaction, authority wiring, and ecosystem static contracts.

[[2026-07-14T00:22:45+02:00]]
## Builder Notes

### Value Boundary
- Implemented only directly observed contradictions or behavior with clear operational impact.
- Excluded Kanban runtime/API changes, atomic batch claims, terminal sandboxing, index-generator changes, and unrelated pipeline behavior because current tools and evidence did not justify them.

### Changes And Impact
- Connected reshape ownership: kept builder/verifier/collector at one task per invocation; allowed shaper one explicit connected subject only when every existing task is claimed in deterministic order before writes. This fixes the observed multi-task refusal without weakening execution-agent isolation.
- Research authority: reduced `w-research` from an autonomous route/task/challenge workflow to a proportional evidence-returning companion. This removes duplicate approval authority and 90 net lines while retaining bounded scope, source quality, durable artifacts, and attribution.
- Mode loading: kept only common pipeline protocol eager; selected mode and architecture/orientation companions now load when triggered. This removes irrelevant context from mechanical repair without changing either mode's substantive decisions.
- Orientation: ordinary discovery no longer regenerates committed indexes. The explicit command remains documented for requested index maintenance, preserving capability without surprise worktree writes.
- Memory: removed the local reflection quota and fixed confidence; decomposition now applies the universal specific, non-obvious, reusable qualification gate.
- Structural output: documented the existing human-summary exception for user-facing pipeline agents rather than changing the already-correct pipeline instruction.

### Evidence
- Commit: `0f6b746ce9f7d84a2987465d6e066e3eb3cf34fd`.
- Relevant static regression: 81 passed.
- Focused shaper/authority contracts: 16 passed.
- Ruff check and format check: PASS.
- Agent validator: PASS, all 23 agents.
- Skill validator: PASS.
- Editor diagnostics: none.
- `git diff --check`: PASS.
- builder-challenger: PASS; no concrete blocker or invented-complexity concern.
- `../owlbear` remained clean and untouched.

[[2026-07-14T05:00:31+02:00]]
## Verify Notes

### Evidence Reviewed
- Acceptance criteria and Builder Notes on task #1928, including builder commit `0f6b746ce9f7d84a2987465d6e066e3eb3cf34fd` (an ancestor of the verification revision).
- Direct source review: `share/agents/shaper.agent.md`, `share/skills/w-research/SKILL.md`, `share/skills/r-pipeline-protocol/SKILL.md`, and the focused static contracts.
- Named authorities checked against the task intent: `r-pipeline-protocol` preserves one-task execution-agent isolation while defining deterministic connected-set shaper ownership; shaper defers mode-specific workflows; research returns evidence only and owns no routing; orientation forbids ordinary index regeneration; decomposition uses the universal memory qualification wording.

### Change Module Map And Boundary
- Changed configuration and workflow modules remain inside the stated authority boundary: shaper agent/prompt, shared shaper companions, orientation, structure/instruction wiring, and focused static contracts.
- No module-map deviation or interface expansion found. Normal-path verification reads the actual user-facing shaper and research workflow sources; tests do not replace the workflow/authority boundary with mocks.

### Checks Run
- `uv run pytest -q tests/test_shaper_interaction_contract.py tests/test_skill_authority_wiring.py` -> `18 passed in 0.28s`.
- `uv run python .owlbear/scripts/validate_agents.py` -> `PASS — all 23 agent files conform to conventions`.
- Builder-recorded evidence: skill validator PASS, relevant static regression 81 passed, focused shaper/authority contracts 16 passed, Ruff/format PASS, and `git diff --check` PASS at the builder commit.
- Attempts to rerun the skill validator during verification were invalid terminal-capture results (delayed unrelated browser-test output), not a skill validation failure.

### Patch Applied
- Removed trailing whitespace from this task record's AC metadata only. Targeted trailing-whitespace regex check is clean.

### Challenger
- `verifier-challenger`: `decision: pass`; no concrete AC, evidence, or scope blocker.

### Final Route
- PASS -> collect.
