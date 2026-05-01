---
id: 1253
title: 'P3-02: GREEN — KanbanBoard filter state and layout integration'
status: research
priority: needed
created: 2026-05-01T04:34:58.097220+00:00
updated: 2026-05-01T04:37:37.075462+00:00
tags:
- phase-3
- scope:cockpit-web
- tdd:green
parent: 1247
depends_on:
- 1252
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- KanbanBoard.tsx wires FilterPanel:
  - useState for FilterState and panelOpen
  - Derived filteredTasks via filterTasks() applied to full task set
  - Derived availableTags from full (unfiltered) task set
  - Filter toggle button with badge showing active filter count
  - Result count adjacent to toggle when filters active
  - FilterPanel rendered with all required props
- Layout refactored to vertical flex-column:
  - Toggle + count row at top
  - FilterPanel below toggle (when open)
  - Columns container with flex:1 + overflow-x/y:auto
- Interaction rules:
  - Filter change sets contextMenu to null
  - Filter change clears dragSourceStatus
- All #1252 integration tests pass (GREEN)

## In Scope
- KanbanBoard.tsx state additions and FilterPanel wiring
- Layout refactor (flex-column)
- Toggle button + result count

## Out of Scope
- Accessibility attributes (Phase 4)
- aria-live, focus management (Phase 4)

Brief: see parent #1247