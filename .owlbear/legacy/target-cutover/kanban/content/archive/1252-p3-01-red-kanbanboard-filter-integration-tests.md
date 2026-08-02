---
id: 1252
title: 'P3-01: RED — KanbanBoard filter integration tests'
status: archived
priority: medium
created: 2026-05-01T04:34:55.076834+00:00
updated: 2026-05-03T11:21:43.918409+00:00
tags:
- phase-3
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on:
- 1251
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Vitest + Testing Library integration tests for KanbanBoard filter wiring:
  - Board renders filter toggle button (td:1)
  - Toggle button opens/closes FilterPanel (td:2)
  - Filter state changes cause filtered tasks to appear in correct columns (td:2)
  - Derived availableTags computed from full (unfiltered) task set — set-membership, order-insensitive (td:1)
  - Result count displays "N / M tasks" when filter is active (td:1)
  - Filter change dismisses open context menu (td:1)
  - Filter change cancels active drag — drop targets deactivated (td:1)
  - Empty filter state shows all tasks (td:1)
- All tests fail (RED) — KanbanBoard not yet wired to FilterPanel (td:0)

## In Scope
- Integration test file for KanbanBoard + FilterPanel
- Tests for state management, derived data, interaction rules

## Out of Scope
- KanbanBoard implementation changes (next task)
- Layout/CSS assertions (visual regression, not unit-testable)
- Accessibility (Phase 4)

Brief: see parent #1247
[[2026-05-02]]
## Research

**Key findings:** KanbanBoard currently has zero filter-related code — no toggle, no FilterPanel import, no filterTasks call. All 10 planned integration tests will fail cleanly on missing DOM elements.

**Test strategy:**
- Mock FilterPanel following ArchivalModal pattern (vi.mock + callback capture)
- 10 test cases covering 8 AC lines
- Testids: `filter-toggle`, `filter-result-count`, `filter-panel-stub`, `filter-badge`
- File: `src/__tests__/KanbanBoard_1252.test.tsx`

**Trade-off:** Single mock strategy (callback capture) — no competing options. Confidence: 0.92.

**Doc:** `.owlbear/research/kanbanboard-filter-integration-red-1252.md`

No follow-up tasks needed — #1253 (GREEN successor) already exists with correct dependency.
[[2026-05-02]]
## Architecture Review

### Verdict: APPROVED

### AC Assessment

| AC Line | td | Assessment | Action |
|---|---|---|---|
| Board renders filter toggle button | td:1 | Clear, testable via DOM query | None |
| Toggle button opens/closes FilterPanel | td:2 | Two states (open/close), needs both transitions | None |
| Filter state → filtered columns | td:2 | Multiple filter scenarios needed | None |
| availableTags from full set | td:1 | Tightened: set-membership, order-insensitive | Reworded — challenger caught ordering ambiguity |
| Result count "N / M tasks" | td:1 | Clear format, single assertion | None |
| Filter change dismisses context menu | td:1 | Clear interaction chain | None |
| Filter change cancels drag | td:1 | Reworded to behavioral: "drop targets deactivated" | Reworded — challenger caught naming drift (dragSourceStatus vs dragSource) |
| Empty filter shows all tasks | td:1 | Clear baseline check | None |
| All tests fail (RED) | td:0 | Meta-condition, verified by running tests | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test file, one concern: KanbanBoard filter wiring |
| Interface clarity | PASS | After refinement — behavioral AC, no internal-state naming |
| Dependency correctness | PASS | #1251 (FilterPanel GREEN) archived/done; FilterPanel.tsx and filterTasks.ts both exist |
| Module layering | PASS | Test-only task, no production code |
| TDD compliance | PASS | This IS the RED phase task; #1253 GREEN successor exists |
| KISS/YAGNI | PASS | 10 tests for 8 AC lines — proportionate |
| Premise challenge | PASS | KanbanBoard has zero filter code; tests drive GREEN implementation |
| Pattern consistency | PASS | Mock strategy follows ArchivalModal callback-capture pattern (KanbanBoard_1246.test.tsx) |
| Security surface | PASS | Test file only |
| Single domain | PASS | Frontend tests, single component |

### Challenger Results

Confidence: 0.62, recommendation: block.

Three points accepted and addressed:
1. **td annotations missing** — added to all AC lines
2. **availableTags ordering** — tightened to "set-membership, order-insensitive"
3. **Drag-cancel naming drift** — reworded to "drop targets deactivated" (observable behavior)

Two points overridden:
- **Selector overreach** — research provides implementation hints; AC is behavioral. Test-writer determines selectors.
- **Mock as integration** — mocking FilterPanel is correct for wiring coverage. FilterPanel internals are Phase 2's domain (shipped). Challenger acknowledged this as valid alternative reading.

### Architecture Notes

- KanbanBoard.tsx confirmed: zero filter-related code (no imports, state, or render)
- FilterPanel props: `{filter, onFilterChange, priorities, availableTags, open}` — stable interface from #1251
- filterTasks: `filterTasks(tasks, filter) → Task[]` — pure function, already implemented
- 6 existing KanbanBoard test files establish clear patterns for mocking, wrapping, and asserting
[[2026-05-02]]
## Test-Writer Notes

- **File:** `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`
- **Class:** `TestFromAC_FilterIntegration`
- **Total:** 10 tests, all FAIL (RED confirmed)
- **Lint:** ESLint clean

### Tests per category

| Category | Count | Tests |
|---|---|---|
| Happy path | 4 | toggle opens panel, priority filter hides tasks, text filter hides tasks, empty filter shows all tasks |
| Edge/boundary | 2 | toggle closes panel (second click), availableTags from full set regardless of active filter |
| Interaction rules | 3 | filter change dismisses context menu, filter change deactivates drag targets, result count shows N/M |
| Render | 1 | filter toggle button exists |

### AC coverage

| AC Line | td | Tests |
|---|---|---|
| Board renders filter toggle button | 1 | `renders a filter toggle button` |
| Toggle opens/closes FilterPanel | 2 | `clicking filter toggle opens FilterPanel`, `clicking filter toggle again closes FilterPanel` |
| Filter state → filtered columns | 2 | `priority filter removes non-matching tasks`, `text filter removes non-matching tasks` |
| availableTags from full set (order-insensitive) | 1 | `FilterPanel receives all tags from all tasks regardless of active filter` |
| Result count "N / M tasks" | 1 | `shows result count element with filtered and total counts` |
| Filter change dismisses context menu | 1 | `filter change dismisses an open context menu` |
| Filter change cancels drag — drop targets deactivated | 1 | `filter change deactivates drop targets by cancelling active drag` |
| Empty filter shows all tasks | 1 | `empty filter state shows all tasks in their columns` |

### Failure root causes

All 10 fail because KanbanBoard has no filter code:
- `[data-testid="filter-toggle"]` absent → 3 tests fail at toggle query
- FilterPanel never rendered → `capturedOnFilterChange` / `capturedAvailableTags` null → 7 tests fail

### Mock strategy

FilterPanel mocked with callback-capture pattern (KanbanBoard_1246 ArchivalModal precedent). `capturedOnFilterChange` and `capturedAvailableTags` captured on every render (even `open=false`). ArchivalModal also stubbed (existing KanbanBoard dep).
[[2026-05-02]]
## Builder Notes
- Files changed: none (temporary `serve/cockpit/web/src/KanbanBoard.tsx` experiment was fully reverted; zero net diff).
- RED verification (quality-runner, scoped): 10 failed / 0 passed, lint clean.
- GREEN verification attempt (quality-runner, scoped): 3 passed / 7 failed, lint clean.
- Blocker: tests in `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx` call `act(...)` from `vitest` import; runtime error is `TypeError: act is not a function` at lines 180, 199, 220, 236, 265, 292, 308.
- Why reject: This is a test-harness/interface issue in `TestFromAC_FilterIntegration`, not a source implementation issue. Per builder protocol, `TestFromAC_*` classes must not be edited by builder.
- Test-writer fix needed: import/use a valid React Testing Library/React `act` implementation in `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`, then re-run RED to ensure failures reflect missing KanbanBoard filter wiring behavior (not `act` runtime errors).
- Commit status: none (no deliverable source change possible while test harness is broken).

### Reflection
- Problem faced: task is a RED-phase test task routed to builder; execution uncovered harness-level failure before behavioral assertions.
- Workaround applied: implemented minimal trial wiring only to validate failure mode, then reverted completely to avoid partial GREEN work.
- Pattern discovered: when test files import `act` from `vitest`, runtime `TypeError` can mask actual AC failures and must be fixed by test-writer first.
[[2026-05-02]]
## Test-Writer Notes
- **Retry fix:** `act` was imported from `vitest` (which has no such export) → `TypeError: act is not a function`. Fixed by moving `act` to the `@testing-library/react` import (matches KanbanBoard_1242, KanbanBoard_1246 patterns).
- **File:** `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`
- **Class:** `TestFromAC_FilterIntegration`
- **Tests per category:** render 1, happy 4, edge/boundary 2, interaction 3
- **Total:** 10 tests, all FAIL (RED confirmed)
- **ESLint:** clean
- **Failure mode:** All 10 fail with `expected null not to be null` — no `filter-toggle` or `filter-panel-stub` testids exist in KanbanBoard yet. No `TypeError` from `act`.
[[2026-05-02]]
## Builder Notes
- Non-implementation pass-through: task is RED-phase (`tdd:red`) and scoped to integration tests only; no production-code change belongs in builder.
- Verification (quality-runner, scoped): `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx` -> 0 passed / 10 failed.
- Failure evidence quality: failures are behavioral (`filter-toggle`/`filter-panel-stub` missing, callback capture null), not harness/runtime errors.
- Lint status: ESLint clean for `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- Files changed: none.
- Commit status: none (no deliverable source edits required for this task type).

### Reflection
- Problem faced: builder received a RED-only test task with no implementation scope.
- Workaround applied: used scoped quality-runner evidence to validate true RED state before routing.
- Pattern discovered: RED tasks should be advanced only when failures map to intended missing behavior, not test harness issues.
- Quality gap avoided: prevented synthetic/placeholder source edits that would violate surgical-change rules.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped in `serve/cockpit/web`: `0 passed, 10 failed, 0 skipped`.
- Dominant failures are intended RED failures: `[data-testid="filter-toggle"]` is missing and `capturedOnFilterChange` / `capturedAvailableTags` stay null because the live board has no filter wiring.
- Verified source matches RED state: `serve/cockpit/web/src/KanbanBoard.tsx` groups raw tasks directly into `tasksByStatus` at line 137 and renders columns / context menu / archival modal only; workspace search found no `FilterPanel`, `filterTasks`, `filter-toggle`, or `filter-result-count` usage in that file.
- No prior `## Review Evidence` sections were present in `.owlbear/kanban/tasks/1252-p3-01-red-kanbanboard-filter-integration-tests.md`, so this is treated as a first review failure.

### Lint
- quality-runner: ESLint clean for `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- VS Code diagnostics: no errors in the task test file.

### Coverage
- N/A for gate purposes. Scoped coverage did not produce meaningful data because all task tests fail in RED phase before any GREEN path can be exercised.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| 1. Board renders filter toggle button | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:146` asserts `filter-toggle` exists | PASS |
| 2. Toggle button opens/closes FilterPanel | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:156` and `:171` assert panel stub mounts/unmounts after clicks | PASS |
| 3. Filter state changes cause filtered tasks to appear in correct columns | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:181-190` and `:200-209` drive filter changes and assert visible/hidden cards | PASS |
| 4. Derived `availableTags` computed from full (unfiltered) task set | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:225-228` only checks positive membership via `Set.has(...)`; extra or stale tags would still pass | FAIL |
| 5. Result count displays `N / M tasks` when filter is active | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:243-244` only matches `/1/` and `/3/`; malformed strings could still pass | FAIL |
| 6. Filter change dismisses open context menu | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:261-269` opens a real menu, applies a filter, and asserts dismissal | PASS |
| 7. Filter change cancels active drag — drop targets deactivated | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:288-299` proves an active drag target clears after a filter change | PASS |
| 8. Empty filter state shows all tasks | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:309-317` clears back to `EMPTY_FILTER` and asserts all three cards are visible | PASS |
| 9. All tests fail (RED) — KanbanBoard not yet wired to FilterPanel | quality-runner `0 passed / 10 failed`; live `serve/cockpit/web/src/KanbanBoard.tsx` has no filter wiring | PASS |

#### Security Review
- No issues in scoped files. `serve/cockpit/web/src/utils/filterTasks.ts:10-20` is a pure in-memory predicate; no filter-derived input reaches network writes.

#### Test Integrity
- No live-file evidence of weakened or removed `TestFromAC_*` cases.
- Confidence deduction: no builder commit diff was available, so TestFromAC immutability could not be proven from history.

#### Test Quality
- FAIL. Assertion specificity is weak on AC4 and AC5.
- AC4 proves inclusion, not the exact derived tag set.
- AC5 proves digits appear, not the required `N / M tasks` display contract.
- Retry note only, not a routing escalator on this first review: the mock captures `onFilterChange` while closed at `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:47-49`, and multiple tests drive that callback directly without opening the panel first (`:181`, `:200`, `:221`, `:237`, `:266`, `:293`, `:309`, `:312`). Because the task artifacts explicitly chose that harness strategy, I am recording it as a robustness risk rather than an architecture rejection here.

#### Data Safety
- No issues.

#### Required Follow-up
- Strengthen AC4 to prove the exact available-tag set, order-insensitive, not just positive membership.
- Strengthen AC5 to assert the exact `N / M tasks` contract (or one equivalent exact-format assertion), not digit substrings.
- On retry, prefer opening the mocked panel before driving `onFilterChange`, or otherwise prove the callback-driving approach cannot reject a behaviorally valid implementation.

### Deductions
- `-0.10` AC4 lax proof
- `-0.10` AC5 lax proof
- `-0.04` no diff-backed immutability proof
- `-0.02` callback-capture robustness risk

### Verdict
- FAIL -> todo
- Confidence: `0.84`

### Action
- Route to test-writer for proof strengthening only. No source implementation issue found in this review.
[[2026-05-02]]
## Test-Writer Notes (retry — proof strengthening)

**File:** `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`
**Class:** `TestFromAC_FilterIntegration`
**Total:** 10 tests, all FAIL (RED confirmed)
**ESLint:** clean

### Changes from first pass
- **AC4 (availableTags):** replaced three positive `.has()` membership checks with a single `expect(new Set(capturedAvailableTags!)).toEqual(new Set(['alpha', 'beta', 'gamma']))` — proves the derived set is **exactly** the union of all task tags, rejecting extra or missing entries.
- **AC5 (result count):** replaced `/1/` + `/3/` substring matches with `/^1 \/ 3 tasks$/` — enforces the exact `N / M tasks` format contract, rejecting malformed strings.

### RED verification
- quality-runner (vitest, scoped): **0 passed / 10 failed** — all failures on missing `filter-toggle` / `filter-panel-stub` testids; no runtime errors.
- ESLint: exit 0, clean.

### AC coverage (unchanged)
| AC Line | td | Test |
|---|---|---|
| Board renders filter toggle button | 1 | `renders a filter toggle button` |
| Toggle opens/closes FilterPanel | 2 | `clicking filter toggle opens FilterPanel`, `clicking filter toggle again closes FilterPanel` |
| Filter state → filtered columns | 2 | `priority filter removes non-matching tasks`, `text filter removes non-matching tasks` |
| availableTags from full set (exact, order-insensitive) | 1 | `FilterPanel receives all tags from all tasks regardless of active filter` |
| Result count `N / M tasks` (exact format) | 1 | `shows result count element with filtered and total counts when filter is active` |
| Filter change dismisses context menu | 1 | `filter change dismisses an open context menu` |
| Filter change cancels drag — drop targets deactivated | 1 | `filter change deactivates drop targets by cancelling active drag` |
| Empty filter shows all tasks | 1 | `empty filter state shows all tasks in their columns` |
[[2026-05-02]]
## Builder Notes
- Non-implementation pass-through for RED test task (`tdd:red`): no production code changes required.
- Files changed: none.
- Scoped quality-runner verification:
  - Vitest `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`: 0 passed / 10 failed.
  - Failures are behavioral RED signals (`filter-toggle` missing, FilterPanel callback captures remain null), consistent with KanbanBoard not yet wired to filtering.
  - ESLint: clean on `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx` (after one required env retry with frontend cwd hint).
- Evidence summary: RED state is valid and attributable to missing implementation wiring, not test harness/runtime errors.
- Commit status: none (no deliverable code changes in this task).

### Reflection
- Problem faced: task is a RED-phase integration-test artifact routed through builder lane.
- Workaround applied: performed scoped quality-runner verification + mandated env retry to ensure trustworthy evidence.
- Pattern discovered: RED tasks can be advanced safely when failures remain behaviorally aligned and lint is clean, without forcing synthetic implementation edits.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped in `serve/cockpit/web`: 0 passed, 10 failed, 0 skipped.
- Dominant failure remains behavioral RED (`expected null not to be null` on missing filter-toggle / filter-panel wiring), not a harness runtime error.

### Lint
- ESLint clean for `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- VS Code diagnostics: no errors in the task test file.

### Coverage
- Not a gate for this review. All task tests remain RED, so coverage would not be meaningful evidence yet.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| 1. Board renders filter toggle button | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:144-173` proves the toggle is expected, clickable, and controls panel visibility in the happy path tests. | PASS |
| 2. Toggle button opens/closes FilterPanel | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:150-173` asserts open and close transitions against the panel stub. | PASS |
| 3. Filter state changes cause filtered tasks to appear in correct columns | The active-filter tests require callback capture before the panel is ever opened (`serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:47-49`, `:179`, `:198`), while the real component renders nothing when closed (`serve/cockpit/web/src/components/FilterPanel.tsx:69-70`). They also only assert backlog cards under active filtering (`:186-190`, `:205-209`); the only todo-column assertion is after clearing the filter (`:322`). A valid conditional-mount implementation, or one that leaves stale todo cards visible, can still fail or pass incorrectly. | FAIL |
| 4. Derived availableTags computed from full (unfiltered) task set | The exact Set proof at `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:226-228` is improved and discriminating, but it is still gated by closed-panel capture at `:47-49` and `:217`. That adds a non-AC mount requirement. | FAIL |
| 5. Result count displays `N / M tasks` when filter is active | The exact-format assertion at `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:240-243` is improved and discriminating, but it still depends on pre-open callback capture at `:235`. | FAIL |
| 6. Filter change dismisses open context menu | The dismissal assertion at `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:257-269` is meaningful, but it still depends on pre-open callback capture at `:263`, so the test can reject a valid closed-panel mounting strategy before the behavioral proof runs. | FAIL |
| 7. Filter change cancels active drag and deactivates drop targets | The drag-target assertion at `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:281-298` is meaningful, but it still depends on pre-open callback capture at `:290`, so the same false-fail risk remains. | FAIL |
| 8. Empty filter state shows all tasks | The restore-all-tasks assertion at `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:308-322` is meaningful, but it still depends on pre-open callback capture at `:305`, so the same false-fail risk remains. | FAIL |
| 9. All tests fail (RED) and KanbanBoard is not yet wired to FilterPanel | quality-runner confirms 0 passed and 10 failed with behavioral RED failures; no harness/runtime error remains. | PASS |

#### Security Review
- No scoped security issues. The task deliverable is a test file; inspected production code in `FilterPanel.tsx` and `filterTasks.ts` is local UI / in-memory filtering only.

#### Test Integrity
- No weakening/removal finding was visible in the live file.
- Confidence deduction only: no builder diff or commit hash was available, so TestFromAC immutability could not be proven from history.

#### Test Quality
- FAIL. The prior review's main structural concern was not fixed: the suite still encodes a mount-timing requirement that the AC does not require.
- Positive note: AC4 and AC5 exact-value assertions are now materially stronger than the prior attempt.
- Blocking issue: AC3 through AC8 still depend on `capturedOnFilterChange` or `capturedAvailableTags` being populated before the panel is opened.

#### Data Safety
- No issues.

#### Required Follow-up
- Rework the filter-driving tests so they open the panel before consuming captured callbacks, or explicitly revise the task contract to require an always-mounted closed FilterPanel.
- Tighten AC3 so active filtering proves board-wide column correctness, including the non-matching todo task disappearing while the filter is active.
- Keep the strengthened AC4 and AC5 exact assertions; those are good and should be preserved.

### Deductions
- `-0.12` unresolved pre-open callback dependency across AC3-AC8
- `-0.06` AC3 active-filter proof does not cover the todo column under filtered state
- `-0.04` no diff-backed immutability proof

### Verdict
- FAIL to backlog
- Confidence: `0.78`

### Action
- This task already contains one prior `## Review Evidence` section at `.owlbear/kanban/tasks/1252-p3-01-red-kanbanboard-filter-integration-tests.md:191`, so this second review failure uses the loop-breaker route to backlog.
- The remaining problem is test-contract quality, not implementation correctness.
[[2026-05-02]]

## Architecture Review (re-review after R2 rejection)

### Verdict: APPROVED

### Refinements

**AC3 tightened:** Changed from "Filter state changes cause filtered tasks to appear in correct columns" to "Filter state changes cause filtered tasks to appear in correct columns — verified across all status columns in fixture; non-matching tasks in non-backlog columns must also disappear." The prior test only checked backlog cards under active filter; the todo column was never verified during filtering.

**Architecture guidance added — pre-open callback pattern:** The reviewer correctly identified that AC3–AC8 tests call `capturedOnFilterChange` immediately after `renderBoard()` without clicking the toggle. This encodes a mount-timing assumption (FilterPanel always rendered at mount with `open=false`) that the AC does not require. A valid conditional-rendering implementation (`{isOpen && <FilterPanel/>}`) would never populate the callback, causing tests to fail for the wrong reason.

**Binding constraint for test-writer:** Tests that drive `capturedOnFilterChange` or read `capturedAvailableTags` MUST first click the toggle button and `await waitFor` the `filter-panel-stub` to appear. This ensures the mock fires regardless of whether the builder uses always-mount or conditional-rendering. The existing AC1/AC2 tests already follow this pattern correctly — extend it to AC3–AC8.

### AC Assessment (delta from prior review)

| AC Line | Change | Rationale |
|---|---|---|
| AC3 — filter state → correct columns | Tightened: added cross-column requirement | R2 reviewer found only backlog column was tested under active filter |
| AC4–AC8 | No AC text change | Implementation guidance added: open panel before driving callbacks |
| All others | Unchanged | Prior review's AC4/AC5 strengthening preserved |

### Architecture Notes

- No architectural change from original approval. FilterPanel props, filterTasks signature, and mock strategy (callback capture) remain sound.
- The pre-open callback issue is a test sequencing concern, not an architecture defect. The fix is mechanical: add toggle-click + waitFor before each test that drives callbacks.
- Prior challenger results (confidence 0.62 → overrides accepted, two points addressed) still apply. No re-challenge needed — refinements only tighten test precision, not change design.

### Dependency Check
- #1251 (FilterPanel GREEN): archived/done — dependency satisfied.
- FilterPanel.tsx and filterTasks.ts both exist and are stable.
- #1253 (GREEN successor) exists with correct dependency on this task.
[[2026-05-02]]
Re-approved after R2 rejection. AC3 tightened to require cross-column proof. Binding architecture guidance added: tests must click toggle and await panel-stub before driving capturedOnFilterChange/capturedAvailableTags. Prior challenger results still valid — refinements are precision improvements, not design changes.
[[2026-05-02]]
## Test-Writer Notes (retry R3 — pre-open callback + cross-column fix)

**File:** `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`
**Class:** `TestFromAC_FilterIntegration`
**Total:** 10 tests, all FAIL (RED confirmed)
**ESLint:** clean

### Changes from R2

Two issues cited by reviewer, both resolved:

**Issue 1 — Pre-open callback pattern (AC3–AC8):**
All tests that drive `capturedOnFilterChange` or read `capturedAvailableTags` now first click the toggle button and `await waitFor` the `filter-panel-stub` to appear. This ensures callback capture works with any mount strategy (always-mounted OR conditional `{isOpen && <FilterPanel />}`). The old pattern assumed FilterPanel is always rendered even with `open=false` — now removed from all 6 affected tests.

**Issue 2 — AC3 cross-column proof:**
Both AC3 sub-tests (priority filter, text filter) now assert that TASK_TODO (status=`todo`) also disappears from the todo column when the filter is active. Prior tests only verified backlog column changes. Added: `expect(container.querySelector('[data-column="todo"] [data-testid="task-card"][data-id="3"]')).toBeNull()` to both filter scenarios.

### Tests per category (unchanged)

| Category | Count | Tests |
|---|---|---|
| Render | 1 | filter toggle button present |
| Happy path | 4 | toggle opens panel, priority filter, text filter, empty filter |
| Edge/boundary | 2 | toggle closes panel, availableTags from full set |
| Interaction rules | 3 | context menu dismissed, drag deactivated, result count |

### RED verification
- quality-runner (vitest, scoped): **0 passed / 10 failed**
- All failures: `expected null not to be null` on missing `filter-toggle` testid
- No runtime errors (`act is not a function` was fixed in prior cycle)
- ESLint: exit 0, clean

### AC coverage

| AC Line | td | Test |
|---|---|---|
| Board renders filter toggle button | 1 | `renders a filter toggle button` |
| Toggle opens/closes FilterPanel | 2 | `clicking filter toggle opens FilterPanel`, `clicking filter toggle again closes FilterPanel` |
| Filter state → filtered columns (all columns) | 2 | `priority filter removes non-matching tasks from columns`, `text filter removes non-matching tasks from columns` |
| availableTags from full set (exact, order-insensitive) | 1 | `FilterPanel receives all tags from all tasks regardless of active filter` |
| Result count `N / M tasks` (exact format) | 1 | `shows result count element with filtered and total counts when filter is active` |
| Filter change dismisses context menu | 1 | `filter change dismisses an open context menu` |
| Filter change cancels drag — drop targets deactivated | 1 | `filter change deactivates drop targets by cancelling active drag` |
| Empty filter shows all tasks | 1 | `empty filter state shows all tasks in their columns` |

**Commit:** cc7e608c
[[2026-05-02]]
## Builder Notes
- Non-implementation pass-through for RED test task (`tdd:red`): no production code changes required.
- Files changed: none.
- Scoped quality verification (quality-runner):
  - Vitest `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`: 0 passed / 10 failed.
  - Failure signature is consistent and behavioral: `[data-testid="filter-toggle"]` is missing across all cases.
  - ESLint: clean for `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- Evidence summary: failures reflect intended RED state (missing KanbanBoard filter wiring), not harness/runtime errors.
- Commit status: none (no deliverable source edits in this task type).

### Reflection
- Problem faced: builder lane received a RED-only integration test task with no implementation scope.
- Workaround applied: used a fresh scoped quality-runner verification to confirm true RED behavior and eliminate harness-noise risk.
- Pattern discovered: safe RED pass-through requires consistent behavioral failures plus clean lint before review routing.
- Quality gap avoided: prevented synthetic code edits that would violate surgical-change and ownership boundaries.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped in `serve/cockpit/web`: `0 passed, 10 failed, 0 skipped`.
- Failure signature is a clean RED signal, not a harness problem: all 10 fail on missing `[data-testid="filter-toggle"]` / filter wiring.
- quality-runner reported the frontend environment as healthy; no jsdom/setup/runtime error masked the assertions.

### Lint
- quality-runner: ESLint clean for `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- VS Code diagnostics: no errors in `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`, `serve/cockpit/web/src/KanbanBoard.tsx`, or `serve/cockpit/web/src/components/FilterPanel.tsx`.

### Coverage
- Not a gate for this RED review. quality-runner did not produce meaningful coverage because all task tests are intentionally failing before GREEN implementation exists.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| 1. Board renders filter toggle button | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:144` asserts `[data-testid="filter-toggle"]` exists. | PASS |
| 2. Toggle button opens/closes FilterPanel | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:150-171` clicks the toggle and proves `filter-panel-stub` appears then disappears. | PASS |
| 3. Filter state changes cause filtered tasks to appear in correct columns — verified across all status columns in fixture; non-matching tasks in non-backlog columns must also disappear. | Under active filtering the suite asserts only: task 1 present in backlog (`:192`, `:222`), task 2 absent from backlog (`:196`, `:226`), and task 3 absent from todo (`:200`, `:230`). There are no active-filter assertions for task 1 absent from todo or task 3 absent from backlog. A future implementation that duplicates or misbuckets filtered tasks can still satisfy the current proof, so the `correct columns` contract remains under-proved. | FAIL |
| 4. Derived availableTags computed from full (unfiltered) task set — set-membership, order-insensitive | The R3 retry now opens the panel first and uses exact Set equality at `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:236-253`, with callback capture updated at `:47-48`. | PASS |
| 5. Result count displays `N / M tasks` when filter is active | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:259-275` requires the result-count element and exact `^1 / 3 tasks$` formatting. | PASS |
| 6. Filter change dismisses open context menu | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:280-306` opens a real context menu, applies a filter change, and requires the menu to disappear. | PASS |
| 7. Filter change cancels active drag — drop targets deactivated | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:311-342` proves the todo column is an active drag target before the filter change and inactive after it. | PASS |
| 8. Empty filter state shows all tasks | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:347-372` applies a filter, clears back to `EMPTY_FILTER`, and requires all three fixture tasks to be visible in their expected columns. | PASS |
| 9. All tests fail (RED) — KanbanBoard not yet wired to FilterPanel | quality-runner confirms `0 passed / 10 failed`. Live `serve/cockpit/web/src/KanbanBoard.tsx` still groups raw tasks by status at `:137`, renders the board shell at `:183`, archival modal at `:209`, and context menu at `:223`; grep of `FilterPanel|filterTasks|filter-toggle|filter-result-count` in that file returned no matches. | PASS |

#### Security Review
- No scoped security issues. The deliverable under review is a frontend test file with local mocks/fixtures only.

#### Test Integrity
- No live-file evidence of weakened or removed `TestFromAC_*` coverage: `TestFromAC_FilterIntegration` remains present in `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- Commit evidence exists for the latest retry: `.git/logs/HEAD:1629` records `cc7e608c370d5df2ddc07952cf18a89a3e558bb3` with message `test: fix pre-open callback pattern and cross-column AC3 proof for KanbanBoard filter integration (#1252, test-writer)`.
- Confidence remains slightly reduced because no diff-backed immutability proof was available from review mode.

#### Test Quality
- FAIL. The R3 retry fixed the prior pre-open callback defect and materially strengthened AC4/AC5, but AC3 is still under-proved for a td:2 task.
- The remaining gap is exact placement proof under active filtering: the suite proves selective presence/disappearance, but not that filtered tasks appear only in the correct columns.

#### Data Safety
- No issues.

#### Required Follow-up
- Strengthen AC3 so active filtering proves exact placement, not only selective visibility. At minimum, add wrong-column negatives for retained tasks, or extend the fixture so a matching non-backlog task must remain in its own column and nowhere else.
- Preserve the current open-first callback sequencing and the strengthened AC4/AC5 exact assertions.

### Deductions
- `-0.10` AC3 exact-placement proof gap
- `-0.03` no diff-backed immutability proof

### Verdict
- FAIL -> backlog
- Confidence: `0.87`

### Action
- The task file already contains prior `## Review Evidence` sections at `.owlbear/kanban/tasks/1252-p3-01-red-kanbanboard-filter-integration-tests.md:191` and `.owlbear/kanban/tasks/1252-p3-01-red-kanbanboard-filter-integration-tests.md:295`, so this third review cycle uses the loop-breaker route to `backlog`.
- Failure type is test-contract quality, not implementation correctness.

### Reflection
- Problem faced: the latest retry fixed the previous harness-level and sequencing defects, so the remaining decision required re-evaluating the refined AC rather than inheriting older fail notes.
- Workaround applied: combined fresh quality-runner evidence, live-file inspection, commit-log confirmation, and a challenger pass before final routing.
- Pattern discovered: `correct columns` ACs need exact placement proof, not only presence in expected columns plus disappearance of one non-match.
- Quality gap: looped td:2 tasks can still miss a narrow false-green path even after the obvious harness defects are corrected.
[[2026-05-03]]

## Architecture Review (re-review after R3 rejection)

### Verdict: APPROVED

### Challenger Results

Challenger confidence: 0.41, recommendation: block. Three challenges accepted, two blind spots addressed:

**Accepted:**
1. **Source-of-truth drift** — canonical AC section never updated despite prior tightenings. Fixed below.
2. **Reusing failed remedy** — prior AC3 refinement said "non-matching tasks in non-backlog columns must also disappear" but the test already did that. The real gap is (a) wrong-column negatives for retained tasks, and (b) no retained non-backlog match in any scenario. This refinement is structurally different — it requires multi-column matching proof.
3. **Fixture limitation** — current fixture makes task 1 (backlog) the only match in both filter scenarios. A td:2 proof must exercise retained tasks across ≥2 distinct columns. AC3 now explicitly requires this.

**Blind spot addressed:**
- Both negative directions required: retained tasks NOT in wrong columns AND non-matching tasks NOT in wrong columns (not just absent from their home columns).

### Refinements Applied to Canonical AC

**AC3 BEFORE:**
> Filter state changes cause filtered tasks to appear in correct columns (td:2)

**AC3 AFTER:**
> Filter state changes cause filtered tasks to appear only in their correct columns: (a) matching tasks present in home column and absent from all other columns; (b) non-matching tasks absent from all columns — at least one sub-test must have matching tasks in ≥2 distinct status columns (td:2)

This is structurally different from the prior refinement because it:
- Requires wrong-column negatives for BOTH retained and non-matching tasks
- Requires a multi-column matching scenario (forces fixture adjustment — cannot be satisfied with only backlog-resident matches)
- Uses "only in their correct columns" framing to close the duplicate/misbucket false-green path the reviewer documented

### Binding Guidance for Test-Writer

1. At least one AC3 sub-test must use a filter where matching tasks reside in ≥2 distinct status columns. This may require adjusting the fixture (e.g., a todo-status task whose title/priority/tags also pass the filter) or adding a third sub-test with a broader filter.
2. Every AC3 sub-test must assert: (a) each matching task present in its home column, (b) each matching task absent from every OTHER column, (c) each non-matching task absent from ALL columns.
3. Preserve the open-first callback sequencing from R3 (click toggle → await panel-stub → drive filter).
4. Preserve the strengthened AC4 exact-Set and AC5 exact-format assertions.

### AC Assessment (delta from prior reviews)

| AC Line | Change | Rationale |
|---|---|---|
| AC3 — filter state → correct columns | Rewritten: added wrong-column negatives (both directions) + multi-column matching requirement | R3 reviewer found exact-placement gap; challenger confirmed fixture limitation for td:2 |
| All others | Unchanged | AC4/AC5 strengthening from R2 and pre-open fix from R3 are preserved |

### Architecture Notes

- No architectural change from original approval. FilterPanel props, filterTasks signature, and mock strategy remain sound.
- The fix is test-level: fixture extension and additional assertions. No production code or interface change.
- Prior challenger results from original review (overrides on selector overreach and mock-as-integration) still apply.

### Dependency Check
- #1251 (FilterPanel GREEN): done — dependency satisfied.
- #1253 (GREEN successor) exists with correct dependency on this task.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Evaluation (unchanged criteria)

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test file, one concern |
| Interface clarity | PASS | AC3 now fully specified with assertion contract |
| Dependency correctness | PASS | #1251 done |
| Module layering | PASS | Test-only task |
| TDD compliance | PASS | RED phase; #1253 GREEN exists |
| KISS/YAGNI | PASS | Proportionate proof for td:2 |
| Premise challenge | PASS | KanbanBoard has zero filter code |
| Pattern consistency | PASS | Callback-capture follows ArchivalModal pattern |
| Security surface | PASS | Test file only |
| Single domain | PASS | Frontend tests |

[[2026-05-03]]
Re-approved after R3 rejection. AC3 rewritten with structurally different refinement: (a) wrong-column negatives required for both retained AND non-matching tasks, (b) at least one sub-test must have matching tasks in ≥2 distinct status columns. Challenger confidence 0.41 → all three challenges accepted and addressed in the refinement. Prior AC4/AC5/pre-open fixes preserved.
[[2026-05-03]]
## Test-Writer Notes (retry R4 — AC3 exact-placement fix)

**File:** `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`
**Class:** `TestFromAC_FilterIntegration`
**Total:** 10 tests, all FAIL (RED confirmed)
**ESLint:** clean

### Changes from R3

**AC3 exact-placement — two issues addressed per R3 reviewer + R4 arch guidance:**

**Issue 1 — Multi-column matching scenario required (td:2 contract):**
Added `TASK_TODO_MATCH` fixture (id=4, status='todo', priority='needed', tags=['delta']). The priority filter test now uses a 4-task fixture (`[TASK_NEEDED, TASK_SOMEDAY, TASK_TODO, TASK_TODO_MATCH]`) with `priority='needed'` filter — produces matching tasks in both `backlog` (TASK_NEEDED) and `todo` (TASK_TODO_MATCH). Satisfies "at least one AC3 sub-test must have matching tasks in ≥2 distinct status columns".

**Issue 2 — Wrong-column negatives for all tasks (both directions):**
Both AC3 sub-tests now assert the full exact-placement contract per R4 binding guidance:
- (a) Each matching task present in home column
- (b) Each matching task absent from every OTHER column
- (c) Each non-matching task absent from ALL columns

Priority filter test: 8 placement assertions (2 per task × 4 tasks). Test renamed to `'priority filter proves exact placement of matching and non-matching tasks across columns'`.
Text filter test: 6 placement assertions (home + wrong-column for retained task; both columns for 2 non-matching tasks).

### Preserved from R3
- Open-first callback sequencing (click toggle → await panel-stub → drive filter)
- AC4 exact Set equality assertion
- AC5 exact `^N / M tasks$` format assertion
- AC6–AC8 unchanged

### RED verification
- vitest scoped: **0 passed / 10 failed** — all failures `expected null not to be null` on missing `filter-toggle` (behavioral RED, no harness errors)
- ESLint: exit 0, clean

### Commit: 765454f6

### AC coverage (delta — AC3 strengthened)
| AC Line | td | Test |
|---|---|---|
| AC3 — filter state → correct columns (exact placement, ≥2 columns) | 2 | `priority filter proves exact placement of matching and non-matching tasks across columns`, `text filter removes non-matching tasks from columns` |
| All others | unchanged | same as R3 |
[[2026-05-03]]
## Builder Notes
- Files changed: none.
- Scope: RED-phase pass-through verification for KanbanBoard filter integration tests; no production code changes required.
- Test results (quality-runner, scoped): 0 passed / 10 failed / 0 skipped in `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- Failure signature: all failures are behavioral RED signals (`expected null not to be null`) rooted in missing `[data-testid="filter-toggle"]` wiring in `KanbanBoard`.
- Lint status: ESLint clean for `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- Coverage: not collected (scoped RED run; tests intentionally fail before GREEN implementation).
- Evidence summary: frontend test runtime is healthy; failures are not harness/config errors and are attributable to intentionally missing filter integration in current board implementation.
- Fixes applied: none (task type is RED test verification).
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped: `0 passed, 10 failed, 0 skipped` in `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- Failure signature is clean RED, not a harness problem: all failures are missing `filter-toggle` / filter wiring assertions; no jsdom or `act(...)` runtime error remains.

### Lint
- quality-runner: ESLint clean for `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- VS Code diagnostics: no errors in `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`, `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/FilterPanel.tsx`, or `serve/cockpit/web/src/utils/filterTasks.ts`.

### Coverage
- Not a gate for this RED review. quality-runner coverage hung during V8 initialization on the intentionally failing jsdom suite, so no meaningful coverage metric was produced before GREEN implementation exists.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| 1. Board renders filter toggle button | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:158-160` requires the toggle test id, and `:164-185` then clicks the same control and proves it drives panel state. That is sufficient for this Phase 3 wiring task; semantic button-role checks belong to the stated Phase 4 accessibility scope. | PASS |
| 2. Toggle button opens/closes FilterPanel | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:164-185` opens then closes `filter-panel-stub`. | PASS |
| 3. Filter state changes cause filtered tasks to appear only in their correct columns: matching tasks present in home column and absent from all other columns; non-matching tasks absent from all columns; at least one sub-test with matching tasks in >=2 distinct status columns | Latest binding refinement is in `.owlbear/kanban/tasks/1252-p3-01-red-kanbanboard-filter-integration-tests.md:537,547-548`. Current AC3 tests at `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:192-275` satisfy that refinement. The priority case uses the added multi-column fixture described at `.owlbear/kanban/tasks/1252-p3-01-red-kanbanboard-filter-integration-tests.md:603`, and both AC3 tests assert home-column positives plus wrong-column / all-column negatives. | PASS |
| 4. Derived `availableTags` computed from full (unfiltered) task set — set-membership, order-insensitive | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:278-295` opens the panel first and then asserts exact Set equality at `:294`. | PASS |
| 5. Result count displays `N / M tasks` when filter is active | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:301-317` requires `filter-result-count` and exact `^1 / 3 tasks$` formatting. | PASS |
| 6. Filter change dismisses open context menu | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:322-348` opens a real context menu, applies a filter change, and requires dismissal. | PASS |
| 7. Filter change cancels active drag — drop targets deactivated | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:353-384` proves an active drop target before the filter change and an inactive target after it. | PASS |
| 8. Empty filter state shows all tasks | `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx:389-409` applies a filter, clears back to `EMPTY_FILTER`, and restores all cards. | PASS |
| 9. All tests fail (RED) — KanbanBoard not yet wired to FilterPanel | quality-runner confirms `0 passed / 10 failed`. Live `serve/cockpit/web/src/KanbanBoard.tsx:137-183` still groups raw tasks by status and renders the board shell without filter wiring; `serve/cockpit/web/src/components/FilterPanel.tsx:69` still returns `null` when `open=false`. | PASS |

#### Security Review
- No scoped security issues. The deliverable is a frontend test file with local mocks / fixtures only.

#### Test Integrity
- `git diff --name-only 765454f6~1 765454f6` shows only `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- `git log --oneline -- serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx` shows only the three task-specific test-writer commits (`3d0d7f98`, `cc7e608c`, `765454f6`); no later commit touches this file.
- No live-file evidence of weakened or removed `TestFromAC_*` assertions.

#### Test Quality
- PASS. The prior AC3 exact-placement false-green path is closed by the R4 retry.
- The earlier reviewer FAIL at `.owlbear/kanban/tasks/1252-p3-01-red-kanbanboard-filter-integration-tests.md:451-503` is superseded by the later architecture re-review at `:516-553` and the R4 retry notes at `:592-629`.
- Informational only: this integration suite uses representative text / priority filter-state changes rather than exhausting every `FilterState` dimension. That is acceptable under the ratified 10-test scope for this RED wiring task. Separate direct coverage for tag / blocked behavior already exists in `serve/cockpit/web/src/__tests__/filterTasks_1248.test.ts` and `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`.

#### Data Safety
- No issues.

### Deductions
- `-0.04` quality-runner coverage unavailable on the RED jsdom path; not a gate, but it limits supplemental evidence.
- `-0.03` tag / blocked board-level wiring is not directly exercised in this single integration file; treated as residual risk, not an AC failure under the current task contract.

### Verdict
- PASS -> docs
- Confidence: `0.93`

### Action
- Advance to docs. No remaining blocking implementation or test-proof defect is traceable to the current ratified AC.
[[2026-05-03]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 0a | Review Evidence present | YES | PASS | Final `## Review Evidence` section present (PASS → docs, confidence 0.93) |
| 1 | Prose docs affected | NO | N/A | Task is test-only (RED phase); no behavior, API, CLI, config, or package-structure change |
| 2 | Python module docstrings | NO | N/A | Frontend test file only; no `.py` files changed |
| 3 | External attribution | NO | N/A | All sources in research doc are internal workspace files |
| 4 | Research doc | YES | PASS | `.owlbear/research/kanbanboard-filter-integration-red-1252.md` exists and is linked from task body; follow-up note correctly cites #1253 |
| 5 | Diagram maintenance | YES | DONE | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — matches `KanbanBoard_1252.test.tsx`; footer updated to `2026-05-03 (bb63990c)` |
| 6 | Explicit diagram creation | NO | N/A | No diagram creation request in task body |
| 7 | Deletion detection | NO | N/A | No files deleted; no orphaned IN-scope docs detected |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer `Last verified: 2026-05-03 (bb63990c)`

### Child Tasks Created
None.

### Scratch Files Cleaned
No `.owlbear/scratch/1252-*` files found.

### Commit
`7dd1efcd` — docs: update cockpit diagram footer for KanbanBoard filter integration tests (#1252, doc-writer)
[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. Board renders filter toggle button | `KanbanBoard_1252.test.tsx:158-160` asserts `filter-toggle` testid | PASS |
| 2. Toggle opens/closes FilterPanel | `:164-185` click toggle, assert panel-stub mount/unmount | PASS |
| 3. Filter state → correct columns (exact placement, ≥2 columns) | `:192-275` 4-task fixture, matching tasks in backlog+todo, 8 placement assertions per sub-test | PASS |
| 4. availableTags from full set (exact, order-insensitive) | `:278-295` exact Set equality after applying filter | PASS |
| 5. Result count `N / M tasks` | `:301-317` exact `/^1 \/ 3 tasks$/` format | PASS |
| 6. Filter change dismisses context menu | `:322-348` opens real menu, applies filter, asserts dismissal | PASS |
| 7. Filter change cancels drag — drop targets deactivated | `:353-384` proves drag target active before, inactive after | PASS |
| 8. Empty filter shows all tasks | `:389-409` filter→clear→all 3 cards visible | PASS |
| 9. All tests fail (RED) | quality-runner 0/10 passed; grep confirms zero filter code in KanbanBoard.tsx | PASS |

### Test Results
- vitest (full): 947 passed, 11 failed (10 expected RED + 1 pre-existing ActivityTab_1156 failure — not from this task)
- ESLint: clean

### Architect Quality: 4/5
Original AC3 too vague for td:2 — required 3 refinement cycles. Architect adapted well each time; final AC set is specific and complete. Challenger used effectively.

### Deduction Breakdown
- Full suite not fully clean: 1 pre-existing failure outside task scope (ActivityTab_1156, last touched by #1156). No regression detected. → -0.02

### Confidence: .98
### Action: archive