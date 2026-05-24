---
id: 1831
title: Review DetailTab save action stack trace error
status: done
priority: important
created: 2026-05-24T11:24:06.544691+02:00
updated: 2026-05-24T23:25:35.075188+02:00
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
claimed_at: 2026-05-24T23:25:35.075188+02:00
archival_reason:
archival_refs: []
---
Found during #1825 full Vitest verification. DetailTab.test.tsx has a residual save-action failure reported as STACK_TRACE_ERROR. The failure needs triage separate from the Ideas router blocker.

## User Decision
Approved direction: product-first triage.

Implementation direction: reproduce the actual mouse-driven task edit/save flow. If saving is broken, fix the product behavior. If the product behavior works and the failure is a test harness/jsdom/PDS artifact, fix or remove the bad test.

## Implementation Outcome
Completed as test harness cleanup. The actual save flow remained intact; the stale duplicate conflict/history/action checks in the legacy DetailTab file were reduced or made deterministic because dedicated conflict and history suites already cover those behaviors.

Evidence: DetailTab focused suite passed with 63 passed, 1 skipped; affected bundle passed with 126 passed, 1 skipped; full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped.