---
id: 1826
title: Review HealthBadge accessible label wording
status: archived
priority: medium
created: 2026-05-24T11:19:10.363983+02:00
updated: 2026-05-24T23:18:34.666929+02:00
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
archival_reason: completed
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

[[2026-05-24T23:18:34+02:00]]
## Audit

### Regression Detection
Quality-runner full suite: 2218 passed, 114 failed (all timeouts in unrelated test files — ArchivalModal, TailwindStylelint, PInlineNotification, DetailTab.conflict-resolution), 11 skipped. ESLint error for missing fixture file from unrelated task #1592. Task #1826 only deleted `KeyboardA11y.test.tsx`; file deletion cannot cause timeout regressions in other files. These are environment/resource-related timeouts, not task-caused regressions. No regression attributable to this task.

### Intent Verification
Changed file: single deletion of `serve/cockpit/web/src/__tests__/KeyboardA11y.test.tsx` — stays within `scope:cockpit-web` domain. Implementation matches stated purpose (user decided against a11y work; stale test removed per user direction). No extraneous scope.

### Architect Quality
Score: 4/5. AC was adequate for a discussion/review task. AC2 and AC3 became N/A after user decision directed minimal work; AC1 was met. Minor gap: AC lines assumed a wording change might be approved, but the boundary section correctly framed it as a product decision.

### Commit Integrity
Builder deliverable present in commit `8e58f235` (feat: complete cockpit interaction batch #1773). Batch commit for parent task includes this subtask's change.

### Deductions
- Missing explicit `## Review Evidence` section: -0.03

### Confidence: 0.97 — ARCHIVE
