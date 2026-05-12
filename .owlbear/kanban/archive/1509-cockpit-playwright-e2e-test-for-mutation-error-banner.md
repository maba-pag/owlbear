---
id: 1509
title: 'Cockpit: Playwright E2E test for mutation error banner'
status: archived
priority: nice-to-have
created: 2026-05-12T08:33:03.181002+00:00
updated: 2026-05-12T20:19:00.650708+00:00
tags:
  - cockpit
  - frontend
  - testing
  - type:test
parent: 1494
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---


## Objective
Add Playwright E2E test verifying the PDS PBanner mutation error banner in the Cockpit frontend.

## Acceptance Criteria
- New file `e2e/mutation-error-banner.spec.ts` in `serve/cockpit/web/`
- Test 1: PBanner visible after simulated API error — mock `/api/tasks/*/move` to 500, trigger context-menu transition, assert `p-banner` visible with heading containing "Move failed"
- Test 2: PBanner dismissible — dismiss banner from test 1, assert banner no longer visible
- Test 3: Banner clears on retry success — mock move to 200, re-trigger transition, assert no open `p-banner`
- Use `page.route()` mocking pattern from `kanban-board.spec.ts`
- Register route handlers in LIFO order: catch-all first, then specific routes
- Handle PDS shadow DOM for dismiss button interaction (Playwright auto-pierce or `page.evaluate()` fallback)

## Source
Research from task #1500; research doc `.owlbear/research/cockpit-mutation-error-tests.md`
2026-05-12T16:58:29+00:00

## Research
- Research doc: .owlbear/research/1509-playwright-mutation-error-banner.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: T1 autonomous — straightforward E2E test using established patterns (confidence: 0.90)
- Key findings: PDS shadow DOM auto-pierced by Playwright `.locator()`; dismiss button at `p-banner [popover] .dismiss`; context-menu → transition-item trigger proven in bench_959.spec.ts; LIFO route stub pattern from accessibility-1395.spec.ts
2026-05-12T16:58:34+00:00
Research complete. Validated existing research from #1500, confirmed PDS shadow DOM selectors from upstream source and E2E test patterns. Key findings: dismiss button at `p-banner [popover] .dismiss` (Playwright auto-pierces); context-menu trigger from bench_959.spec.ts; LIFO route stub from accessibility-1395.spec.ts. Task ready for architecture review — no follow-up tasks needed (this task IS the follow-up).
2026-05-12T17:23:01+00:00
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: E2E test for mutation error banner |
| Interface clarity | PASS | AC specifies exact file, 3 test scenarios with specific assertions |
| Dependency correctness | PASS | No deps; parent #1494 exists; banner impl in Shell.tsx confirmed |
| Module layering | N/A | Test file only — no production imports to violate |
| TDD compliance | PASS | Task IS a test; tagged `type:test` for pass-through |
| KISS/YAGNI | PASS | 3 focused test cases, follows existing patterns |
| Premise challenge | PASS | No E2E coverage for banner exists; unit tests in Vitest but E2E gap confirmed |
| Pattern consistency | PASS | References proven LIFO stub pattern (accessibility-1395), context-menu trigger (bench_959) |
| Security surface | N/A | Test file only |
| Single domain | PASS | Frontend testing domain only |

### Codebase Verification
- `PBanner` in Shell.tsx (L167-174): `open`, `heading`, `description`, `state`, `onDismiss`
- `onMutationError` in KanbanBoard.tsx (L167, 172, 221, 226): fires 'Move failed' on catch
- `data-testid="context-menu"` (KanbanBoard.tsx:349), `data-testid="transition-item"` (KanbanBoard.tsx:357)
- LIFO `stubApis()` helper: accessibility-1395.spec.ts L109-130
- 6 existing E2E specs in `serve/cockpit/web/e2e/` — pattern well-established

### Challenge Results
- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation
- Planner assignment: (not assigned)
- Final bundle: skip
- Existing proof scope: N/A
- Test-writer: SKIP

### Non-implementation tagging
- Added `type:test` — task writes tests with no production code change

### Verdict: APPROVE
### Action Taken: Advanced to todo. Tagged `type:test` for test-writer pass-through.
2026-05-12T18:11:37+00:00
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no Python test writing applicable.
- Task delivers a Playwright E2E TypeScript spec (`e2e/mutation-error-banner.spec.ts`); the builder authors the spec directly.
- Passing through to builder.
2026-05-12T19:00:04+00:00
## Builder Notes
- Files changed:
  - `serve/cockpit/web/e2e/mutation-error-banner.spec.ts`
- Implementation summary:
  - Added Playwright E2E coverage for mutation error banner behavior with 3 scenarios:
    - 500 `/api/tasks/*/move` response surfaces Move failed banner state.
    - Banner can be dismissed via PDS shadow DOM dismiss control (with evaluate fallback).
    - Banner clears after retry success when `/move` returns 200.
  - Reused established E2E route stubbing pattern with catch-all registered first to respect Playwright LIFO matching.
  - Added explicit mutation response assertions (`500` then `200`) to prove error then retry-success behavior.
- Test results (quality-runner, scoped):
  - Playwright: 3 passed, 0 failed (`serve/cockpit/web/e2e/mutation-error-banner.spec.ts`)
  - Lint (eslint on file): clean
  - Coverage: N/A for E2E run
- Verification evidence summary:
  - Initial RED evidence: target spec absent / failing harness before implementation.
  - GREEN evidence: quality-runner final report shows all 3 tests passing and lint clean.
- Fixes applied during build:
  - Tightened API route matching for `/move` endpoint handling.
  - Switched banner checks to runtime `p-banner` state polling and heading assertions for robust PDS behavior checks.
  - Added deterministic response-status checks around transition-triggered mutation requests.
- Commit:
  - `3b5b6a68a344f230653117b1efdbebd8e03991cb`
  - `test: add mutation error banner playwright coverage (#1509, builder)`
2026-05-12T19:39:46+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1509 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped quality-runner report shows Playwright 3 passed / 0 failed for `serve/cockpit/web/e2e/mutation-error-banner.spec.ts`, eslint clean, commit `3b5b6a68a344f230653117b1efdbebd8e03991cb`.
- Commit scope review: builder commit matched one changed file (`serve/cockpit/web/e2e/mutation-error-banner.spec.ts`); no overlapping review-scope changes were detected.
- Blocking findings: none.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| New file `e2e/mutation-error-banner.spec.ts` in `serve/cockpit/web/` | `serve/cockpit/web/e2e/mutation-error-banner.spec.ts:1` exists and the builder commit is scoped to that file | Builder evidence reports 3 passing Playwright checks on the new spec | PASS |
| Test 1: PBanner visible after simulated API error; mock `/api/tasks/*/move` to 500; trigger context-menu transition; assert heading contains `Move failed` | `serve/cockpit/web/src/KanbanBoard.tsx:209-221` raises `onMutationError('Move failed', ...)`; `serve/cockpit/web/src/Shell.tsx:167-172` binds `PBanner` `open`, `heading`, and `onDismiss` | `serve/cockpit/web/e2e/mutation-error-banner.spec.ts:66`, `:90`, `:100-124`, `:142-151`, `:150` stub `/move` to 500, trigger the transition, and assert open banner state plus `Move failed` heading | PASS |
| Test 2: PBanner dismissible | `serve/cockpit/web/src/Shell.tsx:172` clears banner state on dismiss | `serve/cockpit/web/e2e/mutation-error-banner.spec.ts:127-137`, `:154-180`, `:162` uses `p-banner [popover] .dismiss` with `shadowRoot` fallback and asserts `heading: ''` / `open: false` after dismiss | PASS |
| Test 3: Banner clears on retry success with `/move` returning 200 | `serve/cockpit/web/src/Shell.tsx:59-60` clears banner on mutation success; `serve/cockpit/web/src/KanbanBoard.tsx:211` calls `onMutationSuccess?.()` after successful move | `serve/cockpit/web/e2e/mutation-error-banner.spec.ts:184-213`, `:192`, `:197` flips the stub from 500 to 200, retries the transition, and asserts closed banner state | PASS |
| Use `page.route()` mocking pattern from `kanban-board.spec.ts` | `serve/cockpit/web/e2e/kanban-board.spec.ts:84-96` establishes the pre-navigation `page.route()` stubbing pattern; the new spec follows that same route-stub-before-`goto` structure at `serve/cockpit/web/e2e/mutation-error-banner.spec.ts:41-66` | All three tests rely on the shared `stubApis()` helper and route fulfillment setup | PASS |
| Register route handlers in LIFO order: catch-all first, then specific routes | `serve/cockpit/web/e2e/mutation-error-banner.spec.ts:40-66` registers `/api/**` first at line 41 and the specific `/move` handler at line 66; this matches the documented LIFO pattern in `serve/cockpit/web/e2e/accessibility-1395.spec.ts:109-137` | Route order is explicit in the helper and is necessary for the `/move` response assertions to pass | PASS |
| Handle PDS shadow DOM for dismiss button interaction | `serve/cockpit/web/src/Shell.tsx:172` wires `onDismiss`; existing banner contract tests in `serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx:235`, `:292`, `:322` validate heading/dismiss/success semantics for this banner surface | `serve/cockpit/web/e2e/mutation-error-banner.spec.ts:128-137`, `:165-180` exercises the auto-pierced dismiss control with an evaluate fallback and verifies the banner closes | PASS |

## Observations
- Proof sufficiency is acceptable: the E2E spec asserts `p-banner` host state (`open`, `heading`) rather than raw shadow text, and that aligns with the established Shell banner contract in `serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx`.
- Safety and security review: test-only change, no new dependencies, no secret handling, and no new untrusted-input path introduced.
2026-05-12T20:01:22+00:00
## Docs Gate

**Verdict: PASS**

### Checklist

| Item | Finding | Status |
|---|---|---|
| 1. README Verification | Changed file: `serve/cockpit/web/e2e/mutation-error-banner.spec.ts` → maps to `serve/cockpit/README.md`. Layer 1: no removed symbols/commands/flags (file-add only). Layer 2: README correctly describes E2E runner; new test file adds no new feature, interface, or command that requires doc update. | PASS — no-op |
| 2. External Attribution | Sources studied were internal code patterns (existing E2E specs, PDS/Playwright docs). No new external packages — no `overview.md` update needed. | N/A |
| 3. Research Doc | `.owlbear/research/1509-playwright-mutation-error-banner.md` exists and is linked in task body. | PASS |
| 4. Deletion Detection | No files deleted. | N/A |

### Files Updated
None — test-only task with no documentation drift.

### Scratch Cleanup
No `.owlbear/scratch/1509-*` files found.
2026-05-12T20:19:00+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 4396 passed, 212 failed, 4 skipped, lint clean\n- All 212 failures confirmed pre-existing (spot-checked at parent commit `d8b489d4` — same failures reproduce). All are Python tests; task added only a TypeScript E2E file — causal link impossible.\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS — single file `serve/cockpit/web/e2e/mutation-error-banner.spec.ts` (216 lines), placed correctly in `e2e/` alongside 6 existing specs\n- purpose match: PASS — E2E test for mutation error banner matches stated objective; 3 scenarios align with AC\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 5/5\nAC was specific and complete: exact file path, 3 named test scenarios with concrete assertions (mock 500, dismiss banner, retry 200), explicit pattern references (LIFO, shadow DOM), and named upstream source patterns. No builder improvisation required. Clean implementation path.\n\n### Commit Integrity\n- upstream commit presence: PASS — `3b5b6a68` scoped to exactly one file, message format correct (`test: ... (#1509, builder)`)\n- kanban commit packaging: pending (this step)\n\n### Deduction Breakdown\nNo deductions applied.\n\n### Confidence: 1.00\n### Action: archive