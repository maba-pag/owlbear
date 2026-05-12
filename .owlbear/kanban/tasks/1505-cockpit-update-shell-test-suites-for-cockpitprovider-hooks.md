---
id: 1505
title: 'Cockpit: Update Shell test suites for CockpitProvider hooks'
status: backlog
priority: important
created: 2026-05-12T02:59:59.249161+00:00
updated: 2026-05-12T10:47:41.395484+00:00
tags:
  - cockpit
  - frontend
  - testing
parent: 1491
depends_on:
  - 1504
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Update 8 Shell test files to mock CockpitProvider consumer hooks instead of current direct hook mocks.

## Acceptance Criteria
- All 8 Shell.*.test.tsx files updated: mock paths change from `../hooks/useBoard` etc. to CockpitProvider consumer hooks
- Hook-level tests (useBoard.test.ts, usePendingDRs.test.ts, useScanPolling.test.ts, useBoard.sse-context.test.ts) remain unchanged — hooks survive as internal modules
- Test count parity: same number of assertions before and after
- All Vitest suites pass (npm test)
- No new test dependencies added

## Source
Research: .owlbear/research/1491-cockpit-provider-extraction.md
2026-05-12T10:47:41+00:00
Advanced from research to backlog. Research phase complete — full AC present from researcher. Ready for independent architecture review (after #1504).