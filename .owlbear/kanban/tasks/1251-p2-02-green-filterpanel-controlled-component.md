---
id: 1251
title: 'P2-02: GREEN — FilterPanel controlled component'
status: research
priority: needed
created: 2026-05-01T04:34:51.936867+00:00
updated: 2026-05-01T04:37:37.061927+00:00
tags:
- phase-2
- scope:cockpit-web
- tdd:green
parent: 1247
depends_on:
- 1250
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- FilterPanel.tsx component implemented with:
  - Text input with placeholder "Search by title…"
  - PDS Select for priority (single-select, "All priorities" empty option)
  - PDS MultiSelect for tags (type-to-filter, hidden when availableTags empty)
  - PDS Switch for blocked toggle ("Show only blocked tasks")
  - Reset button ("Clear all") visible when any filter is active
- Controlled component: receives filter + onFilterChange + priorities + availableTags + open as props
- All #1250 component tests pass (GREEN)

## In Scope
- FilterPanel.tsx component
- FilterPanelProps interface

## Out of Scope
- KanbanBoard integration (Phase 3)
- Accessibility attributes beyond basic labels (Phase 4)
- Layout/positioning within board (Phase 3)

Brief: see parent #1247