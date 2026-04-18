---
id: 1008
title: 'Architect: update planner delegation to use structured prefix'
status: research
priority: important
created: 2026-04-18T21:54:49.289730+00:00
updated: 2026-04-18T21:54:49.289730+00:00
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
Architect delegates to planner when task body contains "Needs decomposition:" but the delegation prompt (`Plan: {description}`) lacks a structured task ID or mode prefix. This could cause planner to default to approval mode mid-pipeline.

## Changes Required
1. Update architect.agent.md: planner delegation prompt must use "Plan and create: #{task_id} — {description}" prefix.
2. Ensure the architect passes its claimed task ID to the planner dispatch prompt.

## Acceptance Criteria
- architect.agent.md planner delegation uses "Plan and create: #{id}" prefix.
- Planner auto-creates subtasks when dispatched by architect (no approval prompt).

## Affected Files
- `share/agents/architect.agent.md`

## Context
See `.owlbear/research/998-planner-askquestions-approval.md`. Depends on #1005 for the mode convention.
