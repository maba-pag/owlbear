---
id: 1643
title: 'P1-03: Route-conditional sidecar — suppress sidecar DOM on non-kanban routes'
status: todo
priority: needed
created: 2026-05-18T00:49:27.343819+02:00
updated: 2026-05-19T09:43:37.837179+02:00
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
archival_reason:
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
