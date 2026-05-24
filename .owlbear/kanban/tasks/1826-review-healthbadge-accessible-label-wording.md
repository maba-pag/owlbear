---
id: 1826
title: Review HealthBadge accessible label wording
status: done
priority: important
created: 2026-05-24T11:19:10.363983+02:00
updated: 2026-05-24T17:49:32+02:00
tags:
  - scope:cockpit-web
  - a11y
  - health-badge
  - discussion
parent: 1773
depends_on: []
ac:
  - HealthBadge trigger wording is reviewed for assistive clarity rather than
    blindly matching the stale test regex.
  - If a wording change is approved, the accessible name remains meaningful for
    green/yellow/red states.
  - Any approved change is covered by focused accessibility tests.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The full Cockpit frontend suite reported a KeyboardA11y failure: the HealthBadge trigger aria-label was `Workspace status: 1 issues`, while the existing test expected wording that matched `/health/i`.

## Evidence
- Test: `serve/cockpit/web/src/__tests__/KeyboardA11y.test.tsx`
- Failure: `aria-label must describe health state: expected 'Workspace status: 1 issues' to match /health/i`

## Boundary
Treat this as a product/accessibility wording question, not a test-as-spec mandate. Decide whether the visible/assistive label should say workspace status, health, issues, or a clearer combined phrase before implementation.

## User Decision
Decision: do not spend effort on accessibility or keyboard usability that does not fit the actual single-user, mouse-driven Cockpit workflow. Keep any change minimal and only resolve wording that is contradictory or required for the product to work.

Implementation direction: do not add broad accessibility work from this task. If the current HealthBadge wording is not product-confusing, keep it and adjust/delete stale test expectations rather than treating the test regex as authority.

## Implementation Outcome
Completed per user decision. No product wording change was needed for the mouse-driven Cockpit workflow; the stale keyboard/accessibility test surface was removed instead of treating its regex as product spec.

Evidence: full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped; frontend build passed; backend Cockpit ideas/mutation tests passed.
