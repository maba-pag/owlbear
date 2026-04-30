---
id: 1193
title: 'P3-05: Test resolve modal component'
status: backlog
priority: needed
created: 2026-04-30T00:52:25.642042+00:00
updated: 2026-04-30T00:58:07.486565+00:00
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

- Test ResolveModal renders full DR body as markdown
- Test response selector offers: approved, rejected, needs-info
- Test optional notes textarea accepts freeform markdown
- Test submit calls `POST /api/decisions/{id}/resolve` with selected response + notes
- Test modal closes on successful submission
- Test error state shown on failed submission
- Test cancel/close without submitting does not mutate

## Scope

- IN: Vitest component tests for ResolveModal
- OUT: status indicator (covered by #1191), backend endpoints

Brief: see parent #1179

[[2026-04-30]]
## Research
- Research doc: .owlbear/research/resolve-modal-test-strategy.md
- Sources: 7 studied (all internal codebase), 5 high-relevance
- Recommendation: Follow RepairPanel + DetailTab patterns — single test file, prop-driven component, fetch stub, react-markdown mock (confidence: 0.90)
- Follow-up tasks created: none (this IS the test task)
- Decision requests: none

## Findings
- RepairPanel_1167.test.tsx is the exact structural analogue (dialog phases, confirm/cancel, error state)
- DetailTab.test.tsx provides the fetch mocking + async POST assertion pattern
- react-markdown factory mock already established in codebase
- API contract confirmed: POST /api/decisions/{id}/resolve with {response, notes}
- Component interface: props-driven (receives PendingDR object + onClose + onResolved)
- Single test file: src/__tests__/ResolveModal_1193.test.tsx (~12-15 tests)
- No blockers, no new deps, T1 autonomous

## Challenge Results
- Challenger: FALLBACK — trivial T1 pattern replication, no technology choice to challenge
- Confidence in original: 0.90