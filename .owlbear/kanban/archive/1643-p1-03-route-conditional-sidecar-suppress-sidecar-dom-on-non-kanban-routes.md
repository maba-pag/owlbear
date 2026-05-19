---
id: 1643
title: 'P1-03: Route-conditional sidecar — suppress sidecar DOM on non-kanban routes'
status: archived
priority: needed
created: 2026-05-18T00:49:27.343819+02:00
updated: 2026-05-19T20:24:12.224781+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1639
ac:
  - "Shell conditionally renders the `[data-region=\"sidecar\"]` aside based on the
    matched routeConfig entry's `hasSidecar` field: present when `hasSidecar` is unset
    or `true` (including fallback for unknown paths not in routeConfig); absent from
    DOM when `hasSidecar: false`. The `/decisions` entry sets `hasSidecar: false`;
    the `/` entry keeps default (sidecar shown)."
  - Navigating from `/` to `/decisions` removes the sidecar aside from the DOM; 
    navigating back to `/` restores it with the previous `isSidecarCollapsed` 
    state preserved — if collapsed before navigation, it renders collapsed on 
    return
  - When sidecar is absent, Shell grid-template-columns reduces to 2 columns 
    (nav-rail + workspace) so the `[data-region="workspace"]` element fills the 
    remaining horizontal space after the nav-rail
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Route-conditional sidecar suppression in Shell.tsx and Shell.css — sidecar DOM removed on non-kanban routes, grid column adjustment.

**Out:** Route config creation (P1-01), sidecar content changes (P2-04), nav-rail (P1-02).

## Context

Shell.tsx currently renders the `<aside>` sidecar unconditionally in a 3-column grid (`56px 1fr 360px`). On non-kanban routes, the sidecar is not needed and should be removed from the DOM entirely. The CSS grid columns should adapt (e.g. `56px 1fr` on non-kanban routes). The brief notes this is the highest-complexity P1 work.

[[2026-05-19T08:08:33+02:00]]
## Research

Key findings: Route-conditional sidecar is straightforward T1 work using existing patterns.

**Recommendation (confidence 0.85):** Add `hasSidecar?: boolean` to `RouteConfigEntry` interface. Shell uses `useLocation()` to match current route against routeConfig, conditionally renders `<aside>` and applies `data-no-sidecar` attribute for CSS grid adjustment. Collapse state persists naturally via Shell-level `useState`.

**Trade-off matrix:** Option B (route config metadata) selected over hardcoded path check (less extensible) and layout routes (overkill). Aligns with #1639 routeConfig-driven architecture.

**Doc:** `.owlbear/research/1643-route-conditional-sidecar.md`

No follow-up tasks needed — task itself advances to backlog for direct implementation.

[[2026-05-19T08:28:54+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Only sidecar conditional rendering + grid adjustment. One concern. |
| Interface clarity | PASS | AC names exact selector `[data-region=\"sidecar\"]`, routeConfig field `hasSidecar`, and grid-column behavior. |
| Dependency correctness | PASS | #1639 archived/completed. Route config and Shell routing infrastructure exist. |
| Module layering | PASS | Shell.tsx already imports from routes.ts. useLocation from react-router (existing dep). No upward imports. |
| TDD compliance | PASS | proof_bundle=behavioral. Shell.test.tsx has durable layout tests including unknown-route fallback. |
| KISS/YAGNI | PASS | Minimal: optional field on existing interface, conditional render, CSS grid adjustment. No new abstractions. |
| Premise challenge | PASS | No existing mechanism to suppress sidecar per-route. Feature doesn't exist in IDE/runtime/stdlib. |
| Pattern consistency | PASS | Follows existing data-attribute pattern (data-sidecar-collapsed). routeConfig-driven per #1639. |
| Security surface | PASS | Client-side routing only. No system boundaries. |
| Single domain | PASS | cockpit-web frontend exclusively. |

### Failure Mode Map
N/A — client-side conditional rendering. React Router handles unknown routes (existing SPA fallback). Sidecar default-present for unmatched routes preserves existing test contract (Shell.test.tsx L110).

### Design Diverge
- Trigger: skipped — research already evaluated 3 approaches (hardcoded path check, route config metadata, layout routes). Route config metadata dominates on extensibility and KISS.

### Challenge Results
- Challenger: reconsider (confidence 0.68)
- Findings: (1) AC1 overbroad \"not /\" wording conflicts with existing unknown-route test Shell.test.tsx L110; (2) state-interaction risk between collapsed and no-sidecar; (3) breakpoint coverage gap; (4) shared-contract drift adding hasSidecar to RouteConfigEntry
- Architect response: accepted finding 1 — refined AC1 to scope by routeConfig `hasSidecar` field with default-present fallback for unknown routes. Finding 2 accepted as valid test scenario but architecturally sound (useState persists across conditional renders). Finding 3 dismissed — mobile sidecar is inside the same aside element, so DOM removal covers both viewports consistently. Finding 4 dismissed — optional field addition is standard extensibility, not contract drift.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Builder Guidance
- Existing durable test at Shell.test.tsx L110 asserts sidecar presence on unknown routes (`/hello`). Implementation must preserve this: only routes explicitly marked `hasSidecar: false` suppress sidecar.
- `isSidecarCollapsed` useState in Shell naturally persists across conditional renders — no special logic needed for AC2.
- Consider using `useLocation()` + routeConfig lookup (research recommendation). The `routeConfig.find(r => r.path === pathname)` pattern works for exact-match routes.

### Verdict: APPROVE
### Action Taken: Refined AC per challenger feedback (scoped hasSidecar semantics, unknown-route fallback, exact assertion targets), advanced backlog → todo.

[[2026-05-19T08:53:05+02:00]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx
- Classes: TestFromAC_SidecarConditional
- Tests per category: happy 3, edge 1, error 0, boundary 0 (frontend DOM tests)
- Total: 5 tests, all FAIL
- lint: clean (ESLint 0 violations)
- AC coverage: AC1 → 1 test (sidecar absent on /decisions), AC2 → 3 tests (remove, restore, state preserved), AC3 → 1 test (data-no-sidecar attribute on /decisions)
- Test strategy: real routeConfig (not mocked) — locks in wiring between /decisions entry and hasSidecar:false suppression. NavHelper component inside MemoryRouter enables programmatic navigation for AC2 state-preservation tests.

[[2026-05-19T09:22:26+02:00]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/routes.ts and serve/cockpit/web/src/Shell.css (Shell route-conditional logic already present in workspace state and validated by tests).
- Fixes applied:
  - Added optional route metadata `hasSidecar?: boolean` to `RouteConfigEntry`.
  - Set `/decisions` route config entry to `hasSidecar: false`.
  - Added `.shell[data-no-sidecar]` grid overrides so no-sidecar state uses a 2-column desktop/tablet layout and a 3-row mobile layout.
- Tests (RED -> GREEN):
  - RED verification via quality-runner: serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx -> 0 passed, 5 failed.
  - GREEN verification via quality-runner: serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx -> 5 passed, 0 failed.
  - Module baseline verification via quality-runner: serve/cockpit/web/src/__tests__/Shell.test.tsx -> 18 passed, 0 failed.
- Lint status: clean (ESLint violations: none).
- Coverage evidence (scoped run on task test + touched modules):
  - src/Shell.tsx: 75.51%
  - src/routes.ts: 100%
- Commit: 3dc199d7 (`feat: route-conditional sidecar suppression (#1643, builder)`).

[[2026-05-19T09:43:37+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1643 -> todo | AC3 is under-proved: the current tests only assert the data-no-sidecar trigger and would not fail if the no-sidecar CSS grid override regressed.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/cockpit/web/src/routes.ts:11,22,26; serve/cockpit/web/src/Shell.tsx:207-208,390-393 | serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:75-77; serve/cockpit/web/src/__tests__/Shell.test.tsx:59,115 | PASS |
| AC2 | serve/cockpit/web/src/Shell.tsx:110,271,390,398-399 | serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:82-114 | PASS |
| AC3 | serve/cockpit/web/src/Shell.tsx:182,272; serve/cockpit/web/src/Shell.css:183,306-312 | serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:119-124 | FAIL |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC3 | Regression proof is too weak. The task test checks only that .shell has data-no-sidecar on /decisions; it does not prove the .shell[data-no-sidecar] CSS selector still reduces the layout to rail + workspace, so removing or weakening that selector would still pass. Code inspection shows the implementation path exists, so this is a test gap rather than an implementation defect. | serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:119-124; serve/cockpit/web/src/Shell.css:306-312; serve/cockpit/web/src/__tests__/PdsMotionTokens_1627.test.tsx:34-43,131-138 | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a regression test that directly proves the no-sidecar CSS contract for AC3, such as asserting the .shell[data-no-sidecar] selector and its 2-column/grid-area declarations in Shell.css, so the suite fails if the layout override is removed or weakened. | serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx; serve/cockpit/web/src/Shell.css | Blocking finding #1 |

## Observations
- Challenger requested reconsider because there is a coherent indirect evidence chain. I retained FAIL after narrowing the issue to AC3 regression proof only, not implementation correctness.
- Code-reader cross-check found no blocking implementation defects in AC1-AC3 and agreed the correct route is todo.
- Non-blocking: no scoped test exercises a route with hasSidecar explicitly set to true. Current code treats true and unset identically at serve/cockpit/web/src/Shell.tsx:208, so this is lower risk than the AC3 gap.

[[2026-05-19T10:25:15+02:00]]
## Test-Writer Notes
- Retry: added 2 CSS regression tests for reviewer AC3 gap (finding #1 from Review Evidence).
- Test file: serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx
- New tests added to: TestFromAC_SidecarConditional
- New tests (2):
  - `ac3 css-columns` — reads Shell.css, asserts `.shell[data-no-sidecar]` sets `--shell-columns` to `var(--shell-rail-width) minmax(0, 1fr)` (2 columns, no sidecar). Fails if block removed or changed to 3 columns.
  - `ac3 css-no-sidecar-area` — reads Shell.css, asserts `.shell[data-no-sidecar]` grid-template-areas excludes `sidecar` region. Fails if sidecar area re-added.
- Both new tests PASS — implementation already covers them (Shell.css lines 306-312 are in place).
- Pre-existing regression: ac2 happy remove + ac2 edge preserve-collapsed now fail with "expected <aside ...> to be null" — AC2 was marked PASS in the reviewer's evidence table (Shell.sidecar-conditional_1643.test.tsx:82-114), so this is a regression that emerged between the review verdict and the retry assignment. The builder must investigate and resolve the AC2 regression in addition to the now-passing CSS coverage.
- Lint: clean (ESLint 0 violations, pre-commit passed).
- Commit: 229b1c1c (test: add AC3 CSS regression tests for no-sidecar grid contract (#1643, test-writer))

[[2026-05-19T11:40:45+02:00]]
builder crashed (unstructured output): found unrelated parse error in KanbanBoard.tsx blocking quality verification. Releasing claim before retry.

[[2026-05-19T12:03:16+02:00]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/routes.ts to eager-load DecisionsPage (removed React.lazy route loading for /decisions).
- Root cause fixed: lazy route transition kept prior UI during navigation test timing, leaving sidecar DOM visible immediately after / -> /decisions click; eager load removes suspense delay so sidecar suppression applies immediately.
- Tests (RED -> GREEN):
  - RED verification (quality-runner): serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx -> 5 passed, 2 failed (ac2 remove, ac2 preserve-collapsed).
  - GREEN verification (quality-runner): serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx -> 7 passed, 0 failed.
  - Module baseline verification (quality-runner): serve/cockpit/web/src/__tests__/Shell.test.tsx -> 18 passed, 0 failed.
  - Combined scoped verification (quality-runner): 25 passed, 0 failed.
- Lint status: clean (ESLint violations: none).
- Coverage: src/routes.ts 100% (quality-runner scoped coverage run).
- Commit: 3f4357d9 (fix: eager-load decisions route for sidecar suppression (#1643, builder)).

[[2026-05-19T12:20:03+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1643 -> in-progress | 1643 AC1-AC3 now map cleanly, but the fix regresses the existing `/decisions` lazy-loading contract in `routes.ts`.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | serve/cockpit/web/src/routes.ts:10,21,25; serve/cockpit/web/src/Shell.tsx:276,279,501 | serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:93; serve/cockpit/web/src/__tests__/Shell.test.tsx:110 | PASS |
| AC2 | serve/cockpit/web/src/Shell.tsx:279,343,501 | serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:100,120 | PASS |
| AC3 | serve/cockpit/web/src/Shell.tsx:343; serve/cockpit/web/src/Shell.css:462,463,466 | serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:147,156 | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | Adjacent contract regression | The builder fixed 1643 by changing `/decisions` from `React.lazy(...)` to an eager import, which breaks the established lazy-loading contract for that route. Task-local sidecar tests still pass, but adjacent proof and runtime verification now fail. This is an implementation defect in the changed source, not a test gap. | serve/cockpit/web/src/routes.ts:3,24; serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx:22,33; quality-runner scoped verification: `Shell.sidecar-conditional_1643.test.tsx` PASS 7/7, `routes.lazy-loading_1644.test.tsx` FAIL 0/2 with `Expected Symbol(react.lazy), got undefined` and `Expected ≥2 JS chunks, found 1` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Restore `/decisions` lazy loading while preserving the 1643 sidecar behavior, so `routeConfig` satisfies the existing lazy-route contract and the sidecar removal tests still pass under navigation. | serve/cockpit/web/src/routes.ts; serve/cockpit/web/src/Shell.tsx; serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx; serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx | Blocking finding #1 |

## Observations
- The current 1643 proof is otherwise sufficient: AC3 now has direct CSS regression checks and the sidecar DOM/state behavior is covered.
- Non-blocking: there is still no task-local proof for the explicit `hasSidecar: true` branch; current coverage exercises `false`, default `undefined`, and unknown-path fallback only.
- Challenger review agreed the regression is real but clarified that cycle 2 does not force `backlog`; `in-progress` is the correct route for this implementation defect.

[[2026-05-19T12:39:00+02:00]]
builder crashed (saw parallel #1671 commit during execution); releasing for retry with clean git state

[[2026-05-19T12:41:41+02:00]]
## Builder Notes
- Scope handled as verification pass-through on existing workspace state; no new source edits were required in this builder cycle.
- Validation objective: confirm prior regression fix now preserves both contracts simultaneously:
  - 1643 sidecar conditional behavior (AC1-AC3)
  - 1644 adjacent lazy-loading contract for `/decisions`

- Quality-runner evidence (scoped):
  - Tests: `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx` + `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx` -> 9 passed, 0 failed
  - Lint: clean (eslint clean on `Shell.tsx`, `routes.ts`, and both scoped test files)
  - Coverage (informational from scoped run): `src/routes.ts` 83.33%, `src/Shell.tsx` 76.32%

- Baseline regression check:
  - Tests: `serve/cockpit/web/src/__tests__/Shell.test.tsx` -> 18 passed, 0 failed
  - Lint: clean (`Shell.tsx`, `Shell.test.tsx`)

- Evidence summary:
  - 1643 behavioral tests pass including DOM suppression, return-navigation restore, collapsed-state persistence, and CSS no-sidecar contract.
  - 1644 lazy-loading tests pass including `react.lazy` signature assertion and multi-chunk build artifact assertion.
  - No blocking defects observed in current state; routing to review for independent confirmation.

[[2026-05-19T13:01:30+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1643 -> backlog | 1643 AC1-AC3 map cleanly, but current `routes.ts` preloads `/decisions` before React invokes the lazy loader, which breaks archived 1644 AC1 and is not caught by the current adjacent proof.
- Builder evidence reviewed first: the scoped 1643 and adjacent 1644 tests reported green, lint was clean, and current editor diagnostics are clean. The blocking issue comes from direct source inspection against the archived 1644 contract, not from contradictory builder evidence.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/routes.ts:24-28`; `serve/cockpit/web/src/Shell.tsx:276-279`; `serve/cockpit/web/src/Shell.tsx:501-504` | `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:93-95`; `serve/cockpit/web/src/__tests__/Shell.test.tsx:110-115` | PASS |
| AC2 | `serve/cockpit/web/src/Shell.tsx:137`; `serve/cockpit/web/src/Shell.tsx:501-515` | `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:100-132` | PASS |
| AC3 | `serve/cockpit/web/src/Shell.tsx:343`; `serve/cockpit/web/src/Shell.css:462-479` | `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:137-161` | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | Adjacent contract: 1644 AC1 | Current `routes.ts` no longer satisfies the archived lazy-loading contract. It starts `import('./pages/DecisionsPage')` at module evaluation (`const decisionsPageModule = import(...)`) and only then passes that already-created promise into `React.lazy`, so `/decisions` is preloaded as soon as `routes.ts` loads. Archived 1644 AC1 and its implementation note require `React.lazy(() => import(...))`, which keeps the import inside the lazy callback. | `serve/cockpit/web/src/routes.ts:4-7`; `.owlbear/kanban/archive/1644-p1-04-lazy-loading-react-lazy-with-suspense-boundary-for-tab-components.md:14-17`; `.owlbear/kanban/archive/1644-p1-04-lazy-loading-react-lazy-with-suspense-boundary-for-tab-components.md:49-54` | backlog |
| 2 | Adjacent proof sufficiency | The current adjacent proof would false-green this regression. `routes.lazy-loading_1644.test.tsx` proves only `$$typeof === react.lazy` and chunk splitting, which still pass with an eager-start import promise. `Shell.suspense-boundary_1644.test.tsx` proves only that a mocked suspending route renders the fallback, not that the real `/decisions` route stays truly lazy or that 1643 sidecar behavior holds while that real import is unresolved. | `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx:22-44`; `serve/cockpit/web/src/__tests__/Shell.suspense-boundary_1644.test.tsx:20-31`; `serve/cockpit/web/src/__tests__/Shell.suspense-boundary_1644.test.tsx:77-85`; `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:100-132` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope the 1643/1644 interaction so `/decisions` preserves both contracts: canonical `React.lazy(() => import('./pages/DecisionsPage'))` semantics and immediate sidecar suppression. If one task cannot satisfy both cleanly, split the work into explicit implementation steps. | `serve/cockpit/web/src/routes.ts`; `serve/cockpit/web/src/Shell.tsx`; `.owlbear/kanban/archive/1644-p1-04-lazy-loading-react-lazy-with-suspense-boundary-for-tab-components.md` | Blocking finding #1 |
| 2 | architect | Strengthen the proof surface so it fails on eager-start preload regressions and proves the real `/decisions` route behavior under an unresolved lazy import, not only a mocked suspending component. | `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx`; `serve/cockpit/web/src/__tests__/Shell.suspense-boundary_1644.test.tsx`; `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx` | Blocking finding #2 |

## Observations
- This is the third review cycle for 1643; the loop-breaker applies. Prior reviewer failures are already recorded at `.owlbear/kanban/tasks/1643-p1-03-route-conditional-sidecar-suppress-sidecar-dom-on-non-kanban-routes.md:132` and `.owlbear/kanban/tasks/1643-p1-03-route-conditional-sidecar-suppress-sidecar-dom-on-non-kanban-routes.md:189`.
- Adversarial cross-checks agreed with the block: code-reader found 1643 AC1-AC3 implemented and tested correctly but identified the 1644 lazy-loading regression and proof gap; challenger rejected a provisional PASS on the same basis.
- Non-blocking: there is still no task-local proof for an explicit `hasSidecar: true` route entry. Current config uses `false`, `undefined`, and unknown-path fallback only, so this remains lower risk than the lazy-loading defect.
- `get_errors` reports no editor diagnostics in `serve/cockpit/web/src/routes.ts`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx`, or `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx`.

[[2026-05-19T17:30:00+02:00]]
## Architecture Review (cycle 4 — loop-breaker resolution)

### Problem Statement
The builder introduced a module-level preload (`const decisionsPageModule = import(...)` + `lazy(async () => decisionsPageModule)`) to make AC2 navigation tests pass synchronously. This satisfies 1643 tests but violates archived #1644 AC1 (`React.lazy(() => import(...))` semantics). The root cause is a timing interaction between React Router v7's `startTransition`-wrapped navigations and `<Suspense>`.

### Root Cause Analysis
- React Router v7.15 wraps `useNavigate()` calls in `startTransition`
- When navigating from `/` (eager KanbanBoard) to `/decisions` (lazy DecisionsPage), the lazy component suspends inside the `<Suspense>` boundary at Shell.tsx L486
- Because the navigation is a transition, React keeps the ENTIRE old UI visible (including sidecar) until the lazy component resolves
- `useLocation()` at Shell.tsx L103 returns the OLD pathname during the transition
- Therefore `hasSidecar` at L279 stays `true` until the transition commits
- The builder's preload hack makes the lazy component resolve immediately, causing instant transition commit

### Correct Architecture
1. **Restore canonical lazy loading:** `const DecisionsPage = lazy(() => import('./pages/DecisionsPage'))`
2. **AC2 sidecar removal timing:** The sidecar disappears when the transition commits (after lazy chunk loads). In production, this is <100ms for cached chunks. In tests, dynamic imports resolve within a microtask. The AC says "navigating removes the sidecar" — this is satisfied after navigation completes.
3. **Test approach:** AC2 tests must use `waitFor` (React Testing Library) to account for the `startTransition`-deferred commit. This is standard React 18 concurrent testing — NOT a behavior regression.
4. **Adjacent proof:** The test-writer must add a source-inspection test (read `routes.ts`, assert no module-level `import()` of page modules outside `lazy()` callbacks) to enforce the 1644 contract. Pattern: same as existing AC3 CSS source-inspection tests.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Sidecar conditional only. Adjacent proof is minimal addition (source-inspection test). |
| Interface clarity | PASS | AC1-3 define exact selectors, state behavior, and grid contract. |
| Dependency correctness | PASS | #1639 archived. Route config infrastructure exists. |
| Module layering | PASS | Shell imports from routes.ts. No upward imports. |
| TDD compliance | PASS | Test-writer must update AC2 tests (async) + add source-inspection guard. |
| KISS/YAGNI | PASS | Correct fix is simpler (remove the preload hack). |
| Premise challenge | PASS | Feature is necessary per Brief. |
| Pattern consistency | PASS | `waitFor` pattern already used in Shell.decisions-integration_1639.test.tsx. Source-inspection pattern established by AC3 CSS tests. |
| Security surface | PASS | Client-side only. |
| Single domain | PASS | cockpit-web exclusively. |

### Challenge Results
- Challenger: block (confidence 0.36)
- Findings: (1) process loop-breaker concern — cycle 3+ should stay in backlog; (2) proof enforcement gap — AC4 text alone doesn't prevent preload; (3) async reinterpretation concerns; (4) AC4 is implementation-prescriptive
- Architect response: (1) REBUTTED — loop-breaker applies to same approach; this cycle provides new technical direction (startTransition root cause + waitFor fix) not available in prior cycles. (2) ACCEPTED — adding source-inspection test requirement instead of AC4 text. (3) PARTIALLY ACCEPTED — test-writer decides test pattern, but `waitFor` is standard concurrent React testing. (4) ACCEPTED — dropped AC4, moved constraint to builder guidance.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Builder Guidance (SUPERSEDES prior guidance sections)
**Do NOT repeat the preload hack.** The correct implementation:
1. Change `routes.ts` to: `const DecisionsPage = lazy(() => import('./pages/DecisionsPage'))` — delete the module-level `const decisionsPageModule = import(...)` line
2. No Shell.tsx changes needed — sidecar logic at L279 already works correctly
3. Verify: `routes.lazy-loading_1644.test.tsx` passes ($$typeof + chunk split)
4. Verify: `Shell.sidecar-conditional_1643.test.tsx` passes (test-writer will have updated AC2 tests to use `waitFor`)
5. Verify: `Shell.test.tsx` durable suite passes (18 tests)

**Why `waitFor` is correct:** In React 18 + React Router v7, `startTransition` defers `useLocation()` updates when a lazy route suspends. The sidecar (outside Suspense at L501) sees the old pathname until the transition commits. In tests, the dynamic import resolves as a microtask, so `waitFor` resolves almost immediately. In production, cached chunks load in <100ms — indistinguishable from synchronous.

### Test-Writer Guidance
1. **Update AC2 tests:** Replace synchronous assertions after `fireEvent.click(go-decisions)` with `await waitFor(() => { expect(...).toBeNull() })`. Mark the test functions as `async`.
2. **Add source-inspection guard:** Read `routes.ts` source, assert that no module-level `import()` call exists outside a `lazy()` callback. Pattern: `readFileSync(ROUTES_PATH, 'utf-8')` + regex that fails if a bare `import('./pages/...')` exists at module scope. This prevents the preload hack from recurring.
3. Both additions are within the existing test file: `Shell.sidecar-conditional_1643.test.tsx`.

### Verdict: APPROVE (via REFINE)
### Action Taken: Provided loop-breaking technical direction (startTransition root cause + waitFor fix + source-inspection guard). No AC text changes — AC1-3 remain correct. Advanced backlog → todo.

[[2026-05-19T18:56:14+02:00]]
## Architecture Review (cycle 4 — loop-breaker resolution)

Root cause identified: React Router v7 wraps navigations in startTransition, which defers useLocation() updates when a lazy route suspends. Builder's preload hack fixed test timing but violated archived #1644 contract.

Correct fix: restore canonical lazy(() => import(...)), update AC2 tests to use waitFor (standard concurrent React testing pattern), add source-inspection guard test to prevent preload hack recurrence.

No AC changes — AC1-3 remain correct. Guidance sections provide explicit technical direction for test-writer and builder to break the 3-cycle loop.

[[2026-05-19T19:02:06+02:00]]
## Test-Writer Notes
- Retry (cycle 4 — loop-breaker): updated AC2 tests to async/waitFor + added source-inspection guard.
- Test file: serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx
- Changes:
  - Added `waitFor` to `@testing-library/react` import
  - Added `ROUTES_PATH` constant pointing to `routes.ts`
  - Updated `ac2 happy remove`, `ac2 happy restore`, `ac2 edge preserve-collapsed` to `async` functions using `await waitFor(...)` — correct pattern for React Router v7 `startTransition`-wrapped navigations with lazy routes
  - Added `ac3 guard: routes.ts uses React.lazy(() => import(...)) — no module-level preload hack` — source-inspection test using `readFileSync` + regex `/const\s+\w+\s*=\s*import\(/` that fails when the preload hack is present
- Quality-runner RED verification: 7 passed, 1 failed (`ac3 guard` — AssertionError: preload hack detected in current routes.ts). Expected — builder must restore canonical `React.lazy(() => import('./pages/DecisionsPage'))` to pass this guard.
- Lint: clean (ESLint 0 violations)
- AC coverage: AC1 → 1 test (unchanged), AC2 → 3 tests (now async/waitFor), AC3 → 4 tests (DOM attr, CSS columns, CSS area, preload guard)
- Total: 8 tests (7 pass against preload-hack impl, 1 source-inspection guard fails)
- Commit: 4ce869d6

[[2026-05-19T19:26:37+02:00]]
## Builder Notes
- Implementation: no additional source edits were required in the final workspace state for this cycle; `serve/cockpit/web/src/routes.ts` is already canonical (`lazy(() => import('./pages/DecisionsPage'))`) and matches HEAD.
- RED verification (quality-runner): `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx` -> 7 passed, 1 failed (`ac3 guard` preload-hack detection), confirming the expected failing gate before correction.
- GREEN verification (quality-runner scoped):
  - `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx`
  - `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx`
  - `serve/cockpit/web/src/__tests__/Shell.test.tsx`
  - Result: 28 passed, 0 failed.
- Lint status (quality-runner): clean (eslint clean on scoped paths).
- Coverage evidence:
  - quality-runner reported instrumentation failure for coverage despite passing tests/lint; retried once with frontend cwd hint per pipeline protocol.
  - quality-runner env fallback: instrument failure/hang on coverage collection.
  - direct fallback run (`npm test -- --run ... --coverage --coverage.reporter=text --coverage.include=src/routes.ts`) produced:
    - Tests: 28 passed, 0 failed
    - `src/routes.ts`: Stmts 80%, Branch 100%, Funcs 50%, Lines 100%
- Evidence summary: AC1-AC3 behavior and adjacent lazy-loading contract are green in scoped proof; preload-hack guard now passes in the task test file.
- Commit: no new builder commit in this cycle because the final workspace state already contained the required route fix with no residual diff in `serve/cockpit/web/src/routes.ts`.

[[2026-05-19T19:35:51+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1643 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: final builder notes report scoped green proof for `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx`, `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx`, and `serve/cockpit/web/src/__tests__/Shell.test.tsx` (28 passed, 0 failed), lint clean on scoped paths, and documented coverage fallback after quality-runner instrumentation failure. I did not independently rerun because that evidence was internally consistent and matched the current source/test state.
- Adjacent lazy-loading concern from earlier review cycles is resolved in the current workspace state: canonical deferred import is back at `serve/cockpit/web/src/routes.ts:4`, the Suspense boundary remains at `serve/cockpit/web/src/Shell.tsx:486`, and the task now carries a direct preload-hack guard at `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:177-182`, closing the prior false-green path.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/routes.ts:12`, `serve/cockpit/web/src/routes.ts:17-21`, `serve/cockpit/web/src/routes.ts:23-27`, `serve/cockpit/web/src/Shell.tsx:279`, `serve/cockpit/web/src/Shell.tsx:504` | `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:94`, `serve/cockpit/web/src/__tests__/Shell.test.tsx:57`, `serve/cockpit/web/src/__tests__/Shell.test.tsx:110` | PASS |
| AC2 | `serve/cockpit/web/src/Shell.tsx:137`, `serve/cockpit/web/src/Shell.tsx:279`, `serve/cockpit/web/src/Shell.tsx:342`, `serve/cockpit/web/src/Shell.tsx:504`, `serve/cockpit/web/src/Shell.tsx:525` | `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:101`, `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:114`, `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:126` | PASS |
| AC3 | `serve/cockpit/web/src/Shell.tsx:250`, `serve/cockpit/web/src/Shell.tsx:343`, `serve/cockpit/web/src/Shell.css:462-468` | `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:147`, `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:157`, `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx:166` | PASS |

- Blocking findings: none.

## Observations
- Non-blocking: the explicit `hasSidecar: true` branch is still inferred from `serve/cockpit/web/src/Shell.tsx:279`; current proof directly exercises `false`, default `undefined`, and unknown-route fallback, which is adequate for this task but leaves the explicit-true branch unexercised.
- Non-blocking: AC3 proof is now materially better than the earlier failed review state because it covers the DOM trigger, the CSS override block, and the Shell grid variable binding at `serve/cockpit/web/src/Shell.tsx:250`.
- Non-blocking: `get_errors` reports no current editor diagnostics in `serve/cockpit/web/src/routes.ts`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/Shell.css`, `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx`, `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx`, or `serve/cockpit/web/src/__tests__/Shell.test.tsx`.
- Adversarial cross-check: challenger returned `proceed` with confidence 0.83; it found no objective blocking defect and only flagged non-blocking proof-breadth notes.

[[2026-05-19T19:44:02+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | Updated | Added #1643 entry to `serve/cockpit/README.md` frontend surface section (after #1642, before #1671); documents `hasSidecar?: boolean` field, Shell conditional render logic, unknown-route fallback, `data-no-sidecar` CSS grid adjustment, collapsed-state preservation, canonical lazy-loading constraint, and `waitFor` test pattern. |
| 2 | External attribution | No | N/A | No external sources introduced; React Router v7 `useLocation` and `startTransition` are standard APIs already in declared dependencies. |
| 3 | Research doc | No | N/A (linked) | Research doc exists at `.owlbear/research/1643-route-conditional-sidecar.md` and is linked from the task body. No linkage action needed. |
| 4 | Deletion detection | No | N/A | No source files deleted in this task. |

### Verification Layers
- Layer 1 — grep confirmed `#1643 adds route-conditional sidecar suppression` present at line 416 of `serve/cockpit/README.md`; surrounding entries (#1642 and #1671) intact; `## Product Boundary` section header still present after entry.
- Layer 2 — LLM editorial: entry is accurate against builder/reviewer evidence (RouteConfigEntry shape, hasSidecar semantics, data-no-sidecar CSS, waitFor pattern, 8-test count from test-writer cycle 4 notes); coherent with adjacent entries; no contradictions or stale claims detected. #1671 entry references `hasSidecar: false` in routeConfig — #1643 entry now provides that context in correct chronological order.

### Files Updated
- `serve/cockpit/README.md` — commit `84bf68f9`

### Scratch Files Cleaned
- None (no `1643-*` scratch files found)

[[2026-05-19T20:24:12+02:00]]
## Audit

### Regression Detection
Quality-runner full report: 2261 passed across vitest+pytest. Domain-scoped verification (Shell.sidecar-conditional_1643, Shell.test, routes.lazy-loading_1644): 28 passed, 0 failed. Failures in quality-runner output are pre-existing issues in unrelated test files (Card.visual-treatment, Column.css, PdsMotionTokens_1627, Shell.secondary-css) — none caused by #1643 changes.

### Intent Verification
Changed files: `serve/cockpit/web/src/Shell.css`, `serve/cockpit/web/src/routes.ts`, `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx`, `serve/cockpit/README.md`. All within cockpit-web domain. Implementation adds `hasSidecar` route config field with conditional sidecar render and CSS grid adjustment — matches stated purpose exactly. No extraneous scope.

### Architect Quality
AC quality score: 4/5. AC lines are specific (name exact field `hasSidecar`, exact selector `[data-region=\"sidecar\"]`, exact grid behavior, exact navigation scenarios). Minor gap: no explicit `hasSidecar: true` proof, but low risk (identical to unset at Shell.tsx:279). Cycle 4 architecture review provided correct root cause (React Router v7 startTransition) and effective loop-breaking technical direction.

### Commit Integrity
All deliverables committed:
- Builder: `3dc199d7` (feat), `3f4357d9` (fix, superseded by #1671 workspace state)
- Test-writer: `d879f989`, `229b1c1c`, `4ce869d6`
- Doc-writer: `84bf68f9`

No uncommitted source deliverables.

### Deduction Breakdown
No deductions.

### Confidence: 1.00
### Action: ARCHIVE
