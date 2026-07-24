---
id: 2026
title: Reduce runtime instruction noise
status: collect
priority: low
created: 2026-07-24T20:03:13.310394+02:00
updated: 2026-07-24T20:29:24.216311+02:00
tags:
  - cleanup
  - agent
  - scope:copilot
  - type:docs
  - rigor:standard
parent:
depends_on: []
ac:
  - Active orchestration, shaping, research, repair, and pipeline instructions 
    contain current actionable policy without duplicated migration or pitfall 
    narration.
  - Orchestration recovery names executable dispatch, release, block, and 
    unclaimed-fallback operations while matching the live pick_tasks schema.
  - Agent and skill validators plus focused shaping and authority-wiring tests 
    pass.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Scope

Simplify active agent runtime instructions by removing migration narration, duplicated checklists and pitfalls, and unsupported interaction claims while preserving current routing, mutation, safety, authority, and evidence behavior.

## Out of Scope

- Native delivery runtime implementation
- New orchestration filtering support
- Changes to the derived WIRING map when no loading or delegation edge changes

Proof guidance: run agent/skill validators, focused shaping and wiring contracts, Ruff for changed Python tests, and diff whitespace checks.

[[2026-07-24T20:09:08+02:00]]
## Builder Notes

- Reduced active orchestration, shaping, research, repair, and pipeline context by removing migration narration, duplicated checklists/pitfalls, duplicated memory pre-flight, and unsupported scope-filter interaction claims.
- Preserved executable orchestration recovery with the `agent` capability's named-field `runSubagent` operation, `end_work` release/block calls, and `edit_task` fallback for `ERR_NOT_CLAIMED`.
- Matched `/orchestrate` to the live `pick_tasks(wave_size, max_waves)` schema: all eligible work, no unsupported filter input.
- Added Runtime Relevance guidance and focused wiring assertions for dispatch/recovery mechanics.

Evidence:
- `uv run python .owlbear/scripts/validate_agents.py` -> PASS (12 files)
- `uv run python .owlbear/scripts/validate_skills.py` -> PASS
- focused shaping/authority suite -> 52 passed
- post-correction `tests/test_skill_authority_wiring.py` -> 15 passed
- Ruff check and format check -> PASS
- `git diff --check` -> PASS
- builder-challenger -> `decision: pass`

Files: share/agents/orchestrator.agent.md; share/prompts/orchestrate.prompt.md; share/skills/h-agent-structure/SKILL.md; share/skills/r-pipeline-protocol/SKILL.md; share/skills/w-orchestration/SKILL.md; share/skills/w-research/SKILL.md; share/skills/w-task-decomposition/SKILL.md; share/skills/w-task-repair/SKILL.md; tests/test_skill_authority_wiring.py.

[[2026-07-24T20:29:24+02:00]]
## Verify Notes

- Evidence reviewed: builder notes, implementation commit `a9a848f`, and the active orchestration, shaping, research, repair, and pipeline authorities.
- Named authorities checked: `share/skills/h-mcp-kanban/SKILL.md` confirms `pick_tasks(wave_size, max_waves)`; `share/skills/w-orchestration/SKILL.md` retains named `runSubagent`, `end_work` release/block, and `ERR_NOT_CLAIMED` to `edit_task` recovery operations.
- Change Module Map: none supplied. The implementation stays within the task's named agent, prompt, skill, and wiring-test surfaces; no architecture deviation found.
- Normal-path boundary: the focused wiring test checks orchestration signal consumption and executable recovery declarations without replacing the command/workflow under test.
- Checks run:
  - `uv run pytest tests/test_skill_authority_wiring.py` - 15 passed.
  - `uv run pytest tests/test_shaper_interaction_contract.py tests/test_idea_refinement_customization.py tests/test_openspec_setup.py` - 29 passed.
  - `uv run python .owlbear/scripts/validate_agents.py` - PASS (12 files).
  - `uv run python .owlbear/scripts/validate_skills.py` - PASS.
  - `uv run ruff check tests/test_skill_authority_wiring.py` and `uv run ruff format --check tests/test_skill_authority_wiring.py` - PASS.
  - Task-record and task-owned implementation `git diff --check` checks - PASS after repair.
- Patch applied: removed four trailing spaces from this task record's serialized acceptance criteria; no behavioral content changed. Task record has no editor errors.
- AC evidence:
  - AC1: direct authority review plus agent and skill validators confirms current actionable policy and valid structure.
  - AC2: direct workflow/schema comparison and the 15-test wiring suite confirms the live `pick_tasks` signature and executable recovery operations.
  - AC3: the focused shaping suite, wiring suite, validators, and Ruff checks all pass.
- Prior same-failure-key rejection check: none. The verifier-challenger first identified missing named shaping-proof evidence, which was closed by the explicit 29-test shaping command; it then identified record whitespace, which was locally repaired and rechecked.
- Verifier-challenger: final `decision: pass`; no unresolved follow-up.
- Final route: PASS to collect.
