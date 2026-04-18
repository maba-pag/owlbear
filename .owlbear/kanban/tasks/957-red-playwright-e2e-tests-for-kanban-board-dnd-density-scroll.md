---
id: 957
title: 'RED: Playwright E2E tests for kanban board DnD, density, scroll'
status: research
priority: nice-to-have
created: 2026-04-18T13:49:17.523985+00:00
updated: 2026-04-18T13:49:17.523985+00:00
tags:
- cockpit
- frontend
- phase-2
- type:test
parent:
depends_on:
- 955
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Write failing Playwright E2E tests for the 3 kanban board AC items that cannot be tested in jsdom.

## Context

Deferred from #931 (jsdom feasibility matrix §3.2). Research in `.owlbear/research/955-e2e-kanban-board-tests.md`. Depends on Playwright infra setup and kanban board GREEN implementation.

## Acceptance Criteria

- [ ] DnD highlights test: drag card → valid target columns show highlight class/style; invalid targets show dim
  - Use `page.mouse.down()/move()` for mid-drag state assertions
- [ ] Card density test: each task card has rendered height between 48-56px
  - Use `locator.boundingBox()` to measure
- [ ] Scroll test: horizontal scroll navigates between columns; vertical scroll within a column with overflow
  - Use `mouse.wheel()` or `scrollIntoViewIfNeeded()`
- [ ] Tests are in `serve/cockpit/web/e2e/kanban-board.spec.ts`
- [ ] All tests fail (RED phase — component not yet implemented)

## Dependencies

- Playwright E2E infra setup task
- Kanban board GREEN implementation must be in progress or complete