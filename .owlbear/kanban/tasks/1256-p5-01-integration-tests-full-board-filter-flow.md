---
id: 1256
title: 'P5-01: Integration tests — full board filter flow'
status: research
priority: important
created: 2026-05-01T04:35:07.029411+00:00
updated: 2026-05-01T08:30:28.777206+00:00
tags:
- phase-5
- scope:cockpit-web
- test:integration
- type:test
parent: 1247
depends_on:
- 1255
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- End-to-end Vitest integration test suite verifying complete filter feature:
  - Filtered tasks appear in correct status columns
  - Empty columns after filtering show "No tasks" placeholder
  - Result count updates correctly ("0 / N tasks", "M / N tasks")
  - Toggle badge reflects active filter count ("Filter (2)")
  - Filter change while context menu open dismisses menu
  - Filter change while dragging cancels drag
  - Selected tag persisting after tag vanishes from task set (0-result state)
  - Reset clears all filters and restores full task view
  - All accessibility attributes present in integrated state
- Tests pass (GREEN) — verifies the complete feature integration

## In Scope
- Full board integration test file
- Multi-dimensional filter scenarios
- Edge case combinations

## Out of Scope
- Playwright E2E (separate effort if needed)
- Performance benchmarks
- Visual regression

Brief: see parent #1247