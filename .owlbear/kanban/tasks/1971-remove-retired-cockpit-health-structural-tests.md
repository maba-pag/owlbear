---
id: 1971
title: Remove retired Cockpit health structural tests
status: verify
priority: high
created: 2026-07-21T15:43:00.863642+02:00
updated: 2026-07-21T15:45:09.573009+02:00
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
archival_reason:
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
