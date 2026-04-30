---
id: 1216
title: Split engine.py — extract agent_view.py + cockpit_view.py + validators.py
status: backlog
priority: needed
created: '2026-04-30 15:29:15.267734+00:00'
updated: '2026-04-30 15:32:04.194197+00:00'
tags:
- audit-kanban
- architecture
parent:
depends_on:
- 1215
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Split 3,361-line engine.py into focused modules.

## Files
- engine.py → engine.py + agent_view.py + cockpit_view.py + validators.py

## Change
KanbanEngine stays in engine.py. AgentView → agent_view.py. CockpitView → cockpit_view.py. Shared validators → validators.py. Update all internal and external imports.

## AC
- [ ] engine.py contains only KanbanEngine
- [ ] agent_view.py contains AgentView class
- [ ] cockpit_view.py contains CockpitView class
- [ ] validators.py contains shared validation logic
- [ ] All imports resolve correctly
- [ ] All tests pass without modification (or with import-only updates)

## Finding: 2.1
