---
id: 1381
title: 'P2-06: Implement Cockpit task action gating and confirmations'
status: review
priority: needed
created: 2026-05-06T01:04:37.405026+00:00
updated: 2026-05-09T15:59:41.440878+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- task-actions
- workflow
parent: 1363
depends_on:
- 1380
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement state-aware task action gating and action-specific confirmations in Cockpit task detail.

## Problem Evidence
- DetailTab renders Unclaim even for unclaimed tasks, causing avoidable backend 409 responses.
- Move backward, unblock, unclaim, and destructive-ish actions need state-aware gating and clear consequences.
- Confirmation dialogs are generic and lack action-specific labels and focus semantics.

## Acceptance Criteria
- Action buttons are shown or enabled only when valid for the current task status, claim state, block state, and backend transition rules. (td:2)
- Unclaim is unavailable for unclaimed tasks and cannot issue a mutation in that state. (td:2)
- Unblock and move-backward actions expose clear action-specific confirmation text before mutating state. (td:2)
- Confirmation labels name the concrete action and target state instead of using generic Confirm text. (td:2)
- Confirmation keyboard and focus behavior meets the expectations captured in #1380, with final global accessibility verification left to a separate task. (td:2)
- Expected 409, 404, and 422 responses use the frontend error contract from #1375. (td:2)
- The implementation satisfies #1380's 22-test suite and existing `DetailTab.test.tsx` conflict-resolution tests pass without regression, without changing conflict-resolution behavior owned by #1383. (td:1)

## Scope
- In scope: Cockpit frontend task action gating and confirmation behavior.
- Out of scope: conflict resolution, decision resolution, backend route changes, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1380.

[[2026-05-09]]


## Builder Guidance
The implementation for all AC lines was committed during #1380's pipeline cycle (commit `b899bbb2`, builder notes in archived #1380). Source changes to `DetailTab.tsx` and `ConfirmDialog.tsx` are already in the codebase. This task is a verification pass: run the full `DetailTab_1380.test.tsx` suite (22 tests), verify the existing `DetailTab.test.tsx` conflict tests still pass (AC7 non-regression), and confirm no regressions in adjacent suites (`DetailTab_1344`, `DetailTab_1378`, `DetailTab_1379`).

[[2026-05-09]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Frontend action gating and confirmations only |
| Interface clarity | PASS | AC specifies DOM gating, label content, keyboard/focus, error contract paths |
| Dependency correctness | PASS | #1380 (test task) archived/done; #1375 (error contract) archived/done |
| Module layering | PASS | Changes scoped to DetailTab.tsx and ConfirmDialog.tsx — no upward imports |
| TDD compliance | PASS | Test task #1380 completed; `DetailTab_1380.test.tsx` has 22 tests |
| KISS/YAGNI | PASS | Minimal scope — gating + confirmations only |
| Premise challenge | PASS (with note) | Implementation already committed during #1380's pipeline (commit b899bbb2). Task is a verification pass — still valid as pipeline artifact for formal GREEN confirmation |
| Pattern consistency | PASS | Follows existing ConfirmDialog pattern, error contract from #1375 |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Provenance Note
The builder on test task #1380 implemented source changes to `DetailTab.tsx` and `ConfirmDialog.tsx` to make RED tests GREEN. This is a boundary overlap where #1380's builder crossed into #1381's implementation scope. All 22 tests in `DetailTab_1380.test.tsx` now pass. Builder guidance added to task body directing verification-only pass.

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Key challenges: (1) AC7 non-regression scope not covered by #1380 suite alone, (2) provenance inconsistency between #1380 builder notes and #1381 backlog status, (3) stale line references
- Architect response: revised — refined AC7 to explicitly require `DetailTab.test.tsx` conflict-resolution regression check alongside #1380 suite pass. Added builder guidance noting existing implementation. Provenance issue documented but does not invalidate AC quality.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED (tests exist from #1380; test-writer verifies coverage sufficiency)

### Verdict: APPROVE
### Action Taken: Annotated AC with td depths, refined AC7 to include explicit conflict-test non-regression check, added Builder Guidance section documenting existing implementation provenance. Advanced to todo.
[[2026-05-09]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/DetailTab_1381.test.tsx`
- Classes: `TestFromAC_ConflictResolutionNonRegression`
- Tests per category: happy 1, edge 0, error 0, boundary 0
- Total: 1 test (AC7 non-regression guard)
- ESLint: clean

**AC coverage:**
| AC | td | Coverage source | Status |
|----|----|----------------|--------|
| AC1: action buttons gated by task state | td:2 | `DetailTab_1380.test.tsx` — 4 tests | Covered |
| AC2: unclaim absent + no mutation for claimed=false | td:2 | `DetailTab_1380.test.tsx` — 1 test | Covered |
| AC3: action-specific confirmation text | td:2 | `DetailTab_1380.test.tsx` — 3 tests | Covered |
| AC4: confirmation labels name concrete action | td:2 | `DetailTab_1380.test.tsx` — 5 tests (incl. exact labels) | Covered |
| AC5: keyboard/focus behavior | td:2 | `DetailTab_1380.test.tsx` — 5 tests (incl. Escape+restore) | Covered |
| AC6: 409/404/422 error contract for action mutations | td:2 | `DetailTab_1380.test.tsx` — 4 tests | Covered |
| AC7: non-regression of conflict-resolution + #1380 suite pass | td:1 | `DetailTab_1381.test.tsx` — 1 smoke test | Covered |

**Implementation status note:** All 23 tests PASS. Implementation was pre-committed during #1380's pipeline cycle (commit `b899bbb2`) per builder guidance. The `DetailTab_1380.test.tsx` 22-test suite and the new AC7 smoke test serve as the builder's verification targets. Builder task is a verification pass: run these two suites plus adjacent suites (`DetailTab.test.tsx`, `DetailTab_1344`, `DetailTab_1378`, `DetailTab_1379`) to confirm no regressions.
[[2026-05-09]]
## Builder Notes
- Implementation: verification-only pass; no source edits were required in this task. Existing implementation in `serve/cockpit/web/src/components/DetailTab.tsx` and `serve/cockpit/web/src/components/ConfirmDialog.tsx` already satisfies AC behavior.
- Tests: 109 passed, 1 skipped across required suites.
  - `serve/cockpit/web/src/__tests__/DetailTab_1380.test.tsx` (22)
  - `serve/cockpit/web/src/__tests__/DetailTab_1381_legacy.test.tsx` (1)
  - `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` (48, 1 skipped)
  - `serve/cockpit/web/src/__tests__/DetailTab_1344_legacy.test.tsx` (11)
  - `serve/cockpit/web/src/__tests__/DetailTab_1378_legacy.test.tsx` (24)
  - `serve/cockpit/web/src/__tests__/DetailTab_1379_legacy.test.tsx` (4)
- Lint: scoped ESLint run clean (0 violations) for `DetailTab.tsx`, `ConfirmDialog.tsx`, and all six verification test files.
- Coverage: not run in this scoped frontend verification pass.
- Evidence summary: action-gating/confirmation suite and AC7 conflict-resolution non-regression guard pass together with adjacent DetailTab suites; no regressions observed in targeted scope.
- Note on RED verification: task body explicitly marks this as a verification pass with pre-existing implementation provenance from #1380, so TestFromAC failures are not reproducible in current code state.