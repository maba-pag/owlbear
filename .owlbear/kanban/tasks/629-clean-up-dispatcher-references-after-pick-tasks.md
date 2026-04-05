---
id: 629
title: Clean up dispatcher references after pick_tasks migration
status: backlog
priority: important
created: 2026-04-05T10:42:19.8702275+02:00
updated: 2026-04-05T16:47:15.8495814+02:00
tags:
    - scope:agents
    - phase-2
    - type:docs
parent: 619
depends_on:
    - 622
class: standard
---

## Acceptance Criteria

- `share/instructions/agent-common.instructions.md`: remove dispatcher row from Per-Agent Section Mapping table
- `share/skills/r-pipeline-protocol/SKILL.md`: update "the dispatcher will dispatch the planner" reference (line ~95) to reflect orchestrator handling DECOMP routing
- `share/skills/r-pipeline-protocol/SKILL.md`: update "blocked for triage by dispatcher" reference (line ~180) to reflect new owner
- `share/agents/README.md`: remove/update dispatcher from T1 Orchestrator tier row
- `share/skills/h-agent-structure/SKILL.md`: remove dispatcher from T1 Orchestrator tier row
- `share/agents/dispatcher.agent.md`: add deprecated header OR delete file

## Context

After #622 wires pick_tasks into the orchestrator, these cross-cutting references to the dispatcher agent become stale. See .owlbear/research/wire-pick-tasks-orchestrator.md.

[[2026-04-05]] Sun 14:17


## Research Note from #623
- GAP: `share/skills/w-task-decomposition/SKILL.md` L19 references "dispatcher-dispatched" — add to cleanup scope

[[2026-04-05]] Sun 16:46
## Research
- Research doc: .owlbear/research/cleanup-dispatcher-refs.md
- Sources: 9 studied, 7 high-relevance (all codebase-internal)
- Recommendation: Proceed as-is with 2 AC refinements (confidence: .92)
- Follow-up tasks created: none (refinements apply to #629 itself)
- Decision requests: none - T1 autonomous docs cleanup

### AC Refinements for Architect
1. Narrow AC item 6 (dispatcher.agent.md): change to verification-only - #623 handles deprecation
2. Add AC item 7: w-task-decomposition/SKILL.md L19 - replace dispatcher-dispatched with orchestrator-dispatched
3. Minor: README.md agent count is 14 but 16 files exist on disk - update while editing

## Challenge Results
- Challenge: SKIP - T1 docs cleanup within approved #619 migration plan
- Tier: T1 (autonomous), no new capability or architecture change
- Confidence: .92

[[2026-04-05]] Sun 16:47
Research complete. Doc at .owlbear/research/cleanup-dispatcher-refs.md. All 6 AC items verified against codebase; 1 overlap with #623 (narrow to verification), 1 gap found (w-task-decomposition L19). No follow-up tasks needed.
