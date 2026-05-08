---
id: 1387
title: 'P2-12: Implement Cockpit decision data contract and refetch flow'
status: review
priority: needed
created: 2026-05-06T01:04:49.160414+00:00
updated: 2026-05-08T15:40:53.305002+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- decisions
- interface-contract
parent: 1363
depends_on:
- 1386
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement the pending decision frontend data contract and refetch behavior needed by the decision viewport.

## Problem Evidence
- usePendingDRs omits body even though the backend returns it and ResolveModal needs it.
- ResolveModal only refetches pending decision requests after resolution, not affected task or board state.
- Decision frontend errors must use the frontend error contract from #1375.

## Acceptance Criteria
- Pending decision frontend types include the full body returned by the backend.
- Pending decision data preserves task link/context, agent or request type, age, body or preview content, and status needed by the UI.
- Successful resolution refetches pending decisions and affected task or board state after backend lifecycle side effects from #1385.
- Loading, empty, and expected error states consume the frontend error contract from #1375.
- The implementation satisfies #1386 without building the visible viewport redesign owned by #1389.

## Scope
- In scope: Cockpit frontend decision hooks, types, API adapters, and refetch flow.
- Out of scope: backend decision lifecycle from #1385, visible viewport redesign from #1389, task detail workflows, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1386.

[[2026-05-08]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Scoped to decision data contract and refetch |
| Interface clarity | PASS | AC lines are specific |
| Dependency correctness | PASS | #1386 is archived/done (test task complete) |
| Module layering | PASS | Frontend hooks/types only |
| TDD compliance | PASS | Test task #1386 exists and is archived |
| KISS/YAGNI | N/A | See premise challenge |
| Premise challenge | **FAIL** | All three problems described are already resolved in the current codebase |
| Pattern consistency | PASS | Follows existing hook/refetch patterns |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |

### Premise Challenge Evidence

All three problem-evidence items are stale — the code already implements what the AC requires:

1. **"usePendingDRs omits body"** — FALSE. `PendingDR` interface at `serve/cockpit/web/src/hooks/usePendingDRs.ts:14` already declares `body: string`.

2. **"ResolveModal only refetches pending DRs, not task/board state"** — FALSE. `Shell.tsx:260-263` onResolved handler already calls both `void refetchPendingDRs()` AND `refetchTasks()`.

3. **"Decision frontend errors must use the frontend error contract from #1375"** — ALREADY DONE. `ResolveModal.tsx:14` imports and uses `getResponseErrorMessage`. `usePendingDRs` uses `usePollingFetch` which also calls `getResponseErrorMessage`.

The RED test file (`DecisionContract_1386.test.tsx`) claims "All FAIL until #1387 adds refetchTasks()" but `refetchTasks()` is already present in the onResolved handler. These tests likely already pass.

### Required Research

A researcher should:
1. Run `npm test -- --testPathPattern DecisionContract_1386` to confirm tests pass against current code.
2. If all pass → close task as already-completed (work was done by other tasks in the pipeline).
3. If any fail → rewrite problem evidence to accurately describe what's actually broken.

### Challenge Results
- Challenger: SKIPPED — premise challenge fails, no approval to validate

### Test Depth
- Max depth: N/A (rejected)
- Test-writer: N/A

### Verdict: REJECT
### Action Taken: Rejected to research — problem evidence is stale, all AC lines describe existing behavior. Researcher must verify test state and either close or rewrite.
[[2026-05-08]]
## Research
- Research doc: .owlbear/research/1387-decision-data-contract-noop.md
- Sources: 4 codebase files verified, 2 test files executed
- Recommendation: Close as no-op (confidence: 0.95)

### Verification summary
All 12 tests from #1386 pass GREEN against the current codebase. The three problem-evidence items are stale — `body` field exists in `PendingDR`, `refetchTasks()` is already called in `onResolved`, and `getResponseErrorMessage` is already imported in `ResolveModal`. No implementation work needed. No follow-up tasks created.
[[2026-05-08]]

[[2026-05-08]]
## Architecture Review (Pass 2)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | PASS | Research confirmed all 3 problems already resolved; 12/12 tests GREEN |
| Single responsibility | PASS | N/A — no-op |
| TDD compliance | PASS | #1386 archived, tests pass |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| Pending decision frontend types include full body | Already implemented (`PendingDR.body: string` at `usePendingDRs.ts:13`) | td:0 |
| Pending decision data preserves task link/context/age/body/status | Already implemented in existing hook | td:0 |
| Resolution refetches pending decisions and affected task/board state | Already implemented (`Shell.tsx:266-269` calls both refetch functions) | td:0 |
| Loading/empty/error states consume frontend error contract | Already implemented (`ResolveModal.tsx:11` imports `getResponseErrorMessage`) | td:0 |
| Implementation satisfies #1386 without viewport redesign | Confirmed — all #1386 tests pass without viewport changes | td:0 |

### Architecture Notes
All AC lines describe behavior already present in the codebase. Research doc `.owlbear/research/1387-decision-data-contract-noop.md` provides test execution evidence. No code changes required.

### Challenge Results
- Challenger: SKIPPED — all AC lines td:0, no implementation to challenge

### Test Depth
- Max depth: td:0 (all lines)
- Test-writer: SKIP

### Verdict: APPROVE (no-op — all AC satisfied by existing code)

[[2026-05-08]]
APPROVED #1387 -> todo | No-op: all AC already satisfied by existing code. Research verified 12/12 tests GREEN. All AC lines td:0, Test-writer: SKIP.
[[2026-05-08]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.
- Architecture Review confirmed all 5 AC lines already satisfied by existing code (12/12 tests GREEN on #1386). No new tests to write.
[[2026-05-08]]
## Builder Notes
- Non-implementation task (td:0 pass-through from architecture + test-writer).
- Code changes: none.
- Tests: no builder test run required for pass-through; prior pipeline evidence reports #1386 GREEN (12/12).
- Lint: no code touched.
- Passing through to review.