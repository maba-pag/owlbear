---
id: 1387
title: 'P2-12: Implement Cockpit decision data contract and refetch flow'
status: archived
priority: medium
created: 2026-05-06T01:04:49.160414+00:00
updated: 2026-05-08T16:49:54.930995+00:00
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
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner scoped pass on `serve/cockpit/web/src/__tests__/DecisionContract_1386.test.tsx` and `serve/cockpit/web/src/__tests__/DecisionContract_1386_hook.test.ts`: 12 passed, 0 failed, vitest exit 0, eslint exit 0.
- quality-runner adjacent pass on `serve/cockpit/web/src/__tests__/DRStatusIndicator_1191.test.tsx`: 25 passed, 0 failed, vitest exit 0, eslint exit 0.
- quality-runner baseline hook pass on `serve/cockpit/web/src/__tests__/usePendingDRs_1191.test.ts`: 24 passed, 0 failed, vitest exit 0, eslint exit 0.
- VS Code diagnostics reported no errors in `serve/cockpit/web/src/hooks/usePendingDRs.ts`, `serve/cockpit/web/src/components/ResolveModal.tsx`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/DRStatusIndicator.tsx`, and the task-owned decision test files.

### Lint Results
- eslint clean for the reviewed frontend sources: `usePendingDRs.ts`, `ResolveModal.tsx`, `Shell.tsx`, `DRStatusIndicator.tsx`.
- No lint violations reported in any scoped quality-runner pass.

### Coverage
- N/A for this review. Builder notes report no code changes, no builder commit hash was provided, and the scoped frontend quality-runner passes did not collect coverage. Because this is a verified no-op task, evidence came from current source inspection plus green task-owned and adjacent suites.

### Security Review
- No scoped security issues found.
- `ResolveModal` continues to render decision markdown through `rehypeSanitize` (`serve/cockpit/web/src/components/ResolveModal.tsx:89`), so the no-op verdict does not expose a new unsafe rendering path.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Pending decision frontend types include the full body returned by the backend. | Backend pending-decision route emits `body` and `body_preview` (`serve/cockpit/src/owlbear_cockpit/routes/decisions.py:101-102`); frontend `PendingDR` includes `body: string` and `body_preview: string` (`serve/cockpit/web/src/hooks/usePendingDRs.ts:13-14`). Backend README documents the same response shape (`serve/cockpit/README.md:73`). | `serve/cockpit/web/src/__tests__/DecisionContract_1386_hook.test.ts:94`; quality-runner 12/12 green | PASS |
| Pending decision data preserves task link/context, agent or request type, age, body or preview content, and status needed by the UI. | `usePendingDRs` preserves `count` and `items` (`serve/cockpit/web/src/hooks/usePendingDRs.ts:22-23,49`); `Shell` passes pending decision items to the indicator (`serve/cockpit/web/src/Shell.tsx:22,164`); `DRStatusIndicator` derives UI status from `count` (`serve/cockpit/web/src/components/DRStatusIndicator.tsx:21,28`) and has an empty-state message (`serve/cockpit/web/src/components/DRStatusIndicator.tsx:39`). Backend/API docs define item fields as `{id, task_id, agent, request_type, created, title, body, body_preview}` rather than an item-level `status` field (`serve/cockpit/README.md:73`). | `serve/cockpit/web/src/__tests__/DecisionContract_1386_hook.test.ts:94`; `serve/cockpit/web/src/__tests__/DRStatusIndicator_1191.test.tsx:90,96,102`; `serve/cockpit/web/src/__tests__/usePendingDRs_1191.test.ts:183,190`; quality-runner green on all three suites | PASS |
| Successful resolution refetches pending decisions and affected task or board state after backend lifecycle side effects from #1385. | `Shell` onResolved handler calls both `void refetchPendingDRs()` and `refetchTasks()` (`serve/cockpit/web/src/Shell.tsx:261-262`). | `serve/cockpit/web/src/__tests__/DecisionContract_1386.test.tsx:259,279`; quality-runner 12/12 green | PASS |
| Loading, empty, and expected error states consume the frontend error contract from #1375. | `usePendingDRs` exposes `isLoading` and computes it from fetch state (`serve/cockpit/web/src/hooks/usePendingDRs.ts:24,73`); empty/error states reset `items` and `count` (`serve/cockpit/web/src/hooks/usePendingDRs.ts:49,57`); `usePollingFetch` and `ResolveModal` both use `getResponseErrorMessage` (`serve/cockpit/web/src/hooks/usePollingFetch.ts:69`; `serve/cockpit/web/src/components/ResolveModal.tsx:45`); `Shell` renders `pendingDRError.message` (`serve/cockpit/web/src/Shell.tsx:168-169`). | `serve/cockpit/web/src/__tests__/DecisionContract_1386_hook.test.ts:130,160`; `serve/cockpit/web/src/__tests__/DecisionContract_1386.test.tsx:419,439`; `serve/cockpit/web/src/__tests__/usePendingDRs_1191.test.ts:129,136,142,183,190`; `serve/cockpit/web/src/__tests__/DRStatusIndicator_1191.test.tsx:102`; all green in quality-runner | PASS |
| The implementation satisfies #1386 without building the visible viewport redesign owned by #1389. | Archived counterpart task lookup confirms `#1386` is complete; all 12 decision-contract tests pass green against the current codebase with no new viewport-only implementation. The live sources in scope remain `usePendingDRs.ts`, `Shell.tsx`, `ResolveModal.tsx`, and `DRStatusIndicator.tsx`, consistent with the non-redesign scope. | quality-runner scoped pass on `DecisionContract_1386.test.tsx` + `DecisionContract_1386_hook.test.ts` (12 passed, 0 failed); archived task lookup via kanban list | PASS |

### Test Integrity / Quality
- No evidence of weakened task-owned assertions in the current review scope.
- The executable assertions are discriminating: exact `body` field checks, exact error-message checks, exact `refetchTasks()`/`refetchPendingDRs()` call expectations, and exact dormant/attention indicator behavior.
- Informational only: some stale comments in `DecisionContract_1386.test.tsx` still describe these cases as failing until `#1387`; the comments are outdated, but the assertions themselves are strong and pass against the live code.

### Findings
- No blocking findings.
- This task is a genuine no-op at review time: the contract was already satisfied before the builder pass-through.
- AC2 wording about "status needed by the UI" is satisfied by the existing `count` -> indicator-status flow, not by an item-level `status` field. Current backend/frontend/docs all agree on the item shape without `status`, so this was treated as wording drift rather than an implementation miss.

### Deductions
- -0.02: stale AC/comment wording required source-level interpretation against the live backend/frontend contract.
- -0.01: no builder commit hash in the task body, so TestFromAC immutability could not be proven from diff history during this review.

### Verdict
- PASS. Confidence: 0.95.
- Action: advance to `docs`. Current code already satisfies the implementation contract; no builder retry is needed.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No-op task — builder made zero code changes; no behavior, API, CLI, or config change occurred. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | Research used codebase-only verification (test execution + source inspection); no external repos, articles, or docs were relied upon. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1387-decision-data-contract-noop.md` exists, is linked from the task body ("Research doc: .owlbear/research/1387-decision-data-contract-noop.md"), and contains no follow-up tasks (correct — research confirmed none needed). |
| 5 | Diagram maintenance (describes match) | No | N/A | Doc-index loaded; no diagram `describes` glob covers the reviewed frontend files (`usePendingDRs.ts`, `Shell.tsx`, `ResolveModal.tsx`, `DRStatusIndicator.tsx`). |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/hooks/usePendingDRs.ts` | OUT | No change (verified, no builder edit) |
| `serve/cockpit/web/src/components/ResolveModal.tsx` | OUT | No change |
| `serve/cockpit/web/src/Shell.tsx` | OUT | No change |
| `serve/cockpit/web/src/components/DRStatusIndicator.tsx` | OUT | No change |
| `.owlbear/research/1387-decision-data-contract-noop.md` | IN | Verified (exists, linked, no follow-ups needed) |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1387-*` scratch files existed)
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Pending decision frontend types include full body | PendingDR.body: string at usePendingDRs.ts:13 (spot-checked) | PASS |
| Pending decision data preserves task link/context/age/body/status | Reviewer mapped all fields; existing hook/component structure confirmed | PASS |
| Resolution refetches pending decisions and affected task/board state | Shell.tsx:260-262 calls refetchPendingDRs() and refetchTasks() (spot-checked) | PASS |
| Loading/empty/error states consume frontend error contract | Reviewer cites getResponseErrorMessage imports in ResolveModal.tsx:45, usePollingFetch.ts:69; accepted | PASS |
| Satisfies 1386 without viewport redesign | Vitest 1109/0, DecisionContract 1386 tests pass green | PASS |

### Test Results
- pytest: 2977 passed, 178 failed, 4 skipped (all failures pre-existing background debt, none in task scope; no-op task made zero code changes)
- vitest: 1109 passed, 0 failed (includes task-owned DecisionContract 1386 suites)
- ruff: 29 violations (pre-existing, no code touched)
- eslint: 4 problems (pre-existing)

### Architect Quality: 3/5
AC lines were specific and verifiable, which enabled the successful premise challenge. However, all 3 problem-evidence items were stale (described behavior already present), causing unnecessary pipeline work (research, second arch review, multiple pass-throughs). Upstream task scoping should verify current state before drafting.

### Deduction Breakdown
- Start: 1.00
- AC quality score 3 (le 3): -.03
- No AC evidence gaps (all 5 verified with file-line evidence)
- No task-scope test failures (178 pytest failures are pre-existing background debt)
- No lint violations attributable to task (no-op)
- Reviewer evidence section present and detailed (PASS verdict, 0.95 confidence)
- Research doc committed (2485828a)

### Confidence: .97
### Action: archive

### Commits Verified
- 2485828a docs: research decision data contract no-op (1387, researcher)
- No source code commits expected (no-op task)