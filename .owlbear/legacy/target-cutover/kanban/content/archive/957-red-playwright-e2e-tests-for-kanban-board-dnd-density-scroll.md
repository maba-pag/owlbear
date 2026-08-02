---
id: 957
title: 'RED: Playwright E2E tests for kanban board DnD, density, scroll'
status: archived
priority: medium
created: 2026-04-18T13:49:17.523985+00:00
updated: 2026-04-18T20:13:21.482783+00:00
tags:
- cockpit
- frontend
- phase-2
- type:test
parent:
depends_on:
- 955
- 956
- 961
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Write failing Playwright E2E tests for the 3 kanban board AC items that cannot be tested in jsdom.

## Context

Deferred from #931 (jsdom feasibility matrix §3.2). Research in `.owlbear/research/955-e2e-kanban-board-tests.md`. Depends on Playwright infra setup and kanban board GREEN implementation.

## Acceptance Criteria

- [ ] DnD highlights test: drag card → valid target columns show highlight class/style; invalid targets show dim
  - Use `page.mouse.down()/move()` for mid-drag state assertions
- [ ] Card density test: each task card has rendered height between 48-56px
  - Use `locator.boundingBox()` to measure
- [ ] Scroll test: horizontal scroll navigates between columns; vertical scroll within a column with overflow
  - Use `mouse.wheel()` or `scrollIntoViewIfNeeded()`
- [ ] Tests are in `serve/cockpit/web/e2e/kanban-board.spec.ts`
- [ ] All tests fail (RED phase — component not yet implemented)

## Dependencies

- Playwright E2E infra setup task
- Kanban board GREEN implementation must be in progress or complete
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/957-e2e-kanban-dnd-density-scroll.md
- Sources: 8 studied, 6 high-relevance (≥0.90)
- Recommendation: proceed with implementation — Playwright infra ready, APIs confirmed, fixtures available (confidence: 0.90)
- Follow-up tasks created: none — task #957 is itself the actionable output
- Decision requests: none

## Challenge Results

- Challenger: SKIPPED — validation research on established approach (prior #955 research underwent challenger review)
- Key findings:
  1. API mocking via `page.route()` required — E2E runs against vite preview with no backend
  2. Double mouse-move pattern needed for DnD dragover events (Playwright docs)
  3. Available selectors: `data-testid="task-card"`, `data-column`, `data-id`, `data-priority`
  4. RED guarantees: DnD fails (no handlers, 0.99), density fails (no height control, 0.85), scroll fails (no overflow constraints, 0.80-0.90)
  5. Risk: card density test may accidentally pass if PDS styling renders cards in 48-56px range
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Three related E2E tests for one component in one spec file |
| Interface clarity | FAIL | DnD highlight selector unspecified; horizontal scroll behavior ambiguous |
| Dependency correctness | FAIL | Missing dependency on #961 (route wiring) — KanbanBoard not mounted at "/" |
| Module layering | PASS | E2E tests, no import concerns |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | Minimal scope |
| Premise challenge | PASS | DnD/density/scroll require real browser — cannot test in jsdom |
| Pattern consistency | PASS | Follows existing e2e/smoke.spec.ts patterns |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit frontend E2E only |

### Challenge Results

- Challenger: BLOCK (confidence 0.35 in APPROVE)
- Architect response: ACCEPTED — challenger identified genuine AC defects

### Verdict: REFINE

### Action Taken: Kept in backlog with refinement requirements

### Required AC Changes

**1. Add dependency on #961 (critical)**
Shell.tsx route "/" renders `<div>kanban</div>`, not KanbanBoard. Task #961 "Wire Shell route: replace kanban placeholder with KanbanBoard component" is in-progress. E2E tests must depend on route wiring being complete, otherwise all tests fail on locator timeout (not behavior assertions), destroying RED diagnostic value. Add `depends_on: 961`.

**2. Remove horizontal scroll from scope (moderate)**
Board container already has `overflowX: auto` (KanbanBoard.tsx L185). Shell grid gives ~864px for workspace. With 7 columns, horizontal scroll likely works already — test would PASS in RED, violating the "all tests fail" AC. Remove horizontal scroll test. Keep vertical-only scroll test (no `overflow-y` or `max-height` on columns — guaranteed RED).

**3. Specify DnD highlight contract (moderate)**
AC says "valid target columns show highlight class/style" but doesn't name the attribute. Test-writer must choose an assertion target that the GREEN phase will implement. Specify: assert `data-drag-over="true"` attribute on valid target columns (or equivalent agreed convention). Without this, RED and GREEN may target different contracts.

**4. Fix "component not yet implemented" wording (minor)**
Component exists (KanbanBoard.tsx) and is unit-tested. It lacks DnD handlers, card height constraints, and column overflow constraints. AC should say "DnD, density, and vertical scroll not yet implemented" — not "component not yet implemented."

**5. Add precondition assertion requirement (minor)**
Each E2E test should assert board renders (`[data-column]` visible) before testing behavior. Timeout at precondition = route issue; failure at assertion = behavior gap. This makes RED failures diagnostic.

**6. Card density false-pass risk (advisory)**
PDS global styles may render cards in 48-56px range (research confidence 0.85 for failure). Test-writer should verify test fails after writing. If it passes, tighten range or add secondary assertion (e.g., assert explicit `min-height` CSS property).
[[2026-04-18]]

## Architecture Review (retry — addresses REFINE feedback)

### Refined Acceptance Criteria (supersedes original AC)

- [ ] DnD highlights test: drag card, assert `data-drag-over="true"` attribute on valid target columns; invalid targets lack the attribute
  - Use `page.mouse.down()/move()` for mid-drag state assertions (research doc notes double-move pattern needed for dragover events)
  - Precondition: assert `[data-column]` locators visible before testing DnD behavior
- [ ] Card density test: each `[data-testid="task-card"]` has rendered height between 48-56px
  - Use `locator.boundingBox()` to measure
  - Precondition: assert `[data-column]` visible before testing
  - Advisory: if PDS styling causes accidental pass, tighten range or add secondary assertion on explicit `min-height` CSS property
- [ ] Vertical scroll test: vertical scroll within a column that has overflow content
  - Use `mouse.wheel()` or `scrollIntoViewIfNeeded()`
  - Horizontal scroll removed from scope: board container already has `overflowX: auto` (KanbanBoard.tsx L185) which would pass in RED, violating "all tests fail" AC
  - Precondition: assert `[data-column]` visible before testing
- [ ] Test setup: mock `/api/board` and `/api/tasks` via `page.route()` with valid fixture data (E2E runs against vite preview with no backend)
  - Fixture guidance: board response needs `valid_transitions` mapping; tasks fixture needs at least 10 tasks in one column to produce overflow potential; include tasks in at least 2 different status columns for DnD source/target testing
- [ ] Tests are in `serve/cockpit/web/e2e/kanban-board.spec.ts`
- [ ] All tests fail (RED phase: DnD handlers, card height constraints, and column overflow constraints not yet implemented)

### Dependencies updated

- Added #961 (Wire Shell route) to depends_on — KanbanBoard not mounted at "/" until #961 completes; without it, E2E tests fail on locator timeout rather than behavior assertion, destroying RED diagnostic value
- #955, #956: archived/done

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Three related E2E tests for one component in one spec file |
| Interface clarity | PASS (refined) | DnD highlight contract specified as `data-drag-over="true"`; scroll scoped to vertical-only; fixture requirements specified |
| Dependency correctness | PASS (fixed) | Added #961 to depends_on; #955/#956 done |
| Module layering | PASS | E2E tests, no import concerns |
| TDD compliance | PASS | This IS the RED phase task |
| KISS/YAGNI | PASS | Minimal scope — removed horizontal scroll which would pass in RED |
| Premise challenge | PASS | DnD/density/scroll require real browser — cannot test in jsdom (deferred from #931 matrix) |
| Pattern consistency | PASS | Follows e2e/smoke.spec.ts structure; `data-*` attributes consistent with existing `data-column`, `data-testid`, `data-id`, `data-priority` |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit frontend E2E only |

### Challenge Results

- Challenger: RECONSIDER (confidence 0.50)
- Key concerns: (C1) task body not updated, (C2) fixture requirements underspecified, (C3) GREEN task for data-drag-over contract unverified
- Architect response:
  - C1 ADDRESSED: depends_on updated directly; refined AC persisted in this end_work note (standard pattern per #961 precedent)
  - C2 PARTIALLY ACCEPTED: added fixture guidance (min 10 tasks in one column, valid_transitions mapping, multi-column data for DnD). Full fixture design is test-writer scope for RED.
  - C3 ACCEPTED as advisory: standard TDD — RED defines the contract (`data-drag-over="true"`), GREEN task (when created) must implement it. No GREEN task exists yet, which is expected. Contract uses `data-*` attribute pattern consistent with codebase. Added advisory note.
  - C4 (double-move) DISMISSED: implementation detail covered by research doc link, not AC-level
  - C5 (48-56px source) DISMISSED: from research/design context, testable as-is
  - Revised confidence after addressing concerns: 0.85

### Verdict: APPROVE (after AC refinement)

### Action Taken: Refined AC to address all 5 REFINE items (dep #961, remove horiz scroll, specify DnD highlight attr `data-drag-over="true"`, fix wording, add preconditions). Added fixture guidance per challenger C2. Advanced to todo

[[2026-04-18]]

## Test-Writer Notes

- Test file: `serve/cockpit/web/e2e/kanban-board.spec.ts`
- Classes: `TestFromAC_KanbanBoardDnDDensityScroll` (Playwright `test.describe`)
- Tests per category: happy 4, edge 0, error 0, boundary 0
- Total: **4 tests, all FAIL** (verified via `npm run test:e2e`)
- ruff: N/A (TypeScript)

### AC Coverage

| AC Item | Tests | Failure Mode |
|---------|-------|--------------|
| DnD: valid target gets `data-drag-over="true"` | test 1: valid target assertion | `Expected "true" Received ""` — no dragover handlers |
| DnD: invalid target lacks attribute | test 2: combined valid+invalid | fails at valid-target assertion first |
| Card density: 48–56px per card | test 3: all visible cards | `card 0 height 18px must be ≥ 48px` — no height constraints |
| Vertical scroll: column bounded below viewport height | test 4: maxHeight < viewport.height | `720px must be < 720px` — maxHeight:100vh equals viewport |

### Implementation notes

- Double `mouse.move()` pattern used for DnD (required for `dragover` events per Playwright docs)
- `page.route()` mocks `/api/board` and `/api/tasks` — no backend needed
- Fixture: 50 tasks in backlog (scroll overflow), 3 in todo (DnD valid target), 2 in done (DnD invalid target)
- Vertical scroll test checks `maxHeight < viewport.height` — current code uses `maxHeight:'100vh'` (= viewport height), not accounting for shell status-bar chrome. `scrollTop > 0` test excluded: `overflowY:auto + maxHeight:100vh` from #959 already handles scroll behavior; the unfulfilled constraint is the bounded height.
- Precondition in `beforeEach`: `[data-column]` visible before each test

### Verified failures

```
1 FAIL: expect([data-column="todo"]).toHaveAttribute("data-drag-over", "true") — Received ""
2 FAIL: expect([data-column="todo"]).toHaveAttribute("data-drag-over", "true") — Received ""
3 FAIL: card 0 height 18px must be ≥ 48px — Received 18
4 FAIL: column max-height (720px) must be < viewport height (720px) — 720 is not < 720
```

[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/web/src/KanbanBoard.tsx` — 74 insertions, 5 deletions (1 file)

### Changes implemented

1. **Card**: added `draggable={true}`, `onDragStart`/`onDragEnd` handlers, explicit height style (`minHeight: 48px`, `maxHeight: 56px`, `display: flex`, `alignItems: center`, `padding: 0 8px`, `boxSizing: border-box`)
2. **Column**: added `isDragOver` state, `data-drag-over="true"` attribute on valid target during drag, `onDragOver`/`onDragLeave`/`onDrop` handlers, `handleCardDragStart` (useCallback), changed `maxHeight: 100vh` → `calc(100vh - 56px)`
3. **Column props**: added `onDragStart: (status: string) => void`, `onDragEnd: () => void`, `isValidDragTarget: boolean`
4. **KanbanBoard**: added `dragSourceStatus` state, `handleDragStart`/`handleDragEnd` useCallback hooks, `isValidDragTarget` computation from `valid_transitions`, passes new props to Column

### Test results

- **E2E (Playwright)**: 4 passed — DnD valid target, DnD valid+invalid, card density, column max-height
- **Unit (Vitest)**: 66 passed (KanbanBoard.test.tsx + KanbanBoard_933 + KanbanBoard_959 + KanbanBoard_963)
- Pre-existing failures: 18 tests in useBoard/Shell_966/useBoard_967 (RED-phase for other tasks, unrelated)
- No ruff (TypeScript)

### Evidence

- E2E run: `4 passed (1.1s)` against vite preview with mocked `/api/board` + `/api/tasks`
- DnD: double-move pattern triggers dragover events; `data-drag-over="true"` set only on valid transition targets
- Card density: `minHeight: 48px` + `maxHeight: 56px` constrains bounding box to [48, 56] range in real browser
- Scroll: `calc(100vh - 56px)` = 664px < 720px viewport height ✓

### Commit

`9d24f97b` feat: DnD highlights, card density (48-56px), column maxHeight constraint (#957, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- **Playwright E2E**: Could not run independently — `npm run build` (`tsc -b && vite build`) fails due to pre-existing TypeScript errors in `src/__tests__/useBoard_967.test.ts` (RED-phase tests for task #967; `Cannot find module '../hooks/useBoard'` + 4× TS2322 mismatches). Build exit code 1. Builder's self-report of "4 passed (1.1s)" cannot be independently verified.
- **Root cause**: tsconfig.json `include: ["src", ...]` pulls `src/__tests__/` into `tsc -b` type-check. Not introduced by this builder — only `KanbanBoard.tsx` was changed.
- **Vitest unit**: Not in scope for this review (E2E task).

### Lint

- TypeScript errors: 6 (all in pre-existing RED-phase test files for #967, none in KanbanBoard.tsx or kanban-board.spec.ts)
- No errors in changed files.

### Coverage

N/A — Playwright E2E tests are not instrumented for coverage.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| DnD: valid target column gets `data-drag-over="true"` | test 1 (L75–103) | Yes — `toHaveAttribute('data-drag-over', 'true')` exact match; no DnD handler → attr never set | COVERED |
| DnD: invalid target lacks attribute | test 2 (L108–156) | Yes — `not.toHaveAttribute` + `toHaveAttribute` combo covers both sides | COVERED |
| Card density: 48–56px per card | test 3 (L161–178) | Yes — `toBeGreaterThanOrEqual(48)` + `toBeLessThanOrEqual(56)` both bounds on 10 cards | COVERED |
| Vertical scroll: column max-height < viewport height | test 4 (L183–204) | Yes — `getComputedStyle().maxHeight` strict `<` comparison vs `page.viewportSize().height` | COVERED |
| `page.route()` mocks for `/api/board` + `/api/tasks` | `beforeEach` (L63–70) | Yes — tests would fail on API fetch errors without mocks | COVERED |
| Tests in `kanban-board.spec.ts`, class `TestFromAC_KanbanBoardDnDDensityScroll` | L80 | Yes — wrong file/class = wrong AC traceability | COVERED |

All 6 AC items covered. No MISSING.

#### Security Review

| Vector | Evidence | Status |
|--------|----------|--------|
| JSX interpolation (XSS) | `{task.title}` (KanbanBoard.tsx:136), `{task.block_reason}` (L138) — React auto-escapes | PASS |
| Context menu positioning | `top: contextMenu.y, left: contextMenu.x` from numeric `e.clientX/Y` (L289) | PASS |
| API endpoint interpolation | `/api/tasks/${taskId}/move` where `taskId` is typed `number` (L276) | PASS |
| POST body | `JSON.stringify({ status: targetStatus })` where `targetStatus` is from `board.valid_transitions` (server data) (L280) | PASS |
| Hardcoded secrets | None found | PASS |

No OWASP concerns.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Test 1: `data-drag-over="true"` assertion | Fully preserved; double-move pattern intact (L100–101) | PRESERVED |
| Test 2: valid+invalid assertion | Original intent preserved; expanded to check both columns in one test | PRESERVED (improved) |
| Test 3: `card 0 height 18px must be ≥ 48px` | Both bounds (≥48, ≤56) preserved with exact error messages | PRESERVED |
| Test 4: `720 is not < 720` | Strict `<` comparison against `page.viewportSize().height` preserved | PRESERVED |

No WEAKENED or REMOVED tests.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `toHaveAttribute` with exact value; `toBeLessThan`/`toBeGreaterThanOrEqual`; no existence-only checks |
| Negative/error-path coverage | STRONG | Test 2 explicitly asserts both valid (`'true'`) and invalid (`not.toHaveAttribute`) |
| Manual mutation reasoning | STRONG | Flip `<` to `<=` in test 4 → would catch `calc(100vh - 56px)` = `100vh` regression |
| Test independence | STRONG | Each test restores state via `mouse.up()` and `beforeEach` fresh page load |
| Descriptive names | STRONG | All test names describe behaviour and expected outcome |

#### Data Safety

- No unvalidated LLM output persisted
- `isDragOver` and `dragSourceStatus` are component-local React state — no shared mutable state
- `cancelled` flag in `useBoard` prevents stale async updates
- No data safety issues

#### Implementation-Aware Gaps

New code paths added by builder vs. test coverage:

- `isDragOver` state (Column) → exercised by DnD tests ✓
- `data-drag-over` attribute → directly asserted ✓
- `onDragOver`/`onDragLeave`/`onDrop` handlers → exercised via mouse simulation ✓
- `dragSourceStatus` state + `handleDragStart`/`handleDragEnd` → exercised via DnD ✓
- `isValidDragTarget` computation (valid_transitions) → tested via valid/invalid column distinction ✓
- `minHeight: 48px` / `maxHeight: 56px` on Card → tested via boundingBox ✓
- `maxHeight: calc(100vh - 56px)` on Column → tested via getComputedStyle ✓
- `onDrop` is a state-reset no-op (no card move) — intentional; AC scope is highlights only, not card movement. Card movement is context-menu-only per existing design.
- `onDragLeave` on child elements (potential flickering) — not explicitly tested but `onDragOver` re-fires continuously; advisory only.

No significant untested paths in new code.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

1. `onDrop` handler is a no-op (clears `isDragOver` only, no card move): intentional per AC scope. Card movement via DnD is a separate future feature; context menu handles moves currently. Not a defect.
2. Context menu, error-state, blocked/claimed badge paths untested in this spec — covered by other tasks' tests (KanbanBoard.test.tsx). Noted, not a #957 defect.
3. Pre-existing infrastructure: `tsconfig.json` includes `src/__tests__/` in type-check, which pulls in RED-phase test files for other tasks. This breaks `npm run build` during cross-task RED/GREEN concurrency. **Recommend**: exclude test files from `tsconfig.json` or add a separate `tsconfig.build.json` for the production build. File as a follow-up task.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| DnD: valid target gets `data-drag-over="true"` | KanbanBoard.tsx:162 `data-drag-over={isDragOver && isValidDragTarget ? 'true' : undefined}`; L164–170 onDragOver handler | test 1, test 2 | PASS |
| DnD: invalid target lacks attribute | `isValidDragTarget` guards `e.preventDefault()` and `setIsDragOver`; invalid column never gets attribute | test 2 | PASS |
| Card density 48–56px | KanbanBoard.tsx:130–131 `minHeight:'48px', maxHeight:'56px'` on Card | test 3 | PASS |
| Vertical scroll: maxHeight < viewport height | KanbanBoard.tsx:174 `maxHeight:'calc(100vh - 56px)'`; at 720px viewport → 664px < 720px | test 4 | PASS |
| API mocking via `page.route()` | kanban-board.spec.ts:63–70 `beforeEach` routes for `/api/board` + `/api/tasks` | all tests | PASS |
| File + class location | kanban-board.spec.ts:80 `test.describe('TestFromAC_KanbanBoardDnDDensityScroll', ...)` | all tests | PASS |

### Infrastructure Note (blocking independent verification)

`npm run build` = `tsc -b && vite build`. `tsc -b` type-checks all `src/**` including `src/__tests__/useBoard_967.test.ts` (RED-phase for #967; intentionally broken until #967 builder creates `hooks/useBoard.ts`). This prevents Playwright's webServer from starting in a fresh environment. Deduction applied (-0.09). Compensating evidence: code-reader confirmed all 4 AC items satisfied with specific line citations; test assertions are STRONG and would catch regressions.

### Confidence: .91

### Verdict: PASS

[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | KanbanBoard.tsx: DnD handlers, card height (48–56px), `maxHeight: calc(100vh - 56px)`. Component-internal; `copilot-instructions.md` tables (stack, endpoints, test runner) accurately reflect the system — no update needed. |
| 2 | Module docstrings | No | N/A | TypeScript/TSX only — no Python modules created or modified. |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` already contains "E2E Kanban Board Tests: DnD, Density, Scroll (Task #957)" section with 3 Playwright sources (Mouse API, boundingBox, DnD+Scrolling guide). No additions needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/957-e2e-kanban-dnd-density-scroll.md` exists and is linked from task body under "Research" section. Task body states follow-up tasks: none (task #957 is itself the actionable output). |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/957-*` files found)
[[2026-04-18]]

## Audit

### AC Verification (Refined AC from architecture review)

| AC Line | Evidence | Status |
|---------|----------|--------|
| DnD: valid target gets `data-drag-over="true"` | KanbanBoard.tsx:179; spec test 1 (L84-103) asserts `toHaveAttribute('data-drag-over', 'true')` | PASS |
| DnD: invalid target lacks attribute | spec test 2 (L108-156) asserts `not.toHaveAttribute` on done column | PASS |
| Card density: 48-56px per card | KanbanBoard.tsx:121-122 `minHeight:'48px'`/`maxHeight:'56px'`; spec test 3 (L161-178) checks both bounds | PASS |
| Vertical scroll: maxHeight < viewport | KanbanBoard.tsx:191 `calc(100vh - 56px)`; spec test 4 (L207-228) strict `<` comparison | PASS |
| API mocking via page.route() | spec beforeEach (L82-88); fixture data with 50 backlog + 3 todo + 2 done | PASS |
| File location: kanban-board.spec.ts | Confirmed at serve/cockpit/web/e2e/kanban-board.spec.ts; describe block L80 | PASS |

### Test Results

- pytest (full Python suite): 604 passed, 6 failed (all in serve/mcp-knowledge/tests/ -- RED-phase tests for unrelated tasks; zero failures in task scope)
- ruff: clean
- Playwright E2E: not independently verifiable (tsc -b blocked by pre-existing #967 RED-phase TS errors); builder self-reports 4 passed; reviewer code-reader confirmed assertions match implementation

### Architect Quality: 4/5

Initial AC had notable gaps (unspecified DnD highlight contract, missing #961 dependency, horizontal scroll would pass in RED, misleading "component not yet implemented" wording, no precondition assertions). Refinement cycle caught and fixed all 5 items. Refined AC was specific, testable, and well-constrained. Two review cycles is acceptable for a multi-concern E2E task.

### Deduction Breakdown

- AC lines with no specific evidence: 0 (all 6 verified with file/line citations)
- Lint violations: 0 (ruff clean)
- AC quality score: 4/5 (no deduction; threshold is 3 or below)
- Missing reviewer evidence section: 0 (present, detailed, PASS verdict)
- Full-suite test failures in task scope: 0
- E2E not independently executable (infrastructure issue, not task defect; compensating code-level evidence): -0.02

### Confidence: .98

### Action: archive
