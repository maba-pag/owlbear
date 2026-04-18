---
id: 1007
title: 'Ideator M6 + w-ideation: use structured planner dispatch prefix'
status: research
priority: important
created: 2026-04-18T21:54:42.565983+00:00
updated: 2026-04-18T21:54:42.565983+00:00
tags:
- type:improvement
- scope:agents
parent: 998
depends_on:
- 1005
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Problem
Ideator M6 invokes planner with `brief.md` reference but no structured task ID or mode prefix. This caused the #973 failure where planner defaulted to output-only mode instead of auto-creating tasks.

## Changes Required
1. Update ideator.agent.md M6 section: planner invocation must use "Plan and create: #{parent_id} — {brief summary}" prefix.
2. Update w-ideation skill Step 6 (M6: Handoff): document the structured prefix convention for planner dispatch.
3. Clarify that the parent kanban task ID created at M6 step 1 must be passed to planner at M6 step 2.

## Acceptance Criteria
- ideator.agent.md M6 handoff section uses "Plan and create: #{id}" prefix convention.
- w-ideation Step 6 documents the prefix with the created parent task ID.
- Ideator M6 planner dispatch will trigger auto-create mode (not user-approval mode).

## Affected Files
- `share/agents/ideator.agent.md`
- `share/skills/w-ideation/SKILL.md`

## Context
See `.owlbear/research/998-planner-askquestions-approval.md`. This is the root cause fix for the #973 failure. Depends on #1005 for the mode convention.
