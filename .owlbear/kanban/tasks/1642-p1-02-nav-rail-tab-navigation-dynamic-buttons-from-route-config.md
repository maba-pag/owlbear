---
id: 1642
title: 'P1-02: Nav-rail tab navigation — dynamic buttons from route config'
status: review
priority: needed
created: 2026-05-18T00:49:27.319192+02:00
updated: 2026-05-19T10:24:22.599768+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1639
ac:
  - Nav-rail element has role="navigation" and renders one button per route 
    config entry; each button triggers useNavigate() to its route path on click
  - Active route's nav-rail button has aria-current="page"; inactive buttons do 
    not have aria-current; switching routes updates aria-current accordingly
  - 'Validation gate: adding a third entry to the route config array produces a third
    nav-rail button that navigates to the new route path'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Nav-rail `<nav>` element wiring in Shell.tsx — render buttons from route config, `useNavigate()` handlers, `aria-current="page"` on active route, `role="navigation"` semantics.

**Out:** Route config creation (P1-01), sidecar conditioning (P1-03), lazy loading (P1-04), badge (P2-03).

## Context

Shell.tsx nav-rail currently has a single hardcoded `<button>` with `data-surface="kanban"` and static `aria-current="page"`. This task replaces it with dynamic buttons driven by route config, using `useLocation()` or `useMatch()` to determine the active state.

[[2026-05-19T08:06:34+02:00]]
## Research

See `.owlbear/research/nav-rail-tab-navigation.md`

**Key findings:**
- Use `useLocation()` + exact pathname match for active state (hooks-rules compliant, KISS)
- Use `useNavigate()` for click handlers
- Icon rendering via module-level `Record<string, ReactNode>` SVG map (no new deps)
- Keep `data-surface={route.icon}` to preserve existing test selectors
- Add explicit `role="navigation"` to `<nav>` per AC
- ~1 file touched: Shell.tsx (add imports, hooks, replace hardcoded button with `routeConfig.map()`)
- Durable tests query `[data-surface="kanban"]` and `[aria-current="page"]` — implementation must preserve these selectors

**Implementation: single file edit**
1. Shell.tsx — add `useNavigate`/`useLocation` imports, icon map const, replace hardcoded button with dynamic loop

**Classification:** T1 — standard React Router pattern, no architecture change
**Confidence:** 0.92

[[2026-05-19T08:06:42+02:00]]
## Research

Research complete. Key findings:
- Single viable approach: `useLocation()` + exact pathname match + `useNavigate()` handlers (NavLink renders `<a>` not `<button>`; `useMatch` violates hooks rules in loops)
- Icon rendering via module-level SVG map (`Record<string, ReactNode>`) — KISS, no new deps
- Preserve `data-surface={route.icon}` for durable test selector compatibility
- Implementation: ~1 file (Shell.tsx edit only)
- Trade-off matrix documented; Option A dominates on all criteria

Doc: `.owlbear/research/nav-rail-tab-navigation.md`
Confidence: 0.92
Classification: T1 — standard React Router pattern
No new follow-up tasks — siblings already cover downstream work.

[[2026-05-19T08:27:44+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Only nav-rail button wiring from route config. Route config (P1-01), sidecar (P1-03), lazy loading (P1-04), badge (P2-03) properly split into siblings. |
| Interface clarity | PASS | AC specifies observable DOM behavior: role attribute, button count from config, navigate on click, aria-current toggle. |
| Dependency correctness | PASS | #1639 archived/completed. `routeConfig` array exists in `routes.ts` with `{ path, label, icon, component }` entries. |
| Module layering | PASS | Shell.tsx already imports `routeConfig` from `./routes`. Adding `useNavigate`/`useLocation` from `react-router` is leaf-level hook usage. No upward imports. |
| TDD compliance | PASS | proof_bundle=behavioral. Shell.test.tsx has durable selectors (`[data-surface=\"kanban\"]`, `[aria-current=\"page\"]`). |
| KISS/YAGNI | PASS | Single file edit. Module-level icon SVG map for 2 icons. Exact pathname match (not prefix). No new deps. |
| Premise challenge | PASS | Nav-rail buttons are currently hardcoded. NavLink renders `<a>` not `<button>` (incompatible). No existing tooling provides this. |
| Pattern consistency | PASS | Follows routeConfig.map() pattern from #1639. Uses standard React Router hooks. |
| Security surface | PASS | Client-side navigation only. No new system boundaries. |
| Single domain | PASS | Cockpit frontend only (scope:cockpit-web). |

### Failure Mode Map
N/A — client-side nav rendering. No failure codepaths beyond React's own error boundary.

### Design Diverge
- Trigger: skipped — research compared 3 options, Option A (useLocation + exact match) dominates on all criteria. Option B invalid (hooks rules in loops). Option C incompatible (renders anchors, not buttons).

### Challenge Results
- Challenger: reconsider (confidence 0.64)
- Findings: (1) B1 — AC lines don't name Shell component explicitly as target, (2) regression surface broader than single file (PdsMigration, e2e specs), (3) icon map exhaustiveness not guaranteed by AC3, (4) PDS exception scope for multiple buttons
- Architect response: override with justification
  - (1) Frontend tests target rendered DOM elements — \"nav-rail element\" is the concrete target. Shell is implied by task scope. Minor stylistic.
  - (2) Research doc explicitly guides builder to preserve `data-surface={route.icon}` and durable tests guard regressions.
  - (3) AC3 tests button rendering + navigation, not icon presence. YAGNI for 2-icon system.
  - (4) PDS exception is guarded by existing PdsMigration durable tests.
  - All concerns are implementation-level risks already mitigated by research guidance + durable test safety net, not AC clarity defects.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Approved backlog → todo. Challenger override justified — concerns are implementation risks already mitigated by research doc guidance and durable test regressions, not AC ambiguity.

[[2026-05-19T08:49:34+02:00]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx`
- Classes: `TestFromAC_NavRailButtons`
- Tests per category: happy 14, edge 2, boundary 6
- Total: 22 tests, all FAIL (0 passed)
- lint: ESLint clean

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1 — role="navigation" + one button per routeConfig entry, click triggers navigate | 8 tests |
| AC2 — aria-current="page" on active; absent on inactive; updates on route switch | 9 tests |
| AC3 — validation gate: 3-entry routeConfig produces 3rd button navigating to new path | 5 tests |

**Why all fail against current code:**
- Hardcoded kanban `<nav>` has no explicit `role="navigation"` attribute → AC1 #1 fails
- Only 1 hardcoded button (`data-surface="kanban"`); routeConfig mocked to 3 entries → count tests fail
- `[data-surface="decisions"]` and `[data-surface="test-route"]` missing → nav helper throws → fails
- Hardcoded `aria-current="page"` on kanban (ignores route) → AC2 inactive/unknown-route tests fail
- No `onClick` / `useNavigate()` handler on kanban button → navigate("/") test fails

[[2026-05-19T09:16:44+02:00]]
## Builder Notes
- Implementation: serve/cockpit/web/src/Shell.tsx
- Files changed: dynamic nav-rail buttons now render from route config with explicit role="navigation", click-to-navigate handlers, and route-aware aria-current state.
- Approach: added useNavigate + existing useLocation pathname matching; replaced hardcoded kanban button with routeConfig map; preserved selectors via data-surface={route.icon} and kept PDS exception markers per button.
- Tests (quality-runner): 22/22 passed in serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx
- Module baseline (quality-runner): 18/18 passed in serve/cockpit/web/src/__tests__/Shell.test.tsx
- Lint (quality-runner): clean for serve/cockpit/web/src/Shell.tsx and task test file
- Coverage (quality-runner): Shell.tsx 71.21% on scoped task-proof run
- Commit: f2c36663 (feat: wire nav-rail buttons from route config (#1642, builder))

[[2026-05-19T09:48:21+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1642 -> todo | AC1/AC3 dynamic route-config behavior is implemented in code, but the task-local proof would also pass a manually hardcoded three-button nav.
- Builder evidence reviewed first: `NavRailButtons_1642.test.tsx` 22/22 passed, `Shell.test.tsx` 18/18 passed, lint clean for `Shell.tsx` and the task test, scoped `Shell.tsx` coverage 71.21%.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/Shell.tsx:344-358` adds explicit `role="navigation"`, renders buttons via `routeConfig.map(...)`, and wires `onClick={() => navigate(route.path)}`. | `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx:103-155` verifies explicit role, three rendered buttons, presence of specific surfaces, and click navigation for `/` and `/decisions`. | FAIL — the assertions prove the current three-button behavior, but not that button rendering is actually derived from `routeConfig` rather than hardcoded to the current mocked trio. |
| AC2 | `serve/cockpit/web/src/Shell.tsx:346-355` computes active state from `pathname === route.path` and gates `aria-current` per button. | `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx:160-220` covers active/inactive states, route switching, unknown-route behavior, exact `aria-current="page"`, and single-active-button behavior. | PASS |
| AC3 | `serve/cockpit/web/src/Shell.tsx:346-358` maps every route entry to a button and navigates to the entry path. | `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx:29-37` fixes the mock to three entries, then `:228-257` asserts a `test-route` button exists, navigates, and becomes current. | FAIL — a manually hardcoded three-button nav that matches the mocked trio would still satisfy this suite, so the validation gate is not falsifiable from tests alone. |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1, AC3 | Task-local proof does not falsify a non-data-driven implementation. The suite pins the mock to exactly three entries and asserts `3` plus a hardcoded `test-route` button, so a manually hardcoded three-button nav would still pass. | `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx:29-37`, `:111`, `:152-155`, `:228-257`; contrast with the real data-driven implementation at `serve/cockpit/web/src/Shell.tsx:346-358`. | todo |

## Observations
- Adjacent durable regression surfaces exist at `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx:292-298` and `serve/cockpit/web/src/__tests__/Shell.tab-routing_1639.test.tsx:206`; including the relevant ones in the next evidence bundle would strengthen confidence, but their omission was not the blocking issue.
- No editor-reported TypeScript errors were found in `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx`, or `serve/cockpit/web/src/__tests__/Shell.test.tsx` during review.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen task-local proof so at least one test fails against a manually hardcoded three-button nav and specifically proves nav buttons are derived from `routeConfig` entries, not just matched to the current mocked trio. | `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx` | Review finding #1; current mock/assert pattern at `:29-37`, `:111`, `:152-155`, `:228-257`. |

[[2026-05-19T10:24:22+02:00]]
## Test-Writer Notes
- Retry: added 4 falsifiability gate tests addressing reviewer finding #1. Builder skip: test-only retry, all 26 tests green.
- Test file: `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx`
- New describe class: `AC1/AC3 — falsifiability gate: button count and surface track config entries` (nested in `TestFromAC_NavRailButtons`)
- Tests added (4): happy/falsify × 4

**What changed:**
- Replaced static `vi.mock('../routes', () => ({ routeConfig: [...] }))` with a `vi.hoisted()` mutable array (`routeConfigMut`) exported via the same mock. Shell.tsx holds a reference to this array; in-place mutation is visible at render time.
- Each falsifiability test mutates `routeConfigMut` to use novel entries (`sentinel-1642`, `gate-1642`, `extra-gate-1642`) that no hardcoded implementation would render, then restores via `afterEach`.

**AC coverage gap closed:**
| Finding | Test(s) | Why it falsifies hardcoded |
|---------|---------|---------------------------|
| AC1/AC3: 3-button mock matches what impl could hardcode | ac1 falsify (1-entry → 1 button) | Hardcoded 3-button nav yields 3 ≠ 1 |
| AC1/AC3: 3-button mock matches what impl could hardcode | ac1 falsify (sentinel icon present) | Hardcoded nav has no sentinel-1642 button |
| AC1/AC3: 3-button mock matches what impl could hardcode | ac3 falsify (4-entry → 4 buttons) | Hardcoded 3-button nav yields 3 ≠ 4 |
| AC1/AC3: 3-button mock matches what impl could hardcode | ac3 falsify (gate-1642 navigates to /gate-test-1642) | Hardcoded nav has no gate-1642 button → navBtn throws |

- Quality-runner: 26/26 passed, ESLint clean
- Commit: 69b45761 (test: add falsifiability gate tests for nav-rail data-driven rendering (#1642, test-writer))
