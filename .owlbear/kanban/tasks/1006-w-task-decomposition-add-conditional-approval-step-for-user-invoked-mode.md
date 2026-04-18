---
id: 1006
title: 'w-task-decomposition: add conditional approval step for user-invoked mode'
status: research
priority: important
created: 2026-04-18T21:54:33.726798+00:00
updated: 2026-04-18T21:54:33.726798+00:00
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
w-task-decomposition skill has no approval step between plan validation and task creation. When planner runs in user-invoked mode, it needs to present the plan and ask for approval before executing create_task calls.

## Changes Required
1. Add a conditional Step 5b between Step 5a (validate) and Step 6 (create):
   - If user-invoked mode (no "and create" prefix): present the planned tasks, call askQuestions for approval, proceed to Step 6 only on approve.
   - If dispatch mode ("Plan and create" prefix): skip Step 5b, proceed directly to Step 6.
2. Document what happens if user rejects: planner stops and reports the rejection.

## Acceptance Criteria
- w-task-decomposition SKILL.md includes conditional approval step.
- Step references the explicit mode prefix convention from planner.agent.md.
- Approval uses askQuestions (not prose question).
- Rejection ends the workflow cleanly without creating tasks.

## Affected Files
- `share/skills/w-task-decomposition/SKILL.md`

## Context
See `.owlbear/research/998-planner-askquestions-approval.md`. Depends on #1005 for the mode convention.
