---
id: 1232
title: Ideation — filter/search in kanban view
status: archived
priority: medium
created: 2026-04-30 16:31:18.673614+00:00
updated: 2026-05-01T17:00:34.991221+00:00
tags:
- cockpit
- needs-ideation
parent:
depends_on: []
blocked: true
block_reason: 'Needs UX ideation: filtering/search for large boards'
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Design filtering and search UX for the kanban board to handle 1200+ tasks.

## Context
All task data is already client-side (fetched in useBoard). No backend changes needed. The board currently shows all tasks in all columns with no way to filter.

## Needs Ideation
- Filter dimensions: priority, tag, text search, blocked status
- UI placement: toolbar above board? filter chips? search input?
- Should empty columns be hidden when filters are active?
- Persistence: remember filter state across page loads?