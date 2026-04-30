---
id: 1208
title: Add full=True parameter to list_tasks to avoid body re-reads
status: backlog
priority: needed
created: '2026-04-30 15:29:06.239755+00:00'
updated: '2026-04-30 15:32:04.140633+00:00'
tags:
- audit-kanban
- performance
parent:
depends_on:
- 1207
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Avoid body re-reads for callers that need full task objects.

## Files
- engine.py (list_tasks method)

## Change
Add optional `full: bool = False` parameter to list_tasks(). When True, return full Task objects (with body) instead of body-stripped summaries. Callers needing body (pick_tasks, dispatch) use full=True.

## AC
- [ ] list_tasks accepts full parameter
- [ ] full=False returns stripped summaries (default, no regression)
- [ ] full=True returns complete Task objects with body
- [ ] pick_tasks uses full=True
- [ ] Tests cover both modes

## Finding: 5.3
