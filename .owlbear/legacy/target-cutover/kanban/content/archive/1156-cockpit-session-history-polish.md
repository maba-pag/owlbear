---
id: 1156
title: Cockpit session history polish
status: archived
priority: medium
created: 2026-04-28T17:28:32.776197+00:00
updated: 2026-04-28T20:35:42.127612+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective

Polish the cockpit session history UX: add missing filter states, visual distinction for problematic sessions, and click-through navigation from session entries to task detail views. Seed from ideation #1042.

## Current State

- **ActivityTab** (`serve/cockpit/web/src/components/ActivityTab.tsx`): shows sessions with client-side filters (active/all/failed/released). Session rows are clickable via `onSelectTask(task_id, 'history')`. Currently fetches `/api/sessions` with no filter param (defaults to `active` on backend — only `running` + `stuck` sessions). Pre-existing bug: `applyFilter` checks `state === 'in-progress'` but the backend produces `state: 'running'`.
- **HistorySubtab** (`serve/cockpit/web/src/components/HistorySubtab.tsx`): per-task session history — displays agent, duration, outcome. No click-through, no visual state indicators. Rendered by DetailTab which does not expose an `onSelectTask` prop.
- **DetailTab** (`serve/cockpit/web/src/components/DetailTab.tsx`): Mounts HistorySubtab, fetches sessions with `filter=all`. Has no `onSelectTask` callback prop currently.
- **Backend** `GET /api/sessions?filter=`: supports `active` (running + stuck), `blocked-or-rejected` (blocked + rejected), `released`, `all`. Session states produced by the engine: `running`, `stuck`, `completed`, `rejected`, `released`, `blocked`, `expired`.
- **SessionRecord model**: task_id, task_status_at_start, agent, state, started_at, ended_at, outcome, duration, duration_s.

## Acceptance Criteria

### AC1 — Fetch strategy fix and expanded filter buttons in ActivityTab
- ActivityTab must fetch `/api/sessions?filter=all` (not the default `active`) so all session states are available for client-side filtering.
- Fix the existing `active` filter predicate: change `s.state === 'in-progress'` to `s.state === 'running'` to match backend state taxonomy.
- Replace the existing "Failed" filter button with a "Blocked" filter button (`data-testid="filter-blocked"`) that shows sessions where `state === 'blocked' || state === 'rejected'`.
- Add a "Stuck" filter button (`data-testid="filter-stuck"`) that shows sessions where `state === 'stuck'`.
- Existing "Active", "All", and "Released" filter buttons remain unchanged (except the `active` predicate fix above).

### AC2 — Visual state indicators for problematic sessions
- Session rows in both ActivityTab and HistorySubtab must display a visual indicator (CSS class or data attribute on the row element) distinguishing session states: `running`, `stuck`, `blocked`, `rejected`, `released`, `completed`, `expired`.
- At minimum: `stuck` and `blocked` sessions must be visually distinguishable from normal `completed`/`released` sessions without reading the text label.
- Use Porsche Design System notification tokens from `tokens.css` where applicable (e.g. `--pds-theme-light-notification-error` for blocked, `--pds-theme-light-notification-warning` for stuck).
- Each row must include a `data-state` attribute matching the session state value, enabling test assertions on visual state.

### AC3 — Click-through navigation from HistorySubtab
- HistorySubtab must accept an `onSelectTask` callback prop (same signature as ActivityTab: `(taskId: number, subtab?: string) => void`).
- HistorySubtab session rows must be clickable and invoke `onSelectTask(session.task_id, 'history')`.
- DetailTab must accept an `onSelectTask` prop and thread it to HistorySubtab.
- Cursor style must indicate clickability (`cursor: pointer`).

### AC4 — Filter type alignment
- `FilterType` union must be: `'all' | 'active' | 'blocked' | 'stuck' | 'released'` (removes `'failed'`, adds `'blocked'` and `'stuck'`).
- `applyFilter()` must handle all `FilterType` cases — no unhandled switch branches.
- The `Session` interface must be defined once and shared between ActivityTab and HistorySubtab (currently duplicated).

### AC5 — Test coverage
- Unit tests for the corrected `active` filter (matches `running` + `stuck`, not `in-progress`).
- Unit tests for the new `blocked` filter (matches `blocked` + `rejected` states).
- Unit tests for the new `stuck` filter (matches `stuck` state only).
- Test that HistorySubtab rows fire the `onSelectTask` callback on click.
- Test that visual state indicators (via `data-state` attribute) render for each session state variant.
- Test that DetailTab threads `onSelectTask` to HistorySubtab.

## Scope

**In scope:** ActivityTab fetch strategy fix, filter expansion (replace failed with blocked, add stuck), HistorySubtab click-through + visual indicators, DetailTab prop threading, filter type alignment, shared Session interface, test coverage for new behavior.

**Out of scope:** Backend filter changes (existing filters are sufficient), session pagination, session sorting, real-time session updates, expired session filtering (expired sessions appear in "All" only — no dedicated filter button).
[[2026-04-28]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes within session-history UX domain (2 components + 1 prop-threading parent) |
| Interface clarity | PASS (after refine) | Original AC had fetch-strategy gap, state taxonomy mismatch, undocumented prop threading. Refined to specify exact fetch URL, state names, FilterType union, DetailTab threading |
| Dependency correctness | PASS | No task dependencies needed; backend filters already exist |
| Module layering | PASS | Frontend-only; no upward imports |
| TDD compliance | PASS | AC5 specifies test coverage; test-writer will process |
| KISS/YAGNI | PASS | No new abstractions; extends existing filter + callback patterns |
| Premise challenge | PASS | Uses existing backend capabilities; no redundancy with IDE features |
| Pattern consistency | PASS | Filter buttons follow existing data-testid pattern; PDS tokens from existing tokens.css |
| Security surface | PASS | No new system boundaries; data from existing endpoint |
| Single domain | PASS | cockpit-frontend only |

### Refinements Applied

1. **Fetch strategy**: Specified ActivityTab must fetch `filter=all` (was fetching default `active`, making blocked/completed filters impossible)
2. **State taxonomy fix**: Documented `in-progress` → `running` mismatch; AC1 now explicitly requires the fix
3. **"Failed" → "Blocked" disposition**: Specified replacement (not addition) to avoid semantic overlap on `rejected`
4. **DetailTab prop threading**: AC3 now requires DetailTab to accept and thread `onSelectTask`
5. **`data-state` attribute**: AC2 now specifies testable DOM contract for visual indicators
6. **`expired` state**: Documented in Current State; explicitly scoped out of filter buttons (appears in "All" only)
7. **Shared Session interface**: AC4 now requires deduplication (currently defined in both ActivityTab and HistorySubtab)

### Challenge Results
- Challenger: reconsider (confidence 0.28)
- Key valid challenges: fetch-strategy gap (critical), state taxonomy mismatch (critical), DetailTab prop threading (moderate)
- Architect response: accepted — all critical concerns incorporated into refined AC

### Verdict: APPROVE (after REFINE)
### Action Taken: Rewrote AC with 7 refinements addressing challenger findings. Advanced to todo.
[[2026-04-28]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx
- Classes: TestFromAC_FetchStrategyFix, TestFromAC_ActiveFilterPredicate, TestFromAC_NewFilterButtons, TestFromAC_VisualStateIndicators, TestFromAC_HistorySubtabClickThrough, TestFromAC_DetailTabPropThreading, TestFromAC_FilterTypeAlignment
- Tests per category: happy 5, edge 4, error 4, boundary 28 (data-state per-state variants)
- Total: 41 tests, all FAIL
- ruff: N/A (TypeScript/Vitest); ESLint: 0 errors
- Commit: 9d29a4fd

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 fetch ?filter=all | FetchStrategyFix (2 tests) |
| AC1 active predicate fix (running not in-progress) | ActiveFilterPredicate (4 tests) |
| AC1 filter-blocked button | NewFilterButtons — presence + behavior (7 tests) |
| AC1 filter-stuck button | NewFilterButtons — presence + behavior (2 tests) |
| AC1 filter-failed removed | NewFilterButtons — 1 test |
| AC2 data-state on ActivityTab rows | VisualStateIndicators (10 tests: 1 direct + 7 each-state + 2 contrast) |
| AC2 data-state on HistorySubtab rows | VisualStateIndicators (8 tests: 1 direct + 7 each-state) |
| AC3 HistorySubtab click-through | HistorySubtabClickThrough (4 tests: cursor, task_id, subtab, second-row) |
| AC3 DetailTab threads onSelectTask | DetailTabPropThreading (1 test: click-through e2e) |
| AC4 applyFilter handles blocked/stuck | FilterTypeAlignment (4 tests: released unchanged, blocked/stuck no-throw, released data-state) |

### Notes
- AC1 unchanged buttons (filter-active, filter-all, filter-released) not tested in task-scoped file — covered by existing ActivityTab.test.tsx
- AC4 shared Session interface not directly testable at runtime (TypeScript-only concern); structural coverage via HistorySubtab render tests
[[2026-04-28]]
## Builder Notes
- Implementation: updated [serve/cockpit/web/src/components/ActivityTab.tsx](serve/cockpit/web/src/components/ActivityTab.tsx), [serve/cockpit/web/src/components/HistorySubtab.tsx](serve/cockpit/web/src/components/HistorySubtab.tsx), and [serve/cockpit/web/src/components/DetailTab.tsx](serve/cockpit/web/src/components/DetailTab.tsx).
- AC1: ActivityTab now fetches `/api/sessions?filter=all`; active filter matches `running || stuck`; replaced `Failed` with `Blocked` (`data-testid="filter-blocked"`), added `Stuck` (`data-testid="filter-stuck"`), retained active/all/released.
- AC2: Added per-row `data-state` attribute and visual state indicator styles in ActivityTab and HistorySubtab using PDS token variables (`--pds-theme-light-notification-error*`, `--pds-theme-light-notification-warning*`) so problematic states are visually distinct.
- AC3: HistorySubtab now accepts `onSelectTask` and row clicks call `onSelectTask(task_id, 'history')`; DetailTab now accepts `onSelectTask` and threads it into HistorySubtab.
- AC4: Filter union in ActivityTab is now `'all' | 'active' | 'blocked' | 'stuck' | 'released'`; removed failed branch; shared `Session` interface by importing the type from HistorySubtab into ActivityTab.
- Tests (task-scoped): 41 passed, 0 failed (`serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx`).
- Lint (scoped): clean on touched frontend files.
- Regression baseline: durable suites run for context (`ActivityTab.test.tsx`, `DetailTab.test.tsx`) reported 7 failures in legacy ActivityTab assertions tied to old contract (`in-progress`/`failed` filter). This aligns with intentional AC behavior changes in #1156.
- Type check/editor diagnostics: no errors on changed files.
- Commit: `0d19af30` (`feat: cockpit session history polish (#1156, builder)`).
[[2026-04-28]]
## Review Evidence

### Test Results
- Task-scoped: `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx` -> 41 passed, 0 failed.
- Related durable suites: `serve/cockpit/web/src/__tests__/ActivityTab.test.tsx` -> 8 passed, 7 failed; `serve/cockpit/web/src/__tests__/DetailTab.test.tsx` -> 34 passed, 0 failed.
- Combined proof run (`ActivityTab_1156.test.tsx` + `DetailTab.test.tsx`) -> 75 passed, 0 failed.
- Failing durable assertions are still pinned to the pre-1156 contract:
  - expects `filter-failed` at `ActivityTab.test.tsx:126-128`
  - expects failed/rejected filter behavior at `ActivityTab.test.tsx:151-164`
  - fixture still uses `state: 'in-progress'` at `ActivityTab.test.tsx:17` and asserts it at `ActivityTab.test.tsx:226-233`
  - row field / click assertions still assume the old first-row semantics at `ActivityTab.test.tsx:200-269`

### Lint
- ESLint clean on touched files and task-scoped test file.

### Coverage
- Task-scoped coverage:
  - `ActivityTab.tsx`: 92.75% stmts / 91.3% branch / 97.61% lines
  - `HistorySubtab.tsx`: 89.47% stmts / 87.5% branch / 100% lines
  - `DetailTab.tsx`: 83.94% stmts / 82.4% branch / 85.71% lines
- Broader coverage attempt (`ActivityTab_1156.test.tsx` + `DetailTab.test.tsx`) timed out during Vitest instrumentation, so I do not have independent evidence rehabilitating the sub-90 modules.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Verdict |
|---------|----------|---------|
| AC1 | `ActivityTab.tsx:38,40,55,77-80`; tests `ActivityTab_1156.test.tsx:178,220,234,337,370` | COVERED |
| AC2 | `ActivityTab.tsx:14-23,92`; `HistorySubtab.tsx:21-30,47`; tests `ActivityTab_1156.test.tsx:425,485,493` | COVERED |
| AC3 | `ActivityTab.tsx:93`; `HistorySubtab.tsx:48`; `DetailTab.tsx:144`; tests `ActivityTab_1156.test.tsx:514,521,530,539,557` | COVERED |
| AC4 | `HistorySubtab.tsx:3-15`; `ActivityTab.tsx:2,8,33-43`; tests `ActivityTab_1156.test.tsx:600,615,623` | COVERED |
| AC5 | task-scoped suite exists and passes all requested behaviors | COVERED |

#### Security Review
- No issues in scoped files. Same-origin fetches only; no dynamic HTML sink, command execution, path construction, or secret material.

#### Test Integrity
- No weakened `TestFromAC_*` assertions detected in the current snapshot. Builder notes only claim source-file changes; current task test file still contains the expected AC-mapped suites.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | exact fetch/filter/data-state/callback assertions in `ActivityTab_1156.test.tsx` |
| Negative/error-path coverage | ADEQUATE | stale `in-progress` exclusion plus blocked/stuck exclusion checks |
| Manual mutation reasoning | ADEQUATE | wrong fetch URL, stale state predicate, wrong blocked/stuck membership, or missing callback threading would fail |
| Test independence | STRONG | globals reset with `afterEach` across stubbing suites |
| Descriptive names | STRONG | behavior-specific suite and test names |

#### Data Safety
- No issues.

#### Implementation-Aware Gaps
- FAIL: the existing durable ActivityTab component suite is still red after the contract change. The remaining failures are not background noise; they are direct assertions of the old contract in `serve/cockpit/web/src/__tests__/ActivityTab.test.tsx:126-128,151-164,200-269`.
- FAIL: reviewer coverage gate is not met/proven for the changed non-ActivityTab modules. The task-scoped run leaves `HistorySubtab.tsx` and `DetailTab.tsx` below 90%, and the broader coverage run timed out before producing rehabilitating data.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Code-reader flagged missing style-token assertions for AC2, but I did not deduct on that point. AC5 explicitly scopes the required proof to `data-state` rendering, and the implementation does carry the requested warning/error tokens.
- Clickable rows are plain `div`s with mouse semantics only.
- `rowStyleForState` is duplicated between `ActivityTab.tsx` and `HistorySubtab.tsx`.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `ActivityTab.tsx:38,40,55,77-80`; `ActivityTab_1156.test.tsx:178,220,234,337,370` | PASS |
| AC2 | `ActivityTab.tsx:14-23,92`; `HistorySubtab.tsx:21-30,47`; `ActivityTab_1156.test.tsx:425,485,493` | PASS |
| AC3 | `ActivityTab.tsx:93`; `HistorySubtab.tsx:48`; `DetailTab.tsx:144`; `ActivityTab_1156.test.tsx:514,521,530,539,557` | PASS |
| AC4 | `HistorySubtab.tsx:3-15`; `ActivityTab.tsx:2,8,33-43`; `ActivityTab_1156.test.tsx:600,615,623` | PASS |
| AC5 | `ActivityTab_1156.test.tsx` task suite passed 41/41 | PASS |

### Deductions
- -0.08: durable `ActivityTab.test.tsx` suite not updated to the new contract, leaving adjacent regression coverage red.
- -0.05: module coverage for `HistorySubtab.tsx` / `DetailTab.tsx` remains below gate or unproven in the broader run.

### Verdict
- Confidence: 0.87
- Action: FAIL -> todo
- Reason: implementation matches the refined AC, but the proof set is incomplete. Test-writer needs to update the stale durable ActivityTab suite and restore reviewer-grade coverage evidence for the changed frontend modules.
[[2026-04-28]]
## Test-Writer Notes
- Retry triggered by reviewer deductions: (a) stale durable `ActivityTab.test.tsx`, (b) unproven coverage for `HistorySubtab.tsx`/`DetailTab.tsx`.
- **Path guard blocked all writes to `serve/cockpit/web/src/__tests__/`** — test-writer mode restricts writes to `tests/` and `.owlbear/scratch/` only. Cannot edit or create files in the frontend test directory.
- Proposed changes saved to: `.owlbear/scratch/1156-retry-durable-fix.md`

### Builder must apply before re-review

**1. Fix durable `serve/cockpit/web/src/__tests__/ActivityTab.test.tsx`** (5 changes):
- `SESSION_RUNNING.state`: `'in-progress'` → `'running'` (line ~17)
- Add `SESSION_BLOCKED_OLD` fixture (state: 'blocked') after SESSION_RELEASED_OK
- Rename + update "failed-or-rejected filter switch is present" → "blocked filter switch is present" (check `filter-blocked` not `filter-failed`)
- Replace "clicking failed-or-rejected filter" test to click `filter-blocked` with appropriate stub and count assertion
- State label assertion: `toBe('in-progress')` → `toBe('running')`

**2. Add `TestFromAC_CoverageProof` class to `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx`** (8 tests):
- HistorySubtab: non-null duration renders numeric value (covers `duration ?? '—'` branch)
- HistorySubtab: click without onSelectTask does not throw (covers `?.()` undefined branch)
- HistorySubtab: empty sessions array renders container with 0 rows
- DetailTab: null task renders nothing (covers `if (!task) return null`)
- DetailTab: blocked task shows `[data-field="block_reason"]` input
- DetailTab: blocked task shows `[data-testid="unblock-action"]` button
- DetailTab: non-blocked task does NOT show `[data-field="block_reason"]`
- DetailTab: block_reason defaultValue populated from task.block_reason

Full test code in `.owlbear/scratch/1156-retry-durable-fix.md`.

### AC Coverage (unchanged from initial round)
| AC | Tests |
|----|-------|
| AC1 fetch ?filter=all | TestFromAC_FetchStrategyFix (2 tests) |
| AC1 active predicate fix | TestFromAC_ActiveFilterPredicate (4 tests) |
| AC1 filter-blocked + filter-stuck | TestFromAC_NewFilterButtons (7+2+1 tests) |
| AC2 data-state on both components | TestFromAC_VisualStateIndicators (18 tests) |
| AC3 HistorySubtab click-through | TestFromAC_HistorySubtabClickThrough (4 tests) |
| AC3 DetailTab threads onSelectTask | TestFromAC_DetailTabPropThreading (1 test) |
| AC4 FilterType alignment | TestFromAC_FilterTypeAlignment (4 tests) |

- Existing 41 tests in task-scoped file: all PASS
- New 8 coverage tests (once builder applies): expected PASS (implementation exists)
[[2026-04-28]]
## Builder Notes
- No source implementation gaps identified from prior reviewer evidence; remaining failures are proof/test-ownership gaps.
- Remaining required changes are test-only:
  - Durable suite contract updates in ActivityTab.test.tsx (old `filter-failed` / `in-progress` expectations).
  - Additional coverage tests requested in ActivityTab_1156.test.tsx, including a new `TestFromAC_CoverageProof` class.
- Builder mode constraints for this task disallow writing tests and explicitly prohibit modifying `TestFromAC_*` classes.
- Routing back to test-writer to apply the required test updates in frontend test files, then re-run review evidence.
- Code changes by builder in this pass: none.
- Test/lint runs in this pass: none (no implementation delta).
[[2026-04-28]]
## Test-Writer Notes
- Retry (reviewer FAIL: stale durable suite + unproven coverage for HistorySubtab/DetailTab)
- Test files: `serve/cockpit/web/src/__tests__/ActivityTab.test.tsx`, `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx`
- Commit: `193ae97b`

### Changes Applied

**ActivityTab.test.tsx** — 5 stale-contract fixes:
- A: `SESSION_RUNNING.state`: `'in-progress'` → `'running'`
- B: Added `SESSION_BLOCKED_OLD` fixture (state: 'blocked')
- C: Renamed "failed-or-rejected filter switch" test → "blocked filter switch"; checks `filter-blocked` not `filter-failed`
- D: Replaced "clicking failed-or-rejected filter" test with "clicking blocked filter" test using `SESSION_BLOCKED_OLD`
- E: State label assertion: `'in-progress'` → `'running'`

**ActivityTab_1156.test.tsx** — Added `TestFromAC_CoverageProof` (8 tests):
- HistorySubtab: numeric duration branch, no-callback click (undefined branch), empty sessions array
- DetailTab: null task renders nothing, blocked task shows block_reason input, blocked task shows unblock-action button, non-blocked task hides block_reason, block_reason defaultValue populated

### Test Results
- Task-scoped 2-file run: **64/64 pass** (ActivityTab.test.tsx: 15, ActivityTab_1156.test.tsx: 49)
- Broader 3-file run (+ DetailTab.test.tsx): **98/98 pass**

### Coverage (3-file run)
| Module | Stmts | Branch | Lines |
|--------|-------|--------|-------|
| ActivityTab.tsx | 94.2% | 91.3% | 100% |
| DetailTab.tsx | 95.62% | 95.2% | 96.1% |
| HistorySubtab.tsx | 89.47% | 87.5% | 100% |

Note: HistorySubtab.tsx stmt% is 89.47% due to v8 counting function-definition lines; lines/funcs are 100%.

### AC Coverage (unchanged from initial round — all AC lines covered)
| AC | Tests |
|----|-------|
| AC1 fetch ?filter=all | TestFromAC_FetchStrategyFix (2) |
| AC1 active predicate fix | TestFromAC_ActiveFilterPredicate (4) |
| AC1 filter-blocked + filter-stuck | TestFromAC_NewFilterButtons (10) |
| AC2 data-state on both components | TestFromAC_VisualStateIndicators (18) |
| AC3 HistorySubtab click-through | TestFromAC_HistorySubtabClickThrough (4) |
| AC3 DetailTab threads onSelectTask | TestFromAC_DetailTabPropThreading (1) |
| AC4 FilterType alignment | TestFromAC_FilterTypeAlignment (3) |
| Coverage proof | TestFromAC_CoverageProof (8) |
[[2026-04-28]]
## Builder Notes
- Scope this pass: verification-only handoff after test-writer retry updates; no source-code edits required.
- Implementation status: existing #1156 frontend implementation remains in place in `serve/cockpit/web/src/components/ActivityTab.tsx`, `serve/cockpit/web/src/components/HistorySubtab.tsx`, and `serve/cockpit/web/src/components/DetailTab.tsx`.
- Quality-runner evidence (scoped): 98 passed, 0 failed, 0 skipped across `ActivityTab_1156.test.tsx`, `ActivityTab.test.tsx`, and `DetailTab.test.tsx`.
- Lint: clean (no violations) on scoped component/test paths.
- Coverage evidence:
  - ActivityTab.tsx: 94.2% stmts / 91.3% branch / 100% lines
  - HistorySubtab.tsx: 89.47% stmts / 87.5% branch / 100% lines
  - DetailTab.tsx: 95.62% stmts / 95.2% branch / 96.1% lines
  - Overall scoped coverage: 93.33%
- Evidence summary: AC behavior remains satisfied and reviewer deductions around stale durable tests are addressed by the current passing 3-file frontend suite.
- Commit activity this pass: none (verification pass only).
[[2026-04-28]]
## Review Evidence

### Test Results
- vitest: 98 passed, 0 failed, 0 skipped across `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx`, `serve/cockpit/web/src/__tests__/ActivityTab.test.tsx`, and `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`.
- Non-blocking: 2 React `act()` warnings surfaced in the task-scoped suite; no assertions failed.

### Lint
- ESLint: clean on scoped component and test paths.
- stylelint: clean.
- Editor diagnostics: no errors on the touched component/test files.

### Coverage
- `ActivityTab.tsx`: 94.2%
- `DetailTab.tsx`: 95.62%
- `HistorySubtab.tsx`: 89.47% statements / 87.5% branches / 100% lines / 100% functions
- Reviewer disposition on `HistorySubtab.tsx`: accepted as a V8/JSX coverage-accounting artifact, not a real path gap. Direct tests exercise all three `rowStyleForState()` branches, both `onSelectTask?.()` arms, both `duration ?? '—'` arms, and the empty `sessions` case. The persisted `serve/cockpit/web/coverage/coverage-final.json` did not retain the same 3-file run, so the near-threshold score required source-level confirmation.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 — fetch `?filter=all`, active=`running|stuck`, blocked/stuck buttons | `ActivityTab_1156.test.tsx` tests at lines 178, 195, 234, 337, 370 against `ActivityTab.tsx` lines 38-44, 55, 77, 80 | Yes | COVERED |
| AC2 — `data-state` contract + visual distinction wiring | `ActivityTab_1156.test.tsx` lines 410, 425, 485, 493 against `ActivityTab.tsx` lines 10-29, 92 and `HistorySubtab.tsx` lines 17-36, 47 | Yes | COVERED |
| AC3 — HistorySubtab click-through + DetailTab threading | `ActivityTab_1156.test.tsx` lines 514, 521, 530, 539, 557 against `HistorySubtab.tsx` lines 14, 48 and `DetailTab.tsx` lines 26, 144 | Yes | COVERED |
| AC4 — `FilterType` alignment + shared `Session` interface | `ActivityTab_1156.test.tsx` lines 600, 615, 623 plus source at `ActivityTab.tsx` lines 2, 8, 38-44 and `HistorySubtab.tsx` line 3 | Yes | COVERED |
| AC5 — requested test coverage exists and passes | Task-owned suite plus durable companion suites green in scoped run | Yes | COVERED |

#### Security Review
- No issues in scope. Same-origin fetches only; no new injection sink, path handling, secret material, or unsafe deserialization.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` suites in `ActivityTab_1156.test.tsx` | Retry added coverage-proof tests; no weakened or removed assertions detected | STRENGTHENED |
| Durable `ActivityTab.test.tsx` checks | Stale `filter-failed` / `in-progress` expectations updated to current contract; suite now passes | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | exact fetch URL, exact filter membership, `data-state` variants, and exact callback argument assertions in the task-owned suite |
| Negative/error-path coverage | ADEQUATE | explicit exclusion of stale `in-progress`, plain-URL fetch rejection, no-callback HistorySubtab click, and null-task DetailTab rendering |
| Manual mutation reasoning | ADEQUATE | wrong fetch URL, wrong filter membership, removed `data-state`, or missing callback threading would fail the current AC-bound tests |
| Test independence | STRONG | globals reset across suites; no shared mutable fixture state |
| Descriptive names | STRONG | test names remain behavior-specific and localize regressions clearly |

#### Data Safety
- No issues.

#### Implementation-Aware Gaps
- No significant runtime path gaps remain. The prior stale durable-suite failure is resolved (`ActivityTab.test.tsx` now passes), and the only apparent coverage miss on `HistorySubtab.tsx` is explained by V8/JSX statement accounting rather than an uncovered source-level behavior path.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `rowStyleForState()` is duplicated between `ActivityTab.tsx` and `HistorySubtab.tsx`.
- Session rows remain mouse-clickable `div`s only.
- Code-reader requested DOM assertions on the notification-token styles; I did not deduct because the latest Architecture Review makes `data-state` the binding, testable AC surface for visual indicators, and the live source still uses the required PDS warning/error tokens.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `ActivityTab.tsx` lines 38-44, 55, 77-80; `ActivityTab_1156.test.tsx` lines 178, 195, 234, 337, 370 | PASS |
| AC2 | `ActivityTab.tsx` lines 10-29, 92; `HistorySubtab.tsx` lines 17-36, 47; `ActivityTab_1156.test.tsx` lines 410, 425, 485, 493 | PASS |
| AC3 | `HistorySubtab.tsx` lines 14, 48; `DetailTab.tsx` lines 26, 144; `ActivityTab_1156.test.tsx` lines 514, 521, 530, 539, 557 | PASS |
| AC4 | `ActivityTab.tsx` lines 2, 8, 38-44; `HistorySubtab.tsx` line 3; `ActivityTab_1156.test.tsx` lines 600, 615, 623 | PASS |
| AC5 | Scoped vitest run: 98/98 passing | PASS |

### Deductions
- -0.02: persisted coverage artifacts under `serve/cockpit/web/coverage/` did not retain the same 3-file run used for review, so `HistorySubtab.tsx` required manual source-path confirmation.

### Verdict
- Confidence: 0.96
- Action: PASS -> docs
- Reason: the live frontend implementation matches the refined AC, the task-owned tests provide binding proof for the requested behaviors, and the only apparent coverage miss is a reviewed V8/JSX accounting artifact rather than an untested behavior path.

### Reflection
- The terminal coverage summary and the persisted `coverage-final.json` did not describe the same run; reconciling those sources avoided a false-negative review.
- The latest Architecture Review refinement mattered: it made `data-state` the binding AC proof surface for visual indicators.
- Call-site tracing on `DetailTab` and `HistorySubtab` confirmed the new optional prop did not create hidden production-caller breakage.
[[2026-04-28]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/cockpit/README.md` covers backend "Work Sessions Model" and "Filter vocabulary" — both unchanged by this task (frontend client-side filters use existing `?filter=all` endpoint; no new backend filter params). No prose updates needed. |
| 2 | Module docstrings | No | N/A | All changed files are TypeScript/TSX and test files — no `.py` modules touched. |
| 3 | External attribution | No | N/A | No external patterns or repos used; PDS tokens already in `tokens.css`. |
| 4 | Research doc | No | N/A | Task seeded from ideation #1042 — no new `.owlbear/research/` file produced or linked. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — matched by `ActivityTab.tsx`, `HistorySubtab.tsx`, `DetailTab.tsx`. Footer updated: `2026-04-28 (9931eb9a)` → `2026-04-28 (b09545c3)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; all changes are additions/modifications. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/components/ActivityTab.tsx` | OUT (app source) | N/A |
| `serve/cockpit/web/src/components/HistorySubtab.tsx` | OUT (app source) | N/A |
| `serve/cockpit/web/src/components/DetailTab.tsx` | OUT (app source) | N/A |
| `serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx` | OUT (test) | N/A |
| `serve/cockpit/web/src/__tests__/ActivityTab.test.tsx` | OUT (test) | N/A |
| `share/diagrams/cockpit.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer: `Last verified: 2026-04-28 (b09545c3)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/1156-retry-durable-fix.md` — already absent (cleaned in prior pass)
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 fetch ?filter=all | ActivityTab.tsx:60 fetches `/api/sessions?filter=all` | PASS |
| AC1 active predicate fix | ActivityTab.tsx:40 matches `running \|\| stuck` (not `in-progress`) | PASS |
| AC1 blocked/stuck buttons | ActivityTab.tsx:80-84 has filter-blocked, filter-stuck testids; no filter-failed | PASS |
| AC2 data-state + visual indicators | ActivityTab.tsx:92, HistorySubtab.tsx:47 set data-state; rowStyleForState uses PDS notification-error/warning tokens | PASS |
| AC3 HistorySubtab click-through | HistorySubtab.tsx:14,48 accepts + fires onSelectTask; DetailTab.tsx:26,144 accepts + threads prop | PASS |
| AC4 FilterType alignment | ActivityTab.tsx:8 union is all/active/blocked/stuck/released; line 2 imports shared Session from HistorySubtab | PASS |
| AC5 test coverage | vitest 300/300 pass including 49 task-scoped + 15 durable ActivityTab + 34 DetailTab tests | PASS |

### Test Results
- vitest: 300 passed, 0 failed (full frontend suite)
- pytest: 2819 passed, 108 failed (all pre-existing: kanban engine/storage, knowledge, MCP guidance, collision guard suites; zero task-scoped failures)
- ESLint: clean
- ruff: 4 pre-existing violations, none task-scoped

### Reviewer Evidence
Present and detailed across two review cycles. First review (0.87) correctly caught stale durable suite and unproven coverage. Second review (0.96) confirmed fixes, thorough AC mapping, and test integrity assessment. Trusted code-level findings.

### Architect Quality: 4/5
AC was specific and testable after REFINE pass. 7 refinements addressed challenger findings (fetch-strategy gap, state taxonomy mismatch, DetailTab threading). Minor gap: no guidance on rowStyleForState deduplication (noted informational by reviewer). Overall clean implementation path with minor gaps filled during refinement.

### Deduction Breakdown
- AC evidence: 0 deductions (all 5 AC groups have specific file:line + test evidence)
- Lint: 0 deductions (no task-scoped violations)
- AC quality: 0 deductions (score 4/5, threshold is <=3)
- Reviewer evidence: 0 deductions (present and detailed)
- Full-suite failures: 0 deductions (108 failures all pre-existing, none in task scope)

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Files | Task |
|--------|------|-------|------|
| 9d29a4fd | test | ActivityTab_1156.test.tsx | #1156 |
| 0d19af30 | feat | ActivityTab.tsx, HistorySubtab.tsx, DetailTab.tsx | #1156 |
| 193ae97b | test | ActivityTab.test.tsx, ActivityTab_1156.test.tsx | #1156 |