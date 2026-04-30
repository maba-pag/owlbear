---
id: 1207
title: Direct dep lookup in AgentView.show_task
status: backlog
priority: needed
created: '2026-04-30 15:29:06.229446+00:00'
updated: '2026-04-30 15:32:04.134372+00:00'
tags:
- audit-kanban
- performance
parent:
depends_on:
- 1205
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Replace O(N) list_tasks calls with O(D) direct lookups for dependencies.

## Files
- engine.py (AgentView.show_task)

## Change
Replace two `list_tasks()` calls with direct `show_task()` lookups for each dependency ID. O(D) where D ≈ 2-5, instead of O(N) where N ≈ 250.

## AC
- [ ] show_task uses direct lookups for dependency resolution
- [ ] No full list_tasks() call for dependency enrichment
- [ ] Correct behavior when dependencies don't exist
- [ ] Tests pass

## Finding: 5.2
