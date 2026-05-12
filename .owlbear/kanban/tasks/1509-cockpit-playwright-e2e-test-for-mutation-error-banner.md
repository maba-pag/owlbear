---
id: 1509
title: 'Cockpit: Playwright E2E test for mutation error banner'
status: research
priority: nice-to-have
created: 2026-05-12T08:33:03.181002+00:00
updated: 2026-05-12T08:33:22.244580+00:00
tags:
  - cockpit
  - frontend
  - testing
parent: 1494
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Objective
Add Playwright E2E test verifying the PDS PBanner mutation error banner in the Cockpit frontend.

## Acceptance Criteria
- New file `e2e/mutation-error-banner.spec.ts` in `serve/cockpit/web/`
- Test 1: PBanner visible after simulated API error — mock `/api/tasks/*/move` to 500, trigger context-menu transition, assert `p-banner` visible with heading containing "Move failed"
- Test 2: PBanner dismissible — dismiss banner from test 1, assert banner no longer visible
- Test 3: Banner clears on retry success — mock move to 200, re-trigger transition, assert no open `p-banner`
- Use `page.route()` mocking pattern from `kanban-board.spec.ts`
- Register route handlers in LIFO order: catch-all first, then specific routes
- Handle PDS shadow DOM for dismiss button interaction (Playwright auto-pierce or `page.evaluate()` fallback)

## Source
Research from task #1500; research doc `.owlbear/research/cockpit-mutation-error-tests.md`