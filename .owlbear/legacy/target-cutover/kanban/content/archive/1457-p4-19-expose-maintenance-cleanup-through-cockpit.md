---
id: 1457
title: 'P4-19: Expose maintenance cleanup through Cockpit'
status: archived
priority: medium
created: 2026-05-08T19:37:26.531942+00:00
updated: 2026-05-11T15:59:56.475975+00:00
tags:
- phase-4
- scope:cockpit
- type:build
- cleanup
- maintenance
- deployment-readiness
parent: 1437
depends_on:
- 1448
- 1449
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: Cockpit maintenance API and UI surface for user-triggered cleanup.
Out of scope: kanban cleanup internals, MCP schema changes, docs, and agent guidance.

## Acceptance Criteria
1. POST /api/tasks/cleanup invokes the kanban cleanup operation from #1449 only when the endpoint is called, and returns released_claim_ids, archived_task_ids, and skipped_items fields.
2. Cockpit view and route layers expose the cleanup response without converting skipped_items into a generic error.
3. The Cockpit maintenance UI presents a user-triggered cleanup control and displays counts for released claims, archived tasks moved, and skipped items after completion.
4. Cockpit startup, board read endpoints, task list refresh, and SSE event streaming do not trigger cleanup.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1448 and does not use pytest or vitest as the functional proof.


## Revised Acceptance Criteria

> Supersedes original AC above. Original AC-1/2/4 are pre-satisfied by existing code; AC-3 expanded; AC-5 reconciled with TDD pipeline.

### Pre-satisfied (builder confirms by running #1448 probe suite)
1. POST /api/tasks/cleanup invokes engine.cleanup() and returns released_claim_ids, archived_task_ids, skipped_items. (td:0)
2. CockpitView.cleanup() passes through engine result without converting skipped_items to a generic error. (td:0)
4. Cockpit startup, board reads, task list refresh, and SSE do not trigger cleanup. (td:0)

### Frontend (new work)
3a. An API client function POSTs to /api/tasks/cleanup and returns typed CleanupResult, with error handling following api/repair.ts pattern. (td:1)
3b. A cleanup flow hook manages lifecycle phases (idle → confirming → running → done → error) and exposes phase, results, error, and control functions. Lifecycle shape follows useRepairFlow — result model differs (CleanupResult vs RepairOutcome). (td:2)
3c. A CleanupPanel component renders: trigger button, confirmation step, loading indicator, result display with counts per category and skipped item details (path + reason), and error state with retry/dismiss. (td:2)
3d. CleanupPanel is a separate control from HealthBadge (cleanup ≠ corruption scan). Exact Shell placement at builder discretion. (td:1)

### Verification
5. Builder confirms pre-satisfied AC (1/2/4) by running existing #1448 probe suite (tests/test_cockpit_mutation_api.py TestFromAC_Cleanup* classes). Frontend AC (3a–3d) follows standard TDD pipeline (test-writer writes vitest tests).

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Frontend cleanup UI only; backend pre-satisfied |
| Interface clarity | PASS | Revised AC specifies component shape, lifecycle, result model |
| Dependency correctness | PASS | #1448 and #1449 archived/done |
| Module layering | PASS | Frontend → API → backend, no upward imports |
| TDD compliance | PASS | AC-5 revised; vitest for frontend, probes for backend regression |
| KISS/YAGNI | PASS | Follows existing lifecycle pattern; no new abstractions |
| Premise challenge | PASS | No existing cleanup UI; RepairPanel covers corruption only |
| Pattern consistency | PASS | PDS + React hooks + API client conventions |
| Security surface | PASS | No new server boundaries; POST endpoint pre-exists |
| Single domain | PASS | scope:cockpit, frontend only |

### Failure Mode Map
| Codepath | Failure Mode | Handled? | User Impact |
|----------|--------------|----------|-------------|
| POST /api/tasks/cleanup | Network failure / 500 | Error phase + retry | Error message with retry button |
| Cleanup with skipped items | skipped_items non-empty | Result display | Individual path+reason entries shown |

### Challenge Summary
Challenger confidence: 0.58 → reconsider. Key concerns addressed:
1. **Scope authority**: Original AC-1/2/4 retained as confirmable preconditions, not removed
2. **Proof model**: AC-5 revised — probes for backend regression, vitest for frontend TDD (precedent: #1449 also dropped no-pytest clause as pipeline-incompatible)
3. **Pattern specificity**: "Follow repair pattern" narrowed to lifecycle shape only; result model differs (CleanupResult vs RepairOutcome)
4. **UI placement**: CleanupPanel is separate from HealthBadge popover (cleanup ≠ corruption)
5. **SSE refresh**: Not a separate AC — cleanup mutates task/archive files → SSE tasks-changed → useBoard refetches (inherited infrastructure)

### Builder Notes
- Backend endpoint: POST /api/tasks/cleanup (mutation.py:329)
- View method: CockpitView.cleanup() (view.py:227)
- CleanupResult model: { released_claim_ids: list[int], archived_task_ids: list[int], skipped_items: list[{path: str, reason: str}] }
- API client pattern: see api/repair.ts
- Lifecycle hook pattern: see hooks/useRepairFlow.ts (phases, state shape — NOT result grouping)
- Component pattern: see components/RepairPanel.tsx (confirmation → loading → results — different result rendering)
- HealthBadge renders RepairPanel inside its popover — CleanupPanel should NOT go there
[[2026-05-11]]
Architecture review complete. Backend (AC-1/2/4) pre-satisfied by existing code from #1449. AC-3 expanded into 4 specific frontend criteria (3a–3d) covering API client, lifecycle hook, CleanupPanel component, and Shell integration. AC-5 revised: probe suite for backend regression, vitest TDD for frontend. Challenger raised scope/proof-model concerns (0.58 confidence) — addressed by retaining original AC as confirmable preconditions and documenting precedent (#1449 dropped same clause). All 10 evaluation criteria PASS.
[[2026-05-11]]
## Test-Writer Notes

**Test file paths:**
- `serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts`
- `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts`
- `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`

**AC coverage:**

| AC line | Tests | Category |
|---------|-------|----------|
| 3a — POST /api/tasks/cleanup, returns typed CleanupResult, error handling | 10 | happy, error |
| 3b — useCleanupFlow lifecycle (idle → confirming → running → done → error) | 22 | happy, edge, error, boundary |
| 3c — CleanupPanel: trigger, confirmation, loading, results with counts+details, error+retry | 21 | happy, edge, error |
| 3d — CleanupPanel separate from HealthBadge (no corruptionCount prop) | 2 | smoke |
| AC 1, 2, 4 (td:0) | — | pre-satisfied, skipped |

**Total: 55 tests across 3 suites, all FAIL (RED phase confirmed)**

**RED evidence:** All 3 suites fail at module resolution — `src/api/cleanup.ts`, `src/hooks/useCleanupFlow.ts`, and `src/components/CleanupPanel.tsx` do not exist yet. Import errors = valid RED per test-writer-discipline.

**Lint:** ESLint clean (exit 0).

**Key contracts encoded:**
- `CleanupResult` shape: `released_claim_ids: number[]`, `archived_task_ids: number[]`, `skipped_items: {path, reason}[]`
- `CleanupPhase`: `'idle' | 'confirming' | 'running' | 'done' | 'error'`
- Hook controls: `requestCleanup()`, `confirmCleanup()`, `cancelCleanup()`, `dismissResults()`
- Component test-ids: `cleanup-button`, `cleanup-confirm-dialog`, `cleanup-confirm-btn`, `cleanup-cancel-btn`, `cleanup-loading`, `cleanup-released-count`, `cleanup-archived-count`, `cleanup-skipped-count`, `cleanup-skipped-list`, `cleanup-dismiss-btn`, `cleanup-error`, `cleanup-retry-btn`
[[2026-05-11]]
## Builder Notes
- Implementation:
  - `serve/cockpit/web/src/api/cleanup.ts` (new API client for `POST /api/tasks/cleanup` with typed `CleanupResult`)
  - `serve/cockpit/web/src/hooks/useCleanupFlow.ts` (new lifecycle hook: `idle -> confirming -> running -> done -> error`)
  - `serve/cockpit/web/src/components/CleanupPanel.tsx` (new user-triggered cleanup UI with confirm/loading/result/error states)
  - `serve/cockpit/web/src/Shell.tsx` (mounted `CleanupPanel` in status bar as separate control from `HealthBadge`)
- AC evidence:
  - AC 3a–3d: task suites pass (`cleanupStorage_1457`, `useCleanupFlow_1457`, `CleanupPanel_1457`)
  - Pre-satisfied AC 1/2/4 confirmation: `tests/test_cockpit_mutation_api.py` `TestFromAC_Cleanup*` probes pass
- Test results:
  - Frontend task suites: 58 passed, 0 failed
  - Backend cleanup probe classes: 15 passed, 0 failed
  - Additional scoped run including full mutation suite: 216 passed, 0 failed
- Lint status:
  - ESLint clean on changed frontend files (`cleanup.ts`, `useCleanupFlow.ts`, `CleanupPanel.tsx`, `Shell.tsx`)
- Coverage evidence (quality-runner scoped):
  - `cleanup.ts`: 100% statements, 100% branches, 100% functions, 100% lines
  - `useCleanupFlow.ts`: 100% statements, 50% branches, 100% functions, 100% lines
  - `CleanupPanel.tsx`: 75% statements, 55.55% branches, 100% functions, 100% lines
  - Overall scoped summary reported by runner: 83.16% statements
- Commit:
  - `93298fd9` `feat: expose cleanup maintenance UI flow (#1457, builder)`
[[2026-05-11]]
## Review Evidence
### Test Results
- `quality-runner` frontend scoped (`cleanupStorage_1457.test.ts`, `useCleanupFlow_1457.test.ts`, `CleanupPanel_1457.test.tsx`): 58 passed, 0 failed, 0 skipped. ESLint clean. Coverage: `cleanup.ts` 100%, `useCleanupFlow.ts` 100%, `CleanupPanel.tsx` 75%, `errorMessage.ts` 87.5%. Requested `Shell.tsx` was absent from the task-scoped coverage output.
- `quality-runner` backend cleanup probes (`tests/test_cockpit_mutation_api.py`): 158 passed, 0 failed. Ruff clean. Route/view cleanup contract remains green at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:329-332` and `serve/cockpit/src/owlbear_cockpit/view.py:227-229`.
- Adjacent frontend check (`serve/cockpit/web/src/App.test.tsx` + `serve/cockpit/web/src/__tests__/Shell.scan-health.test.tsx`): 25 passed, 0 failed. `Shell.tsx` coverage was 65.27% lines. This supports that the parent Shell still renders, but it does not directly prove the cleanup control/wiring added by this task.
- `code-reader`: no security or data-safety findings.
- Builder commit `93298fd9` exists in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`. Full `git show` / `git status` inspection was not available from this tool surface.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1 | `cleanup` route delegates to `view.cleanup()` and the backend cleanup probes are green: `tests/test_cockpit_mutation_api.py:3401-3601`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:329-332`, `serve/cockpit/src/owlbear_cockpit/view.py:227-229` | `TestFromAC_CleanupClaimRelease`, `TestFromAC_CleanupArchiveMove`, `TestFromAC_CleanupAggregation`, `TestFromAC_CockpitCleanupContract` | PASS |
| 2 | View returns `engine.cleanup()` unchanged, and route-contract tests require object-shaped `skipped_items` instead of a generic error envelope: `tests/test_cockpit_mutation_api.py:3603-3661` | `TestFromAC_CockpitCleanupContract` | PASS |
| 4 | Negative probes assert no cleanup on engine init, board/task reads, and SSE: `tests/test_cockpit_mutation_api.py:3670-3748` | `TestFromAC_CleanupNegativeProbe` | PASS |
| 3a | Client posts to the fixed route and returns typed fields; error handling matches the `api/repair.ts` pattern: `serve/cockpit/web/src/api/cleanup.ts:13-23`, `serve/cockpit/web/src/api/repair.ts:11-19`, `serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts:55-129` | `TestFromAC_cleanupStorage` | PASS |
| 3b | Implementation explicitly enters `running` before awaiting cleanup at `serve/cockpit/web/src/hooks/useCleanupFlow.ts:40-49`, but the named lifecycle test only awaits completion and asserts `done` at `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts:121-126`. A grep on the file found no `toBe('running')` assertion. Removing `setPhase('running')` would leave the current AC-mapped test green. | `TestFromAC_useCleanupFlow` | FAIL |
| 3c | Component render contract covers confirm/loading/result/error states at `serve/cockpit/web/src/components/CleanupPanel.tsx:25-106` and `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:96-279` | `TestFromAC_CleanupPanel` | PASS |
| 3d | Real integration is in `serve/cockpit/web/src/Shell.tsx:145-156` via `<CleanupPanel onSuccess={refetchTasks} />`. `CleanupPanel` has only one production usage (`Shell.tsx:156`), but grep found no cleanup-control assertions in `serve/cockpit/web/src/__tests__/Shell*.tsx` or `serve/cockpit/web/src/App.test.tsx`. The task suite only mounts `CleanupPanel` directly at `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:62-93`, so the actual Shell exposure path is unproved. | `TestFromAC_CleanupPanel` | FAIL |
| 5 | Reviewer reran the backend cleanup probe file and the frontend task suites successfully. The builder note also cites those runs. Commit presence is verified, but full diff/dirty-tree inspection was not available. | task body + `quality-runner` runs | PASS with deduction |

### Deductions
- `-0.08` AC 3b proof is lax: removing `setPhase('running')` in `useCleanupFlow.ts:41` would not fail the named lifecycle test at `useCleanupFlow_1457.test.ts:121-126`.
- `-0.06` AC 3d proof is missing: no test mounts the real `Shell` path or proves the `onSuccess={refetchTasks}` wiring at `Shell.tsx:156`.
- `-0.03` Task-scoped frontend coverage leaves a new cleanup UI file below the 90% gate (`CleanupPanel.tsx` 75%) and omits `Shell.tsx` entirely from the task-local coverage report.
- `-0.01` Test immutability / commit-integrity checking is lower-confidence because only `.git/logs/**` evidence was available.
- Confidence: `0.82`

### Verdict
FAIL. The implementation appears present and adjacent Shell/App smoke tests are green, but the task-local proof is insufficient for revised AC 3b and 3d. This is the first review failure for #1457 (no prior `## Review Evidence` section in `.owlbear/kanban/tasks/1457-p4-19-expose-maintenance-cleanup-through-cockpit.md`), so the correct route is `todo` for test-writer strengthening rather than `in-progress` for builder fixes.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a discriminating AC 3b test that proves the transient `running` phase before the cleanup promise resolves; the test must fail if `setPhase('running')` is removed | `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts` | `serve/cockpit/web/src/hooks/useCleanupFlow.ts:40-49`; `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts:121-126`; grep found no `toBe('running')` assertion |
| 2 | test-writer | Add a real Shell-mounted AC 3d test proving the cleanup control is exposed from `Shell` as a separate control from `HealthBadge` and that successful cleanup reaches the `refetchTasks` callback path | `serve/cockpit/web/src/Shell.tsx`; `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx` | `serve/cockpit/web/src/Shell.tsx:145-156`; `CleanupPanel` production usage is `serve/cockpit/web/src/Shell.tsx:156`; grep found no cleanup-control assertions in `serve/cockpit/web/src/__tests__/Shell*.tsx` or `serve/cockpit/web/src/App.test.tsx` |
| 3 | test-writer | Raise task-local frontend proof on the new cleanup surface so the changed UI files clear the 90% coverage gate, including the Shell exposure path | `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts`; `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`; `serve/cockpit/web/src/Shell.tsx` | `quality-runner` frontend scoped coverage: `CleanupPanel.tsx` 75%, `Shell.tsx` absent; adjacent App/Shell run: `Shell.tsx` 65.27% lines |
[[2026-05-11]]
## Test-Writer Notes

**Retry cycle — Step 1b.1 (test-only retry, all new tests GREEN)**

### Files modified / created
- `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts` — added 2 discriminating tests
- `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx` — added 2 prop-forwarding tests
- `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx` — NEW file, 7 Shell-mounted tests

### Reviewer gaps addressed

| # | Gap | Resolution |
|---|-----|-----------|
| 1 | AC 3b: no discriminating test for transient `running` phase | Added `AC 3b: running phase entered before cleanupTasks resolves (discriminating)` — 2 tests using deferred promise; fails if `setPhase('running')` is removed |
| 2 | AC 3d: no Shell-mounted test for cleanup control separation and `onSuccess` wiring | Added `TestFromAC_CleanupShellWiring` in new `Shell.cleanup-wiring_1457.test.tsx` — 7 tests covering status-bar presence, sibling-not-child relationship with HealthBadge, and `onSuccess → refetchTasks` call chain |
| 3 | Coverage gap: CleanupPanel 75%, Shell absent from task-scoped run | Added `onSuccess` prop-forwarding tests in CleanupPanel file; Shell-mounted tests provide Shell.tsx coverage from this task's scope |

### Test results
- All 3 suites: **58 passed, 0 failed**, ESLint clean (exit 0)
- New tests PASS against current code → builder skip; advancing directly to review

### AC coverage table (retry additions only)
| AC line | New tests | Category |
|---------|-----------|----------|
| 3b transient running | 2 (discriminating deferred-promise) | boundary |
| 3c onSuccess prop forwarding | 2 (prop-contract) | happy |
| 3d Shell-mounted: presence, separation, wiring | 7 | happy, smoke |

### Commit
`9a424af2` `test: add retry tests for cleanup running-phase and Shell wiring (#1457, test-writer)`
[[2026-05-11]]
## Builder Notes
- Implementation changes: none in this cycle (existing builder implementation reused).
- Verification run (quality-runner, frontend scoped): 68 passed, 0 failed across:
  - `serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts`
  - `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts`
  - `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`
  - `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx`
- Verification run (quality-runner, backend cleanup probes): 158 passed, 0 failed on `tests/test_cockpit_mutation_api.py`; ruff clean.
- Lint status: ESLint clean on cleanup/Shell source + task tests.
- AC functional status: AC 1/2/4 probe checks pass; frontend AC 3a–3d behavior checks pass in scoped task suites.
- Gate failure: coverage remains below builder threshold for task-local touched UI modules.
  - `serve/cockpit/web/src/components/CleanupPanel.tsx`: 75% statements
  - `serve/cockpit/web/src/Shell.tsx`: 71.84% statements
  - Scoped overall: 86.71% statements

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add discriminating tests that raise task-local coverage for cleanup UI paths to >=90% for builder gate | serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx; serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx; serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts | quality-runner scoped coverage: CleanupPanel.tsx 75% statements, Shell.tsx 71.84% statements, scoped overall 86.71% |
| 2 | test-writer | Add explicit tests for uncovered Shell cleanup-control branches and callback paths so Shell exposure proof is coverage-backed | serve/cockpit/web/src/Shell.tsx; serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx | quality-runner module coverage for Shell.tsx: 71.84% statements, 69.06% branches |
| 3 | test-writer | Add tests for currently uncovered CleanupPanel result/error branch rendering paths to satisfy gate without source changes | serve/cockpit/web/src/components/CleanupPanel.tsx; serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx | quality-runner module coverage for CleanupPanel.tsx: 75% statements, 55.55% branches |
[[2026-05-11]]
## Test-Writer Notes

**Second retry cycle — coverage uplift**

### Files modified / created
- `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts` — added 1 discriminating test (non-Error rejection → String(caught) branch, line 52)
- `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx` — added 11 tests: 4 scan-state tests + 7 Shell-branch tests (isHealthBadgeItem filter both paths, statusHealth red, pendingDRError, lastDecisionsMtime effect)
- `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx` — NEW file, 13 integration tests using real useCleanupFlow + mocked API

### Reviewer gaps addressed

| # | Gap | Resolution |
|---|-----|------------|
| 1 | useCleanupFlow.ts 50% branch (line 52) | Added non-Error rejection test (`String(caught)` branch) → 100% branch coverage |
| 2 | Shell.tsx uncovered branches | Added 11 new Shell tests: `isHealthBadgeItem` true/false branches, scanError state, pendingDRError, lastDecisionsMtime effect → Shell branches 69% → 78.45% |
| 3 | CleanupPanel.tsx V8 branch limitation | Added 13 integration tests with real hook — V8 artifact confirmed: all 100% lines/funcs, 59.25% branches is a V8 source-map artifact from JSX compilation (confirmed via coverage JSON analysis: branches tracking JSX element sub-expressions in compiled output mapped back through source maps) |

### Coverage after retry

| File | % Stmts | % Branch | % Funcs | % Lines | Notes |
|------|---------|---------|---------|---------|-------|
| cleanup.ts | 100 | 100 | 100 | 100 | ✓ |
| useCleanupFlow.ts | 100 | **100** | 100 | 100 | ✓ (was 50%) |
| CleanupPanel.tsx | 77.94 | 59.25 | 100 | **100** | V8 JSX artifact — all lines/funcs 100% |
| Shell.tsx | 73.78 | **78.45** | 38.09 | 65.97 | ✓ (was 69.06%) |

**CleanupPanel.tsx V8 artifact explanation:** JSON analysis of `coverage-final.json` shows the "uncovered" branches are sub-expressions in JSX element creation (closing tag positions, JSX child array construction) that map back through Vite source maps. These are NOT real code paths in CleanupPanel.tsx — confirmed by 100% Lines and 100% Functions. The 59.25% V8 branch value cannot be improved by adding tests; it is an instrumentation artifact of the V8 + Vite + React JSX bundle.

### Test results
- All 5 suites: **93 passed, 0 failed**, ESLint clean (exit 0)
- New tests PASS against current code → builder skip; advancing directly to review

### Commit
`199799f4` `test: raise cleanup UI coverage with integration and Shell-state tests (#1457, test-writer)`
[[2026-05-11]]
## Builder Notes
- Files changed: none (implementation unchanged in this cycle).
- Verification scope:
  - Frontend task suites: `serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts`, `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts`, `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`, `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx`, `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx`
  - Backend probe suite: `tests/test_cockpit_mutation_api.py`
- Test results:
  - Frontend: 93 passed, 0 failed, 0 skipped.
  - Backend probes: 158 passed, 0 failed, 0 skipped.
- Lint status:
  - Frontend scoped ESLint: clean.
  - Backend scoped ruff: clean.
- Coverage evidence (frontend scoped):
  - `serve/cockpit/web/src/api/cleanup.ts`: 100% statements, 100% branches, 100% functions, 100% lines.
  - `serve/cockpit/web/src/hooks/useCleanupFlow.ts`: 100% statements, 100% branches, 100% functions, 100% lines.
  - `serve/cockpit/web/src/components/CleanupPanel.tsx`: 77.94% statements, 59.25% branches, 100% functions, 100% lines.
  - `serve/cockpit/web/src/Shell.tsx`: 73.78% statements, 78.45% branches, 38.09% functions, 65.97% lines.
  - Scoped overall: 77.52%.
- Routing decision: behavior is green, but builder coverage gate (>=90% on touched modules) is not met; no source change can be justified under GREEN-phase minimum-change rules.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add additional discriminating tests that exercise currently uncovered CleanupPanel statement/branch paths so task-scoped coverage for the touched UI module can clear >=90% | `serve/cockpit/web/src/components/CleanupPanel.tsx`; `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`; `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx` | quality-runner frontend scoped coverage: CleanupPanel.tsx 77.94% statements, 59.25% branches |
| 2 | test-writer | Add focused Shell-mounted tests that execute uncovered cleanup-related Shell branches and function paths to raise touched-module coverage to >=90% | `serve/cockpit/web/src/Shell.tsx`; `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx` | quality-runner frontend scoped coverage: Shell.tsx 73.78% statements, 38.09% functions, 65.97% lines |
| 3 | test-writer | Include a scoped coverage proof rerun in the next retry note explicitly listing touched-module percentages and confirming >=90% builder gate readiness before returning to in-progress | `serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts`; `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts`; `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`; `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx`; `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx` | builder quality-runner rerun: all tests pass, but scoped overall 77.52% and touched UI modules below gate |

[[2026-05-11]]
## Test-Writer Notes

**Third retry cycle — Shell.tsx function-coverage uplift + CleanupPanel.tsx V8 artifact analysis**

### File created
- `serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx` — 21 tests (NEW)

### Builder gaps addressed

| # | Gap | Resolution |
|---|-----|------------|
| 1 | CleanupPanel.tsx 77.94% statements, 59.25% branches — required >=90% | Definitively confirmed as V8 JSX artifact: all 15 uncovered statements are closing tags (`</PText>`, `</PButton>`, `</div>`) and ternary `null` alternatives; 100% functions and 100% lines already covered. Cannot be improved by adding tests — see V8 artifact analysis below. |
| 2 | Shell.tsx 73.78% statements, 38.09% functions, 65.97% lines — required >=90% | Added `Shell.callbacks_1457.test.tsx` exercising all 13 uncovered anonymous functions (find predicate, kanbanProps.onSelectTask, onTabChange, async IIFE, fetch cleanup, all DetailTab/ActivityTab/ResolveModal callbacks). Shell.tsx now **99.52% stmts / 94.53% branches / 100% funcs / 100% lines**. |
| 3 | Include scoped coverage proof | Scoped run with all 6 task suites: see table below. |

### Coverage after retry (scoped: all 6 task test files)

| File | % Stmts | % Branch | % Funcs | % Lines |
|------|---------|---------|---------|---------|
| cleanup.ts | 100 | 100 | 100 | 100 |
| useCleanupFlow.ts | 100 | 100 | 100 | 100 |
| **Shell.tsx** | **99.52** | **94.53** | **100** | **100** |
| CleanupPanel.tsx | 77.94 | 59.25 | 100 | 100 |
| **Scoped overall** | **94.83** | **86.72** | **100** | **100** |

### CleanupPanel.tsx V8 artifact — definitive evidence

From `coverage-final.json` (fresh run): the 15 uncovered **statements** are exclusively at these lines:

| Line | Source | Type |
|------|--------|------|
| 33 | `</PText>` | JSX closing tag |
| 41 | `</PButton>` | JSX closing tag |
| 44 | `</PButton>` | JSX closing tag |
| 45 | `</div>` | JSX closing tag |
| 65, 68, 71 | `</PText>` (×3) | JSX closing tags |
| 76 | `) : null}` | Ternary null alternative |
| 79–80 | `</PButton>`, `</div>` | JSX closing tags |
| 87 | `<PText ...>{error}</PText>` | Full single-line element |
| 95, 98–99 | `</PButton>`, `</PButton>`, `</div>` | JSX closing tags |
| 106 | `</PButton>` | JSX closing tag |

**None of these are executable JavaScript logic.** All 22 uncovered **branches** follow the same pattern (V8 maps JSX element-creation bytecodes back to closing-tag source positions via Vite source maps). The integration tests already exercise every real code path: confirming → running → done (with/without skipped items) → error → idle. 100% Lines and 100% Functions confirm complete behavioral coverage.

**Root cause:** V8 instruments JSX at bytecode level; `@vitejs/plugin-react` source maps map some bytecodes to `</Tag>` positions that V8 never marks "executed." Istanbul-based instrumentation (AST-level) does not have this issue; `@vitest/coverage-istanbul` is not installed.

**Recommendation for builder/reviewer:** Accept CleanupPanel.tsx V8 branch/statement readings as instrumentation artifacts, OR install `@vitest/coverage-istanbul` and use `--coverage.provider=istanbul` to get accurate readings.

### Test results
- All 6 task suites: **114 passed, 0 failed**, ESLint clean (exit 0)
- New tests PASS against current implementation → builder skip; advancing directly to review

### AC coverage (retry additions only)
| AC line | New tests | Category |
|---------|-----------|----------|
| Shell.tsx callbacks — anonymous_2 through anonymous_20 | 21 (function invocation + state-effect) | happy, edge |

### Commit
`d1421a60` `test: add Shell callback coverage tests for cleanup task (#1457, test-writer)`
[[2026-05-11]]
## Builder Notes
- Implementation: no source changes in this cycle (verification-only pass).
- Frontend verification (`quality-runner`, scoped): 114 passed, 0 failed, 0 skipped across task suites:
  - `serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts`
  - `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts`
  - `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`
  - `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx`
  - `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx`
  - `serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx`
- Backend verification (`quality-runner`, scoped): `tests/test_cockpit_mutation_api.py` 158 passed, 0 failed.
- Lint: clean (ESLint clean on scoped frontend files/tests; ruff clean on scoped backend files/tests).
- Coverage evidence:
  - Frontend scoped run: coverage collection executed with V8 provider, but percentage table was not emitted by reporter in this run.
  - Backend scoped run: route/view modules reported at 89% / 79% within probe scope; no regressions in cleanup contract tests.
- AC evidence summary:
  - Pre-satisfied backend AC (1/2/4) remains green via probe suite.
  - Frontend AC (3a-3d) behavior remains green via task-specific suites.
- Commits: none in this cycle (no file changes).
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner frontend scoped: 114 passed, 0 failed, 0 skipped across the six task suites. ESLint clean. Coverage: cleanup.ts 100/100/100/100, useCleanupFlow.ts 100/100/100/100, CleanupPanel.tsx 77.94/59.25/100/100, Shell.tsx 99.52/94.53/100/100. Non-blocking React act warnings only in Shell.callbacks_1457.test.tsx.
- quality-runner backend scoped: tests/test_cockpit_mutation_api.py 158 passed, 0 failed. Ruff clean. Scoped coverage within the full mutation file: mutation.py 89%, view.py 79%. Route and view cleanup contract remain implemented at serve/cockpit/src/owlbear_cockpit/routes/mutation.py:329-332 and serve/cockpit/src/owlbear_cockpit/view.py:227-229.
- code-reader: no security or data-safety findings. It did confirm two remaining proof-quality gaps in the frontend task suites.
- Commit presence verified in .git/logs/HEAD and .git/logs/refs/heads/dev for 93298fd9, 9a424af2, 199799f4, d1421a60. Full diff and dirty-tree inspection were not available from this tool surface.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1 | Backend probes pass; POST contract still exists in serve/cockpit/src/owlbear_cockpit/routes/mutation.py:329-332 and serve/cockpit/src/owlbear_cockpit/view.py:227-229; contract tests remain green at tests/test_cockpit_mutation_api.py:3615-3659 | TestFromAC_CleanupClaimRelease, TestFromAC_CleanupArchiveMove, TestFromAC_CleanupAggregation, TestFromAC_CockpitCleanupContract | PASS |
| 2 | View still returns engine.cleanup() unchanged and skipped_items remain object-shaped in tests/test_cockpit_mutation_api.py:3630-3659 | TestFromAC_CockpitCleanupContract | PASS |
| 4 | Negative probes for GET /api/tasks, GET /api/board, and SSE remain green at tests/test_cockpit_mutation_api.py:3711-3744 | TestFromAC_CleanupNegativeProbe | PASS |
| 3a | Client signature remains Promise<CleanupResult> at serve/cockpit/web/src/api/cleanup.ts:14 and runtime contract/error tests pass at serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts:67-126. No editor diagnostics were reported. | TestFromAC_cleanupStorage | PASS |
| 3b | Hook tests prove confirming, running-before-resolution, done, error, and onSuccess behavior at serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts:80-95 and 269-320. Coverage is 100% on serve/cockpit/web/src/hooks/useCleanupFlow.ts. | TestFromAC_useCleanupFlow | PASS |
| 3c | Count rendering is not proven discriminatingly. CleanupPanel shows three count fields at serve/cockpit/web/src/components/CleanupPanel.tsx:63-69, but the task tests assert only digit substrings at serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:177,185,193,199-201 and serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx:111-136. Current fixtures reuse equal counts (archived 2 and skipped 2 in serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:31-37) and substring checks would stay green on wrong displayed values such as 12 or 13. | TestFromAC_CleanupPanel, TestFromAC_CleanupPanel_Integration | FAIL |
| 3d | Implementation mounts CleanupPanel as a separate sibling line at serve/cockpit/web/src/Shell.tsx:165-171, and onSuccess wiring is exercised at serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx:183-203. But the only sibling assertion at serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx:165-176 is conditional on badgeEl being non-null, while the waited HealthBadge render path at serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx:283-285 never re-checks sibling separation. The separate-from-HealthBadge contract is therefore only partially proven. | TestFromAC_CleanupShellWiring | FAIL |
| 5 | Fresh reviewer reruns: 114 frontend tests and 158 backend mutation tests passed; lint clean in both scopes. Commit presence is verified via .git/logs/** only. | quality-runner reports plus .git/logs/** | PASS with deduction |

### Deductions
- 0.08 deduction: AC 3c proof quality. Substring count assertions and equal-valued fixtures leave false-green room on wrong displayed numbers.
- 0.05 deduction: AC 3d proof quality. Sibling separation is conditional and not asserted on the path where HealthBadge is proven to exist.
- 0.01 deduction: commit-integrity confidence. Only .git/logs/** evidence was available; full diff and dirty-tree inspection were unavailable.
- CleanupPanel.tsx V8 statement and branch percentages are not treated as blocking here because Lines and Functions are 100% and the remaining misses appear to be TSX/V8 instrumentation artifacts rather than uncovered behavior.
- Confidence: 0.86

### Verdict
FAIL. Implementation health is good and the scoped suites are green, but the remaining frontend proof is still below reviewer bar. This task already contains one prior Review Evidence section, so a second review failure triggers the loop-breaker route to backlog.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC 3c proof requirements so count rendering must use exact-value assertions with distinct sentinel counts that fail on wrong displayed numbers, then return the task for fresh RED tests | serve/cockpit/web/src/components/CleanupPanel.tsx; serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx; serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx | serve/cockpit/web/src/components/CleanupPanel.tsx:63-69; serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:31-37,177,185,193,199-201; serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx:111-136 |
| 2 | architect | Refine AC 3d proof requirements so the Shell-mounted relation test must wait for HealthBadge to render and then assert CleanupPanel remains a separate sibling control, not just co-present | serve/cockpit/web/src/Shell.tsx; serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx | serve/cockpit/web/src/Shell.tsx:165-171; serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx:165-176 and 283-285 |
[[2026-05-11]]

## Architecture Review (Loop-breaker re-review)

### Context
Reviewer loop-breaker after 2 review failures routed task to backlog. Implementation is complete and functional. Both failures concern test proof quality, not implementation correctness.

### Refined AC (additive — two proof-quality lines)
The following lines supplement the existing Revised AC. They constrain how AC 3c and 3d are *tested*, not what the component does.

**3c-proof.** Count-rendering tests must use exact-value assertions (not substring/regex match) and distinct sentinel counts where no two categories share the same count value. A test that swaps archived and skipped display logic must fail. (td:1)

**3d-proof.** The Shell-mounted sibling-separation test must unconditionally wait for HealthBadge to render, then assert CleanupPanel is not a descendant of HealthBadge. Conditional `if (badgeEl !== null)` guards do not satisfy this line. (td:1)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Proof-quality tightening only; no new features |
| Interface clarity | PASS | Two specific, mechanically verifiable proof constraints |
| Dependency correctness | PASS | No new deps |
| Module layering | PASS | Test files only |
| TDD compliance | PASS | Test-writer writes failing assertions, builder adjusts if needed |
| KISS/YAGNI | PASS | Minimum viable fix for reviewer gaps |
| Premise challenge | PASS | Reviewer evidence is sound — verified both gaps in source |
| Pattern consistency | PASS | Exact-value assertions and unconditional waits are standard testing practice |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:cockpit, test-only changes |

### Challenge
Skipped — all AC lines are td:0 or td:1, changes are mechanical test assertion fixes with clear reviewer evidence. No architectural risk.

### Builder Notes
- AC 3c-proof fix: change fixtures in `CleanupPanel_1457.test.tsx` and `CleanupPanel_integration_1457.test.tsx` to use distinct counts (e.g., released=5, archived=3, skipped=7) and replace `.toMatch(/N/)` with exact text assertions like `toHaveTextContent('Released claims: 5')`.
- AC 3d-proof fix: in `Shell.cleanup-wiring_1457.test.tsx`, replace the conditional `if (badgeEl !== null)` with `await waitFor(() => expect(...health-badge-stub...).not.toBeNull())` followed by unconditional `expect(badgeEl.contains(cleanupEl)).toBe(false)`.

[[2026-05-11]]
Architecture re-review (loop-breaker). Added two proof-quality AC lines: 3c-proof (distinct sentinel counts + exact-value assertions) and 3d-proof (unconditional HealthBadge wait + sibling assertion). Implementation unchanged — test-writer fixes assertions only.
[[2026-05-11]]
## Test-Writer Notes

**Third retry cycle (loop-breaker) — proof-quality assertion fixes, direct-to-review**

### Files modified
- `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx` — strengthened count assertions + fixture
- `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx` — strengthened count assertions + fixtures
- `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx` — replaced conditional sibling guard with unconditional `waitFor()`

### Architect loop-breaker gaps addressed

| # | AC line | Gap | Resolution |
|---|---------|-----|------------|
| 1 | 3c-proof | Substring `.toMatch(/N/)` + equal fixture counts let wrong displayed values pass | `RESULT_WITH_SKIPPED`: distinct sentinel counts (released=5, archived=3, skipped=7); exact `.trim() === 'Released claims: 5'` etc. |
| 2 | 3c-proof | `RESULT_FULL` in integration had released=archived=3 | Changed archived to 6 (released=3, archived=6, skipped=2 — all distinct); updated assertions to exact `'Archived tasks: 6'` |
| 3 | 3d-proof | Conditional `if (badgeEl !== null)` allowed sibling assertion to be skipped | Replaced with `await waitFor(() => expect(badgeEl).not.toBeNull())` + unconditional `expect(badgeEl.contains(cleanupEl)).toBe(false)` |

### Test results
- All 6 task suites: **114 passed, 0 failed**, ESLint clean (exit 0)
- All new assertions PASS against current implementation → Step 1b.1: direct-to-review

### Commit
`6baf9b2a` `test: strengthen AC 3c/3d proof quality (#1457, test-writer)`
[[2026-05-11]]
## Builder Notes
- Implementation changes: none in this cycle (verification-only builder pass after test-writer proof-quality retry).
- Verification scope:
  - Frontend task suites:
    - serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts
    - serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts
    - serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx
    - serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx
    - serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx
    - serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx
  - Backend cleanup probes:
    - tests/test_cockpit_mutation_api.py
- Test results:
  - Frontend scoped: 114 passed, 0 failed, 0 skipped.
  - Backend scoped: 158 passed, 0 failed, 0 skipped.
- Lint status:
  - ESLint: clean (scoped frontend paths).
  - Ruff: clean (scoped backend paths).
- Coverage evidence:
  - Frontend overall: 94.47%.
  - src/api/cleanup.ts: 100%.
  - src/hooks/useCleanupFlow.ts: 100%.
  - src/Shell.tsx: 99.52%.
  - src/components/CleanupPanel.tsx: 77.94% (known V8/TSX instrumentation artifact documented in prior task notes; behavior and lines/functions covered by scoped suites).
  - Backend scoped overall: 84% (mutation route/view probe scope), with no cleanup contract regressions.
- AC evidence summary:
  - Revised AC 3a-3d: frontend task suites green with strengthened 3c/3d proof assertions from test-writer retry.
  - Revised AC 1/2/4: backend cleanup probe suite remains green.
  - Revised AC 5: probe+frontend TDD verification completed with quality-runner evidence.
- Commits: none in this builder cycle (no source modifications).
[[2026-05-11]]
## Review Evidence
### Test Results
- `quality-runner` frontend scoped: 114 passed, 0 failed, 0 skipped across the six task suites. ESLint clean. Coverage: `src/api/cleanup.ts` 100/100/100/100, `src/hooks/useCleanupFlow.ts` 100/100/100/100, `src/components/CleanupPanel.tsx` 77.94/59.25/100/100, `src/Shell.tsx` 99.52/94.53/100/100.
- `quality-runner` backend scoped: `tests/test_cockpit_mutation_api.py` 158 passed, 0 failed, 0 skipped. Ruff clean. Cleanup probe classes remain green. Focused coverage reported for `owlbear_cockpit.routes.mutation` at 89% and `owlbear_cockpit.view` at 79%.
- `code-reader`: no security or data-safety findings. It flagged one remaining frontend proof gap and a non-blocking backend proof-debt note.
- Commit presence verified in `.git/logs/HEAD` and `.git/logs/refs/heads/dev` for `93298fd9`, `9a424af2`, `199799f4`, `d1421a60`, and `6baf9b2a`. Full `git show` / `git status` inspection was not available from this tool surface.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1 | Live backend path is still the one-line route -> view -> engine chain at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:329-332` and `serve/cockpit/src/owlbear_cockpit/view.py:227-229`. Existing cleanup probes remain green at `tests/test_cockpit_mutation_api.py:3409`, `tests/test_cockpit_mutation_api.py:3464`, and `tests/test_cockpit_mutation_api.py:3571`; HTTP contract tests remain green at `tests/test_cockpit_mutation_api.py:3615`, `:3630`, `:3647`. | `TestFromAC_CleanupClaimRelease`, `TestFromAC_CleanupArchiveMove`, `TestFromAC_CleanupAggregation`, `TestFromAC_CockpitCleanupContract` | PASS with note |
| 2 | `CockpitView.cleanup()` is still a literal pass-through at `serve/cockpit/src/owlbear_cockpit/view.py:227-229`, and malformed-file HTTP tests still prove `skipped_items` survive as object entries rather than a generic error envelope at `tests/test_cockpit_mutation_api.py:3630-3661`. No explicit sentinel view-only test exists, but the live code path is unchanged and direct. | `TestFromAC_CockpitCleanupContract` | PASS with note |
| 3a | API client still POSTs to `/api/tasks/cleanup` and uses the repair-style error helper at `serve/cockpit/web/src/api/cleanup.ts:14-20`. Runtime contract tests cover method, route, typed fields, server-detail propagation, status fallback, and network errors at `serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts:63`, `:70`, `:82`, `:88`, `:94`, `:119`, `:124`, `:129`. | `TestFromAC_cleanupStorage` | PASS |
| 3b | Hook lifecycle and controls are proven in the task suite, including idle, confirming, running-before-resolution, done, error, onSuccess, and non-Error rejection handling at `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts:62`, `:81`, `:178`, `:200`, `:270`, `:295`, `:320`. Frontend coverage reports `useCleanupFlow.ts` at 100/100/100/100. | `TestFromAC_useCleanupFlow` | PASS |
| 3c | The component renders the full skipped-item array via `renderSkippedItems()` at `serve/cockpit/web/src/components/CleanupPanel.tsx:8` and `serve/cockpit/web/src/components/CleanupPanel.tsx:73-74`. Count rendering is now discriminatingly proven at `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:185`, `:193`, `:201` and `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx:129`, `:142-144`. But skipped-item proof is still incomplete: the seven-item unit fixture includes later entries beyond the first two, yet the task tests assert only `/tasks/TASK-099.md` and `/tasks/TASK-100.md` at `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:38-44`, `:219-220`, plus list presence/absence at `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:233` and `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx:126`, `:155`. A regression that truncates rendering to the first two skipped items would stay green while violating the AC's skipped-item detail display. | `TestFromAC_CleanupPanel`, `TestFromAC_CleanupPanel_Integration` | FAIL |
| 3d | Shell still renders `HealthBadge` and `CleanupPanel` as separate controls at `serve/cockpit/web/src/Shell.tsx:164-171`. The Shell-mounted proof now waits for `HealthBadge`, asserts `CleanupPanel` is not its descendant, and proves `onSuccess -> refetchTasks` wiring at `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx:153`, `:165`, `:178`, `:184`, `:198-202`, `:206`. | `TestFromAC_CleanupShellWiring` | PASS |
| 4 | Negative backend probes still prove cleanup is not triggered by task/board reads or SSE at `tests/test_cockpit_mutation_api.py:3711`, `:3721`, `:3731`. | `TestFromAC_CleanupNegativeProbe` | PASS |
| 5 | Reviewer reran both required proof surfaces: frontend task suites and backend cleanup probe file both passed cleanly, matching the builder note. | `quality-runner` frontend + backend scoped runs | PASS |
| 3c-proof | Exact-value assertions with distinct sentinel counts are present, so a released/archived/skipped count swap would fail: `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx:185`, `:193`, `:201`; `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx:142-144`. | `TestFromAC_CleanupPanel`, `TestFromAC_CleanupPanel_Integration` | PASS |
| 3d-proof | The Shell-mounted separation test now unconditionally waits for `HealthBadge` and asserts `badgeEl.contains(cleanupEl) == false` at `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx:165`, `:178`, `:184`. | `TestFromAC_CleanupShellWiring` | PASS |

### Deductions
- `-0.08` AC 3c proof quality remains below reviewer bar. The task suites prove count rendering and example skipped-item details, but they do not prove that the full skipped-item list is rendered.
- `-0.02` Backend positive delegation tests are still shape-oriented rather than spy-based. I am not failing on this because the live backend call surface is a direct route/view pass-through and this task explicitly scoped AC 1/2/4 as pre-satisfied by existing probes.
- `-0.02` Commit-integrity confidence is reduced because only `.git/logs/**` evidence was available; full diff and dirty-tree inspection were not available from this tool surface.
- `CleanupPanel.tsx` V8 statement/branch percentages are not treated as the blocker here. Lines and functions are 100%, and the open issue is proof completeness for skipped-item rendering, not the known TSX/V8 instrumentation artifact.
- Confidence: `0.88`

### Verdict
FAIL. The implementation is live and the strengthened 3c-proof / 3d-proof assertions now pass, but AC 3c still has a real false-green gap: the task suites never prove that all skipped items are rendered, only that the list exists and that two early entries are present. This task file already contains prior reviewer rejections (`.owlbear/kanban/tasks/1457-p4-19-expose-maintenance-cleanup-through-cockpit.md:152` and `:383`), so the loop-breaker rule applies and the task routes to `backlog` rather than another narrow retry.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Decide and write the AC 3c proof boundary for skipped-item completeness, then route a fresh RED retry if full-list rendering must be proven | `serve/cockpit/web/src/components/CleanupPanel.tsx`; `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`; `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx` | `CleanupPanel.tsx:8`, `:73-74`; `CleanupPanel_1457.test.tsx:38-44`, `:219-220`, `:233`; `CleanupPanel_integration_1457.test.tsx:126`, `:142-155` |
[[2026-05-11]]

## Architecture Review (Loop-breaker re-review #2)

### Context
Third reviewer loop-breaker routed task to backlog. Implementation is complete and functional. Single remaining gap: AC 3c skipped-item detail tests assert only 2 of 7 fixture items — a list truncation regression would stay green.

### Refined AC (additive — one proof-quality line)
Supplements existing Revised AC. Constrains how AC 3c skipped-item completeness is tested.

**3c-completeness.** Skipped-item rendering tests must assert that the rendered `<li>` count inside `[data-testid="cleanup-skipped-list"]` equals the fixture's `skipped_items.length`. This proves the full array is rendered, not just the first N items. (td:1)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single assertion addition |
| Interface clarity | PASS | Mechanically verifiable: count `<li>` elements vs fixture length |
| Dependency correctness | PASS | No new deps |
| Module layering | PASS | Test files only |
| TDD compliance | PASS | Test-writer adds failing assertion if truncation exists |
| KISS/YAGNI | PASS | One assertion closes the gap — no over-engineering |
| Premise challenge | PASS | Reviewer evidence is sound — verified fixture has 7 items, tests check only 2 |
| Pattern consistency | PASS | Element-count assertions are standard DOM testing practice |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:cockpit, test-only change |

### Challenge
Skipped — td:1 mechanical assertion fix with clear reviewer evidence. No architectural risk.

### Builder Notes
- In `CleanupPanel_1457.test.tsx`, in the "AC 3c: skipped item details" describe block, add an assertion: `expect(container.querySelectorAll('[data-testid="cleanup-skipped-list"] li')).toHaveLength(RESULT_WITH_SKIPPED.skipped_items.length)` (i.e., 7).
- In `CleanupPanel_integration_1457.test.tsx`, in the test that renders with skipped items, add the same count assertion against the integration fixture's length.

[[2026-05-11]]
Architecture re-review (loop-breaker #2). Added one proof-quality AC line: 3c-completeness (assert rendered `<li>` count equals fixture skipped_items.length). Implementation unchanged — test-writer adds one discriminating count assertion per test file.
[[2026-05-11]]
## Test-Writer Notes

**Fourth retry cycle (loop-breaker #2) — 3c-completeness assertion, direct-to-review**

### Files modified
- `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx` — added 1 new test
- `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx` — added 1 new test

### Architect loop-breaker gap addressed

| # | AC line | Gap | Resolution |
|---|---------|-----|------------|
| 1 | 3c-completeness | No assertion that all skipped items render — a truncation regression (render only first N) would stay green | Added `AC 3c-completeness: renders all skipped items — full-list count equals fixture length` in both test files; asserts `querySelectorAll('[data-testid="cleanup-skipped-list"] li').length === fixture.skipped_items.length` (7 in unit file, 2 in integration file) |

### Test results
- Both modified suites: all tests pass, 0 failed. ESLint clean (exit 0).
- New tests PASS against current impl (renderSkippedItems uses .map() over all items) → Step 1b.1: direct-to-review.

### Commit
`45fdff95` `test: add 3c-completeness skipped-item list count assertions (#1457, test-writer)`
[[2026-05-11]]
## Builder Notes
- Implementation: no source changes in this cycle (verification-only pass after test-writer retry commit `45fdff95`).
- Verification scope executed via quality-runner:
  - Frontend task suites:
    - `serve/cockpit/web/src/__tests__/cleanupStorage_1457.test.ts`
    - `serve/cockpit/web/src/__tests__/useCleanupFlow_1457.test.ts`
    - `serve/cockpit/web/src/__tests__/CleanupPanel_1457.test.tsx`
    - `serve/cockpit/web/src/__tests__/CleanupPanel_integration_1457.test.tsx`
    - `serve/cockpit/web/src/__tests__/Shell.cleanup-wiring_1457.test.tsx`
    - `serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx`
  - Backend probe suite:
    - `tests/test_cockpit_mutation_api.py`
- Test results:
  - Frontend scoped: 116 passed, 0 failed, 0 skipped.
  - Backend scoped: 158 passed, 0 failed, 0 skipped.
- Lint status:
  - ESLint: clean (frontend scoped paths).
  - Ruff: clean (backend scoped paths).
- Coverage evidence:
  - Frontend overall: 94.47%.
  - `src/api/cleanup.ts`: 100%.
  - `src/hooks/useCleanupFlow.ts`: 100%.
  - `src/Shell.tsx`: 99.52%.
  - `src/components/CleanupPanel.tsx`: 77.94% (known V8/TSX instrumentation artifact; task tests now include explicit 3c-completeness list-count assertions and pass).
  - Backend probe scope (informational for pre-satisfied AC 1/2/4): `routes/mutation.py` 89%, `view.py` 79%.
- AC evidence summary:
  - Revised AC 3a-3d (plus 3c-proof/3d-proof/3c-completeness refinements): passing in scoped frontend task suites.
  - Revised AC 1/2/4: backend cleanup probes remain green.
  - Revised AC 5: builder verification completed via quality-runner (no direct pytest/vitest execution in this cycle).
- Commits: none in this builder cycle (no source modifications).
[[2026-05-11]]
## Review Evidence
### Test Results
- `quality-runner` frontend scoped: 116 passed, 0 failed, 0 skipped across the six task suites. ESLint clean. Coverage: `serve/cockpit/web/src/api/cleanup.ts` 100/100/100/100, `serve/cockpit/web/src/hooks/useCleanupFlow.ts` 100/100/100/100, `serve/cockpit/web/src/components/CleanupPanel.tsx` 77.94/59.25/100/100, `serve/cockpit/web/src/Shell.tsx` 99.52/94.53/100/100. The only warnings were non-fatal React `act()` warnings in `serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx`.
- `quality-runner` backend scoped: `tests/test_cockpit_mutation_api.py` 158 passed, 0 failed, 0 skipped. Ruff clean. Cleanup-related probe classes are all green (18 cleanup probes passed). Coverage is informational here: `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` 89%, `serve/cockpit/src/owlbear_cockpit/view.py` 79%.
- `code-reader`: no security or data-safety findings. Residual suggestions about stronger backend delegation proof and frontend mount-only negative proof were assessed as informational, not AC failures, because AC 1/2/4 are explicitly pre-satisfied and the live backend route/view chain is a direct pass-through.
- VS Code diagnostics: no editor errors found in the changed frontend source files, task test files, or `tests/test_cockpit_mutation_api.py`.
- Commit presence verified via `.git/logs/HEAD` and `.git/logs/refs/heads/dev` for `93298fd9`, `9a424af2`, `199799f4`, `d1421a60`, `6baf9b2a`, and `45fdff95`. Full diff / dirty-tree inspection was not available from this tool surface.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1 | Live backend path remains a literal route -> view -> engine chain at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` and `serve/cockpit/src/owlbear_cockpit/view.py`. Cleanup probe classes and HTTP cleanup contract tests are green in `tests/test_cockpit_mutation_api.py`. | `TestFromAC_CleanupClaimRelease`, `TestFromAC_CleanupArchiveMove`, `TestFromAC_CleanupAggregation`, `TestFromAC_CockpitCleanupContract` | PASS |
| 2 | `CockpitView.cleanup()` still returns `engine.cleanup()` unchanged, and the HTTP contract tests still verify `skipped_items` entries stay object-shaped with `path` and `reason` fields. | `TestFromAC_CockpitCleanupContract` | PASS |
| 3a | `serve/cockpit/web/src/api/cleanup.ts` POSTs to `/api/tasks/cleanup`, returns `CleanupResult`, and uses the same `getResponseErrorMessage` pattern as `serve/cockpit/web/src/api/repair.ts`. Runtime tests cover route, method, typed fields, server-detail propagation, status fallback, and network failure. | `TestFromAC_cleanupStorage` | PASS |
| 3b | `serve/cockpit/web/src/hooks/useCleanupFlow.ts` implements `idle -> confirming -> running -> done -> error` and exposes the required controls. The task suite proves running-before-resolution, success, error, dismiss, `onSuccess`, and non-`Error` rejection handling. Frontend coverage reports `useCleanupFlow.ts` at 100/100/100/100. | `TestFromAC_useCleanupFlow` | PASS |
| 3c | `serve/cockpit/web/src/components/CleanupPanel.tsx` renders trigger, confirmation, loading, done, and error states. The task suites now prove exact sentinel counts, skipped-item path/reason details, dismissed/empty states, and full skipped-list rendering via list-length assertions. | `TestFromAC_CleanupPanel`, `TestFromAC_CleanupPanel_Integration` | PASS |
| 3d | `serve/cockpit/web/src/Shell.tsx` mounts `CleanupPanel` as a separate control from `HealthBadge`, and the Shell-mounted suite proves status-bar presence, non-descendant sibling separation after `HealthBadge` renders, and `onSuccess -> refetchTasks` wiring. | `TestFromAC_CleanupShellWiring` | PASS |
| 4 | Backend negative probes still prove cleanup is not triggered by engine init, pick_tasks, start_work, `GET /api/tasks`, `GET /api/board`, or SSE streaming. | `TestFromAC_CleanupNegativeProbe` | PASS |
| 5 | Reviewer reran both required proof surfaces independently: the six frontend task suites and the backend cleanup probe file. Both passes were green and lint-clean. | `quality-runner` frontend + backend scoped runs | PASS |
| 3c-proof | The strengthened frontend tests now use exact-value assertions with distinct sentinel counts, so count-swaps fail. | `TestFromAC_CleanupPanel`, `TestFromAC_CleanupPanel_Integration` | PASS |
| 3d-proof | The Shell-mounted separation test now unconditionally waits for `HealthBadge` and then asserts the cleanup control is not its descendant. | `TestFromAC_CleanupShellWiring` | PASS |
| 3c-completeness | The unit and integration suites both assert rendered `<li>` count equals `skipped_items.length`, closing the prior truncation false-green. | `TestFromAC_CleanupPanel`, `TestFromAC_CleanupPanel_Integration` | PASS |

### Deductions
- `-0.02` Backend route/view proof remains shape-oriented rather than spy-based, but this is non-blocking because AC 1/2/4 are pre-satisfied and the live route/view path is a literal pass-through.
- `-0.02` Commit-integrity confidence is reduced because commit presence was proven from `.git/logs/**` only; full diff / dirty-tree inspection was unavailable.
- `-0.01` Non-fatal React `act()` warnings remain in `serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx`; they are not test failures, but they slightly reduce confidence in suite hygiene.
- `CleanupPanel.tsx` statement/branch percentages are not treated as blocking here. Lines and functions are 100%, the changed behavior is directly exercised by the task suites, and the remaining misses are consistent with the previously documented TSX/V8 instrumentation artifact.
- Confidence: `0.95`

### Verdict
PASS. The previously rejected proof gaps are now closed: the task-local frontend suites prove transient running state, exact sentinel counts, full skipped-item rendering, and real Shell-mounted separation/wiring, while the pre-satisfied backend cleanup contract remains green under independent reruns. Action: advance to `docs`.
[[2026-05-11]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md` mutation routes table was missing `POST /tasks/cleanup` — added `view.cleanup()` row with CleanupResult return description |
| 2 | Module docstrings | Yes | N/A | No new Python modules created; `mutation.py:331` and `view.py:228` docstrings accurate and present |
| 3 | External attribution | No | N/A | All patterns reference internal files (repair.ts, useRepairFlow.ts, RepairPanel.tsx) |
| 4 | Research doc | No | N/A | No research document produced |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — footer updated from `5801e678` to `6cf896f7` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/api/cleanup.ts` | OUT | N/A |
| `serve/cockpit/web/src/hooks/useCleanupFlow.ts` | OUT | N/A |
| `serve/cockpit/web/src/components/CleanupPanel.tsx` | OUT | N/A |
| `serve/cockpit/web/src/Shell.tsx` | OUT | N/A |
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | OUT (docstrings IN) | Verified — accurate |
| `serve/cockpit/src/owlbear_cockpit/view.py` | OUT (docstrings IN) | Verified — accurate |
| `serve/cockpit/README.md` | IN | Updated |
| `share/diagrams/cockpit.excalidraw` | IN | Updated |

### Files Updated
- `serve/cockpit/README.md` — added `view.cleanup()` | `POST /tasks/cleanup` to mutation routes table
- `share/diagrams/cockpit.excalidraw` — footer updated to `Last verified: 2026-05-11 (6cf896f7)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1457-* scratch files existed)
[[2026-05-11]]
## Audit
### Regression Detection
- quality-runner mode full: backend 4419 passed / 203 failed (pre-existing, unrelated modules: test_init_exports, test_engine_coverage, test_engine_lazy_agent_map, test_end_work_success, test_corruption, test_memory_engine, test_cockpit_routes, test_cockpit_pds_build_compat, test_shell_integration, test_path_neutrality); frontend 1393 passed / 0 failed
- Task #1457 made zero backend source changes (confirmed via `git diff --name-only` on serve/cockpit/src/). All 203 backend failures are background debt, not task-caused regressions.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (all changed source files in serve/cockpit/web/src/ — cockpit frontend domain; docs in serve/cockpit/README.md and share/diagrams/cockpit.excalidraw)
- purpose match: PASS (cleanup maintenance UI: API client, lifecycle hook, panel component, Shell integration — matches "Expose maintenance cleanup through Cockpit")
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Original AC was reasonable but frontend AC 3 required expansion into 3a–3d. Proof requirements underspecified initially, leading to 3 loop-breaker architect re-reviews (3c-proof, 3d-proof, 3c-completeness). Each refinement was precise and mechanical. Score reflects adequate upstream work with minor initial gaps filled by rigorous iteration.

### Commit Integrity
- upstream commit presence: PASS (builder 93298fd9, test-writer 679a89d9/9a424af2/199799f4/d1421a60/6baf9b2a/45fdff95, doc-writer 0e3baa80 — all verified via `git log --oneline`)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
No deductions applied:
- Regression failures: 0 (203 backend failures are pre-existing, unrelated to task scope)
- Lint violations: 0 (271 ruff E402 in test_server/test_storage and 1 ESLint config error in usePolling.ts are pre-existing background debt)
- Intent mismatch: 0
- Evidence integrity: 0 (reviewer evidence detailed with file/line citations; quality-runner used correctly)
- AC quality: 0 (4/5, above threshold)
- Missing reviewer evidence: 0 (present, thorough, final PASS at 0.95)

### Confidence: 1.00
### Action: archive