---
id: 1826
title: Review HealthBadge accessible label wording
status: research
priority: important
created: 2026-05-24T11:19:10.363983+02:00
updated: 2026-05-24T11:19:10.363983+02:00
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
