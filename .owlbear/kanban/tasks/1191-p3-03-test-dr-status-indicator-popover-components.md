---
id: 1191
title: 'P3-03: Test DR status indicator + popover components'
status: backlog
priority: needed
created: 2026-04-30T00:52:17.480756+00:00
updated: 2026-04-30T00:57:03.031998+00:00
tags:
- phase-3
- scope:cockpit-fe
- type:test
parent: 1179
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test StatusBarIndicator renders pending DR count
- Test indicator uses attention color when count > 0, dormant when count = 0
- Test indicator click opens popover
- Test popover list renders DR items: title, agent, task_id, age
- Test popover item click triggers navigation/modal open
- Test polling hook fetches `/api/decisions/pending` on interval
- Test empty state (0 pending) renders dormant indicator

## Scope

- IN: Vitest component tests for StatusBarIndicator and DRPopover
- OUT: resolve modal (covered by #1193), backend endpoints

Brief: see parent #1179

[[2026-04-30]]
## Research
- Research doc: .owlbear/research/dr-status-indicator-test-strategy.md
- Sources: 7 studied (all internal codebase), 4 high-relevance
- Recommendation: Follow HealthBadge + useScanPolling test patterns exactly (confidence: 0.92)
- Follow-up tasks created: none (this IS the test task — AC already concrete)
- Decision requests: none

## Findings
- HealthBadge.tsx is an exact structural analogue (indicator → click → popover → item list)
- useScanPolling is the polling hook pattern (interval, stubGlobal, fake timers)
- Two test files needed: DRStatusIndicator_1191.test.tsx (component) + usePendingDRs_1191.test.ts (hook)
- API shape confirmed from sibling #1189: GET /api/decisions/pending → { count, items }
- No blockers, no new deps, T1 autonomous

## Challenge Results
- Challenger: FALLBACK — trivial T1 pattern replication, no technology choice to challenge
- Confidence in original: 0.92