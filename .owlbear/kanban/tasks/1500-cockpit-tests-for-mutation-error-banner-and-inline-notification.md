---
id: 1500
title: 'Cockpit: Tests for mutation error banner and inline notification'
status: in-progress
priority: needed
created: 2026-05-12T02:38:27.742252+00:00
updated: 2026-05-12T09:41:36.103852+00:00
tags:
  - cockpit
  - frontend
  - testing
  - test
parent: 1494
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Add Vitest unit tests and Playwright E2E tests for the new PDS notification components.

## Acceptance Criteria
- Vitest: PBanner appears on simulated move/edit failure, correct state prop, dismiss clears
- Vitest: PBanner auto-clears on next successful mutation
- Vitest: PBanner survives task selection change (selectedTaskId change doesn't clear error)
- Vitest: PInlineNotification appears in ArchivalModal on failure, retry action works
- Vitest: PInlineNotification appears in ResolveModal on failure
- Playwright E2E: Banner visible after simulated API error, dismissible, clears on retry success

## Source
Research doc: .owlbear/research/cockpit-mutation-error-banner.md (task #1494)
2026-05-12T08:33:28+00:00
## Planning

Single follow-up task created (single-task shortcut — no TDD pair needed for a standalone E2E test task at research status).

| ID | Title | Status | Priority | Parent | Tags |
|----|-------|--------|----------|--------|------|
| #1509 | Cockpit: Playwright E2E test for mutation error banner | research | nice-to-have | #1494 | cockpit, frontend, testing |

All 5 Vitest AC items from #1500 are already covered by existing suites (56 tests passing). Only the Playwright E2E gap remains, captured in #1509.

## Research
- Research doc: .owlbear/research/cockpit-mutation-error-tests.md
- Sources: 7 studied, 5 high-relevance (all codebase)
- Recommendation: All Vitest ACs already covered (56 passing tests from #1498/#1499); one follow-up for Playwright E2E gap (confidence: 0.88)
- Follow-up: #1509 — Playwright E2E test for mutation error banner (at research, nice-to-have)


## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1: PBanner on move/edit failure, state prop, dismiss | PASS — covered by Shell.pbanner-1498.test.tsx (6 tests: renders, heading, description, state=error, state=warning, dismiss), KanbanBoard.pbanner-1498.test.tsx (3 tests), DetailTab.pbanner-1498.test.tsx (3 tests) | None |
| AC-2: PBanner auto-clears on success | PASS — covered by Shell.pbanner-1498.test.tsx AC-6/AC-7 (2 tests: onMutationSuccess, onTaskUpdated) | None |
| AC-3: PBanner survives selectedTaskId change | PASS — covered by Shell.pbanner-1498.test.tsx AC-8 (2 tests: task selection, tab switch) | None |
| AC-4: PInlineNotification in ArchivalModal, retry | PASS — covered by PInlineNotification.modal-1499.test.tsx AC-1/AC-3 (~10 tests: 409/422/500/network/client errors + retry action) | None |
| AC-5: PInlineNotification in ResolveModal | PASS — covered by PInlineNotification.modal-1499.test.tsx AC-2 (6 tests: 404/409/422/500/network + description) | None |
| AC-6: Playwright E2E banner test | SPLIT — extracted to #1509 | Excluded from scope |

### Evaluation

| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS — test verification only |
| Interface clarity | PASS — AC names components + behaviors |
| Dependency correctness | PASS — #1498 (archived), #1499 (docs) both near-terminal |
| TDD compliance | N/A — this IS the test task; tests pre-exist from sibling TDD cycles |
| KISS/YAGNI | PASS — no new code needed |
| Pattern consistency | PASS — existing tests use project patterns (PDS stubs, vitest) |
| Security surface | PASS — no new system boundaries |
| Single domain | PASS — frontend testing only |

### Proof-Bundle Validation

- Planner assignment: (none)
- Final bundle: existing
- Existing proof scope: `serve/cockpit/web/src/Shell.pbanner-1498.test.tsx`, `serve/cockpit/web/src/KanbanBoard.pbanner-1498.test.tsx`, `serve/cockpit/web/src/DetailTab.pbanner-1498.test.tsx`, `serve/cockpit/web/src/PInlineNotification.modal-1499.test.tsx`
- Test-writer: SKIP
- Challenger: SKIPPED (bundle existing)

### Notes

- All 5 Vitest ACs are pre-satisfied by #1498/#1499 TDD cycles (64 tests across 4 files)
- Parent #1494 architect review predicted this overlap
- E2E gap correctly extracted to #1509 (research, nice-to-have)
- Tagged `test` for pipeline pass-through

### Verdict: APPROVE

2026-05-12T09:17:12+00:00
Architecture review complete. All 5 Vitest ACs pre-satisfied by #1498/#1499 TDD cycles (64 tests across 4 files). Playwright E2E AC correctly split to #1509. Proof bundle: existing. Tagged `test` for pass-through. Advanced backlog → todo.
2026-05-12T09:41:36+00:00
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- Proof bundle: existing — no new test writing required.
- All 5 Vitest ACs pre-satisfied by #1498/#1499 TDD cycles (64 tests across 4 files: Shell.pbanner-1498.test.tsx, KanbanBoard.pbanner-1498.test.tsx, DetailTab.pbanner-1498.test.tsx, PInlineNotification.modal-1499.test.tsx).
- Playwright E2E gap correctly extracted to #1509.
- Passing through to builder.