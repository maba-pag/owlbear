---
id: 1214
title: Deprecate dispatch.py — port gates to AgentView.pick_tasks
status: backlog
priority: needed
created: '2026-04-30 15:29:15.245023+00:00'
updated: '2026-04-30 15:32:04.182683+00:00'
tags:
- audit-kanban
- architecture
parent:
depends_on:
- 1213
- 1209
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Port dispatch gates into AgentView.pick_tasks; deprecate dispatch.py.

## Files
- dispatch.py
- engine.py (AgentView.pick_tasks)
- __init__.py (exports)

## Change
Add TDD gate and clarity gate logic to AgentView.pick_tasks(). Mark dispatch.py:pick_dispatchable() as deprecated. Update __init__.py exports.

## AC
- [ ] AgentView.pick_tasks includes TDD gate logic
- [ ] AgentView.pick_tasks includes clarity gate logic
- [ ] dispatch.py:pick_dispatchable marked deprecated
- [ ] Existing behavior preserved
- [ ] Tests cover new gate logic in AgentView

## Finding: 2.3
