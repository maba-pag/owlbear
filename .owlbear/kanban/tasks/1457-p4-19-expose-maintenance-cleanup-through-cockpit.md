---
id: 1457
title: 'P4-19: Expose maintenance cleanup through Cockpit'
status: todo
priority: needed
created: 2026-05-08T19:37:26.531942+00:00
updated: 2026-05-11T09:19:02.230365+00:00
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
claimed_at: 2026-05-11T09:19:02.230365+00:00
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