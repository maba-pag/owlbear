---
id: 1250
title: 'P2-01: RED — FilterPanel component tests'
status: research
priority: needed
created: 2026-05-01T04:34:48.876923+00:00
updated: 2026-05-01T04:37:37.053041+00:00
tags:
- phase-2
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on:
- 1249
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Vitest + Testing Library component test suite for FilterPanel:
  - Renders text input, priority select, tags multi-select, blocked switch, reset button when open
  - Hides tag control entirely when availableTags is empty
  - Reset button visible only when activeCount > 0
  - Reset button clears all filter values (calls onFilterChange with empty state)
  - Each control interaction fires onFilterChange with updated FilterState
  - Does not render controls when open={false} (or renders hidden)
- All tests fail (RED) — no FilterPanel component exists yet

## In Scope
- Component test file for FilterPanel
- Test fixtures using FilterState type from #1249

## Out of Scope
- FilterPanel implementation (next task)
- PDS component internals (mock or shallow-render PDS)
- Accessibility attributes (Phase 4)

Brief: see parent #1247