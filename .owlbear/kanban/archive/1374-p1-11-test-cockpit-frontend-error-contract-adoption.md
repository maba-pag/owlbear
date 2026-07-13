---
id: 1374
title: 'P1-11: Test Cockpit frontend error-contract adoption'
status: archived
priority: medium
created: 2026-05-06T00:58:52.272079+00:00
updated: 2026-05-07T21:31:06.033198+00:00
tags:
- cockpit
- audit-remediation
- phase-1
- scope:cockpit-web
- type:test
- frontend
- interface-contract
- error-handling
parent: 1363
depends_on:
- 1367
- 1371
- 1373
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Purpose
Write frontend tests for consistent Cockpit error-envelope parsing and recoverable error rendering across API flows.

## Problem Evidence
- Hooks and components handle errors inconsistently; some failures become empty state or no-op.
- DetailTab handles 409, 404, and 422 specially but not the broader backend contract.
- Health, decision request, task fetch, mutation, and repair errors are displayed inconsistently.

## Acceptance Criteria
- Tests prove frontend API calls extract and render human-readable error messages from backend error responses across both `{code, message}` (domain errors) and `{detail}` (HTTPException) response shapes. (td:2)
- Tests cover representative error rendering and retry/refetch paths for: detail mutations, board moves, health scan, decision request polling/resolution, repair, and task fetch flows. For task fetch, tests assert an error indicator replaces the blank detail pane on failure. (td:2)
- Tests prove no expected backend error becomes a silent no-op or false empty state. (td:2)
- Tests coexist with `Shell_1372.test.tsx` and preserve the health false-OK protection from #1373 while covering the broader error contract. (td:1)
- Tests fail against current inconsistent handling (RED phase): generic status-only error text where `message` should appear, blank detail pane on task-fetch failure, hardcoded error copy in ResolveModal. Suitable for #1375 to satisfy. (td:1)

## Scope
- In scope: Cockpit frontend error parsing and user-visible recoverable error-state tests.
- Out of scope: backend envelope implementation, PDS build/runtime fixes, dashboard redesign, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1375.

[[2026-05-07]]


## Architecture Review

### Context
Reviewed backend error envelope contract in `main.py` (`_error_envelope`, `handle_kanban_error`, `handle_unexpected_error`), decisions route (`decisions.py` — mixed HTTPException + ConcurrencyError), all frontend hooks (`usePollingFetch`, `useBoard`, `useScanPolling`, `useRepairFlow`, `usePendingDRs`), components (`DetailTab`, `ResolveModal`, `Shell`, `HealthBadge`), and existing test suites (`Shell_1372.test.tsx`, `usePollingFetch_1227.test.ts`, etc.).

### Backend Error Shapes (builder reference)
The backend emits TWO error response shapes:
- **Domain errors** (KanbanError subclasses: NotFoundError, ConcurrencyError, ValidationError, ConfigError): `{code: string, message: string}` — handled by `handle_kanban_error` in `main.py`.
- **FastAPI HTTPException** (used in `decisions.py` for 422 "Invalid decision id", 404 "not found"): `{detail: string}` — FastAPI's default handler.
- **Unexpected errors**: `{code: "COCKPIT_INTERNAL_ERROR", message: "An unexpected error occurred."}`.

Tests must mock both shapes depending on the flow being tested.

### Current Frontend Inconsistencies (RED phase targets)
1. `usePollingFetch` throws `Error('Polling request failed with status ${status}')` — never reads response body.
2. `DetailTab.runMutation` reads `{detail}` for 422, ignores body for other errors.
3. `ResolveModal` hardcodes `'Failed to resolve decision request.'` — never reads response body.
4. `repairStorage` throws status-only error — never reads response body.
5. `Shell` task-fetch path sets `selectedTask = null` on error → blank detail pane, no error indicator.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Frontend error-contract tests only |
| Interface clarity | PASS | After AC refinement — envelope shapes cited, failing symptoms named |
| Dependency correctness | PASS | #1367, #1371, #1373 all archived/done |
| Module layering | PASS | Frontend tests, no backend code changes |
| TDD compliance | PASS | This IS the RED phase; implementation is #1375 |
| KISS/YAGNI | PASS | Tests existing flows, no hypothetical features |
| Premise challenge | PASS | Audit evidence confirms inconsistent error handling |
| Pattern consistency | PASS | Follows Shell_1372.test.tsx integration test pattern |
| Security surface | N/A | Test-only task |
| Single domain | PASS | Cockpit frontend only |

### Challenge Results
- Challenger confidence: 0.43, recommended BLOCK
- Critical findings: (1) decisions route uses mixed error shapes, (2) task-fetch has no defined error UX
- Architect response: Both findings are valid AC refinement issues, not blockers. (1) AC1 refined to acknowledge both `{code,message}` and `{detail}` shapes. (2) AC2 refined to define error indicator for task-fetch failure. (3) AC5 refined with concrete failing symptoms. The task scope is TDD RED — defining expected behavior that doesn't exist yet is the point.
- Override rationale: Challenger's "block" was based on incomplete contract knowledge (treating HTTPException paths as bugs rather than a second envelope shape) and treating undefined task-fetch UX as a missing prerequisite rather than a RED-phase target.

### Test Depth
- AC1: td:2 (multiple hooks × both error shapes)
- AC2: td:2 (7 flows × error rendering + retry)
- AC3: td:2 (negative assertions across flows)
- AC4: td:1 (coexistence verification)
- AC5: td:1 (RED phase confirmation)

### Verdict: APPROVE

[[2026-05-07]]
Architecture review complete. Refined all 5 AC lines with test-depth annotations and challenger-driven improvements: (1) AC1 now cites both `{code,message}` and `{detail}` error shapes; (2) AC2 specifies error indicator for task-fetch failure; (3) AC5 names concrete RED-phase failing symptoms. Challenger override: mixed error shapes and undefined task-fetch UX are AC refinement issues, not blockers — the TDD RED phase is precisely for defining expected behavior. All criteria PASS.
[[2026-05-07]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx
- Classes: TestFromAC_ErrorEnvelopeParsing, TestFromAC_ErrorRenderingAndRetry, TestFromAC_NoSilentErrors, TestFromAC_FalseOKCoexistence
- Tests per category: happy 9 (envelope parsing), error 7 (rendering/silent), edge 3 (retry/coexistence)
- Total: 19 tests, all FAIL
- ESLint: clean

### AC Coverage

| AC | Tests | Coverage |
|----|-------|----------|
| AC1 (td:2) — both shapes extracted across flows | tests 1–9 | usePollingFetch × 2, repairStorage × 2, DetailTab × 3, ResolveModal × 2 |
| AC2 (td:2) — error rendering + retry paths | tests 10–14 | scan message, task-fetch indicator, retry button, DR polling, move-backward |
| AC3 (td:2) — no silent no-ops | tests 15–18 | task-fetch 404, network exception, ResolveModal non-generic, DetailTab swallow |
| AC4 (td:1) — coexistence + false-OK preserved | test 19 | combined scan false-OK + body-message extraction |
| AC5 (td:1) — RED phase confirmed | all 19 fail | confirmed by quality run |

### Failure Modes
- Tests 1–4, 7–10, 17, 19: AssertionError — status-only strings returned instead of response body text
- Tests 5, 6, 11, 12, 14–16, 18: waitFor timeout — UI error elements never rendered (errors silently swallowed)
- Test 13: immediate AssertionError — Shell ignores usePendingDRs().error, dr-polling-error element absent
[[2026-05-07]]
## Builder Notes
- Implementation: `serve/cockpit/web/src/api/errorMessage.ts`, `serve/cockpit/web/src/hooks/usePollingFetch.ts`, `serve/cockpit/web/src/api/repair.ts`, `serve/cockpit/web/src/components/DetailTab.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, `serve/cockpit/web/src/Shell.tsx`.
- Tests: 48 passed, 0 failed, 0 skipped (scoped vitest: `ErrorContract_1374`, `Shell_1372`, `ResolveModal_1193`).
- Coverage: N/A in scoped quality-runner mode (not requested by this frontend verification profile).
- Ruff/ESLint: clean (eslint violations: 0).
- Evidence summary: frontend now extracts backend errors from both `{code,message}` and `{detail}` envelopes while preserving legacy status fallback strings; Shell now surfaces task-fetch and DR polling failures with visible indicators and retry path.
- Fixes applied:
  - Added shared response parser in `errorMessage.ts`.
  - Updated polling and repair flows to throw body-derived messages.
  - Updated `DetailTab` mutation errors to render validation text for 422 and other non-ok responses.
  - Updated `ResolveModal` to render response-derived error text.
  - Updated `Shell` to show `task-fetch-error`, `task-fetch-retry`, and `dr-polling-error` states.

### Post-task Reflection
- Problem faced: response mocks in tests did not implement `response.clone()`, causing body parsing to silently fall back to status-only text.
- Workaround applied: switched parser to `response.json()` with guarded fallback.
- Pattern discovered: compatibility with legacy tests required preserving status fallback text even when body message exists.
- Quality gap avoided: scoped coexistence run against `Shell_1372` and `ResolveModal_1193` caught cross-suite regression before release.
- Time sink: extracting precise failing assertions required direct vitest log inspection because one quality summary omitted mismatch details.

Committed: `1bd3c3da` (`fix: adopt frontend error contract parsing and rendering (#1374, builder)`).
[[2026-05-07]]
## Review Evidence

### Test Results
- quality-runner scoped frontend run: 48 passed, 0 failed, 0 skipped across serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx, serve/cockpit/web/src/__tests__/Shell_1372.test.tsx, and serve/cockpit/web/src/__tests__/ResolveModal_1193.test.tsx.
- Adjacent regression run for decision refetch behavior: serve/cockpit/web/src/__tests__/Shell_1263.test.tsx passed 5 tests with 0 failures.

### Lint Results
- ESLint clean for the changed frontend source files and the scoped test files.

### Coverage
- Scoped frontend coverage: overall 71.25%.
- Changed modules reported by quality-runner: src/api/errorMessage.ts 93.75%, src/hooks/usePollingFetch.ts 90.76%, src/api/repair.ts 43.75%, src/components/DetailTab.tsx 76.2%, src/components/ResolveModal.tsx 93.63%, src/Shell.tsx 85%.
- Module percentages below 90 are not the blocking issue here; the rejection is about missing executable proof for one changed retry path.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: frontend API calls extract and render human-readable error messages from both {code,message} and {detail} responses | serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx:271, 292, 318, 327, 341, 357, 375, 396, 416 plus live handlers at serve/cockpit/web/src/api/errorMessage.ts:20, serve/cockpit/web/src/hooks/usePollingFetch.ts:69, serve/cockpit/web/src/api/repair.ts:15, serve/cockpit/web/src/components/DetailTab.tsx:132, serve/cockpit/web/src/components/ResolveModal.tsx:47 prove both response shapes are extracted on the scoped frontend error paths. | PASS |
| AC2: representative error rendering and retry/refetch coverage for detail mutations, board moves, health scan, decision request polling/resolution, repair, and task fetch | serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx:491-503 proves only that task-fetch-retry is rendered. No test clicks that control or proves a second /api/tasks/{id} fetch after the handler in serve/cockpit/web/src/Shell.tsx:201-203. Other retry/refetch paths are covered elsewhere: serve/cockpit/web/src/__tests__/Shell_1372.test.tsx scoped green for scan retry, serve/cockpit/web/src/__tests__/Shell_1263.test.tsx scoped green for lastDecisionsMtime refetch, and serve/cockpit/web/src/__tests__/ResolveModal_1193.test.tsx scoped green for decision resolution submission. | FAIL |
| AC3: no expected backend error becomes a silent no-op or false empty state | serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx:514, 554, 578, 603, 627 plus serve/cockpit/web/src/__tests__/Shell_1372.test.tsx:300 show visible error states replacing false-empty or false-OK behavior. | PASS |
| AC4: tests coexist with Shell_1372 and preserve the false-OK protection from #1373 | serve/cockpit/web/src/__tests__/Shell_1372.test.tsx:300 and :503 remain green in the scoped run, and serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx:656 adds the broader error-contract assertion without regressing the existing health guard. | PASS |
| AC5: tests fail against the pre-fix inconsistent handling and are suitable for #1375-style implementation to satisfy | Test-writer notes recorded 19 failing RED tests before implementation, and the current assertions at serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx:446, 554, and 603 remain discriminating for the named pre-fix failures. | PASS |

### Deductions
- Missing executable proof for the task-fetch retry path required by AC2.
- Dirty-tree contamination check could not be executed in this tool surface; commit existence was confirmed via .git/logs grep for 1bd3c3da, but git status overlap remains unverified.
- Test immutability review is source-level only; no commit diff was available to prove the builder left TestFromAC assertions untouched.

### Verdict
- FAIL. Confidence 0.85.
- Route to todo. The implementation appears correct, but the task-owned evidence does not yet prove the task-fetch retry behavior required by AC2.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | test-writer | Add an executable task-fetch retry test that clicks task-fetch-retry and proves a second task fetch is issued after an error while the error-indicator behavior remains intact | serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx | AC2 gap: serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx:491-503 only checks button presence; serve/cockpit/web/src/Shell.tsx:201-203 contains the unproven retry handler |
[[2026-05-07]]
## Test-Writer Notes
- Retry cycle (reviewer gap fill only).
- Test file: serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx
- New test added: `Shell task-fetch: clicking task-fetch-retry issues a second fetch and error indicator remains` — added to `TestFromAC_ErrorRenderingAndRetry`
- Test count: 1 new test (20 total, was 19)
- All new tests PASS against current code (builder already implemented retry mechanism).

### AC Coverage (gap)
| AC | New test | Evidence |
|----|----------|----------|
| AC2 — retry path proof | `task-fetch-retry clicks → second /api/tasks/42 fetch issued → error indicator intact` | fetch mock asserted ≥2 calls; error indicator visible after failing retry |

### Step 1b.1 — Direct-to-Review
All conditions met: reviewer's Required Follow-up was test-proof gap only; new test passes against current code (no implementation fix needed); lint clean.
Commit: `524a72cc` (`test: add retry tests for task-fetch retry path (#1374, test-writer)`).
Coexistence: 40/40 pass (ErrorContract_1374 + Shell_1372).

[[2026-05-07]]
## Builder Notes
- Implementation: no source edits in this cycle (verification-only pass after test-writer retry evidence update).
- Files changed: none.
- Tests: 49 passed, 0 failed, 0 skipped (scoped quality-runner: ErrorContract_1374 + Shell_1372 + ResolveModal_1193).
- Coverage (scoped): overall 73.94%; modules: src/api/errorMessage.ts 93.75%, src/hooks/usePollingFetch.ts 90.62%, src/api/repair.ts 43.75%, src/components/DetailTab.tsx 75.62%, src/components/ResolveModal.tsx 96.77%, src/Shell.tsx 83.87%.
- Lint: ESLint clean (0 violations).
- Evidence summary: AC2 retry-path proof is now executable in the task suite and passes; coexistence guard suites remain green.

### Post-task Reflection
- Problem faced: prior review failure was evidence-only (missing executable click/retry proof), not an implementation defect.
- Workaround applied: used a focused quality-runner gate that includes the new AC2 retry-proof suite and adjacent coexistence suites.
- Pattern discovered: test-only retry cycles should be treated as verification-first builder passes when implementation already satisfies behavior.
- Quality gap avoided: revalidating coexistence suites in the same run prevented false-green on contract-only fixes.
[[2026-05-07]]
## Review Evidence

### Test Results
- quality-runner primary scoped frontend pass: 54 passed, 0 failed, 0 skipped across `ErrorContract_1374.test.tsx`, `Shell_1372.test.tsx`, `ResolveModal_1193.test.tsx`, and `Shell_1263.test.tsx`.
- quality-runner adjacent proof pass: 73 passed, 0 failed, 0 skipped across `Shell_1194.test.tsx`, `HealthBadgeRepair_1168.test.tsx`, `useRepairFlow_1165.test.ts`, and `repairStorage_1164.test.ts`.
- VS Code diagnostics: no editor errors on the changed frontend source files or the task suite.

### Lint Results
- ESLint clean on both scoped passes: 0 active errors, 0 active warnings.

### Coverage
- Primary scoped coverage captured the changed error-contract modules: `errorMessage.ts` 93.75%, `usePollingFetch.ts` 90.76%, `ResolveModal.tsx` 93.63%, `Shell.tsx` 87.77%; lower module-level percentages on `repair.ts` and `DetailTab.tsx` were resolved by adjacent green proof on the changed paths rather than treated as blocking whole-module debt.
- Adjacent proof coverage captured the refetch/callback chain: `useRepairFlow.ts` 100%, `repair.ts` 93.75%, `HealthBadge.tsx` 92%, `Shell.tsx` 72.22% statements / 69.48% branches within that narrowed proof surface.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1: frontend API calls extract and render human-readable error messages from both `{code,message}` and `{detail}` responses | `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L257-L429` exercises the live parsing sites in `serve/cockpit/web/src/api/errorMessage.ts#L1-L29`, `serve/cockpit/web/src/hooks/usePollingFetch.ts#L69-L84`, `serve/cockpit/web/src/api/repair.ts#L11-L23`, `serve/cockpit/web/src/components/DetailTab.tsx#L100-L136`, and `serve/cockpit/web/src/components/ResolveModal.tsx#L35-L58`. | PASS |
| AC2: representative error rendering and retry/refetch paths for detail mutations, board moves, health scan, decision request polling/resolution, repair, and task fetch | Task-local proof: `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L470-L554` and `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L575-L585`. Adjacent green proof: `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx#L421-L432`, `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx#L503-L521`, `serve/cockpit/web/src/__tests__/Shell_1194.test.tsx#L208-L226`, `serve/cockpit/web/src/__tests__/Shell_1263.test.tsx#L126-L242`, `serve/cockpit/web/src/__tests__/useRepairFlow_1165.test.ts#L355-L372`, and `serve/cockpit/web/src/__tests__/HealthBadgeRepair_1168.test.tsx#L194-L223`, `serve/cockpit/web/src/__tests__/HealthBadgeRepair_1168.test.tsx#L285-L301`. The previously rejected task-fetch retry proof is now explicit at `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L513-L554`. | PASS |
| AC3: no expected backend error becomes a silent no-op or false empty state | `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L596-L686` proves task-fetch and mutation errors surface visible UI instead of blank/false-empty states. | PASS |
| AC4: tests coexist with `Shell_1372.test.tsx` and preserve the health false-OK protection from #1373 | `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L694-L727` remains green alongside retained false-OK guards at `serve/cockpit/web/src/__tests__/Shell_1372.test.tsx#L300-L305`. | PASS |
| AC5: tests fail against the pre-fix inconsistent handling and remain suitable for #1375-style implementation to satisfy | Task history records the original 19-test RED run; the current discriminating assertions still pin the named former failures in `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L288-L332`, `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L384-L429`, `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L470-L554`, and `serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx#L651-L664`. | PASS |

### Deductions
- Dirty-tree contamination could not be checked directly in this tool surface; confidence reduced slightly because `git status --porcelain` overlap was unavailable.
- Commit presence for the builder and retry-cycle test-writer work was confirmed via `.git/logs` grep (`1bd3c3da`, `524a72cc`), but no commit diff was available for a strict before/after TestFromAC immutability comparison.
- AC2 proof is distributed across the task-local suite and adjacent frontend suites, which increases review coordination cost but not defect risk now that both scoped quality runs are green.

### Verdict
- PASS. Confidence 0.94.
- Action: advance to docs.

### Post-task Reflection
- Initial task-local review still looked short on AC2 because the repair-success and decision-resolution refetch proof lived in adjacent suites, not only in `ErrorContract_1374.test.tsx`.
- A second scoped quality pass on those adjacent suites resolved the ambiguity without inventing any new requirement beyond the AC.
- The main remaining confidence limiter in this tool surface is lack of direct `git status` / commit-diff access, not code or test quality.
[[2026-05-07]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are TypeScript/TSX source and test files — no IN-scope README or prose doc references these internal hook/component implementation details |
| 2 | Module docstrings | No | N/A | No Python files modified in this task |
| 3 | External attribution | No | N/A | No external patterns or sources cited in builder/test-writer notes |
| 4 | Research doc | No | N/A | No research doc produced or referenced in this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches all changed files; footer updated from `6143c689` → `87047d0e` (commit `127f4af6`) |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted in this task |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/api/errorMessage.ts | OUT | N/A (TS source) |
| serve/cockpit/web/src/hooks/usePollingFetch.ts | OUT | N/A (TS source) |
| serve/cockpit/web/src/api/repair.ts | OUT | N/A (TS source) |
| serve/cockpit/web/src/components/DetailTab.tsx | OUT | N/A (TSX source) |
| serve/cockpit/web/src/components/ResolveModal.tsx | OUT | N/A (TSX source) |
| serve/cockpit/web/src/Shell.tsx | OUT | N/A (TSX source) |
| serve/cockpit/web/src/__tests__/ErrorContract_1374.test.tsx | OUT | N/A (test file) |
| share/diagrams/cockpit.excalidraw | IN | Updated footer (diagram describes-match) |

### Files Updated
- share/diagrams/cockpit.excalidraw (footer: `Last verified: 2026-05-07 (87047d0e)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files found for task 1374)
[[2026-05-07]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 (td:2): extract/render from both `{code,message}` and `{detail}` shapes | ErrorContract_1374.test.tsx L257-L429 exercises parsing sites in errorMessage.ts, usePollingFetch.ts, repair.ts, DetailTab.tsx, ResolveModal.tsx; 9 tests cover both envelope shapes across flows | PASS |
| AC2 (td:2): error rendering + retry/refetch for 7 flows | ErrorContract_1374.test.tsx L470-L554 (task-fetch retry proof at L513-L554 added in retry cycle); adjacent green proof in Shell_1372, Shell_1263, Shell_1194, useRepairFlow_1165, HealthBadgeRepair_1168 suites | PASS |
| AC3 (td:2): no silent no-ops or false empty state | ErrorContract_1374.test.tsx L596-L686 proves visible error states replace blank/false-empty behavior | PASS |
| AC4 (td:1): coexistence + false-OK preserved | ErrorContract_1374.test.tsx L694-L727 green alongside Shell_1372.test.tsx L300-L305 false-OK guards | PASS |
| AC5 (td:1): RED phase confirmed | Task history records 19 failing tests before implementation; discriminating assertions remain at L288-L332, L384-L429, L470-L554, L651-L664 | PASS |

### Test Results
- vitest (full frontend): 1032 passed, 0 failed — cross-task regression CLEAN
- pytest (full backend): 219 failures — all pre-existing background debt (engine accessor migration, decisions import, MCP memory/kanban, PDS compat timeouts); 0 failures in task scope
- ESLint: 0 violations in task-scoped files (4 pre-existing in unrelated files)
- ruff: 0 violations in task scope (12 pre-existing warnings in unrelated modules)

### Architect Quality: 4/5
AC lines are specific with td annotations, both error shapes explicitly named, RED-phase failing symptoms enumerated. Minor gap: initial AC2 lacked specificity on task-fetch error UX, refined during arch review based on challenger findings. Strong overall.

### Deduction Breakdown
- AC lines with no evidence: 0 (5/5 PASS) → -.00
- Lint violations in scope: 0 → -.00
- AC quality ≤ 3: no (4/5) → -.00
- Missing reviewer evidence: no (present, detailed, two passes) → -.00
- Full-suite failures in task scope: 0 → -.00
- Commit-diff immutability: reviewer verified at source level; no commit diff available for strict before/after comparison → -.02

### Confidence: 0.98
### Action: archive

### Commits Verified
| Commit | Type | Attribution |
|--------|------|-------------|
| abd43e5a | test (RED) | #1374, test-writer |
| 1bd3c3da | fix (GREEN) | #1374, builder |
| 524a72cc | test (retry) | #1374, test-writer |
| 127f4af6 | docs (diagram) | #1374, doc-writer |