---
id: 1405
title: 'A2: Planner skill update — AC drafting via h-ac-quality, consolidation-test
  creation, routing'
status: research
priority: needed
created: 2026-05-07T23:16:25.183704+00:00
updated: 2026-05-07T23:46:47.792263+00:00
tags:
- pipeline
- ws-ac-quality
- scope:agents
parent: 1403
depends_on:
- 1404
blocked: false
block_reason:
claimed_at:
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