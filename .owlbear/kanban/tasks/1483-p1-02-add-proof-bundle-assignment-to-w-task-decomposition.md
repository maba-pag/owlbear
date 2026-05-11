---
id: 1483
title: 'P1-02: Add proof-bundle assignment to w-task-decomposition'
status: backlog
priority: needed
created: 2026-05-11T08:59:01.915026+00:00
updated: 2026-05-11T09:03:05.340792+00:00
tags:
- pipeline
- convention
- scope:skills
- agent
parent: 1481
depends_on:
- 1482
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

1. Selection guide table (signal → likely bundle) present in planner task-creation procedure
2. Planner writes `Proof bundle: {value}` in task body during Step 5/6
3. `existing` bundle requires `Existing proof scope:` line with glob or file list

## Scope

- In: `share/skills/w-task-decomposition/SKILL.md`
- Out: other skill files

Proof bundle: skip
Brief: see parent #1481