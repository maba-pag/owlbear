---
id: 1254
title: 'P4-01: RED — Filter accessibility tests'
status: research
priority: important
created: 2026-05-01T04:35:01.084199+00:00
updated: 2026-05-01T04:37:37.081693+00:00
tags:
- phase-4
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on:
- 1253
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test suite covering filter accessibility contract:
  - Toggle button has aria-expanded reflecting panelOpen state
  - Toggle button has aria-controls="filter-panel"
  - FilterPanel has id="filter-panel", role="region", aria-label="Task filters"
  - Result count region has aria-live="polite"
  - aria-live announces only on user-initiated filter changes (not polling refreshes)
  - aria-live debounced: announcement fires 300ms after last text input keystroke
  - Focus moves to first panel control on expand
  - Focus returns to toggle button on collapse
  - All filter controls have explicit accessible labels
- All tests fail (RED) — accessibility attributes not yet implemented

## In Scope
- Accessibility test cases for FilterPanel and KanbanBoard filter UI
- Focus management behavior tests
- aria-live timing/debounce tests

## Out of Scope
- Accessibility implementation (next task)
- Screen reader integration testing (manual QA)

Brief: see parent #1247