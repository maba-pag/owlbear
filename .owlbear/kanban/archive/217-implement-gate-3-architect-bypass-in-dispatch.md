---
id: 217
title: Implement Gate 3 architect-bypass in dispatch-planning SKILL.md
status: archived
priority: medium
created: 2026-03-30 14:51:52.730328+02:00
updated: 2026-03-30 15:33:10.118148+02:00
started: 2026-03-30 15:33:10.118148+02:00
completed: 2026-03-30 15:33:10.118148+02:00
tags:
- scope:agents
- quality
- type:config
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Modify dispatch-planning SKILL.md to exempt architect-reviewed tasks from Gate 3 atomicity heuristic.

## Acceptance Criteria
- [ ] Board Scan Recipe 1 PS adds ARCH:REVIEWED marker when body contains ## Architecture Review
- [ ] Gate 3 text updated: tasks with ARCH:REVIEWED marker skip the and heuristic
- [ ] What the PowerShell layer adds section documents the new marker
- [ ] What remains for LLM reasoning section updated for Gate 3 exemption
- [ ] No other gates affected
- [ ] The and heuristic remains active for tasks WITHOUT ## Architecture Review

## Context
See docs/research/gate-3-atomicity-architect-bypass.md for full analysis.
Owning research: #214
