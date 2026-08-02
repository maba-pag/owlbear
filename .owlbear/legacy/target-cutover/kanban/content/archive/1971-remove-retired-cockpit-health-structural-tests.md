---
id: 1971
title: Remove retired Cockpit health structural tests
status: archived
priority: high
created: 2026-07-21T15:43:00.863642+02:00
updated: 2026-07-21T15:48:21.738619+02:00
tags:
  - baseline
  - scope:cockpit-web
  - test-curation
  - maintenance
parent:
depends_on: []
ac:
  - The obsolete HealthBadge structural test file is deleted, and the retired 
    useScanPolling assertion is removed without weakening the remaining 
    shared-polling assertions.
  - The focused retained polling suite passes and repository search finds no 
    active root-test requirement for HealthBadge or useScanPolling.
  - 'No product source, Kanban or memory source, admission artifact, or task #1968
    path is changed.'
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
Restore the committed Python baseline after the Workspace Status cutover by removing durable structural assertions that require the intentionally deleted `HealthBadge` and `useScanPolling` paths.

## Scope
In scope: delete `tests/test_health_badge_frontend.py`; remove only `test_usscanpolling_imports_usepollingfetch` and its stale class wording from `tests/test_frontend_polling.py`; focused Python proof and exact-commit verification. Out of scope: Cockpit product code, retained polling contracts, Kanban or memory source formatting, admission artifacts, and task #1968.

## Evidence
At exact revision `0510ad334048b544c9438fbf7519aaf706f84da4`, the build/browser-dependent Python group passes 37 of 37 after normal setup. The two scoped legacy files run 23 tests with 13 passing and exactly 10 failing: nine require the removed HealthBadge component/test, and one requires the removed useScanPolling hook. The current Workspace Status implementation and #1944 explicitly replaced those paths without compatibility aliases.

[[2026-07-21T15:45:09+02:00]]
## Builder Notes

**Verdict:** DONE to verify.

**Change envelope:** Deleted the obsolete `tests/test_health_badge_frontend.py` structural suite and removed only the retired `useScanPolling` assertion plus its two descriptive references from `tests/test_frontend_polling.py`. All retained polling guards remain unchanged. No product, Kanban source, memory source, admission, or #1968 path is owned.

**Observed defect:** At exact revision `0510ad334048b544c9438fbf7519aaf706f84da4`, normal setup made the Cockpit/browser-dependent Python group pass 37 of 37. The two scoped legacy files then produced exactly 10 failures: nine required removed HealthBadge artifacts and one required the removed scan hook; 13 retained tests already passed.

**Proof:** The post-edit retained polling suite passes 13 of 13. Ruff lint is clean, Ruff format reports the retained file already formatted, editor diagnostics are empty, and owned-path `git diff --check` passes. Active `tests/**` search finds no remaining HealthBadge or useScanPolling requirement; the sole text match is an arbitrary `__tests__` path in a generic write-guard fixture.

**Durable-test judgment:** The deleted assertions preserved retired implementation/file shapes and contradicted the approved Workspace Status cutover. They fail the Rent Test and must not force compatibility aliases. Retained polling assertions still guard active shared behavior.

**Memory assessment:** All ten recalled entries were assessed. Artifact-to-scope and do-not-restore-removed-contract guidance were applied; the remaining entries were not used.

**Builder challenger:** `decision: pass`; focused pytest, Ruff lint/format, search, diff scope, and durable-test removal all passed with no auto-fix.

[[2026-07-21T15:47:36+02:00]]
## Verify Notes

**Verdict:** PASS to collect.

**Exact revision:** `7bbb25fba72f98fc984d8e3f71a1e859da041293` in the disposable baseline checkout.

**Scope review:** The commit contains only the #1971 task record, the narrow retained-polling test update, and deletion of the obsolete HealthBadge structural suite. No product, Kanban source, memory source, admission, or #1968 path is present.

**Exact-commit proof:** After normal clean-checkout setup and Cockpit production build, the focused polling suite passed 13 of 13. The complete non-API/non-E2E Python suite passed 3,746 of 3,746 with only ten third-party deprecation warnings. Scoped Ruff lint passed, scoped Ruff format passed, and the checkout had no tracked proof delta. Active test search found no remaining requirement for HealthBadge or useScanPolling; the sole name match is an arbitrary generic write-guard fixture path.

**AC judgment:** The stale suite and scan assertion preserved removed implementation shapes and contradicted the approved Workspace Status replacement. Their removal does not weaken the 13 retained shared-polling guards and does not restore a compatibility alias.

**Separate baseline context:** Repository-wide Ruff still reports committed style debt in two source files outside #1971. Those paths have substantial unrelated uncommitted behavioral edits in the main worktree, whose current versions pass Ruff. This remains an admission-baseline blocker but is not a defect in this task.

**Memory assessment:** All ten recalled verifier entries were assessed. Artifact-to-scope, background-debt separation, and removed-contract guidance were applied.

**Verifier challenger:** `decision: pass`; no unresolved task AC or scope defect. It explicitly kept the repository-wide Ruff issue outside #1971.

[[2026-07-21T15:48:21+02:00]]
## Collect Notes

**Verdict:** ARCHIVED as completed.

This ordinary verified leaf has no parent, dependencies, pending requests, or resolved-request obligations. The committed verifier PASS at `9f6a26db` covers all three ACs at exact builder revision `7bbb25fba72f98fc984d8e3f71a1e859da041293`: focused polling passed 13 of 13, the complete Python suite passed 3,746 of 3,746 after normal build/browser setup, scoped Ruff passed, and the exact checkout remained clean.

The task-owned change contains only its task record, narrow polling-test curation, and deletion of the obsolete HealthBadge structural suite. No product or #1968 artifact was included. Repository-wide Ruff debt in unrelated dirty source paths remains separate admission-baseline work.

All seven recalled collector memories were assessed; background-debt separation, active-workspace, and build-proof guidance were applied.
