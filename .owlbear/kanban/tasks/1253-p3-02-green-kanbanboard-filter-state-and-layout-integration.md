---
id: 1253
title: 'P3-02: GREEN — KanbanBoard filter state and layout integration'
status: review
priority: needed
created: 2026-05-01T04:34:58.097220+00:00
updated: 2026-05-03T13:27:56.856212+00:00
tags:
- phase-3
- scope:cockpit-web
- tdd:green
parent: 1247
depends_on:
- 1252
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- KanbanBoard.tsx wires FilterPanel: (td:2)
  - useState for FilterState (initial: `{text:'', priority:'', tags:[], blocked:false}`) and panelOpen (initial: false) (td:1)
  - Derived filteredTasks via filterTasks() applied to full task set from useBoard (td:1)
  - Derived availableTags: deduplicated tags from full (unfiltered) task set (td:1)
  - Filter toggle button (`data-testid="filter-toggle"`) with badge showing active filter count (td:1)
  - Result count (`data-testid="filter-result-count"`, format "N / M tasks") adjacent to toggle when filters active (td:1)
  - FilterPanel rendered with props: filter, onFilterChange, priorities (from board.priorities), availableTags, open (td:1)
- Layout refactored to vertical flex-column: (td:1)
  - Toggle + count row at top (td:1)
  - FilterPanel below toggle (when open) (td:1)
  - Columns container with flex:1 + overflow-x:auto for horizontal scroll (td:1)
  - Column.tsx: remove hardcoded `maxHeight: 'calc(100vh - 56px)'` — columns fill available height from flex parent while retaining their own overflowY:auto (td:0)
- Interaction rules: (td:2)
  - onFilterChange callback sets contextMenu to null (td:1)
  - onFilterChange callback clears dragSourceStatus (td:1)
- All #1252 integration tests pass (GREEN) (td:0)
- All pre-existing KanbanBoard test suites (KanbanBoard.test.tsx, KanbanBoard_959.test.tsx) continue passing (td:0)

## In Scope
- KanbanBoard.tsx state additions and FilterPanel wiring
- Layout refactor (flex-column)
- Toggle button + result count
- Column.tsx height removal

## Out of Scope
- Accessibility attributes (Phase 4)
- aria-live, focus management (Phase 4)
- FilterPanel internals (already complete)
- filterTasks logic (already complete and tested)

## Builder Notes
- Shell.css `.shell__workspace` already has `overflow: auto` and fills grid 1fr row — KanbanBoard flex-column will inherit bounded height
- Task.tags is `string[]` (required per useBoard.ts interface) — no nullish guard needed
- Use `[...new Set(tasks.flatMap(t => t.tags))]` or equivalent for deduplicated availableTags
- Existing KanbanBoard_959.test.tsx has DOM-budget assertions — new elements (toggle, panel wrapper) must not violate those constraints

Brief: see parent #1247
[[2026-05-03]]
## Research
- Research doc: .owlbear/research/kanbanboard-filter-green-1253.md
- Sources: 7 studied, 5 high-relevance
- Recommendation: proceed directly to GREEN implementation (confidence: 0.90)
- Follow-up tasks created: none — successor tasks #1254–#1256 already exist
- Decision requests: none

Key findings:
- All 10 RED tests (#1252) confirmed failing on missing `filter-toggle` testid
- Implementation is ~40 lines of additions to KanbanBoard.tsx: 2 state hooks, derived values, toggle button, result count, FilterPanel wiring, flex-column layout
- One risk: Column.tsx hardcoded `calc(100vh - 56px)` needs removal for flex layout; verify existing test suites post-implementation
- Edge case: availableTags needs deduplication (multiple tasks may share tags)
- Challenge: skipped (T1 GREEN, no trade-offs)
[[2026-05-03]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: wire FilterPanel into KanbanBoard with layout refactor |
| Interface clarity | PASS | Props, testids, format strings, initial values all specified |
| Dependency correctness | PASS | #1252 (RED tests) is archived/done; FilterPanel + filterTasks exist and are tested |
| Module layering | PASS | KanbanBoard → FilterPanel (components/) + filterTasks (utils/) — correct direction, verified via Explore |
| TDD compliance | PASS | 10 RED tests exist in KanbanBoard_1252.test.tsx covering all behavioral AC |
| KISS/YAGNI | PASS | No new abstractions — 2 state hooks + derived values + JSX, ~40 LOC additions |
| Premise challenge | PASS | Filter UX is a clear user need; no existing capability serves this |
| Pattern consistency | PASS | useState hooks follow existing KanbanBoard pattern (4 existing hooks) |
| Security surface | PASS | Client-side only, no system boundaries |
| Single domain | PASS | cockpit-web frontend exclusively |

### Challenge Results
- Challenger: reconsider (0.66)
- Key concerns: (1) RED tests don't assert layout CSS directly; (2) Task.tags is required — nullish guard unnecessary; (3) Column.tsx height removal is a scroll-ownership trade-off; (4) Broader regression surface (KanbanBoard_959 DOM budget tests)
- Architect response: REBUTTED — all concerns are AC-precision issues addressed via refinement:
  - Removed misleading `t.tags ?? []` guidance; noted tags is required string[]
  - Added explicit Column.tsx AC line with behavioral requirement (retain internal scroll)
  - Added regression gate: existing KanbanBoard test suites must continue passing
  - Added Builder Notes section with Shell layout context and DOM-budget warning
  - Layout CSS being untested by RED suite is acceptable — it's implementation detail serving tested behavior

### Test Depth
- Max depth: td:2 (behavioral wiring + interaction rules)
- Test-writer: PROCEED (verify #1252 tests exist and cover AC, pass through)

### Verdict: APPROVE (with REFINE)
### Action Taken: Refined AC with td annotations, Column.tsx removal line, deduplication requirement, Builder Notes section, and regression gate. Advanced to todo.
[[2026-05-03]]
## Test-Writer Notes
- Non-implementation pass-through: `tdd:green` task — RED tests already written in #1252.
- Verified: `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx` exists with 10 tests in `TestFromAC_FilterIntegration`.
- AC coverage (all td:1/td:2 lines):
  - AC1 → renders filter toggle (td:1)
  - AC2 → toggle opens/closes FilterPanel (td:2, 2 tests)
  - AC3 → priority and text filter route tasks to correct columns (td:2, 2 tests)
  - AC4 → availableTags from full unfiltered task set (td:1)
  - AC5 → result count "N / M tasks" when filter active (td:1)
  - AC6 → filter change dismisses context menu (td:1)
  - AC7 → filter change cancels drag / deactivates drop targets (td:1)
  - AC8 → empty filter shows all tasks (td:1)
- Layout AC lines (td:1): architect confirmed these are implementation details served by behavioral tests — no additional tests needed.
- td:0 lines: no tests required.
- Architect directive: "Test-writer: PROCEED (verify #1252 tests exist and cover AC, pass through)."
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Implementation: updated `serve/cockpit/web/src/KanbanBoard.tsx` to add `FilterState` + `panelOpen` state, `filterTasks()`-derived task rendering, deduplicated `availableTags`, filter toggle (`data-testid="filter-toggle"`), active filter badge, and result count (`data-testid="filter-result-count"`) with `N / M tasks` formatting.
- Layout: refactored board root to flex-column with top control row, `FilterPanel` below controls, and columns container set to `flex: 1`, `minHeight: 0`, `overflowX: auto`.
- Interaction rules: `onFilterChange` now clears both `contextMenu` and `dragSource` before applying new filter state.
- Column height rule: removed hardcoded `maxHeight: 'calc(100vh - 56px)'` from `serve/cockpit/web/src/components/Column.tsx`; preserved `overflowY: auto`.
- Tests (RED baseline): quality-runner confirmed all 10 `TestFromAC_FilterIntegration` tests failed before implementation.
- Tests (GREEN): quality-runner scoped run passed 55/55 for `KanbanBoard_1252.test.tsx`, `KanbanBoard.test.tsx`, `KanbanBoard_959.test.tsx`.
- Regression + coverage gate: quality-runner run across all KanbanBoard suites passed 98/98 with module coverage `KanbanBoard.tsx` 93.54%, `Column.tsx` 95.83%.
- Lint: quality-runner reported eslint clean for both changed files.

### Reflection
- Scoped coverage across only 3 suites under-reported module coverage (83.87/87.5); expanded to all durable KanbanBoard suites to produce representative gate evidence.
- AC-driven implementation remained surgical: only 2 source files changed and no test modifications.
- Existing architecture notes accurately predicted the single layout risk (`Column` max-height), reducing rework.
[[2026-05-03]]
## Review Evidence
- Parallel fan-out: quality-runner succeeded. `code-reader` returned no response, so I completed the sequential fallback review manually.
- Scope: builder commit `489578a3` changed only `serve/cockpit/web/src/KanbanBoard.tsx` and `serve/cockpit/web/src/components/Column.tsx`. No test files changed, so TestFromAC immutability is preserved with high confidence.

### Test Results
- quality-runner scoped frontend run: 55 passed, 0 failed, 0 skipped across `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`, and `serve/cockpit/web/src/__tests__/KanbanBoard_959.test.tsx`.

### Lint
- ESLint clean for `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/Column.tsx`, and `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- VS Code diagnostics: no errors in the two changed source files or the task suite.

### Coverage
- `serve/cockpit/web/src/KanbanBoard.tsx`: 94%
- `serve/cockpit/web/src/components/Column.tsx`: 96%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Filter toggle exists | `KanbanBoard_1252.test.tsx:158` | Yes | COVERED |
| `panelOpen` defaults closed and toggles open/closed | `KanbanBoard_1252.test.tsx:164`, `KanbanBoard_1252.test.tsx:175` | Yes | COVERED |
| `filterTasks()` drives filtered column placement | `KanbanBoard_1252.test.tsx:192`, `KanbanBoard_1252.test.tsx:238`; source `KanbanBoard.tsx:74` | Yes | COVERED |
| `availableTags` comes from full unfiltered task set | `KanbanBoard_1252.test.tsx:278`; source `KanbanBoard.tsx:75` | Yes | COVERED |
| Toggle badge shows active filter count | Only toggle existence/open-close tests at `KanbanBoard_1252.test.tsx:158`, `KanbanBoard_1252.test.tsx:164`, `KanbanBoard_1252.test.tsx:175`; no assertion on button text/count while source renders count at `KanbanBoard.tsx:76-81` and `KanbanBoard.tsx:225-226` | No | MISSING |
| Result count shows exact `N / M tasks` format | `KanbanBoard_1252.test.tsx:301`; source `KanbanBoard.tsx:228-230` | Yes | COVERED |
| `FilterPanel` receives `filter`, `onFilterChange`, `priorities`, `availableTags`, `open` | Source passes all props at `KanbanBoard.tsx:236-240`, but the stub only consumes `onFilterChange`, `availableTags`, `open` at `KanbanBoard_1252.test.tsx:46`; wrong `filter` or `priorities` values would stay green | No | MISSING |
| `onFilterChange` clears `contextMenu` and `dragSource` | `KanbanBoard_1252.test.tsx:322`, `KanbanBoard_1252.test.tsx:353`; source `KanbanBoard.tsx:202-205` | Yes | COVERED |

#### Security Review
- No issues found. The diff adds client-side state, JSX, and style changes only; no new network boundary, HTML injection path, or secret exposure.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_FilterIntegration` suite | Builder commit `489578a3` changes only `KanbanBoard.tsx` and `Column.tsx`; no test files in diff | PRESERVED |

#### Test Quality
- Assertion specificity: ADEQUATE for the covered filter-routing, result-count, context-menu, and drag-reset cases.
- Manual mutation reasoning: WEAK for the active-filter badge and `FilterPanel` prop-forwarding sub-bullets. Removing `(${activeFilterCount})` from `KanbanBoard.tsx:226` or passing the wrong `filter` or `priorities` props at `KanbanBoard.tsx:236-240` would not fail the current TestFromAC suite.

#### Data Safety
- No issues found. The change is local UI state over an existing in-memory task array; no persistence, shared mutation, or unbounded work added.

#### Test Gaps
- Missing proof for the active-filter badge count on the toggle control.
- Missing proof that `FilterPanel` receives live `filter` state and `priorities={board.priorities}` rather than arbitrary values.
- Layout lines are source-verified in `KanbanBoard.tsx:210-243` and the `Column.tsx` diff, but I did not use them as the routing reason because the architect explicitly scoped them as implementation-detail verification.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability was introduced.

#### Builder Process Quality
- CLEAN. One implementation attempt, no repeated reviewer loop, no unchanged retries.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Filter state and `panelOpen` wiring | `KanbanBoard.tsx:30-35`, `KanbanBoard.tsx:70-71`; open/close behavior proven by `KanbanBoard_1252.test.tsx:164`, `KanbanBoard_1252.test.tsx:175` | `clicking filter toggle opens FilterPanel`, `clicking filter toggle again closes FilterPanel` | PASS |
| Derived `filteredTasks` from full task set | `KanbanBoard.tsx:74`; filtered placement proven at `KanbanBoard_1252.test.tsx:192` and `KanbanBoard_1252.test.tsx:238` | priority/text filter tests | PASS |
| Derived deduplicated `availableTags` from full task set | `KanbanBoard.tsx:75`; proven at `KanbanBoard_1252.test.tsx:278` | availableTags test | PASS |
| Toggle badge shows active filter count | Source renders suffix at `KanbanBoard.tsx:76-81` and `KanbanBoard.tsx:225-226`; no test asserts the count | none | FAIL |
| Result count `N / M tasks` | `KanbanBoard.tsx:228-230`; proven at `KanbanBoard_1252.test.tsx:301` | result-count test | PASS |
| `FilterPanel` prop forwarding | `KanbanBoard.tsx:236-240`; task suite only proves `onFilterChange`, `availableTags`, and `open` because the stub ignores `filter` and `priorities` at `KanbanBoard_1252.test.tsx:46` | partial only | FAIL |
| Vertical flex-column layout, controls row, panel placement, scroll container | `KanbanBoard.tsx:210-243` | architect accepted source verification | PASS |
| `Column.tsx` removes hardcoded `maxHeight` and keeps `overflowY:auto` | builder diff removes `maxHeight`; current `Column.tsx:57` keeps `overflowY: auto` | source verification | PASS |
| Interaction rules clear `contextMenu` and `dragSource` | `KanbanBoard.tsx:202-205`; proven at `KanbanBoard_1252.test.tsx:322` and `KanbanBoard_1252.test.tsx:353` | context-menu and drag-reset tests | PASS |
| #1252 integration suite passes | quality-runner scoped run confirms the 10 task-specific tests are green within a 55-test run | `KanbanBoard_1252.test.tsx` | PASS |
| Pre-existing KanbanBoard suites continue passing | quality-runner scoped run confirms `KanbanBoard.test.tsx` and `KanbanBoard_959.test.tsx` are green | durable regressions | PASS |

### Deductions
- `0.08` missing TestFromAC proof for the active-filter badge count.
- `0.05` missing TestFromAC proof for `FilterPanel` `filter` and `priorities` prop forwarding.
- `0.02` `code-reader` returned no response; manual sequential fallback completed.

### Verdict
- Confidence: `0.85`
- FAIL
- Route: `todo`

### Required Follow-up
- Add a TestFromAC assertion that activating filters updates the toggle control with the active-filter count, not just the separate result-count element.
- Add a TestFromAC assertion that `FilterPanel` receives live `filter` state and `priorities={board.priorities}`. The current stub at `KanbanBoard_1252.test.tsx:46` should capture and assert those props.
- Re-run the same scoped frontend quality gate after strengthening the tests. No source-code change is currently indicated by this review.
[[2026-05-03]]
## Test-Writer Notes
- Retry: filled 2 reviewer-cited gaps in `serve/cockpit/web/src/__tests__/KanbanBoard_1252.test.tsx`.
- Mock updated: `capturedFilter` and `capturedPriorities` added; `FilterPanel` stub now captures all 5 props.
- New tests (added to `TestFromAC_FilterIntegration`):
  1. `filter toggle label reflects the active filter count` — asserts toggle text is "Filters" with no count when no filters active, "Filters (1)" with one criterion, "Filters (2)" with two criteria.
  2. `FilterPanel receives the live filter state and board priorities as props` — asserts `capturedFilter` starts as EMPTY_FILTER, updates after `onFilterChange` call, and `capturedPriorities` equals `board.priorities` throughout.
- Tests per category: happy 2, edge 0, error 0, boundary 0 (2 new tests).
- Quality gate: all 12 `KanbanBoard_1252` tests pass + 45/45 durable suites (KanbanBoard.test.tsx, KanbanBoard_959.test.tsx).
- ESLint: clean.
- Both new tests PASS against current implementation (implementation already correct per reviewer — no source change indicated).
- Builder skip: test-only retry, all tests green → advancing directly to review per Step 1b.1.
[[2026-05-03]]
Builder skip: test-only retry — all 2 new proof tests pass against current impl. No source change needed. Advancing to review.