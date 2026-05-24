---
id: 1812
title: Refresh ConfirmDialog e2e path after move menu
status: archived
priority: important
created: 2026-05-24T08:49:00+02:00
updated: 2026-05-24T10:50:02.789096+02:00
tags:
  - scope:cockpit-web
  - test-harness
  - accessibility
  - discussion
parent: 1773
depends_on:
  - 1773
ac:
  - ConfirmDialog e2e coverage opens a currently reachable confirmation action.
  - The dual-theme accessibility sweep no longer waits on stale
    `[data-testid="move-backward"]` selectors.
  - Any repair stays harness-scoped unless current product behavior is proven
    wrong.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
While verifying #1781, the broader dual-theme accessibility sweep failed only on the ConfirmDialog surface in both light and dark themes. The spec still waits for `[data-testid="move-backward"]`, but `TaskActions` now exposes task movement through `task-detail-move-menu-trigger` and `task-detail-move-target`, while confirmations remain reachable through other actions such as Unclaim/Unblock.

## Current Interpretation
This appears to be stale e2e harness drift rather than a #1781 readiness issue. The proof-readiness spec passed, and the failing selector is unrelated to route opacity/transform settling.

## Evidence
- Command: `npx playwright test e2e/proof-readiness.spec.ts e2e/accessibility-dual-theme.spec.ts --project=chromium`
- Result: 28 tests run, 26 passed, 2 failed.
- Failures: light and dark `confirm dialog passes wcag2.1 aa under ... theme (AC3)` timed out waiting for `[data-testid="move-backward"]` at `e2e/accessibility-dual-theme.spec.ts`.

## Decision Needed
Decide whether to repair the stale ConfirmDialog e2e path next, likely by opening a current confirmation action rather than restoring the old move-backward button.

## Decision
User selected this task for implementation after #1823.

## Resolution
Refreshed ConfirmDialog E2E openers to use the current `unclaim-action` confirmation path instead of the removed `[data-testid="move-backward"]` button. No product UI behavior was changed.

## Verification
- `npx playwright test e2e/accessibility-dual-theme.spec.ts --project=chromium -g "confirm dialog passes"` -> 6 passed.
- `npx playwright test e2e/accessibility-sweep.spec.ts --project=chromium -g "confirm dialog passes"` -> 3 passed.
- `npx playwright test e2e/overlay-behavior.spec.ts --project=chromium -g "confirm_dialog_has_role_dialog_and_aria_modal|confirm_dialog_tab_focus_cycles_within_dialog|confirm_dialog_focus_returned_to_trigger_after_close"` -> 3 passed.