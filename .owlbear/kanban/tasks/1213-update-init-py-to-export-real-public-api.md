---
id: 1213
title: Update __init__.py to export real public API
status: backlog
priority: needed
created: '2026-04-30 15:29:15.233442+00:00'
updated: '2026-04-30 15:32:04.176979+00:00'
tags:
- audit-kanban
- api
parent:
depends_on:
- 1212
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Update __init__.py to export the real public API surface.

## Files
- serve/kanban/src/owlbear_kanban/__init__.py

## Change
Add AgentView, CockpitView, ValidationError, NotFoundError, ConcurrencyError, CorruptionError to __all__.

## AC
- [ ] __all__ includes all public-facing classes and errors
- [ ] `from owlbear_kanban import AgentView` works
- [ ] `from owlbear_kanban import CockpitView` works
- [ ] All error classes importable from package root

## Finding: 3.4
