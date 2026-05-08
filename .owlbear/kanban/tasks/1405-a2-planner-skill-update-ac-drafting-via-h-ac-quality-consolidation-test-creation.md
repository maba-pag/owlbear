---
id: 1405
title: 'A2: Planner skill update — AC drafting via h-ac-quality, consolidation-test
  creation, routing'
status: backlog
priority: needed
created: 2026-05-07T23:16:25.183704+00:00
updated: 2026-05-08T01:01:05.089951+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
parent: 1403
depends_on:
- 1404
blocked: false
block_reason:
claimed_at: 2026-05-08T01:01:05.089951+00:00
archival_reason:
archival_refs: []
---

Brief: see parent #1403 (`.owlbear/briefs/draft-pipeline-review-rethink/brief.md`)

## Acceptance Criteria

P1: `w-task-decomposition` skill adds `h-ac-quality` to its required_reading for AC drafting
P2: Planner creates consolidation-test tasks when ≥2 implementation tasks exist under a common parent — title pattern "consolidation test: {feature name}", deps listing all sibling implementation task IDs
P2: Planner creates tasks at `backlog` status (not `todo`) — only architect moves backlog→todo
P2: `planner.agent.md` mode instructions updated to reference `h-ac-quality` skill in required reading or critical rules
P3: Verification by diff comparison of modified skill/agent files

## Scope

**In scope:** `w-task-decomposition` skill update, `planner.agent.md` mode instruction update, consolidation-test creation logic
**Out of scope:** h-ac-quality content (A1), architect/challenger validation (A3)


## Transition Note

After this task deploys, #1420 resets all `todo` tasks to `backlog` for architect re-gate under new AC rules.
[[2026-05-08]]
## Research

### Key Findings
- `h-ac-quality` skill confirmed complete (A1 dependency satisfied)
- Neither `w-task-decomposition` nor `planner.agent.md` currently reference h-ac-quality or consolidation-test logic
- Current status routing defaults are mostly correct (decomposition→research, shortcut→backlog) but lacks explicit `todo` prohibition
- Implementation is 4 targeted .md edits with clear insertion points identified

### Trade-off Matrix
N/A — T1 prescribed modification from approved brief. No alternative approaches to evaluate.

### Follow-up Tasks Created
- #1427: Implement planner skill updates — h-ac-quality wiring, consolidation-test logic, routing enforcement (at backlog)

### Research Doc
`.owlbear/research/planner-ac-quality-update.md`