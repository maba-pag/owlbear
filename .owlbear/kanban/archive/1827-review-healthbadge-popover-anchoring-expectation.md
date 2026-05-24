---
id: 1827
title: Review HealthBadge popover anchoring expectation
status: archived
priority: important
created: 2026-05-24T11:19:10.382135+02:00
updated: 2026-05-24T23:20:50.529592+02:00
tags:
  - scope:cockpit-web
  - overlay
  - health-badge
  - discussion
parent: 1773
depends_on: []
ac:
  - HealthBadge popover runtime position is verified against the actual trigger 
    geometry.
  - The decision records whether the product should anchor to trigger-left or 
    use the viewport padding floor.
  - Any approved change is covered by focused anchoring proof.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
The full Cockpit frontend suite reported an OverlayAnchoring failure: the HealthBadge popover left style was `16px` while the test expected `200px` from the trigger-left anchoring formula.

## Evidence
- Test: `serve/cockpit/web/src/__tests__/OverlayAnchoring.test.tsx`
- Failure: `expected '16px' to be '200px'`

## Boundary
Treat this as an overlay positioning behavior review. Verify current runtime anchoring before deciding whether product code or the test expectation should change.

## User Decision
Decision: choose the behavior that is best for the product, not what the test expected. Tests are a TDD/build tool and are not authoritative product spec.

Implementation direction: keep or change HealthBadge popover anchoring based on actual runtime usability and visual behavior. If the current viewport-safe behavior is best for Cockpit, adjust or delete the stale trigger-left test expectation.

## Implementation Outcome
Completed by keeping the product-safe viewport padding behavior and updating the stale trigger-left test expectation. The popover may use the viewport floor when trigger-left anchoring would be less useful or unsafe.

Evidence: focused affected frontend tests passed; full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped; frontend build passed.

[[2026-05-24T23:20:50+02:00]]
## Audit

### Regression Detection
- Task-scoped: OverlayAnchoring.test.tsx — 15/15 passed
- Python cockpit tests: 287 passed, 0 failed
- Broad vitest: environmental timeouts in TailwindStylelint and PDS trap (pre-existing, outside task scope per background-debt separation)

### Intent Verification
- Changed file: `serve/cockpit/web/src/__tests__/OverlayAnchoring.test.tsx` — stays within `scope:cockpit-web` domain
- Purpose: updated stale trigger-left test expectation to match actual viewport-padding-floor behavior per user decision
- No extraneous scope — single test file, one expectation change

### Architect Quality
Score: 4/5 — AC lines adequate for a discussion/review task. User decision context provided clear implementation direction.

### Commit Integrity
- Builder commit: `8e58f235` (feat: complete cockpit interaction batch #1773)
- File committed in HEAD, no uncommitted deliverables

### Deductions
- Missing `## Review Evidence` section: -.03

### Confidence: 0.97 — ARCHIVE
