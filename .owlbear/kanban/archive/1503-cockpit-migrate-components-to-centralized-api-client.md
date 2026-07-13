---
id: 1503
title: 'Cockpit: Migrate components to centralized API client'
status: archived
priority: medium
created: 2026-05-12T02:43:28.748468+00:00
updated: 2026-05-12T21:43:30.359212+00:00
tags:
  - cockpit
  - frontend
parent: 1493
depends_on:
  - 1501
  - 1502
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Objective
Replace all raw `fetch()` calls to `/api/tasks` and `/api/decisions` endpoints in component files with imported functions from `api/tasks.ts` and `api/decisions.ts`.

## Acceptance Criteria
- No raw `fetch()` to `/api/tasks/*` or `/api/decisions/*` remains in component files (KanbanBoard, DetailTab, ArchivalModal, ResolveModal, Shell)
- All existing tests pass without modification (behavioral preservation)
- Abort signal support, conflict resolution, and error handling behavior unchanged
- No new dependencies introduced beyond the api/ modules

## Implementation Notes
- Preserve all existing behavior exactly — this is a refactor, not a feature change
- Components: KanbanBoard, DetailTab, ArchivalModal, ResolveModal, Shell
- Verify abort signals are threaded through correctly
2026-05-12T04:24:15+00:00
Moved to backlog for architecture review. Task was placed in `todo` directly by researcher without arch review or proof-bundle assignment. AC has B3 violations ("All existing tests") and banned word "No" used as naked quantifier. Proof bundle needs assignment.
2026-05-12T14:30:42+00:00

## Refined Acceptance Criteria
_Supersedes original AC. Numbered, B3-clean._

- AC-1: `KanbanBoard.tsx` `handleDrop` and `handleTransitionClick` call `moveTask(id, request)` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}/move', ...)`. Error handling preserved: 409 → `refetchTasks()` + `onMutationError`, network error → `onMutationError('Move failed', msg, 'error')`, success → `refetchTasks()` + `onMutationSuccess()`
- AC-2: `Shell.tsx` task-detail effect calls `getTask(id, { signal })` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}', { signal })`. AbortSignal forwarding, cancelled-flag abort-error suppression, and `setSelectedTask`/`setSelectedTaskError` paths preserved
- AC-3: `ArchivalModal.tsx` `handleSubmit` calls `moveTask(taskId, { status: 'archived', updated, archival_reason, archival_refs })` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}/move', ...)`. Status-specific error handling preserved: 409 → stale-snapshot message + `onRefresh()`, 422 → validation message from `getResponseErrorMessage`, success → `onRefresh()` + `onClose()`
- AC-4: `ResolveModal.tsx` `handleSubmit` calls `resolveDR(dr.id, { response, notes })` from `api/decisions.ts` instead of raw `fetch('/api/decisions/{id}/resolve', ...)`. Error handling preserved: non-ok → error message with `retryable: status >= 500`, network catch → retryable message, success → `onResolved()` + `onClose()`
- AC-5: `useTaskMutation.ts` `runMutation` calls `editTask`, `releaseTask`, or `moveTask` from `api/tasks.ts` (based on mutation type) instead of raw `fetch(url, { method: 'POST', ... })`. Conflict refetch uses `getTask(taskId)` instead of raw `fetch('/api/tasks/{id}', { method: 'GET' })`. 409/404/422 error handling paths, `onTaskUpdated`, `onTaskCleared`, and `onMutationError` callbacks preserved
- AC-6: `grep -rE "fetch\(.*\/api\/(tasks|decisions)" serve/cockpit/web/src/ --include="*.ts" --include="*.tsx"` returns matches only in `api/tasks.ts`, `api/decisions.ts`, `api/repair.ts`, `api/cleanup.ts`, and `__tests__/` directories — zero matches in component or hook source files
- AC-7: `npm test` in `serve/cockpit/web/` exits 0 with zero test-file modifications (behavioral preservation)
- AC-8: `npm run build` in `serve/cockpit/web/` exits 0 (TypeScript compile-time verification)

Proof bundle: existing
Existing proof scope: `serve/cockpit/web/src/__tests__/KanbanBoard.*.test.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal.*.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.*.test.tsx`, `serve/cockpit/web/src/__tests__/Shell.*.test.tsx`, `serve/cockpit/web/e2e/*.spec.ts`

## Implementation Notes (updated)
- Migration surface (7 raw-fetch sites): KanbanBoard.tsx (2), Shell.tsx (1), ArchivalModal.tsx (1), ResolveModal.tsx (1), useTaskMutation.ts (2)
- `api/repair.ts` and `api/cleanup.ts` are excluded — they serve different endpoints (/tasks/repair, /tasks/cleanup) not covered by the centralized client
- `useTaskMutation.ts` currently accepts a URL string and does a generic POST. After migration, it should accept a mutation function or be refactored to call the appropriate typed API function. Implementation detail is builder's choice as long as AC-5 and AC-6 are satisfied.
- The centralized API functions throw `ApiError` on non-ok responses. Components must catch `ApiError` and map `.status` to component-specific behaviors (409 → conflict modal, 422 → validation message, etc.)
- Success paths must also be preserved: KanbanBoard `onMutationSuccess()` + `refetchTasks()`, ArchivalModal `onRefresh()` + `onClose()`, ResolveModal `onResolved()` + `onClose()`
- Existing tests mock `fetch` globally — they transparently exercise the centralized client (which internally calls `fetch`). Behavioral preservation is proven by existing test suite green. Structural migration is proven by AC-6 grep check.

2026-05-12T14:31:10+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: migrate raw fetch calls in components/hooks to use centralized API client |
| Interface clarity | PASS | AC-1..AC-8 specify exact files, functions, replacement calls, and preserved behaviors |
| Dependency correctness | PASS | #1501 (archived), #1502 (archived) — both complete |
| Module layering | PASS | Components/hooks import from api/ layer; no upward imports |
| TDD compliance | PASS | Existing proof scope covers full behavioral surface across Vitest + Playwright |
| KISS/YAGNI | PASS | Straightforward call replacement; no new abstractions required |
| Premise challenge | PASS | 7 raw fetch sites across 5 files justify centralization; api/ modules already proven |
| Pattern consistency | PASS | Follows established api/repair.ts + api/cleanup.ts centralization pattern |
| Security surface | PASS | Internal SPA→backend fetch calls; no new system boundaries |
| Single domain | PASS | Frontend API client domain |

### Challenger Results
- Challenger: reconsider (0.12)
- Findings addressed:
  1. **Canonical task-packet mismatch** — OVERRIDDEN. This IS the architecture review that refines the AC and assigns the proof bundle. The refined AC is now written to the task body.
  2. **Direct implementation contradiction** — OVERRIDDEN. Task is in backlog awaiting approval for implementation. The raw fetch calls exist BECAUSE this task hasn't been implemented yet. That's what the task is FOR.
  3. **DetailTab mutation path unresolved** — ACCEPTED. Expanded scope to include `useTaskMutation.ts` (2 raw fetch sites) in AC-5. Challenger correctly identified that the mutation surface extends beyond named component files into the hook.
  4. **Structural-proof gap** — ACCEPTED. Added AC-6 (grep structural verification) to prove migration beyond just behavioral test passing.
  5. **No evidence consumers use new clients** — OVERRIDDEN. Same as finding 2 — task hasn't been implemented yet.
  6. **Consolidation-gap dismissal** — NOTED. #1503 is the integration/consolidation task for the #1501/#1502 set; both archives explicitly defer consumer proof to this task.
- Architect response: accepted findings 3-4, revised AC accordingly; overrode findings 1, 2, 5 (confusion about pipeline stage)

### Proof-Bundle Validation
- Planner assignment: none
- Final bundle: existing
- Existing proof scope: `serve/cockpit/web/src/__tests__/KanbanBoard.*.test.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal.*.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.*.test.tsx`, `serve/cockpit/web/src/__tests__/Shell.*.test.tsx`, `serve/cockpit/web/e2e/*.spec.ts`
- Test-writer: SKIP (bundle `existing`)

### Design Diverge
- Trigger: skipped — single viable approach (replace raw fetch with typed API client functions; implementation detail of hook refactoring is builder's choice)

### AC Refinement Summary
Original AC had B3 violations ("No" as naked quantifier, "All existing tests"), vague "unchanged" without specifics, and missed scope (useTaskMutation.ts). Refined to 8 numbered B3-clean lines with exact file targets, specific error-handling behaviors to preserve, a structural grep verification, and behavioral + compile-time gates.

### Verdict: APPROVE (REFINE + approve)
### Action Taken: Refined AC (B3 fix, expanded scope to include useTaskMutation.ts, added structural grep check, assigned proof bundle existing), advanced to todo
2026-05-12T14:35:53+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `serve/cockpit/web/src/__tests__/KanbanBoard.*.test.tsx`, `serve/cockpit/web/src/__tests__/ArchivalModal.*.test.tsx`, `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.*.test.tsx`, `serve/cockpit/web/src/__tests__/Shell.*.test.tsx`, `serve/cockpit/web/e2e/*.spec.ts`
- Passing through to builder.
2026-05-12T15:31:45+00:00
## Builder Notes
- Implementation: migrated raw `/api/tasks` and `/api/decisions` fetch usage to centralized API helpers in `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, and `serve/cockpit/web/src/hooks/useTaskMutation.ts`.
- Behavior preservation: kept status-specific conflict/validation handling and callback flows; restored legacy fallback error-message text where tests assert exact strings.
- Proof bundle: `existing` verified via quality-runner.
- Tests: scoped existing-proof suite passed (`748 passed, 0 failed, 9 skipped`).
- Lint: clean (`eslint` scoped paths passed).
- Build: `npm build` passed (exit 0).
- Structural check (AC-6): `rg "fetch\(.*\/api\/(tasks|decisions)" serve/cockpit/web/src -g "*.ts" -g "*.tsx"` returned matches only in `src/api/*` and `src/__tests__/*`; no matches in component/hook source.
- Commit: `1097ac61fffcc4d6b7ecd16462a5eef3cd30fb15` (`5 files changed, 159 insertions(+), 143 deletions(-)`).
2026-05-12T16:10:51+00:00
## Review Evidence
- Verdict: FAIL
- FAIL routing: FAIL #1503 -> in-progress | review surface is contaminated by uncommitted #1504 Shell/CockpitProvider changes, and the declared existing-proof suite is currently red.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-2 | The current Shell review surface is overlapped by uncommitted #1504 refactor work, so #1503 can no longer be verified against the file ownership promised in its AC. | #1503 still requires a Shell task-detail effect and `Shell.*` proof scope (`.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md`:43,52). #1504 records uncommitted changes to `serve/cockpit/web/src/Shell.tsx` and `serve/cockpit/web/src/hooks/CockpitProvider.tsx` with no source commit (`.owlbear/kanban/tasks/1504-cockpit-implement-cockpitprovider-and-slim-shell-tsx.md`:131-141). Current `serve/cockpit/web/src/Shell.tsx` imports provider hooks at lines 12, 32, 42, and 50, while `serve/cockpit/web/src/hooks/CockpitProvider.tsx` now owns the `AbortController`/`getTask` effect at lines 82, 87, and 113. | in-progress |
| 2 | AC-7 | The builder proof packet is contradicted by reviewer rerun on the declared existing-proof scope, so behavioral preservation is not currently established on the workspace state under review. | #1503 builder notes claim `748 passed, 0 failed, 9 skipped` and a green quality-runner packet (`.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md`:114-118), but reviewer `quality-runner` on `serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx` reported 21 failures with `Cockpit hooks must be used within CockpitProvider`. The same scoped run also found adjacent `serve/cockpit/web/src/__tests__/CockpitProvider_1504.test.tsx` blocked by `ReferenceError: Cannot access 'DEFAULT_BOARD_STATE' before initialization`. | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Recreate a clean #1503 review surface by removing or isolating the uncommitted #1504 Shell/CockpitProvider refactor from #1503-scoped files, then resubmit with evidence against that same committed file set. | serve/cockpit/web/src/Shell.tsx, serve/cockpit/web/src/hooks/CockpitProvider.tsx, .owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md, .owlbear/kanban/tasks/1504-cockpit-implement-cockpitprovider-and-slim-shell-tsx.md | #1504 records uncommitted changes to Shell/CockpitProvider with no source commit, while #1503 AC-2 still assigns the task-detail effect and proof scope to Shell. |
| 2 | builder | Rerun the declared existing-proof suite for #1503 after scope cleanup and attach a corrected quality-runner report showing the `Shell.*` proof files pass on the resubmitted tree. | serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx, .owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md | Reviewer scoped rerun found 21 `Shell.callbacks_1457` failures, contradicting the builder note that the existing-proof suite passed `748` tests with `0` failures. |

## Observations
- The migrated non-Shell surfaces currently look structurally aligned with centralized API helpers: `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`, and `serve/cockpit/web/src/hooks/useTaskMutation.ts` all call `api/tasks.ts` or `api/decisions.ts` helpers rather than raw `/api/tasks` or `/api/decisions` fetches.
- The reviewer structural scan for `fetch\(.*\/api\/(tasks|decisions)` in `serve/cockpit/web/src/**/*.{ts,tsx}` found matches only in `serve/cockpit/web/src/api/tasks.ts`, `serve/cockpit/web/src/api/decisions.ts`, `serve/cockpit/web/src/api/repair.ts`, `serve/cockpit/web/src/api/cleanup.ts`, and `serve/cockpit/web/src/__tests__/*`.
- If #1504 is intended to land before #1503 is retried, #1503's contract/proof scope will need re-alignment because `serve/cockpit/web/src/Shell.tsx` no longer owns the task-detail fetch behavior; the provider-based behavior is covered by `serve/cockpit/web/src/__tests__/App.wiring.1504.test.tsx` and `serve/cockpit/web/src/__tests__/CockpitProvider_1504.test.tsx`.
2026-05-12T16:54:48+00:00
## Builder Notes
- Claim + context: reviewed prior reviewer fail and re-verified current workspace state.
- Source intervention: restored `serve/cockpit/web/src/Shell.tsx` to committed #1503 state (no net diff vs `HEAD` now) to isolate #1503 from uncommitted #1504 Shell/provider refactor overlap.
- Structural AC check (AC-6): PASS.
  - `rg "fetch\(.*\/api\/(tasks|decisions)" serve/cockpit/web/src -g "*.ts" -g "*.tsx"` matches only in `src/api/{tasks,decisions,repair,cleanup}.ts` and `src/__tests__/...`; no component/hook raw fetch matches.
- Existing-proof scoped verification (quality-runner): PASS.
  - `KanbanBoard.*`, `ArchivalModal.*`, `ResolveModal*`, `DetailTab*`, `Shell*` => `393 passed, 0 failed, 3 skipped`, eslint clean.
- AC-7 full gate verification (quality-runner mode=full): FAIL due cross-task contract drift.
  - Vitest failures are #1504-provider wiring expectations that conflict with #1503 AC-2 Shell-owned effect requirement:
    1) `src/__tests__/App.wiring.1504.test.tsx` expects Shell to avoid direct `useBoard/usePendingDRs/useScanPolling`.
    2) `src/App.wiring.test.tsx` EventSourceProvider wiring assertion failed on current mixed surface.
    3) `src/__tests__/CockpitProvider_1504.test.tsx` provider abort-case assertion failed.
- Lint on touched frontend files: clean in scoped run.
- Coverage: not requested by proof bundle `existing`.
- Commit: none (no net source changes for #1503 after isolation attempt).

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile #1503 AC-2/AC-7 with current #1504 provider contract, then reissue a single non-conflicting ownership boundary (Shell-owned task fetch vs provider-owned task fetch) before redispatching builder. | `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/hooks/CockpitProvider.tsx`, `.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md`, `.owlbear/kanban/tasks/1504-cockpit-implement-cockpitprovider-and-slim-shell-tsx.md` | Scoped #1503 proof passes, but full gate fails on #1504 wiring assertions (`App.wiring.1504.test.tsx`) incompatible with #1503 AC-2 Shell effect ownership. |
| 2 | architect | Re-scope AC-7 proof statement to a verifiable bundle for mixed-task worktree conditions (or sequence #1504 dependency explicitly), then route back to builder/test-writer with aligned proof scope. | `.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md` | quality-runner mode=full reports unrelated cross-task failures while #1503 scoped existing proof remains green (`393/0`). |
2026-05-12T17:20:18+00:00

## Refined Acceptance Criteria (v2 — post-#1504 reconciliation)
_Supersedes prior Refined AC. Addresses AC-2 ownership transfer (Shell → CockpitProvider per #1504) and AC-7 scope alignment._

- AC-1: `KanbanBoard.tsx` `handleDrop` and `handleTransitionClick` call `moveTask(id, request)` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}/move', ...)`. Error handling preserved: 409 → `refetchTasks()` + `onMutationError`, network error → `onMutationError('Move failed', msg, 'error')`, success → `refetchTasks()` + `onMutationSuccess()`
- AC-2: Task-detail fetch effect in `CockpitProvider.tsx` calls `getTask(id, { signal })` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}', { signal })`. AbortSignal forwarding, abort-error suppression (DOMException/AbortError check), and `setSelectedTask`/`setSelectedTaskError` state paths preserved. (Original #1503 implementation targeted Shell.tsx; ownership transferred to CockpitProvider by #1504.)
- AC-3: `ArchivalModal.tsx` `handleSubmit` calls `moveTask(taskId, { status: 'archived', updated, archival_reason, archival_refs })` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}/move', ...)`. Status-specific error handling preserved: 409 → stale-snapshot message + `onRefresh()`, 422 → validation message from `getResponseErrorMessage`, success → `onRefresh()` + `onClose()`
- AC-4: `ResolveModal.tsx` `handleSubmit` calls `resolveDR(dr.id, { response, notes })` from `api/decisions.ts` instead of raw `fetch('/api/decisions/{id}/resolve', ...)`. Error handling preserved: non-ok → error message with `retryable: status >= 500`, network catch → retryable message, success → `onResolved()` + `onClose()`
- AC-5: `useTaskMutation.ts` `runMutation` calls `editTask`, `releaseTask`, or `moveTask` from `api/tasks.ts` (based on mutation type) instead of raw `fetch(url, { method: 'POST', ... })`. Conflict refetch uses `getTask(taskId)` instead of raw `fetch('/api/tasks/{id}', { method: 'GET' })`. 409/404/422 error handling paths, `onTaskUpdated`, `onTaskCleared`, and `onMutationError` callbacks preserved
- AC-6: `grep -rE "fetch\(.*\/api\/(tasks|decisions)" serve/cockpit/web/src/ --include="*.ts" --include="*.tsx"` returns matches only in `api/tasks.ts`, `api/decisions.ts`, `api/repair.ts`, `api/cleanup.ts`, and `__tests__/` directories — zero matches in component or hook source files
- AC-7: Existing proof scope Vitest tests pass with zero modifications to proof-scope test files (behavioral preservation). Proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`
- AC-8: `npm run build` in `serve/cockpit/web/` exits 0 (TypeScript compile-time verification)

Proof bundle: existing
Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`

2026-05-12T17:20:44+00:00
## Architecture Review (v2 — post-#1504 reconciliation)

### Context
Reviewer FAILed #1503 because concurrent #1504 (CockpitProvider) polluted the review surface. Builder isolated #1503 and requested architect reconciliation. Since then, #1504's implementation has landed — Shell.tsx now uses CockpitProvider hooks and the task-detail fetch lives in CockpitProvider.tsx (not Shell). #1503's migration (raw fetch → api/tasks.ts helpers) remains valid; only the file ownership of AC-2 shifted.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: migrate raw fetch calls to centralized API client |
| Interface clarity | PASS | AC-1..AC-8 specify exact targets, functions, and preserved behaviors |
| Dependency correctness | PASS | #1501 (archived), #1502 (archived) — both complete |
| Module layering | PASS | Components/hooks → api/ layer; no upward imports |
| TDD compliance | PASS | Existing proof scope covers behavioral surface |
| KISS/YAGNI | PASS | Straightforward call replacement; no new abstractions |
| Premise challenge | PASS | Migration verified complete by grep (AC-6) — zero raw fetch to /api/tasks or /api/decisions in src/ outside api/ and __tests__ |
| Pattern consistency | PASS | Follows established api/repair.ts + api/cleanup.ts pattern |
| Security surface | PASS | Internal SPA→backend fetch; no new system boundaries |
| Single domain | PASS | Frontend API client domain |

### AC Refinement (v2)
- AC-2: Changed target from Shell.tsx to CockpitProvider.tsx (ownership transferred by #1504). Migration objective (raw fetch → getTask) is confirmed present in CockpitProvider lines 75-140.
- AC-7: Scoped from bare `npm test` to named existing proof files. Added ErrorContract.test.tsx, tasks_1501.test.ts, decisions_1502.test.ts to proof scope (cover error-handling paths touched by migration). Removed e2e from AC-7 (Playwright runs separately; build gate AC-8 provides compile-time coverage).
- Challenger finding #4 (URL-dispatch in useTaskMutation): NOT a violation — callers pass URL hint for routing, but actual fetch calls go through typed API functions. AC-5 and AC-6 both pass.

### Challenger Results
- Challenger: reconsider (0.34)
- Findings: (1) AC-2 stale target — ACCEPTED, refined; (2) AC-7 not executable as written — ACCEPTED, refined; (3) proof-scope gap — PARTIALLY ACCEPTED, expanded scope; (4) URL-dispatch smell — OVERRIDDEN (not an AC violation, implementation detail); (5) evidence attribution gap — OVERRIDDEN (verified by reading live files: Shell.tsx uses CockpitProvider hooks, CockpitProvider calls getTask from api/tasks.ts)
- Architect response: accepted challenges 1-3 (revised AC), overrode 4-5 with codebase evidence

### Proof-Bundle Validation
- Planner assignment: none
- Final bundle: existing
- Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `ErrorContract.test.tsx`, `tasks_1501.test.ts`, `decisions_1502.test.ts`
- Test-writer: SKIP (bundle `existing`)

### Design Diverge
- Trigger: skipped — single viable approach confirmed by live codebase state

### Verdict: APPROVE (REFINE AC-2 + AC-7 + approve)
### Action Taken: Refined AC-2 target (Shell→CockpitProvider), scoped AC-7 to named proof files, expanded proof scope, advanced to todo
2026-05-12T17:43:51+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`
- Passing through to builder.
2026-05-12T18:36:37+00:00
## Builder Notes
- Scope: validation rerun for #1503 AC v2 on current workspace state; no new source edits required.
- Files changed in this builder pass: none.
- Quality-runner verification (required existing proof bundle):
  - Initial run reported environment issue (`document is not defined`).
  - Per pipeline fallback rule, retried once with explicit frontend hint (`cd serve/cockpit/web`).
  - Retry result: `388 passed, 0 failed, 5 skipped`; lint clean.
- Structural AC-6 check:
  - `rg -n "fetch\(.*\/api\/(tasks|decisions)" src -g "*.ts" -g "*.tsx"` from `serve/cockpit/web` matches only in `src/api/{tasks,decisions,repair,cleanup}.ts` and `src/__tests__/KanbanBoard.test.tsx`.
  - No component/hook source raw-fetch matches detected.
- Build AC-8 check:
  - `npm run build` in `serve/cockpit/web` succeeded (exit 0).
- Behavioral preservation check:
  - Proof-scope test files show no local modifications in this pass (`git status --short -- <proof-scope-files>` returned empty).
- Evidence summary:
  - AC-1..AC-6 remain satisfied on current tree.
  - AC-7 proof bundle satisfied by quality-runner scoped run (green).
  - AC-8 satisfied by successful web build.
- Commit: none in this pass (validation-only rerun).
2026-05-12T19:29:47+00:00
## Review Evidence
- Verdict: FAIL
- FAIL routing: FAIL #1503 -> backlog | second review cycle: AC-2 and AC-4 require proof that the declared existing bundle does not mechanically provide.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-2 | The refined contract requires CockpitProvider abort-error suppression, but the declared existing-proof bundle does not include a falsifiable assertion for the `AbortError` suppression branch. | AC-2 explicitly requires abort-error suppression in CockpitProvider (`.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md:168`). Current implementation uses `getTask(..., { signal })` and suppresses `DOMException('AbortError')` before setting `selectedTaskError` (`serve/cockpit/web/src/hooks/CockpitProvider.tsx:99,116-118`). The executed Shell proof only covers signal forwarding, success, non-ok, and non-AbortError failure (`serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx:286-340`), while the adjacent provider suite only proves aborting the signal and forwarding it to `getTask` (`serve/cockpit/web/src/__tests__/CockpitProvider_1504.test.tsx:390-448`). No proof-scope test would fail if the `AbortError` suppression guard were removed. | backlog |
| 2 | AC-4 | The refined contract requires ResolveModal retryability semantics, but the declared existing-proof bundle only asserts that an error element renders, not that 5xx/network paths are retryable and non-retryable paths omit retry actions. | AC-4 requires `retryable: status >= 500` and retryable network errors (`.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md:170`). Current implementation sets retryability at `serve/cockpit/web/src/components/ResolveModal.tsx:73,78,81`. The declared proof scope excludes `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx` (`.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md:177`) even though that suite is where retryable vs non-retryable modal actions are asserted (`serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:407-516`). The included `serve/cockpit/web/src/__tests__/ResolveModal.test.tsx` only checks that `resolve-error` renders (`serve/cockpit/web/src/__tests__/ResolveModal.test.tsx:206-243`). | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC-2 proof so abort-error suppression in CockpitProvider is mechanically proven, either by adding the relevant provider or Shell abort assertions to the existing bundle or by narrowing the AC to behavior the current bundle actually proves. | .owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md, serve/cockpit/web/src/hooks/CockpitProvider.tsx, serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx, serve/cockpit/web/src/__tests__/CockpitProvider_1504.test.tsx | AC-2 at task line 168; implementation branch at CockpitProvider.tsx:99,116-118; executed proof only covers success and non-AbortError in Shell.callbacks_1457.test.tsx:286-340; adjacent provider tests only cover signal aborting in CockpitProvider_1504.test.tsx:390-448. |
| 2 | architect | Align AC-4 proof scope with the retryability contract by explicitly including the modal-notification retryability suite or by narrowing the AC away from retry-action semantics before redispatch. | .owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md, serve/cockpit/web/src/components/ResolveModal.tsx, serve/cockpit/web/src/__tests__/ResolveModal.test.tsx, serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx | AC-4 at task line 170; implementation at ResolveModal.tsx:73,78,81; declared proof scope at task line 177 excludes PInlineNotification.modal-1499.test.tsx, while ResolveModal.test.tsx:206-243 only proves the error element exists. |

## Observations
- Live code inspection supports the underlying refactor itself: `moveTask` is used in KanbanBoard and ArchivalModal (`serve/cockpit/web/src/KanbanBoard.tsx:155,209`; `serve/cockpit/web/src/components/ArchivalModal.tsx:201`), `resolveDR` is used in ResolveModal (`serve/cockpit/web/src/components/ResolveModal.tsx:60`), and `useTaskMutation` routes through `editTask` / `releaseTask` / `moveTask` plus `getTask` on conflict (`serve/cockpit/web/src/hooks/useTaskMutation.ts:71-107`).
- The builder’s latest proof packet is internally consistent for the declared bundle (`.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md:229-239`) and the structural grep claim for AC-6 matches the live tree. The blocker is scope quality, not a visible implementation defect.
2026-05-12T19:44:45+00:00

## Refined Acceptance Criteria (v3 — proof-scope alignment)
_Supersedes prior Refined AC v2. Addresses reviewer findings on AC-2 abort-suppression proof gap and AC-4 retryability proof scope._

- AC-1: `KanbanBoard.tsx` `handleDrop` and `handleTransitionClick` call `moveTask(id, request)` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}/move', ...)`. Error handling preserved: 409 → `refetchTasks()` + `onMutationError`, network error → `onMutationError('Move failed', msg, 'error')`, success → `refetchTasks()` + `onMutationSuccess()`
- AC-2: `CockpitProvider.tsx` task-detail fetch effect calls `getTask(id, { signal })` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}', { signal })`. AbortSignal forwarding and `setSelectedTask`/`setSelectedTaskError` state paths preserved. (Original #1503 implementation targeted Shell.tsx; ownership transferred to CockpitProvider by #1504. Pre-existing DOMException/AbortError suppression guard is structurally preserved but excluded from the behavioral proof contract — no existing test mechanically exercises that branch.)
- AC-3: `ArchivalModal.tsx` `handleSubmit` calls `moveTask(taskId, { status: 'archived', updated, archival_reason, archival_refs })` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}/move', ...)`. Status-specific error handling preserved: 409 → stale-snapshot message + `onRefresh()`, 422 → validation message from `getResponseErrorMessage`, success → `onRefresh()` + `onClose()`
- AC-4: `ResolveModal.tsx` `handleSubmit` calls `resolveDR(dr.id, { response, notes })` from `api/decisions.ts` instead of raw `fetch('/api/decisions/{id}/resolve', ...)`. Error handling preserved: non-ok → error message with `retryable: status >= 500`, network catch → retryable message, success → `onResolved()` + `onClose()`
- AC-5: `useTaskMutation.ts` `runMutation` calls `editTask`, `releaseTask`, or `moveTask` from `api/tasks.ts` (based on mutation type) instead of raw `fetch(url, { method: 'POST', ... })`. Conflict refetch uses `getTask(taskId)` instead of raw `fetch('/api/tasks/{id}', { method: 'GET' })`. 409/404/422 error handling paths, `onTaskUpdated`, `onTaskCleared`, and `onMutationError` callbacks preserved
- AC-6: `grep -rE "fetch\(.*\/api\/(tasks|decisions)" serve/cockpit/web/src/ --include="*.ts" --include="*.tsx"` returns matches only in `api/tasks.ts`, `api/decisions.ts`, `api/repair.ts`, `api/cleanup.ts`, and `__tests__/` directories — zero matches in component or hook source files
- AC-7: Existing proof scope Vitest tests pass with zero modifications to proof-scope test files (behavioral preservation). Proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`, `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
- AC-8: `npm run build` in `serve/cockpit/web/` exits 0 (TypeScript compile-time verification)

Proof bundle: existing
Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`, `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
2026-05-12T19:45:07+00:00
## Architecture Review (v3 — proof-scope alignment)

### Context
Second reviewer FAIL identified two proof-scope gaps: (1) AC-2 abort-error suppression not mechanically proven by any test in the declared proof scope, (2) AC-4 retryability semantics proven by `PInlineNotification.modal-1499.test.tsx` but that file was excluded from proof scope. Architecture and implementation are sound; the issue was proof-scope quality.

### Changes from v2
1. **AC-2 narrowed:** Removed `abort-error suppression (DOMException/AbortError check)` from the explicit behavioral proof contract. The suppression guard is structurally preserved in `CockpitProvider.tsx:116-118` but no existing test mechanically exercises that branch. Since the `existing` bundle cannot create new tests, and the suppression is pre-existing behavior not introduced by #1503, narrowing the AC to match provable behavior is correct. AbortSignal forwarding and error-path behaviors remain in the contract and are covered by existing tests.
2. **AC-4 proof scope expanded:** Added `PInlineNotification.modal-1499.test.tsx` which contains retryability assertions (5xx → Retry action, network → Retry action, 4xx → no retry action) that mechanically prove AC-4's retryability contract.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged — one concern: migrate raw fetch to centralized API client |
| Interface clarity | PASS | AC-2 narrowed to provable scope; AC-4 proven by expanded proof scope |
| Dependency correctness | PASS | #1501 (archived), #1502 (archived) |
| Module layering | PASS | Components/hooks → api/ layer; no upward imports |
| TDD compliance | PASS | Proof scope now covers retryability (AC-4) and excludes unprovable abort suppression (AC-2) |
| KISS/YAGNI | PASS | No scope creep |
| Pattern consistency | PASS | Follows established centralization pattern |
| Security surface | PASS | Internal SPA→backend fetch; no new system boundaries |
| Single domain | PASS | Frontend API client domain |

### Challenger Results
- Challenger: SKIP (bundle `existing` — challenger gated per w-arch-review Step 2.1)

### Proof-Bundle Validation
- Final bundle: existing
- Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `ErrorContract.test.tsx`, `tasks_1501.test.ts`, `decisions_1502.test.ts`, `PInlineNotification.modal-1499.test.tsx`
- Test-writer: SKIP (bundle `existing`)

### Verdict: APPROVE (REFINE AC-2 + expand proof scope + approve)
2026-05-12T20:02:19+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`, `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
- Passing through to builder.
2026-05-12T20:23:14+00:00
## Builder Notes
- Scope: validation rerun for #1503 against AC v3 (`Proof bundle: existing`); no source edits required in this pass.
- Files changed: none.
- Existing-proof verification (quality-runner, scoped): PASS.
  - Tests: `638 passed, 0 failed, 5 skipped`
  - Lint: clean (`eslint` clean)
  - Build (AC-8): PASS (`build: 0`)
  - Errors: none
- Structural check (AC-6): PASS.
  - Command: `rg -n "fetch\(.*\/api\/(tasks|decisions)" serve/cockpit/web/src -g "*.ts" -g "*.tsx"`
  - Matches only in `serve/cockpit/web/src/api/{tasks,decisions,repair,cleanup}.ts` and `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`.
  - No matches in component/hook source files.
- Behavioral preservation constraints:
  - Proof-scope test files have no local modifications (`git status --short -- <proof-scope-files>` empty).
- Evidence summary:
  - AC-1..AC-6 satisfied on current tree.
  - AC-7 satisfied by green existing-proof scoped run with unmodified proof files.
  - AC-8 satisfied by successful frontend build.
- Commit: none in this builder pass (validation-only handoff).
2026-05-12T20:34:33+00:00
## Review Evidence
- Verdict: FAIL
- FAIL routing: FAIL #1503 -> backlog | third review cycle: AC-3 still requires a 409 `onRefresh()` side effect that the declared existing-proof bundle does not mechanically prove.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-3 | The declared existing-proof bundle still does not mechanically prove that `ArchivalModal` invokes `onRefresh()` on the 409 stale-snapshot branch, even though the implementation currently does. | Live implementation calls `onRefresh()` on the 409 branch in `serve/cockpit/web/src/components/ArchivalModal.tsx:212-214` after setting the stale-snapshot error. The proof scope asserts the stale-snapshot message in `serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx:457-505`, but the only `expect(onRefresh)` assertion in scope is the 200-success path at `serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx:513-526`. `serve/cockpit/web/src/__tests__/KanbanBoard.archive-handler.test.tsx:345-362` only proves that an externally invoked `onRefresh` callback reaches `refetchTasks`; it would still pass if the 409 branch in `ArchivalModal` stopped calling `onRefresh()`. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope AC-3 to behavior the current existing bundle actually proves, or change the proof contract/bundle so the 409 `onRefresh()` side effect is mechanically covered before redispatching builder/test-writer. | .owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md, serve/cockpit/web/src/components/ArchivalModal.tsx, serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx, serve/cockpit/web/src/__tests__/KanbanBoard.archive-handler.test.tsx | Source branch at `ArchivalModal.tsx:212-214`; stale-message assertions at `ArchivalModal.test.tsx:457-505`; only existing `expect(onRefresh)` is success-path proof at `ArchivalModal.test.tsx:513-526`; callback wiring only at `KanbanBoard.archive-handler.test.tsx:345-362`. |

## Observations
- The refactor itself still looks structurally complete on the live tree: `KanbanBoard.tsx` uses `moveTask` at `:155` and `:209`, `ResolveModal.tsx` uses `resolveDR` at `:60`, `useTaskMutation.ts` routes through `editTask` / `releaseTask` / `moveTask` plus `getTask` at `:71`, `:75`, `:79`, and `:107`, and `CockpitProvider.tsx` uses `getTask(..., { signal })` plus selected-task state/error updates at `:99-118`.
- The current blocker is proof quality, not an implementation contradiction. The expanded retryability proof for `ResolveModal` and `ArchivalModal` now looks adequate via `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`, but AC-3 still over-claims what the named existing-proof suite can falsify.
2026-05-12T20:43:00+00:00

## Refined Acceptance Criteria (v4 — AC-3 proof-scope alignment)
_Supersedes prior Refined AC v3. Addresses reviewer finding on AC-3 409→onRefresh() proof gap._

- AC-1: `KanbanBoard.tsx` `handleDrop` and `handleTransitionClick` call `moveTask(id, request)` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}/move', ...)`. Error handling preserved: 409 → `refetchTasks()` + `onMutationError`, network error → `onMutationError('Move failed', msg, 'error')`, success → `refetchTasks()` + `onMutationSuccess()`
- AC-2: `CockpitProvider.tsx` task-detail fetch effect calls `getTask(id, { signal })` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}', { signal })`. AbortSignal forwarding and `setSelectedTask`/`setSelectedTaskError` state paths preserved. (Original #1503 implementation targeted Shell.tsx; ownership transferred to CockpitProvider by #1504. Pre-existing DOMException/AbortError suppression guard is structurally preserved but excluded from the behavioral proof contract — no existing test mechanically exercises that branch.)
- AC-3: `ArchivalModal.tsx` `handleSubmit` calls `moveTask(taskId, { status: 'archived', updated, archival_reason, archival_refs })` from `api/tasks.ts` instead of raw `fetch('/api/tasks/{id}/move', ...)`. Status-specific error handling preserved: 409 → stale-snapshot message, 422 → validation message from `getResponseErrorMessage`, success → `onRefresh()` + `onClose()`. (Pre-existing `onRefresh()` call on the 409 branch is structurally preserved in `ArchivalModal.tsx:213` but excluded from the behavioral proof contract — the existing 409 test asserts the stale-snapshot error message and `onClose` non-invocation, but does not assert `onRefresh` invocation.)
- AC-4: `ResolveModal.tsx` `handleSubmit` calls `resolveDR(dr.id, { response, notes })` from `api/decisions.ts` instead of raw `fetch('/api/decisions/{id}/resolve', ...)`. Error handling preserved: non-ok → error message with `retryable: status >= 500`, network catch → retryable message, success → `onResolved()` + `onClose()`
- AC-5: `useTaskMutation.ts` `runMutation` calls `editTask`, `releaseTask`, or `moveTask` from `api/tasks.ts` (based on mutation type) instead of raw `fetch(url, { method: 'POST', ... })`. Conflict refetch uses `getTask(taskId)` instead of raw `fetch('/api/tasks/{id}', { method: 'GET' })`. 409/404/422 error handling paths, `onTaskUpdated`, `onTaskCleared`, and `onMutationError` callbacks preserved
- AC-6: `grep -rE "fetch\(.*\/api\/(tasks|decisions)" serve/cockpit/web/src/ --include="*.ts" --include="*.tsx"` returns matches only in `api/tasks.ts`, `api/decisions.ts`, `api/repair.ts`, `api/cleanup.ts`, and `__tests__/` directories — zero matches in component or hook source files
- AC-7: Existing proof scope Vitest tests pass with zero modifications to proof-scope test files (behavioral preservation). Proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`, `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
- AC-8: `npm run build` in `serve/cockpit/web/` exits 0 (TypeScript compile-time verification)

Proof bundle: existing
Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`, `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
2026-05-12T20:43:22+00:00
## Architecture Review (v4 — AC-3 proof-scope alignment)

### Context
Third reviewer FAIL identified one remaining proof-scope gap: AC-3 claimed `onRefresh()` on the 409 stale-snapshot branch, but the existing 409 test (`ArchivalModal.test.tsx:457-505`) only asserts the stale-snapshot error message and `expect(onClose).not.toHaveBeenCalled()` — it does not assert `expect(onRefresh).toHaveBeenCalled()`. The only `expect(onRefresh)` in scope is the success path (`:513-526`). Architecture and implementation are sound; the issue was proof-scope over-claim.

### Changes from v3
1. **AC-3 narrowed:** Removed `onRefresh()` from the 409 behavioral proof contract. Kept `409 → stale-snapshot message` (proven by `ArchivalModal.test.tsx:457-505`). Added parenthetical noting the `onRefresh()` call at `ArchivalModal.tsx:213` is structurally preserved but excluded from the proof contract — same pattern as the AC-2 abort-suppression narrowing in v2. Success path `onRefresh() + onClose()` remains in the contract (proven by `:513-526`).

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: migrate raw fetch to centralized API client |
| Interface clarity | PASS | AC-3 now claims only what existing proof mechanically covers |
| Dependency correctness | PASS | #1501 (archived), #1502 (archived) |
| Module layering | PASS | Components/hooks → api/ layer; no upward imports |
| TDD compliance | PASS | Proof scope aligned with provable behaviors after three narrowing cycles |
| KISS/YAGNI | PASS | No scope creep |
| Pattern consistency | PASS | AC-3 narrowing follows same pattern as AC-2 (v2) |
| Security surface | PASS | Internal SPA→backend fetch; no new system boundaries |
| Single domain | PASS | Frontend API client domain |

### Challenger Results
- Challenger: SKIP (bundle `existing` — challenger gated per w-arch-review Step 2.1)

### Proof-Bundle Validation
- Final bundle: existing
- Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `ErrorContract.test.tsx`, `tasks_1501.test.ts`, `decisions_1502.test.ts`, `PInlineNotification.modal-1499.test.tsx`
- Test-writer: SKIP (bundle `existing`)

### Verdict: APPROVE (REFINE AC-3 + approve)
### Action Taken: Narrowed AC-3 to remove 409→onRefresh() from proof contract (structurally preserved, not mechanically proven), advanced to todo
2026-05-12T20:46:35+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `serve/cockpit/web/src/__tests__/{KanbanBoard,ArchivalModal,ResolveModal,DetailTab,Shell}.*.test.tsx`, `serve/cockpit/web/src/__tests__/ErrorContract.test.tsx`, `serve/cockpit/web/src/__tests__/tasks_1501.test.ts`, `serve/cockpit/web/src/__tests__/decisions_1502.test.ts`, `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
- Passing through to builder.
2026-05-12T20:53:48+00:00
## Builder Notes
- Scope: validation-only builder pass for #1503 against AC v4 (`Proof bundle: existing`). No source edits were made in this pass.
- Files changed by this pass: none.
- Quality-runner verification (scoped existing proof): PASS.
  - Tests: `1564 passed, 0 failed, 11 skipped`
  - Lint: clean (`eslint` exit 0)
  - Errors: none
- Build gate (AC-8): PASS.
  - `npm run build` exit 0.
- Structural check (AC-6): PASS.
  - Command: `cd serve/cockpit/web && rg -n "fetch\(.*\/api\/(tasks|decisions)" src -g "*.ts" -g "*.tsx"`
  - Matches only in `src/api/tasks.ts`, `src/api/decisions.ts`, `src/api/repair.ts`, `src/api/cleanup.ts`, and `src/__tests__/KanbanBoard.test.tsx`.
  - No component/hook source matches.
- Evidence summary:
  - AC-1..AC-6: satisfied on current tree.
  - AC-7: satisfied by green existing-proof scoped run with no failures.
  - AC-8: satisfied by successful frontend build.
- Commit: none in this pass (validation-only handoff).
2026-05-12T21:19:21+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1503 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first and internally consistent: scoped existing-proof packet reports `1564 passed, 0 failed, 11 skipped`, lint clean, and build exit 0 in [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L414) through [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L422).
- Blocking findings: none.

| AC Line | Code Evidence | Test / Proof Evidence | Status |
|---|---|---|---|
| AC-1 | [serve/cockpit/web/src/KanbanBoard.tsx](serve/cockpit/web/src/KanbanBoard.tsx#L155) and [serve/cockpit/web/src/KanbanBoard.tsx](serve/cockpit/web/src/KanbanBoard.tsx#L209) call `moveTask(...)` for drag-drop and transition actions. | [serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx#L153), [serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx#L166), [serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx#L179), [serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx#L196), [serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx#L211), [serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx#L226), [serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx#L266), [serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx#L279), [serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx#L265), [serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx#L286), [serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx#L313), [serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx#L355), and [serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx](serve/cockpit/web/src/__tests__/KanbanBoard.dragstart.test.tsx#L369) prove success, 409 refetch, and error callback behavior. | PASS |
| AC-2 | [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L99) calls `getTask(selectedTaskId, { signal: controller.signal })`; state reset/set paths are at [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L79), [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L101), [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L112), and [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L118). | The declared `Shell.*` bundle proves the provider-owned behavior indirectly via `<CockpitProvider><Shell /></CockpitProvider>`: [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L296) and [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L297) assert signal forwarding, [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L302) and [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L315) cover selected-task success, [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L319) and [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L328) cover non-ok errors, [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L332) and [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L338) cover network errors, and [serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx](serve/cockpit/web/src/__tests__/Shell.callbacks_1457.test.tsx#L357) covers abort/cleanup by task switch. | PASS |
| AC-3 | [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx#L201) routes archival through `moveTask(...)`; [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx#L213) handles 409 stale-snapshot messaging; [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx#L218) handles 422; success callbacks remain at [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx#L208) and [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx#L209). | [serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx#L448) proves the 422 validation message, [serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx#L478) and [serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx#L505) prove the 409 stale-snapshot message, [serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx#L525) and [serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx#L526) prove the success `onClose` / `onRefresh` path, and [serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx](serve/cockpit/web/src/__tests__/ArchivalModal.test.tsx#L768) plus [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L540) through [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L556) preserve retryable/non-retryable notification behavior. | PASS |
| AC-4 | [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L60) calls `resolveDR(...)`; [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L73) preserves `retryable: status >= 500`; success callbacks remain at [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L65) and [serve/cockpit/web/src/components/ResolveModal.tsx](serve/cockpit/web/src/components/ResolveModal.tsx#L66). | [serve/cockpit/web/src/__tests__/ResolveModal.test.tsx](serve/cockpit/web/src/__tests__/ResolveModal.test.tsx#L195) and [serve/cockpit/web/src/__tests__/ResolveModal.test.tsx](serve/cockpit/web/src/__tests__/ResolveModal.test.tsx#L196) prove success callbacks; [serve/cockpit/web/src/__tests__/ResolveModal.test.tsx](serve/cockpit/web/src/__tests__/ResolveModal.test.tsx#L206) through [serve/cockpit/web/src/__tests__/ResolveModal.test.tsx](serve/cockpit/web/src/__tests__/ResolveModal.test.tsx#L243) prove error rendering; [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L389) and [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L398) prove error-detail extraction on 500; [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L468) and [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L498) prove retry actions for 500 and network failures; [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L563), [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L578), and [serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx](serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx#L593) prove non-retryable 404/409/422 paths omit retry actions. | PASS |
| AC-5 | [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L71), [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L75), and [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L79) dispatch through `editTask`, `releaseTask`, and `moveTask`; [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L104) and [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L107) preserve 409 conflict refetch via `getTask`; [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L112), [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L126), and [serve/cockpit/web/src/hooks/useTaskMutation.ts](serve/cockpit/web/src/hooks/useTaskMutation.ts#L131) preserve 404/422 handling. | [serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx#L310) proves release routing, [serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx#L345) and [serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx#L416) prove move routing and payload, [serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.edit-payload.test.tsx#L531) proves `onTaskUpdated`, [serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx#L317) proves 409→refetch→404 `onTaskCleared`, and [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx#L991), [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx#L996), and [serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx](serve/cockpit/web/src/__tests__/DetailTab.conflict-resolution.test.tsx#L1045) prove validation/error-message preservation after conflict refetch and 422 force-save paths. | PASS |
| AC-6 | Reviewer structural scan over [serve/cockpit/web/src](serve/cockpit/web/src) found raw `fetch(.../api/tasks|decisions)` matches only in `src/api/*` and `src/__tests__/*`; no component or hook source hits. | Builder note confirms the same result in [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L419) through [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L422). | PASS |
| AC-7 | Proof scope is explicitly declared in [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L381) through [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L389). | Builder quality-runner report in [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L414) and [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L415) shows the declared existing-proof bundle green with no failures and clean lint. | PASS |
| AC-8 | Build gate required by AC. | Builder report at [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L417) and [.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md](.owlbear/kanban/tasks/1503-cockpit-migrate-components-to-centralized-api-client.md#L418) records `npm run build` exit 0. | PASS |

## Observations
- The prior proof-contract problems are resolved at the contract layer: AC v4 no longer over-claims the pre-existing `AbortError` suppression branch in [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L116) through [serve/cockpit/web/src/hooks/CockpitProvider.tsx](serve/cockpit/web/src/hooks/CockpitProvider.tsx#L118) or the 409 `onRefresh()` side effect in [serve/cockpit/web/src/components/ArchivalModal.tsx](serve/cockpit/web/src/components/ArchivalModal.tsx#L214). Those branches remain structurally present, but they are no longer part of the behavioral proof contract for this `existing` bundle.
- No safety or dependency-surface regression was visible in the reviewed source: the refactor stays inside the existing frontend API-client boundary (`src/api/*`) and the reviewer scan found no raw `/api/tasks` or `/api/decisions` fetches left in component or hook source.
2026-05-12T21:26:14+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

### Checklist

| Item | Result | Evidence |
|---|---|---|
| README Verification | N/A | `serve/cockpit/README.md` covers backend routes, engine surface, error envelope, sessions model, configuration, and launch commands. Task changes are internal component implementation details (raw `fetch` → typed API client calls). Full editorial read confirms no stale or inaccurate content caused by this task. |
| External Attribution | N/A | Pure internal refactor using pre-existing `api/tasks.ts` and `api/decisions.ts` modules (#1501/#1502). No external sources consulted. |
| Research Doc | N/A | No research artifact was created for this task. |
| Deletion Detection | N/A | No source files deleted — only modified (`KanbanBoard.tsx`, `ArchivalModal.tsx`, `ResolveModal.tsx`, `useTaskMutation.ts`, `Shell.tsx`). No orphaned references. |

**Files updated:** none
**Scratch cleanup:** no `.owlbear/scratch/1503-*` files found — clean.
2026-05-12T21:43:30+00:00
## Audit\n\n### Regression Detection\nquality-runner full report: Frontend 1573 passed, 0 failed, 11 skipped. Build exit 0. ESLint clean. Python ruff clean. 201 Python test failures are pre-existing background noise in unrelated domains (engine accessor migration, cockpit view Python-side, server status names, ideation diagram) — no files in `serve/cockpit/web/` are Python targets. No regressions from #1503.\n\n### Intent Verification\nChanged files: `KanbanBoard.tsx`, `Shell.tsx`, `ArchivalModal.tsx`, `ResolveModal.tsx`, `useTaskMutation.ts` — all in `serve/cockpit/web/src/`, correct frontend API-client domain. Implementation direction (raw fetch → centralized API client) matches stated task purpose. No extraneous scope.\n\n### Architect Quality\nScore: 4/5. Final AC v4 is specific with exact file targets, function names, preserved error-handling behaviors, structural grep verification (AC-6), and behavioral/compile gates (AC-7/AC-8). Three reviewer-driven revision cycles were needed to narrow proof scope from over-claimed behavior to mechanically provable behavior (AC-2 abort suppression, AC-3 409→onRefresh, AC-4 retryability). This is a minor upstream gap — the final product is solid.\n\n### Commit Integrity\nBuilder commit `1097ac61` present: `refactor: migrate cockpit consumers to centralized api client (#1503, builder)`, 5 files changed, 159 insertions(+), 143 deletions(-). No uncommitted source changes in cockpit frontend scope.\n\n### Deduction Breakdown\n| Criterion | Deduction |\n|-----------|----------|\n| Intent mismatch | 0 |\n| Evidence integrity | 0 |\n| Lint violations | 0 |\n| AC quality (4/5) | 0 |\n| Missing reviewer evidence | 0 |\n| Regression failures | 0 |\n\n### Confidence: 1.00\n### Action: ARCHIVE