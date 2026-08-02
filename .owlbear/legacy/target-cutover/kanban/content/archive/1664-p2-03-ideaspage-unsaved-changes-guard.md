---
id: 1664
title: 'P2-03: IdeasPage — unsaved-changes guard'
status: archived
priority: medium
created: 2026-05-18T17:42:08.375696+02:00
updated: 2026-05-20T17:59:32.650489+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1658
depends_on:
  - 1638
  - 1662
ac:
  - When IdeasPage content is dirty and the user navigates to a different route,
    a confirmation dialog with `alertdialog` role renders displaying 'You have 
    unsaved changes. Leave anyway?' with proceed/cancel actions; clicking 
    proceed completes the navigation, clicking cancel dismisses the dialog and 
    the user remains on IdeasPage
  - When IdeasPage content is dirty, a `beforeunload` event handler calls 
    `event.preventDefault()` triggering the browser's native leave-page prompt 
    on tab/window close
  - When IdeasPage content is clean (content equals lastSavedContent), route 
    navigation proceeds without blocking and no `beforeunload` handler is 
    registered
  - Event listeners (`beforeunload`) are removed on component unmount
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Uses React Router's navigation blocking API (`useBlocker` or equivalent from #1638's router setup) for SPA route transitions. `beforeunload` for browser close/refresh.

Dialog text: "You have unsaved changes. Leave anyway?"

## In Scope

- Route navigation blocking via React Router when dirty
- `beforeunload` event listener when dirty
- Confirmation dialog with proceed/cancel actions
- Cleanup of event listeners on unmount

## Out of Scope

- Dirty-state tracking itself (owned by P2-01)
- External-edit conflict resolution (separate task)
- Custom dialog styling beyond PDS defaults

[[2026-05-20T15:56:48+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Only unsaved-changes guard logic — no dirty-state tracking (owned by P2-01) |
| Interface clarity | PASS | AC specifies observable outcomes: dialog text, role, proceed/cancel behavior, beforeunload semantics |
| Dependency correctness | PASS | #1638 (router/tabs) archived, #1662 (IdeasPage core with isDirty) archived |
| Module layering | PASS | IdeasPage consumes useBlocker from react-router and renders dialog — no upward imports |
| TDD compliance | PASS | proof_bundle=behavioral, test-writer will create router-context tests (MemoryRouter pattern exists in Shell.tab-routing tests) |
| KISS/YAGNI | PASS | Minimal scope: one hook (useBlocker), one useEffect (beforeunload), one dialog |
| Premise challenge | PASS | No built-in IDE/runtime equivalent for SPA route blocking + beforeunload |
| Pattern consistency | PASS | BrowserRouter in App.tsx, PModal/ConfirmDialog patterns exist; builder chooses implementation |
| Security surface | PASS | No new system boundaries — purely client-side UX guard |
| Single domain | PASS | cockpit-web frontend only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| useBlocker | Router context missing | blocker undefined/throws | IdeasPage rendered inside BrowserRouter in App.tsx | None (structurally prevented) |
| beforeunload | Listener leak on HMR | No exception, stale listener | AC4 requires cleanup on unmount | Stale prompt on unrelated navigation |

### Design Diverge
- Trigger: skipped — single obvious approach (useBlocker + beforeunload useEffect + dialog)

### Challenge Results
- Challenger: reconsider (0.71) — AC-quality issues on all 3 original lines; ConfirmDialog exists for confirmations (typed for kanban ops, not general-purpose); PModal lock-in inappropriate
- Architect response: accepted — refined all AC lines to specify observables (alertdialog role, exact text, input/output pairs); added AC4 for cleanup; dropped PModal naming per challenger's correct identification that ConfirmDialog is kanban-typed and implementation choice belongs to builder

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (router-aware test harness needed — MemoryRouter wrapper pattern from Shell.tab-routing_1639.test.tsx)

### Verdict: APPROVE
### Action Taken: Refined AC (4 lines with specific observables, alertdialog role, exact dialog text, cleanup requirement). Advanced to todo.

[[2026-05-20T16:13:44+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx
- Classes: TestFromAC_UnsavedChangesNavGuard, TestFromAC_BeforeUnloadDirty, TestFromAC_CleanStateNoBlock, TestFromAC_EventListenerCleanup
- Tests per category: happy 7, edge 1, error 0, boundary 2, regression-guards 2
- Total: 12 tests, 10 FAIL, 2 PASS
- ESLint: clean

## AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1: dirty + navigate → alertdialog with text, proceed/cancel | 6 tests (alertdialog renders, text, nav blocked, proceed completes nav, cancel keeps page, one-char boundary) | FAIL ✓ |
| AC2: dirty → beforeunload calls preventDefault | 2 tests (dirty state, one-char boundary) | FAIL ✓ |
| AC3: clean → no block, no beforeunload handler | 2 tests | PASS (regression guards) |
| AC4: beforeunload removed on unmount | 2 tests (behavioral unmount check, dirty→clean transition) | FAIL ✓ |

## Regression-Guard Note
AC3 tests pass in RED by design: negative-behavior constraints ("no blocking when clean") are trivially true when no blocking implementation exists. These are retained as regression guards to prevent the implementation from over-blocking clean navigation.

[[2026-05-20T16:46:16+02:00]]
## Builder Notes
- Implementation: serve/cockpit/web/src/pages/IdeasPage.tsx
- Approach: added dirty-state navigation guard with router navigator interception fallback and dirty-only beforeunload handling; rendered an alertdialog with proceed/cancel actions that either complete or cancel pending navigation.
- Fixes applied:
  - Replaced data-router-only blocker usage with router-context navigator interception to support current MemoryRouter-based test harness.
  - Added cleanup for pending transitions/dialog state on dirty-state changes and unmount.
  - Added null-safe navigation context handling to avoid crashes when router context is absent in non-router render paths.
- Tests (quality-runner):
  - serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx -> 12 passed, 0 failed
  - serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx + serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx -> 43 passed, 0 failed
- Lint: clean (eslint) for serve/cockpit/web/src/pages/IdeasPage.tsx and task test file.
- Coverage: src/pages/IdeasPage.tsx = 84.21% (scoped run with 1662+1664 suites); below 90% due existing out-of-scope branches in IdeasPage not covered by this task’s proof bundle.
- Commit: 3d6378773fea355520fe1ce63987673988fbb412

[[2026-05-20T17:11:43+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: FAIL #1664 -> todo | AC1 behavioral proof is too narrow for the production router surface.
- Builder evidence reviewed first: task suite `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx` reported 12 passed / 0 failed, adjacent IdeasPage suites reported 43 passed / 0 failed, eslint was clean, and scoped coverage for `src/pages/IdeasPage.tsx` was 84.21%.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/pages/IdeasPage.tsx:119-175,249-257` blocks via `navigator.block` when present, otherwise patches `navigator.push` / `navigator.replace` / `navigator.go` and renders the `alertdialog` with the required text | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:19,37,47-53,89-170` proves only a `MemoryRouter` harness with a helper button that calls `useNavigate('/')` | FAIL — proof does not cover the production `BrowserRouter` history surface even though the task contract is route-navigation blocking in the shipped app |
| AC2 | `serve/cockpit/web/src/pages/IdeasPage.tsx:204-210` registers dirty-only `beforeunload` and calls `event.preventDefault()` | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:177-194` | PASS |
| AC3 | `serve/cockpit/web/src/pages/IdeasPage.tsx:94-105,142-210` clears pending state when clean and does not register `beforeunload` when clean | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:203-222` | PASS for the tested `MemoryRouter` / `useNavigate` path |
| AC4 | `serve/cockpit/web/src/pages/IdeasPage.tsx:208-210` removes `beforeunload` on cleanup | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:234-287` | PASS |

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC1 | The task's behavioral proof only exercises a `MemoryRouter` helper that calls `useNavigate`, but production runs under `BrowserRouter` (`serve/cockpit/web/src/App.tsx:2,21-29`). The current implementation depends on `UNSAFE_NavigationContext` and, in current router setups, falls back to patching `navigator.push` / `navigator.replace` / `navigator.go` (`serve/cockpit/web/src/pages/IdeasPage.tsx:2,119-175`). React Router's shipped history surface for this app exposes `push`, `replace`, `go`, and `listen`, and browser history changes are driven via `popstate` listener handling (`serve/cockpit/web/node_modules/react-router/dist/development/data-BqZ2x964.d.ts:130-170`; `serve/cockpit/web/node_modules/react-router/dist/development/chunk-D6LUOGOQ.js:337-344`). The current tests do not prove dirty-route blocking on that production history surface, so the AC1 proof is insufficient for a `behavioral` bundle. | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:19,37,47-53,89-170`; `serve/cockpit/web/src/App.tsx:2,21-29`; `serve/cockpit/web/src/pages/IdeasPage.tsx:2,119-175`; `serve/cockpit/web/node_modules/react-router/dist/development/data-BqZ2x964.d.ts:130-170`; `serve/cockpit/web/node_modules/react-router/dist/development/chunk-D6LUOGOQ.js:337-344` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add task-local behavioral proof that exercises dirty route navigation on the production router/history surface instead of only the current `MemoryRouter` + helper-button path; if that proof fails, keep the task in the builder path with the reproduced failing case attached | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx` | Blocking finding #1 |

## Observations
- AC2 and AC4 are adequately implemented and proved for the exercised surface.
- Shell's current nav buttons do use `navigate(route.path)` (`serve/cockpit/web/src/Shell.tsx:75,479`), so the implementation may cover the primary in-app click path; the rejection is about proof sufficiency on the shipped router surface, not contradictory builder evidence.
- Coverage 84.21% is not the blocker here. The blocking issue is missing behavioral proof for the router boundary.
- Challenger cross-check recommended reconsidering a direct implementation FAIL; this rejection is therefore routed to `todo` as a test-gap issue rather than to `in-progress` as a confirmed runtime defect.

[[2026-05-20T17:22:31+02:00]]
## Test-Writer Notes
- Retry: added 5 BrowserRouter surface tests to `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx`
- New class: `TestFromAC_BrowserRouterSurface`
- Tests per category: happy 3 (dirty+nav, dialog text, proceed), boundary 0, error 0, regression-guards 2 (cancel/stay, clean no-block)
- Total new: 5 tests — all PASS against current implementation
- ESLint: clean
- Builder skip: test-only retry (Step 1b.1) — reviewer's Required Follow-up was test-proof gap only; implementation already correctly handles BrowserRouter surface via navigator.push patching, which is the same mechanism used by useNavigate in production.

## AC Coverage (retry additions)
| AC | New Tests | Result |
|----|-----------|--------|
| AC1 (BrowserRouter surface) | alertdialog renders, text correct, proceed navigates, cancel stays | PASS — implementation proven on production router |
| AC3 (BrowserRouter surface) | clean nav proceeds without dialog | PASS — regression guard on production router |
| AC2, AC4 | no changes — existing 4 tests retained and passing | — |

## Why All Pass (per Step 1b.1)
`BrowserRouter` provides `navigator = createBrowserHistory(...)` via UNSAFE_NavigationContext. The implementation's fallback (patch navigator.push/replace/go) works because `useNavigate()` calls `navigator.push` from context — same interception point in BrowserRouter as in MemoryRouter. Empirical proof now on record.

[[2026-05-20T17:39:34+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1664 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: builder notes reported `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx` 12 passed / 0 failed, adjacent IdeasPage suites 43 passed / 0 failed, eslint clean, and scoped coverage for `src/pages/IdeasPage.tsx` at 84.21%. The retry then added 5 BrowserRouter-surface tests and reported all 5 passing against the current implementation.

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | Dirty navigation is intercepted by patching `navigator.push` / `navigator.replace` / `navigator.go` and surfacing the confirmation dialog at `serve/cockpit/web/src/pages/IdeasPage.tsx:210-261,317-323`. Production leaves IdeasPage through `navigate(route.path)` at `serve/cockpit/web/src/Shell.tsx:479`, and React Router string navigation resolves through `navigator.push` / `navigator.replace` at `serve/cockpit/web/node_modules/react-router/dist/development/chunk-4N6VE7H7.mjs:5884-5901`. | The retry mounts BrowserRouter, then proves alertdialog render, required text, proceed, cancel, and clean no-block behavior on that shipped router surface at `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:303-396`; production BrowserRouter mount is at `serve/cockpit/web/src/App.tsx:21`. | PASS |
| AC2 | Dirty-only `beforeunload` registration and `event.preventDefault()` live at `serve/cockpit/web/src/pages/IdeasPage.tsx:267-278`. | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:182-194` proves `beforeunload` prevents default when dirty. | PASS |
| AC3 | Clean state clears pending transition/dialog state and skips the fallback navigation patch / `beforeunload` registration at `serve/cockpit/web/src/pages/IdeasPage.tsx:204-210,267-278`. | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:203-222` proves no `beforeunload` blocking when clean, and `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:390-396` proves clean BrowserRouter navigation proceeds without the dialog. | PASS |
| AC4 | `beforeunload` listener cleanup occurs in the effect teardown at `serve/cockpit/web/src/pages/IdeasPage.tsx:276-278`. | `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx:234-289` proves cleanup on unmount and when dirty state clears. | PASS |

- Challenger cross-check: reconsidered the proposed FAIL; the remaining browser-chrome `popstate` concern is a residual hardening topic, not a blocking AC failure after the BrowserRouter retry.

## Observations
- Non-blocking: the proof now covers the shipped in-app navigation path (`Shell` -> `useNavigate`) that production uses. Browser-toolbar back/forward is not explicitly covered by this task’s AC or tests; if that behavior is desired, tighten the contract in a future task instead of treating it as a blocker here.
- Coverage remains 84.21%, but the blocker from the previous review cycle was proof sufficiency on the production router surface, and that gap is now closed.

[[2026-05-20T17:49:07+02:00]]
## Docs Gate

**Verdict: PASS — docs gate passed**

### Convention Mapping
- Changed files: `serve/cockpit/web/src/pages/IdeasPage.tsx`, `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx`
- Mapped README: `serve/cockpit/README.md`

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | UPDATED | `#1664` entry added after `#1663` — describes `UNSAFE_NavigationContext` guard, `navigator.block`/fallback patch, `alertdialog` with exact required text, `beforeunload` + `event.preventDefault()`, clean-state no-block, cleanup on unmount; 17 test count verified against builder notes (12 original + 5 BrowserRouter retry) |
| 2. External Attribution | N/A | No external sources used — pure React Router API |
| 3. Research Doc | N/A | No research artifact referenced in task body |
| 4. Deletion Detection | N/A | No files deleted |

### Layer 1 — grep structural check
- `#1664` present at line 489 of `serve/cockpit/README.md` ✓

### Layer 2 — editorial review
- Entry accurately reflects implementation: `UNSAFE_NavigationContext`, `navigator.block` with push/replace/go fallback, `div[role="alertdialog"]`, exact dialog text, beforeunload semantics, clean-state contract, unmount cleanup, and test evidence ✓

### Files Updated
- `serve/cockpit/README.md` — added #1664 bullet between #1663 and #1671

### Commit
- `0c0070f7` — `docs: document IdeasPage unsaved-changes guard (#1664)`

### Scratch Cleanup
- No `1664-*` scratch files found — nothing to clean

[[2026-05-20T17:59:32+02:00]]
## Audit

### Regression Detection
Quality-runner full suite: 2333 passed, 0 failed, 11 skipped. ESLint: 1 pre-existing violation in unrelated `SidecarUX.test.tsx` — background debt, not task-caused. No regressions.

### Intent Verification
Changed file `serve/cockpit/web/src/pages/IdeasPage.tsx` stays within cockpit-web frontend domain. Implementation (navigation blocking + beforeunload + alertdialog) aligns with stated purpose. No extraneous scope.

### Architect Quality
AC score: 5/5. All 4 AC lines specify exact observables (alertdialog role, exact text, preventDefault, clean-state contract, cleanup). Challenger refinement cycle produced high-quality acceptance criteria.

### Commit Integrity
4 commits properly attributed with task ID:
- `604efd5d` test: RED phase
- `3d637877` feat: GREEN phase
- `16d0c700` test: BrowserRouter retry
- `0c0070f7` docs: documentation

TDD cycle respected. Reviewer evidence detailed across two review cycles (FAIL → retry → PASS).

### Deductions
None.

### Confidence: 1.00
### Action: ARCHIVE
