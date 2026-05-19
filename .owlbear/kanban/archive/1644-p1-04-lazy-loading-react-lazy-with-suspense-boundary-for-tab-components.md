---
id: 1644
title: 'P1-04: Lazy loading — React.lazy() with Suspense boundary for tab components'
status: archived
priority: important
created: 2026-05-18T00:49:27.367267+02:00
updated: 2026-05-19T12:32:25.885344+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1639
ac:
  - In routes.ts, DecisionsPage (and any future non-default-route entries) is 
    loaded via React.lazy(() => import(...)). KanbanBoard (path '/') remains an 
    eager import. Shell.tsx wraps the <Routes> block in <Suspense fallback={<div
    data-testid="route-loading" />}>.
  - npm run build produces ≥2 JS asset chunks in dist/assets/, confirming 
    DecisionsPage is code-split from the main bundle.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** `React.lazy()` wrapping of route-config tab components, `<Suspense>` boundary in Shell.tsx routing.

**Out:** Route config creation (P1-01), component implementation.

## Context

Route config entries from P1-01 reference tab components directly. This task wraps them in `React.lazy()` for code-splitting and adds a `<Suspense>` fallback around the `<Routes>` output. KanbanBoard may remain eagerly loaded since it is the default route.

[[2026-05-19T08:14:59+02:00]]


## Research

See `.owlbear/research/cockpit-lazy-loading-suspense.md`

### Key Findings

- **Pattern:** `React.lazy()` + `<Suspense>` is the correct approach for declarative `<Routes>` (React Router 7's `route.lazy` object API is Data Mode only)
- **Type safety:** `LazyExoticComponent<ComponentType<P>>` is assignable to `ComponentType<P>` — no `RouteConfigEntry` interface change needed
- **Runtime caveat:** `typeof React.lazy(...)` returns `'object'` not `'function'` — existing test checking `typeof entry.component === 'function'` will break; fix by checking renderability
- **Vite:** Dynamic `import()` auto-creates separate chunks, no config needed
- **React Compiler:** No conflicts

### Implementation Notes

1. `routes.ts`: Replace `import DecisionsPage from './pages/DecisionsPage'` with `const DecisionsPage = lazy(() => import('./pages/DecisionsPage'))`
2. `Shell.tsx`: Wrap `<Routes>` in `<Suspense fallback={<div data-testid=\"route-loading\" />}>`
3. Fix existing test: replace `typeof entry.component === 'function'` with a valid check (e.g. verify entry.component is truthy and renderable)
4. AC2 verify: `npm run build` → check dist/ for separate DecisionsPage chunk

[[2026-05-19T08:15:06+02:00]]
## Research

Research complete — T1 autonomous finding, no follow-up tasks needed.

**Approach:** `React.lazy()` + `<Suspense>` — standard React 19 pattern for declarative `<Routes>` code-splitting. React Router 7's granular `route.lazy` API is Data Mode only (not applicable).

**Key findings:**
- TypeScript: `LazyExoticComponent<ComponentType<P>>` is assignable to `ComponentType<P>` — `RouteConfigEntry` interface unchanged
- Runtime: `typeof React.lazy(...)` is `'object'` — existing test (`typeof entry.component === 'function'`) will break
- Vite: auto-chunks on dynamic `import()` — no config
- React Compiler: no conflicts

**Doc:** `.owlbear/research/cockpit-lazy-loading-suspense.md`
**Follow-ups:** None — implementation covered by task #1644 ACs directly

[[2026-05-19T08:38:35+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Only lazy-loading + Suspense boundary — single concern |
| Interface clarity | PASS (after refine) | AC now names exact files, components, and testable attributes |
| Dependency correctness | PASS | #1639 is archived (done); routes.ts and Shell.tsx exist |
| Module layering | PASS | routes.ts and Shell.tsx are same-package; no upward imports |
| TDD compliance | PASS | Existing test (routes_1639.test.tsx:47-51 typeof check) and Shell.decisions-integration_1639.test.tsx will need adaptation — acknowledged in research notes |
| KISS/YAGNI | PASS | React.lazy() + Suspense is the standard React 19 pattern, minimal approach |
| Premise challenge | PASS | Code-splitting is justified for growing multi-tab app |
| Pattern consistency | PASS | Follows React 19 + Vite standard patterns |
| Security surface | PASS | No new system boundaries — internal code-splitting only |
| Single domain | PASS | All cockpit-web frontend |

### Challenge Results
- Challenger: reconsider (confidence 0.67)
- Key findings: AC1 scope ambiguity (which tabs lazy?), fallback unspecified, AC2 proof method too open
- Architect response: accepted — refined both AC lines to address all findings

### Proof-Bundle Validation
- Planner assignment: smoke
- Final bundle: smoke
- Existing proof scope: N/A
- Test-writer: PROCEED

### Design Diverge
- Trigger: skipped — single clear approach (React.lazy + Suspense), no competing alternatives

### Implementation Guidance
- Existing test `routes_1639.test.tsx` line 49 (`typeof entry.component === 'function'`) will fail after lazy wrapping. Fix by checking renderability (e.g. entry.component is truthy, or check $$typeof symbol).
- `Shell.decisions-integration_1639.test.tsx` may need async rendering (act + waitFor) for lazy component resolution.
- RouteConfigEntry interface should remain unchanged per research — LazyExoticComponent<ComponentType<P>> satisfies ComponentType<P> structurally.

### Verdict: APPROVE
### Action Taken: AC refined for precision (scope, fallback attributes, proof artifact), advanced backlog → todo

[[2026-05-19T09:03:29+02:00]]
## Test-Writer Notes
- Test files:
  - `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx`
  - `serve/cockpit/web/src/__tests__/Shell.suspense-boundary_1644.test.tsx`
- Classes: `TestFromAC_LazyLoadingRoutes`, `TestFromAC_ShellSuspenseBoundary`
- Tests per category: smoke 3, edge 0, error 0, boundary 0
- Total: 3 tests, all FAIL
- ESLint: clean

### AC Coverage
| AC | Test | Failure reason (RED) |
|----|------|----------------------|
| AC1 – DecisionsPage is React.lazy in routes.ts | `ac1 smoke: /decisions component is React.lazy` | `AssertionError: expected undefined to be Symbol(react.lazy)` — DecisionsPage is plain function |
| AC1 – Shell.tsx wraps Routes in Suspense | `ac1 smoke: Shell shows route-loading fallback while lazy route component is loading` | `TestingLibraryElementError: Unable to find an element by: [data-testid="route-loading"]` — no Suspense boundary |
| AC2 – ≥2 JS chunks after build | `ac2 smoke: dist/assets/ contains ≥2 JS chunks` | `AssertionError: Expected ≥2 JS chunks, found 1` — single eager bundle |

Two test files needed because vi.mock(routes) for the Suspense test conflicts with importing the real routeConfig for the lazy-check test.

[[2026-05-19T09:30:59+02:00]]
## Builder Notes
### Files Changed
- serve/cockpit/web/src/routes.ts
- serve/cockpit/web/src/Shell.tsx

### Implementation Summary
- Switched `/decisions` route component to `React.lazy(() => import('./pages/DecisionsPage'))` in `routes.ts`.
- Added `<Suspense fallback={<div data-testid="route-loading" />}>` around `<Routes>` in `Shell.tsx`.
- Kept `/` (`KanbanBoard`) eager-loaded.

### RED Verification (pre-implementation)
- `src/__tests__/routes.lazy-loading_1644.test.tsx`: 2 failed
- `src/__tests__/Shell.suspense-boundary_1644.test.tsx`: 1 failed
- Total RED failures: 3/3 expected

### GREEN Verification (proof bundle: smoke)
- Build: `npm run build` ✅
- Task tests:
  - `src/__tests__/routes.lazy-loading_1644.test.tsx` ✅ (2 passed)
  - `src/__tests__/Shell.suspense-boundary_1644.test.tsx` ✅ (1 passed)
- Lint:
  - `src/routes.ts` ✅
  - `src/Shell.tsx` ✅
  - task test files ✅

### AC Evidence
- AC1: `/decisions` route now carries a lazy component (`$$typeof === Symbol.for('react.lazy')`) and Shell renders `data-testid="route-loading"` fallback via Suspense.
- AC2: `dist/assets/` contains 2 JS chunks after build:
  - `DecisionsPage-*.js`
  - `index-*.js`

### Cross-Task Regression Signal
- Ran nearby durable tests for visibility:
  - `src/__tests__/routes_1639.test.tsx` ❌ (`typeof entry.component === 'function'` now invalid for lazy route component)
  - `src/__tests__/Shell.decisions-integration_1639.test.tsx` ❌ (sync assertion sees Suspense fallback; lazy route resolution is async)
- Lint for those files: ✅
- These failures align with intentional lazy-loading interface evolution introduced by #1644 and indicate follow-up test adaptation may be needed by test ownership.

### Commit
- `d36dba01` — `feat: add lazy-loaded decisions route with suspense boundary (#1644, builder)`

[[2026-05-19T10:16:53+02:00]]
## Review Evidence
- Verdict: FAIL
- Route: todo
- Summary: Builder evidence and direct inspection show the implementation satisfies the lazy-loading behavior, Suspense boundary, and build chunk split, but review cannot approve because adjacent durable route tests are stale and fail against the new lazy-route contract.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/routes.ts:4`, `serve/cockpit/web/src/routes.ts:19`, `serve/cockpit/web/src/routes.ts:25`, `serve/cockpit/web/src/Shell.tsx:375`, `serve/cockpit/web/src/Shell.tsx:383` implement lazy `/decisions`, eager `/`, and the Suspense fallback. | quality-runner: `routes.lazy-loading_1644.test.tsx` PASS (2), `Shell.suspense-boundary_1644.test.tsx` PASS (1), `Shell.test.tsx` PASS including synchronous `/` proof at `serve/cockpit/web/src/__tests__/Shell.test.tsx:101`. | FAIL — the durable proof surface is inconsistent because two adjacent route tests still fail under the new contract. |
| AC2 | Build artifact inspection shows `serve/cockpit/dist/assets/DecisionsPage-Drjp7AeY.js` and `serve/cockpit/dist/assets/index-BWngbxiX.js`. | quality-runner: `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx` build check PASS. | PASS |

- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC1 | The durable `routeConfig` contract test still requires every `component` value to be a callable function, which is incompatible with `React.lazy` and now fails on the exported config. | quality-runner failure at `serve/cockpit/web/src/__tests__/routes_1639.test.tsx:49` (`expected 'object' to be 'function'`); implementation at `serve/cockpit/web/src/routes.ts:4` and `serve/cockpit/web/src/routes.ts:25`. | todo |
| 2 | AC1 | The real-route `/decisions` integration test still assumes synchronous rendering and now fails against the Suspense-based lazy route. | quality-runner failure at `serve/cockpit/web/src/__tests__/Shell.decisions-integration_1639.test.tsx:61` (`Unable to find an element by: [data-testid="decisions-page"]`); lazy route rendered under Suspense at `serve/cockpit/web/src/Shell.tsx:375` and `serve/cockpit/web/src/Shell.tsx:383`. | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update the durable `routeConfig` contract test to accept `React.lazy` for non-default routes while still proving `/` remains eager. | `serve/cockpit/web/src/__tests__/routes_1639.test.tsx` | quality-runner failure at `serve/cockpit/web/src/__tests__/routes_1639.test.tsx:49`; `serve/cockpit/web/src/routes.ts:4`, `serve/cockpit/web/src/routes.ts:19`, `serve/cockpit/web/src/routes.ts:25` |
| 2 | test-writer | Update the real `/decisions` integration test to await lazy route resolution and keep proving Shell wires the real `routeConfig` entry to DecisionsPage. | `serve/cockpit/web/src/__tests__/Shell.decisions-integration_1639.test.tsx` | quality-runner failure at `serve/cockpit/web/src/__tests__/Shell.decisions-integration_1639.test.tsx:61`; `serve/cockpit/web/src/Shell.tsx:375`, `serve/cockpit/web/src/Shell.tsx:383` |

## Observations
- `serve/cockpit/web/src/__tests__/Shell.test.tsx` still passes, including the `/` loading-indicator check at `serve/cockpit/web/src/__tests__/Shell.test.tsx:101`, so the eager home-route behavior remains intact.
- Build artifact inspection matches AC2: `serve/cockpit/dist/assets/` currently contains a dedicated `DecisionsPage` chunk and the main `index` chunk.

[[2026-05-19T10:42:33+02:00]]
## Test-Writer Notes
- Retry: updated 2 stale durable tests from task #1639 that broke under the lazy-loading contract introduced by #1644.
- `routes_1639.test.tsx`: replaced `typeof entry.component === 'function'` (all-entries check) with two targeted tests:
  - Proves `/` (KanbanBoard) is an eager non-lazy callable function (checks `$$typeof !== Symbol.for('react.lazy')`).
  - Proves all entries are renderable (defined and truthy), accepting both eager functions and `React.lazy` objects.
- `Shell.decisions-integration_1639.test.tsx`: made the happy-path integration test async, wrapping render in `act(async)` and asserting via `waitFor` to await Suspense resolution before checking `data-testid=\"decisions-page\"`.
- Quality-runner: 15 passed, 0 failed, ESLint clean.
- Builder skip: test-only retry — all tests green against current impl.
- Commit: `ff1b058f` — `test: fix stale route-contract and decisions-integration tests for lazy-loading (#1644, test-writer)`

[[2026-05-19T10:52:51+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1644 -> docs | AC mapped to code and evidence sufficient.
- Builder/test-writer evidence reviewed first: builder notes report task-local smoke proof green (`routes.lazy-loading_1644.test.tsx` 2 passed, `Shell.suspense-boundary_1644.test.tsx` 1 passed, build and lint clean); retry note reports updated durable suite green (15 passed, 0 failed, ESLint clean).

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/routes.ts:4` lazy-loads `DecisionsPage`; `serve/cockpit/web/src/routes.ts:19` keeps `/` eager via `KanbanBoard`; `serve/cockpit/web/src/routes.ts:25` maps `/decisions` to the lazy component; `serve/cockpit/web/src/Shell.tsx:375` wraps `<Routes>` in `<Suspense fallback={<div data-testid="route-loading" />}>` and `serve/cockpit/web/src/Shell.tsx:376` renders the routes inside that boundary. | Task-local proof: `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx:22` checks `$$typeof === Symbol.for('react.lazy')`; `serve/cockpit/web/src/__tests__/Shell.suspense-boundary_1644.test.tsx:79` and `serve/cockpit/web/src/__tests__/Shell.suspense-boundary_1644.test.tsx:85` prove the `route-loading` fallback renders while the route suspends. Durable proof: `serve/cockpit/web/src/__tests__/routes_1639.test.tsx:47` and `serve/cockpit/web/src/__tests__/routes_1639.test.tsx:55` prove `/` stays eager and callable; `serve/cockpit/web/src/__tests__/Shell.decisions-integration_1639.test.tsx:58`, `serve/cockpit/web/src/__tests__/Shell.decisions-integration_1639.test.tsx:66`, and `serve/cockpit/web/src/__tests__/Shell.decisions-integration_1639.test.tsx:67` await the real `/decisions` route and confirm `data-testid="decisions-page"`. | PASS |
| AC2 | Current build artifacts in `serve/cockpit/dist/assets/` include `DecisionsPage-CFhTohZE.js` and `index-B23J2lOv.js`, matching a split DecisionsPage chunk plus main bundle. | `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx:33` asserts `dist/assets/` contains at least two JS chunks after build; builder notes report `npm run build` green and the retry introduced no source changes that would invalidate the artifact. | PASS |

- Blocking findings: none.
- Safety/security check: no new input-handling, auth, storage, or dependency surface; change is limited to static route lazy-loading, Suspense fallback, and test updates.

## Observations
- The prior review failure is resolved: the durable route-contract and real-route integration tests now model the lazy/eager split instead of assuming every route component is synchronously callable.
- `get_errors` reports no editor diagnostics in `serve/cockpit/web/src/routes.ts`, `serve/cockpit/web/src/Shell.tsx`, or the four reviewed test files.

[[2026-05-19T12:05:59+02:00]]
## Docs Gate

### Checklist

**Item 1 — README Verification**
Convention mapping: `serve/cockpit/web/src/routes.ts`, `serve/cockpit/web/src/Shell.tsx` → `serve/cockpit/README.md`.
- Layer 1 (grep): stale "10 tests" phrase confirmed absent; `#1644` bullet confirmed present at line 388.
- Layer 2 (editorial): new bullet accurately describes `React.lazy()` wrapping, `<Suspense fallback={<div data-testid="route-loading" />}>`, Vite code-splitting, and all three test files with correct counts and assertions. No contradictions.
- Changes made:
  - Updated `routes_1639.test.tsx` count from 10 → 12 (two tests added by #1644 test-writer retry for lazy/eager split contract).
  - Updated `Shell.decisions-integration_1639.test.tsx` note to reflect async `act`/`waitFor` update.
  - Added new `#1644` bullet documenting lazy loading, Suspense boundary, and code-splitting.

**Item 2 — External Attribution**
N/A — no external sources influenced implementation; React.lazy + Suspense is standard library API.

**Item 3 — Research Doc**
Research doc `.owlbear/research/cockpit-lazy-loading-suspense.md` exists and is linked from task body. N/A — linkage verified.

**Item 4 — Deletion Detection**
No files deleted by this task. N/A — no deletion impact.

### Scratch Cleanup
No `.owlbear/scratch/1644-*` files found — nothing to clean.

### Commit
`84724717` — `docs: document lazy-loading routes and Suspense boundary (#1644, doc-writer)`

[[2026-05-19T12:32:25+02:00]]
## Audit

### Regression Detection
Quality-runner full suite: 2160 Python tests passed. Frontend vitest reported 2 failures in `routes.lazy-loading_1644.test.tsx` — caused by task #1643's commit `3f4357d9` (eager-load decisions route for sidecar suppression), NOT by #1644. This cross-task regression is already identified: #1643's reviewer sent it back to in-progress with mandate to restore lazy loading. Other frontend failures (`Shell.secondary-css`, `Card.visual-treatment`) are from unrelated task suites. No regressions attributable to #1644.

### Intent Verification
Changed files: `serve/cockpit/web/src/routes.ts`, `serve/cockpit/web/src/Shell.tsx` — both cockpit-web frontend, matching scope. Implementation adds `React.lazy()` + `<Suspense>` boundary per stated purpose. No extraneous scope.

### Architect Quality
Score: 4/5. AC lines are specific and verifiable — name exact files, React APIs, `data-testid` attributes, and quantifiable chunk threshold (≥2). Minor gap: AC2 doesn't name exact file patterns but the threshold is clear. No deduction (>3).

### Commit Integrity
4 commits present and properly attributed:
- `05c044d7` test: add failing smoke tests (#1644, test-writer)
- `d36dba01` feat: add lazy-loaded decisions route with suspense boundary (#1644, builder)
- `ff1b058f` test: fix stale route-contract and decisions-integration tests (#1644, test-writer)
- `84724717` docs: document lazy-loading routes and Suspense boundary (#1644, doc-writer)

### Deduction Breakdown
- Intent mismatch: 0
- Evidence integrity: 0
- Lint violations: 0
- AC quality ≤3: 0 (score 4)
- Missing reviewer evidence: 0
- Regression failures: 0 (failures caused by #1643, not #1644; actively being resolved)

### Confidence: 1.00
### Action: ARCHIVE
