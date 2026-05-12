---
id: 1503
title: 'Cockpit: Migrate components to centralized API client'
status: backlog
priority: needed
created: 2026-05-12T02:43:28.748468+00:00
updated: 2026-05-12T16:54:48.671744+00:00
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
archival_reason:
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