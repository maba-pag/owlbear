---
id: 1831
title: Review DetailTab save action stack trace error
status: archived
priority: medium
created: 2026-05-24T11:24:06.544691+02:00
updated: 2026-05-24T23:52:41.166479+02:00
tags:
  - scope:cockpit-web
  - detail-tab
  - test-health
  - discussion
parent: 1773
depends_on: []
ac:
  - Reproduce the save-action failure with the current DetailTab suite.
  - Decide whether this is product bug, stale test, or jsdom/PDS harness issue.
  - Any approved change preserves task edit/save behavior.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Found during #1825 full Vitest verification. DetailTab.test.tsx has a residual save-action failure reported as STACK_TRACE_ERROR. The failure needs triage separate from the Ideas router blocker.

## User Decision
Approved direction: product-first triage.

Implementation direction: reproduce the actual mouse-driven task edit/save flow. If saving is broken, fix the product behavior. If the product behavior works and the failure is a test harness/jsdom/PDS artifact, fix or remove the bad test.

## Implementation Outcome
Completed as test harness cleanup. The actual save flow remained intact; the stale duplicate conflict/history/action checks in the legacy DetailTab file were reduced or made deterministic because dedicated conflict and history suites already cover those behaviors.

Evidence: DetailTab focused suite passed with 63 passed, 1 skipped; affected bundle passed with 126 passed, 1 skipped; full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped.

[[2026-05-24T23:52:41+02:00]]
## Audit

### Regression Detection
Vitest (full cockpit-web suite): 2332 passed, 11 skipped, 0 failed (exit 0).
Pytest (cockpit domain): 184 passed, 0 failed.
Ruff: clean (exit 0).
No regressions detected.

### Intent Verification
Changed files stay within cockpit-web domain (DetailTab component + test, other test harness files). Implementation direction (test harness cleanup of stale duplicate checks) matches stated purpose (fix save-action stack trace error by triaging as harness artifact). No extraneous scope — parent batch commit (#1773) is the expected delivery unit.

### Architect Quality
AC score: 4/5. AC lines are well-suited for a triage/discussion task: reproduce, decide root cause, preserve behavior. Clear and verifiable without over-specifying.

### Commit Integrity
Builder commit 8e58f235 contains DetailTab changes. Commit message follows format. No uncommitted deliverables.

### Deductions
- Missing explicit `## Review Evidence` section: -.03

### Confidence: 0.97 → ARCHIVE
