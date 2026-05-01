---
id: 1252
title: 'P3-01: RED — KanbanBoard filter integration tests'
status: research
priority: needed
created: 2026-05-01T04:34:55.076834+00:00
updated: 2026-05-01T04:37:37.067876+00:00
tags:
- phase-3
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on:
- 1251
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Vitest + Testing Library integration tests for KanbanBoard filter wiring:
  - Board renders filter toggle button
  - Toggle button opens/closes FilterPanel
  - Filter state changes cause filtered tasks to appear in correct columns
  - Derived availableTags computed from full (unfiltered) task set
  - Result count displays "N / M tasks" when filter is active
  - Filter change dismisses open context menu
  - Filter change cancels active drag state (clears dragSourceStatus)
  - Empty filter state shows all tasks
- All tests fail (RED) — KanbanBoard not yet wired to FilterPanel

## In Scope
- Integration test file for KanbanBoard + FilterPanel
- Tests for state management, derived data, interaction rules

## Out of Scope
- KanbanBoard implementation changes (next task)
- Layout/CSS assertions (visual regression, not unit-testable)
- Accessibility (Phase 4)

Brief: see parent #1247