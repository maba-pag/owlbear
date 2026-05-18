---
id: 1661
title: 'P1-02: atomic_write docstring — generic framing'
status: backlog
priority: important
created: 2026-05-18T17:41:31.871473+02:00
updated: 2026-05-18T17:42:26.430647+02:00
tags:
  - phase-1
  - scope:kanban
  - housekeeping
parent: 1658
depends_on:
  - 1638
ac:
  - Module docstring and `atomic_write` function docstring describe a generic 
    crash-safe write utility without kanban-specific framing (no references to 
    'kanban task files' or 'Brief C')
proof_bundle: skip
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Brief: see parent #1658

File: `serve/kanban/src/owlbear_kanban/storage_io.py`

Current module docstring references "kanban task files" and "Brief C §3.1". Current function docstring references "Brief C §3.1". Both should be rewritten to describe a generic atomic write utility since it is now consumed by the cockpit ideas route as well.

## In Scope

- Module-level docstring update
- Function-level docstring update

## Out of Scope

- Functional changes to `atomic_write`
- Moving the function to a different module