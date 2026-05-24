---
id: 1831
title: Review DetailTab save action stack trace error
status: research
priority: important
created: 2026-05-24T11:24:06.544691+02:00
updated: 2026-05-24T11:24:06.544691+02:00
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
archival_reason:
archival_refs: []
---
Found during #1825 full Vitest verification. DetailTab.test.tsx has a residual save-action failure reported as STACK_TRACE_ERROR. The failure needs triage separate from the Ideas router blocker.