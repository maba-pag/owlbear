---
id: 1821
title: Triage kanban board split root tests
status: research
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T09:23:21+02:00
tags:
  - scope:cockpit-web
  - scope:kanban-engine
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The two `tests/test_kanban_board_split.py` failures are checked against the current frontend file layout.
  - Static source assertions are updated only if they still protect current architecture.
  - Any frontend-adjacent change has the appropriate Cockpit verification path.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The #1814 root glob has two failures in `tests/test_kanban_board_split.py`, covering `Card.tsx` priority colors and `Column.tsx` memo wrapper assertions.

## Boundary
Do not change Cockpit frontend structure from this root-glob triage task without explicit approval.