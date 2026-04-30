---
id: 1211
title: Consolidate 8 duplicated helper functions
status: backlog
priority: needed
created: '2026-04-30 15:29:15.204775+00:00'
updated: '2026-04-30 15:32:04.162862+00:00'
tags:
- audit-kanban
- dry
parent:
depends_on:
- 1210
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Deduplicate 8 helper functions that exist in multiple modules.

## Files
- engine.py, storage.py, corruption.py

## Change
Deduplicate: generate_slug (keep in storage.py), make_task_filename (keep in storage.py), validate_path_containment (keep in storage.py), move_to_quarantine (keep in storage.py), _dep_effect_from_archival_reason (keep in KanbanEngine, AgentView delegates), _compute_dep_status (keep in KanbanEngine, AgentView delegates).

## AC
- [ ] Each helper exists in exactly one canonical location
- [ ] Other modules import from canonical location
- [ ] No duplicated function bodies remain
- [ ] Tests pass

## Finding: 1.3
