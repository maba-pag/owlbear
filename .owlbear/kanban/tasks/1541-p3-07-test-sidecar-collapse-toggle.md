---
id: 1541
title: 'P3-07: test — sidecar collapse toggle'
status: backlog
priority: important
created: 2026-05-13T18:41:58.362901+00:00
updated: 2026-05-13T22:33:41.401835+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - test
  - frontend
parent: 1534
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Tests for sidecar collapse/expand button, visibility toggle, state persistence across re-renders
- **Out:** Sidecar CSS implementation, transition animation, layout space reclaim verification

## Acceptance Criteria

- AC-1: Vitest renders Shell, finds a collapse toggle button (`data-testid="sidecar-collapse"`) with `aria-expanded="true"` (default open) and `aria-controls` referencing the sidecar region; clicking the button sets `aria-expanded` to `"false"` and the sidecar panel becomes hidden (asserted via `aria-expanded` attribute change)
- AC-2: Vitest verifies collapsed state persists after `rerender()` — sidecar remains collapsed (`aria-expanded="false"`) without re-clicking

Proof bundle: behavioral

## Builder Guidance
- Follow filter toggle ARIA pattern from KanbanBoard.tsx (L269-271: `aria-expanded` + `aria-controls` + `onClick` toggle)
- Use Shell.test.tsx mock setup (vi.mock EventSourceProvider + vi.stubGlobal fetch)
- Test file: `src/__tests__/SidecarCollapse_1541.test.tsx`
- RED phase: tests must fail against current Shell.tsx (no collapse mechanism exists yet)

## Research
- Research doc: .owlbear/research/1541-sidecar-collapse-toggle-test-approach.md
- Sources: 6 studied, 3 high-relevance (filter toggle pattern, Shell.test.tsx, brief)
- Recommendation: ARIA disclosure pattern (aria-expanded + aria-controls) with CSS class toggle for visibility, rerender() for state persistence test (confidence: 0.85)
- Follow-up tasks created: none (implementation task #1549 already exists)
- Decision requests: none
2026-05-13T19:46:57+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: tests for sidecar collapse toggle |
| Interface clarity | PASS (refined) | AC-1/AC-2 tightened to name exact assertion targets (aria-expanded, data-testid, rerender()) |
| Dependency correctness | PASS | No deps needed — RED phase tests against not-yet-implemented code |
| Module layering | PASS | Frontend test, no cross-layer concerns |
| TDD compliance | PASS | This IS the RED phase test task; #1549 depends on it for GREEN |
| KISS/YAGNI | PASS | 2 test cases, minimal scope |
| Premise challenge | PASS | Brief specifies "collapsible sidecar, toggle button" |
| Pattern consistency | PASS | Follows established filter toggle ARIA pattern (KanbanBoard.tsx L269-271, FilterAccessibility.test.tsx) |
| Security surface | PASS | No security boundary |
| Single domain | PASS | Frontend/cockpit only |

### Challenge Results
- Challenger: reconsider (confidence 0.62)
- Findings: (1) AC-1 "hides/shows" ambiguous about assertion mechanism; (2) AC-2 hardcodes "via local React state" (implementation bias from planner); (3) research presents 3 hide mechanisms without fully settling
- Architect response: ACCEPTED findings 1+2, refined AC to specify exact assertion targets (aria-expanded attribute) and removed mechanism bias. Finding 3 addressed by narrowing assertion to aria-expanded (implementation detail of HOW to hide is deferred to impl task #1549). Layout-space-reclaim explicitly scoped out — covered by #1549 and consolidation test #1554.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (pass-through via `test` tag — builder writes test file as deliverable)

### Design Diverge
- Trigger: skipped — single established approach (ARIA disclosure pattern), no competing designs

### Verdict: APPROVE (after AC refinement)
### Action Taken: Refined AC-1 to specify aria-expanded assertion target and data-testid contract; refined AC-2 to remove local-state mechanism bias; added Builder Guidance section; scoped out layout-space verification. Advanced to todo.
2026-05-13T20:07:08+00:00
## Test-Writer Notes
- Non-implementation task (tagged `test`) — no Python pytest tests applicable.
- Frontend Vitest test file is the builder deliverable: `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx`
- AC-1 / AC-2 target Vitest + @testing-library/react assertions against Shell.tsx — builder writes RED-phase tests per Builder Guidance.
- RED constraint: tests must fail against current Shell.tsx (no collapse mechanism exists yet).
- Passing through to builder.
2026-05-13T20:26:42+00:00
## Builder Notes
- Files changed:
  - serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx
- Implemented AC coverage in task-scoped RED test suite:
  - AC-1: asserts `data-testid="sidecar-collapse"`, default `aria-expanded="true"`, `aria-controls` presence, and click transition to `aria-expanded="false"`.
  - AC-2: asserts collapsed state (`aria-expanded="false"`) persists after `rerender()`.
- Quality-runner evidence (scoped):
  - Tests: 0 passed, 2 failed (expected RED)
  - Failed tests:
    - `AC-1: sidecar collapse toggle exposes disclosure ARIA and flips aria-expanded to false on click` → `sidecar-collapse toggle not found`
    - `AC-2: collapsed state persists after rerender` → `sidecar-collapse toggle not found`
  - Lint: clean (`eslint` exit 0)
- Behavioral summary:
  - RED gate confirmed against current Shell implementation (no sidecar collapse control yet).
  - Test deliverable committed for downstream GREEN implementation task.
- Commit:
  - bd8e01fc
  - `test: add RED tests for sidecar collapse toggle (#1541, builder)`
2026-05-13T21:05:11+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1541 -> todo | AC-1 proof is insufficient: the RED test only checks that `aria-controls` exists, not that it references the sidecar region required by the task.
- Builder evidence reviewed first and found sufficient for review scope: task-scoped quality-runner reported `0 passed, 2 failed (expected RED)` with both failures caused by the missing `sidecar-collapse` toggle, lint clean, and builder commit `bd8e01fc` present in git logs.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | Task contract requires `aria-controls` to reference the sidecar region (`.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:30`). Existing Shell sidecar region is the target surface (`serve/cockpit/web/src/Shell.tsx:168`). Comparable cockpit ARIA tests assert a concrete control-to-region linkage rather than mere presence (`serve/cockpit/web/src/__tests__/FilterAccessibility.test.tsx:162`, `serve/cockpit/web/src/components/FilterPanel.tsx:137-138`). | `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:37` selects any element with the test id, and `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:50` only asserts `aria-controls` is truthy. A future GREEN implementation could point `aria-controls` at an orphan or non-sidecar element and still pass this suite. | FAIL |
| AC-2 | No implementation bias in the task contract; only persistence across rerender is required. | `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:56-75` clicks once, verifies `aria-expanded="false"`, rerenders, and re-verifies `aria-expanded="false"` without another click. | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC-1 | The test does not prove that the collapse toggle's `aria-controls` attribute references the sidecar region required by the AC; it only proves the attribute exists. This is a false-green risk for task #1549. | `.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:30`; `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:50`; `serve/cockpit/web/src/Shell.tsx:168` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Tighten AC-1 proof so the `sidecar-collapse` test verifies that the toggle's `aria-controls` value resolves to the sidecar region element, not merely that the attribute is present. | serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx; serve/cockpit/web/src/Shell.tsx | AC-1 contract at `.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:30`; weak assertion at `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:50` |

## Observations
- AC-2 coverage is adequate as written.
- Challenger cross-check returned `proceed` with 0.83 confidence on the FAIL verdict and agreed the strongest blocker is the unproven `aria-controls` -> sidecar relationship.
- Secondary hardening opportunity: consider proving interactive/button semantics explicitly instead of locating any element by `data-testid` alone (`serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:37`), but that is weaker than the blocking AC-1 gap and not required for this reject.
2026-05-13T21:48:11+00:00
## Test-Writer Notes
- Retry: tightened AC-1 `aria-controls` assertion per reviewer Required Follow-up #1.
- Test file: serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx
- Classes: TestFromAC_SidecarCollapse_1541
- AC-1 change: replaced `expect(aria-controls).toBeTruthy()` with bidirectional linkage check — resolves the `aria-controls` value to a DOM element, asserts that element has `data-region="sidecar"`, and asserts that element's `id` matches the `aria-controls` value. A future GREEN impl cannot point `aria-controls` at an orphan element and still pass.
- AC-2: unchanged (PASS in reviewer evidence; no modification)
- Tests per category: happy 1, edge 0, error 0, boundary 0 (AC-2: happy 1) — total 2 tests, all FAIL
- ESLint: clean (exit 0)
- Commit: f20d716b
2026-05-13T22:04:09+00:00
## Builder Notes
- Files changed: none (non-implementation pass-through retry verification)
- Scope check: Test-writer retry updated `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx` to tighten AC-1 `aria-controls` proof (control id resolves to sidecar region)
- Quality-runner evidence (scoped):
  - Tests: 0 passed, 2 failed (expected RED for this test task)
  - Failed tests:
    - `AC-1: sidecar collapse toggle exposes disclosure ARIA and flips aria-expanded to false on click` -> `sidecar-collapse toggle not found`
    - `AC-2: collapsed state persists after rerender` -> `sidecar-collapse toggle not found`
  - Lint: clean (`eslint` exit 0)
- Evidence summary:
  - Reviewer-requested proof gap is addressed in the test file: AC-1 now verifies `aria-controls` targets the sidecar region (`data-region="sidecar"`) rather than only checking attribute presence.
  - Current Shell still has no collapse control, so RED behavior remains correct and expected for downstream GREEN implementation task.
- Fixes applied: none in builder cycle (verification and routing only).
2026-05-13T22:33:41+00:00
## Review Evidence
- Verdict: FAIL
- FAIL #1541 -> backlog | AC-1 still does not prove that the `sidecar-collapse` control is a button, and a second review-cycle proof gap escalates to backlog.
- Builder evidence reviewed first and found sufficient for review scope: task-scoped quality-runner reported `0 passed, 2 failed (expected RED)` with both failures caused by the missing `sidecar-collapse` toggle, lint clean, and commit presence confirmed in `.git/logs/**` for `bd8e01fc` and `f20d716b`.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | The task contract requires a collapse toggle button (`.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:30`). The builder guidance points to the existing disclosure pattern implemented as a real `<button type="button">` in `serve/cockpit/web/src/KanbanBoard.tsx:264-267`. The sidecar region target remains `serve/cockpit/web/src/Shell.tsx:168`. | The retry correctly tightened the `aria-controls` linkage (`serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:51-55`), but the control is still located only via `[data-testid="sidecar-collapse"]` (`serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:37`) and the remaining assertions only inspect ARIA attributes/click behavior (`serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:49-59`). A non-button element with the same attributes and click handler would still satisfy this suite, so the explicit button contract is unproved. | FAIL |
| AC-2 | The task contract requires collapsed state to persist across `rerender()` (`.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:31`). | The test clicks once, verifies `aria-expanded="false"`, rerenders, and re-verifies `aria-expanded="false"` without another click (`serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:62-80`). | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---|---|---|---|
| 1 | AC-1 | The RED test still does not prove the control is a button, even though AC-1 and the referenced repo pattern both require button semantics. This leaves a false-green path for task #1549 because a `div`/`span` with the same test id, ARIA attributes, and click handler would pass. This is the second review cycle on the same task (`.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:109`, `.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:134`), so the remaining proof gap escalates to backlog. | `.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:30`; `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:37`; `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:49-59`; `serve/cockpit/web/src/KanbanBoard.tsx:264-267` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC-1 and builder guidance so the semantic button requirement is explicit and reissue the RED proof obligation with a button/role assertion before this task returns to test-writing. | .owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md; serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx; serve/cockpit/web/src/KanbanBoard.tsx | AC-1 contract at `.owlbear/kanban/tasks/1541-p3-07-test-sidecar-collapse-toggle.md:30`; test selector/attribute-only proof at `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:37` and `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:49-59`; button pattern at `serve/cockpit/web/src/KanbanBoard.tsx:264-267` |

## Observations
- The retry fully closed the earlier `aria-controls` -> sidecar linkage gap: `serve/cockpit/web/src/__tests__/SidecarCollapse_1541.test.tsx:51-55` now tie the control to the sidecar region at `serve/cockpit/web/src/Shell.tsx:168`.
- AC-2 coverage is adequate as written.
- Challenger cross-check returned `reconsider` with 0.72 confidence on a PASS verdict; its only blocking objection matched the button-semantics gap above.
- No independent quality-runner rerun was required because the builder evidence was internally consistent for this RED test task.