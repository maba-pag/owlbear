---
id: 2026
title: Reduce runtime instruction noise
status: verify
priority: low
created: 2026-07-24T20:03:13.310394+02:00
updated: 2026-07-24T20:09:08.917960+02:00
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
