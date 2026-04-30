---
id: 1224
title: Backend — relocate CockpitView from kanban to cockpit package
status: backlog
priority: needed
created: '2026-04-30 16:31:18.599723+00:00'
updated: '2026-04-30 16:33:23.419399+00:00'
tags:
- cockpit
- kanban-engine
- refactor
parent:
depends_on:
- 1222
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Move CockpitView facade from kanban engine into cockpit package where it belongs.

## Acceptance Criteria
- [ ] `CockpitView` class moved from `serve/kanban/src/owlbear_kanban/engine.py` to new file in `serve/cockpit/src/owlbear_cockpit/`
- [ ] All imports updated (cockpit deps.py, tests)
- [ ] `CockpitView` uses public engine properties (from task #1222) instead of private attrs
- [ ] Kanban engine no longer contains cockpit-specific code
- [ ] All cockpit tests pass
- [ ] All kanban tests pass

## Files
- `serve/kanban/src/owlbear_kanban/engine.py`
- `serve/cockpit/src/owlbear_cockpit/view.py` (new)
- `serve/cockpit/src/owlbear_cockpit/deps.py`
