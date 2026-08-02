---
id: 1505
title: 'Cockpit: Update Shell test suites for CockpitProvider hooks'
status: archived
priority: medium
created: 2026-05-12T02:59:59.249161+00:00
updated: 2026-05-12T16:56:24.800080+00:00
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
archival_reason: duplicate
archival_refs:
  - 1504
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
2026-05-12T16:21:19+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: update Shell test mocks for CockpitProvider |
| Interface clarity | REFINE needed | AC-1 says "8 files" but 9 exist; target mock module/hooks not named |
| Dependency correctness | PASS | depends_on=[1504] correct |
| Module layering | N/A | Test-only changes |
| TDD compliance | N/A | Task IS test changes |
| KISS/YAGNI | **FAIL — MERGE** | #1504 AC-10 already requires "npm test passes — including updated Shell test mocks". #1505 scope is fully subsumed. |
| Premise challenge | FAIL | #1504 builder cannot avoid updating Shell test mocks — Shell changes imports from useBoard/usePendingDRs/useScanPolling to CockpitProvider consumer hooks, breaking all 9 Shell test files. AC-10 requires npm test to pass. No residual scope for #1505. |
| Pattern consistency | N/A | |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Frontend/cockpit only |
| User-action detection | NOT DETECTED | AC defines testable TypeScript changes (C1) |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1: "All 8 Shell.*.test.tsx files updated" | B3 (naked "All"), count wrong (9 not 8), B2 target not named | Moot — merged |
| AC-2: "Hook-level tests remain unchanged" | PASS | Already in #1504 AC-2 |
| AC-3: "Test count parity" | PASS — verifiable | Covered by #1504 reviewer |
| AC-4: "All Vitest suites pass" | PASS — standard gate | Already #1504 AC-10 |
| AC-5: "No new test dependencies" | PASS | Already #1504 ethos |

### Codebase Evidence
- 9 Shell.*.test.tsx files (not 8): decisions-refetch, callbacks_1457, on-task-updated, traffic-light, decision-viewport, cleanup-wiring_1457, card-selection.integration, pbanner-1498, scan-health
- ALL 9 mock `../hooks/useBoard`; ALL 9 mock `../hooks/usePendingDRs`; 8 mock `../hooks/useScanPolling`; Shell.scan-health intentionally leaves useScanPolling unmocked for integration testing
- Shell.tsx already imports `useBoardState`, `useTaskSelection`, `useDRState` from `./hooks/CockpitProvider` (line 12) — builder #1504 WIP present in working tree
- #1504 AC-10: "npm test passes — including updated Shell test mocks and App tree assertions"
- #1504 Dependency Note: "AC-10 requires Shell test mock-path updates that overlap with sibling #1505 scope. #1505 will be re-scoped during its own architecture review."

### Design Diverge
- Trigger: skipped — MERGE verdict, no design evaluation needed

### Challenge Results
- Challenger: SKIPPED — MERGE verdict (no approval to challenge)

### Proof-Bundle Validation
- N/A — task merged, no standalone proof

### Verdict: MERGE
### Action Taken: #1505 merged into #1504 — scope fully subsumed by #1504 AC-10. Appended merge note to #1504 with file count correction (9 not 8) and Shell.scan-health integration test guidance.
2026-05-12T16:56:16+00:00
## Audit\n\n### Regression Detection\nNo code deliverables — task merged at architecture review stage. No quality-runner run needed.\n\n### Intent Verification\nMerge reasoning verified: #1504 AC-10 explicitly requires Shell test mock-path updates and npm test pass. #1504 Merge Note documents absorbed scope including file count correction (9 not 8) and Shell.scan-health integration test guidance. No residual scope exists for #1505.\n\n### Architect Quality\nScore: 4/5 — Architect correctly identified KISS/YAGNI violation (duplicate scope) and premise challenge failure (builder cannot avoid Shell test updates). Merge verdict was the right call. Original AC had quality issues (wrong count, unnamed targets) but these are moot given the merge.\n\n### Commit Integrity\nNo source commits expected — no code deliverables. Merge note appended to #1504.\n\n### Deductions\nNone.\n\n### Confidence: 1.00\n### Action: ARCHIVE (merged into #1504)