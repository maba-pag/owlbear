---
id: 1209
title: Add startup validation of hardcoded dispatch constants
status: backlog
priority: needed
created: '2026-04-30 15:29:06.250180+00:00'
updated: '2026-04-30 15:32:04.148443+00:00'
tags:
- audit-kanban
- fragility
parent:
depends_on:
- 1208
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Fail fast if dispatch.py hardcoded constants diverge from config.

## Files
- dispatch.py (PRIORITY_RANK, STATUS_RANK, terminal statuses)
- engine.py (KanbanEngine.__init__)

## Change
At engine init, validate that dispatch.py's PRIORITY_RANK/STATUS_RANK/terminal statuses match config values. Raise on divergence.

## AC
- [ ] Engine init checks dispatch constants against config
- [ ] Mismatch raises clear error at startup
- [ ] Tests cover the divergence detection

## Finding: 5.4
