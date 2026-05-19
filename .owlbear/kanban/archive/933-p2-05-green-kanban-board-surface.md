---
id: 933
title: 'P2-05: GREEN — Kanban board surface'
status: archived
priority: important
created: 2026-04-17T19:58:25.632962+00:00
updated: 2026-04-18T15:39:13.477665+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent: 920
depends_on:
- 931
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Implement the kanban board surface to pass RED tests from #931.

## Acceptance Criteria

- [ ] Board fetches data from `GET /api/board` + `GET /api/tasks` via a plain fetch hook exposing `{ board, tasks, loading, error }` (TanStack Query deferred to #960)
- [ ] Status columns rendered in board config order via CSS Grid or flexbox
- [ ] Cards sorted by priority within columns — descending order derived from `board.priorities` array index (higher index = higher priority)
- [ ] Card indicators: priority-coded left border, block badge (icon + tooltip with `block_reason`), running indicator (derived from `claimed` boolean in API response)
- [ ] Context menu on right-click offers all valid status transitions per `board.valid_transitions[status]` — display-only, click handlers deferred to #958
- [ ] Column headers show task count via `[data-testid="column-count"]`
- [ ] Empty state per column (`[data-testid="empty-column"]` with non-blank text), loading indicator (`[data-testid="loading-indicator"]` or `[data-testid="skeleton"]`), and error state (`[data-testid="error-message"]` with non-empty text, columns not rendered)
- [ ] Both `/api/board` and `/api/tasks` must succeed — if either fails, show error state (both-or-nothing)
- [ ] All 25 RED tests from #931 pass

## Implementation Notes

- **Card height:** target ~48-56px (visual guidance, not tested in jsdom)
- **Scroll:** horizontal scroll between columns, vertical scroll within columns (CSS, not tested in jsdom)
- **File structure:** main component must be default export at `src/KanbanBoard.tsx` to match test import `import KanbanBoard from '../KanbanBoard'`. Sub-components (Column, Card, ContextMenu) may be internal helpers or extracted to separate files if the main file exceeds ~200 lines
- **Hook contract:** `useBoard()` returning `{ board, tasks, loading, error }` — this interface is stable for TanStack Query migration in #960

## Files

- `serve/cockpit/web/src/KanbanBoard.tsx` (default export — required by test import path)
- Sub-components extracted as needed (builder discretion)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/933-kanban-board-green.md
- Sources: 9 studied, 6 high-relevance (≥0.90)
- Recommendation: Single-file KanbanBoard.tsx at src/ (matching test import), plain fetch hook, display-only context menu, priority sort from API index, no DnD/virtualization/TanStack Query yet (confidence: 0.78)
- Challenge: reconsider (0.52) — revised after addressing file-path conflict, context menu action gap, 700-task perf, TanStack Query trade-off, priority sort derivation
- Follow-up tasks created: #958 (context menu move RED tests), #959 (700-task benchmark), #960 (TanStack Query + polling), #961 (Shell route wiring)
- Decision requests: none — all findings T1 (autonomous follow-ups)
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | GREEN implementation for kanban board surface. DnD (#957 E2E), status bar (#960), context menu actions (#958), and Shell wiring (#961) properly deferred to separate tasks |
| Interface clarity | PASS | Hook contract `useBoard(): { board, tasks, loading, error }` specified. All data-testid selectors documented in AC. Both-or-nothing fetch failure behavior explicit |
| Dependency correctness | PASS | Depends on #931 (RED tests). Tests verified at `src/__tests__/KanbanBoard.test.tsx` — 25 `it()` blocks confirmed. Follow-ups #958, #960, #961, #962 depend on this task |
| Module layering | PASS | Frontend component consuming read-only API. No upward imports or layering violations |
| TDD compliance | PASS | #931 is the preceding RED task. 25 tests define the exact contract |
| KISS/YAGNI | PASS | Removed DnD and status bar wiring from AC (no RED tests). Plain fetch hook instead of TanStack Query. Display-only context menu. No virtualization |
| Premise challenge | PASS | Kanban board is the core Cockpit surface — valid and necessary |
| Pattern consistency | PASS | Uses PDS design system, standard fetch API, CSS Grid/flexbox. Consistent with Shell.tsx patterns |
| Security surface | PASS | Read-only data display. Move endpoint validation happens server-side (`mutation.py` validates against `valid_transitions`). No new attack surface |
| Single domain | PASS | Frontend/cockpit domain only |

### Refinements Applied (REFINE + APPROVE)

1. **Removed AC #5 (DnD)** — no RED tests, deferred to E2E task
2. **Removed AC #10 (status bar wiring)** — deferred to #960 (TanStack Query + polling)
3. **Fixed `claim_status` → `claimed`** — API model `TaskSummaryOut` has `claimed: bool`, not `claim_status`
4. **Fixed "TanStack Query or fetch hooks" → "plain fetch hook"** — research decided plain fetch for GREEN, TanStack Query deferred to #960
5. **Fixed test count: 25 tests** (not 26 as originally stated)
6. **Fixed file paths** — `src/KanbanBoard.tsx` (default export) to match test import `import KanbanBoard from '../KanbanBoard'`, not `src/surfaces/kanban/`
7. **Moved visual-only guidance** (card height, scroll behavior) from AC to Implementation Notes section — not testable in jsdom
8. **Added both-or-nothing AC** — if either `/api/board` or `/api/tasks` fails, show error state
9. **Specified hook contract** — `useBoard(): { board, tasks, loading, error }` for stable TanStack Query migration surface

### Follow-up Task Created

- #962: RED tests for context menu dismiss behavior + accessibility basics (Escape, outside-click, second-card-click, ARIA roles, done-status empty menu)

### Challenge Results

- Challenger: reconsider (0.55)
- Concerns raised: (C1) test count 25 not 26 — accepted, fixed. (C2) task body not yet edited — accepted, body rewritten before advancing. (C3) untestable visual constraints in AC — accepted, moved to Implementation Notes. (C4) context menu dismiss untested — accepted, created follow-up #962. (C5) accessibility gaps — accepted, included in #962
- Blind spots noted: partial fetch failure (added to AC as both-or-nothing), unknown priority indexOf edge case (defensive, API controls priorities), single-file size (200-line threshold in implementation notes)
- Architect response: all actionable concerns addressed via AC rewrite and follow-up task creation. Revised confidence after addressing: 0.88

### Verdict: APPROVE (after refinement)

### Action Taken: Rewrote AC in task body — removed 2 out-of-scope items, fixed 3 factual errors, added 2 missing constraints, moved visual guidance to Implementation Notes. Created #962 for dismiss + a11y test gap. Advanced to todo

[[2026-04-18]]

## Test-Writer Notes

- Test file: `serve/cockpit/web/src/__tests__/KanbanBoard_933.test.tsx`
- Classes: `TestFromAC_KanbanBoardBothOrNothing`
- Tests per category: happy 0, edge 0, error 8, boundary 0
- Total: 8 tests, all FAIL (ImportError — `KanbanBoard.tsx` does not exist)
- TypeScript: clean (only expected TS2307 "module not found" error)

### AC Coverage

| AC Line | Tests |
|---------|-------|
| AC#1–7, #9 | Covered by 25 existing tests in `KanbanBoard.test.tsx` (#931) |
| AC#8 — both-or-nothing (both APIs must succeed) | `/api/board` network error → error state + no columns (2 tests); `/api/tasks` network error → error state + no columns (2 tests); `/api/board` HTTP 500 → error state + no columns (2 tests); `/api/tasks` HTTP 500 → error state + no columns (2 tests) |

### Gap filled

The architecture review on #933 added the both-or-nothing AC (partial failure: one API succeeds, one fails). The #931 tests only covered total failure (`stubFetchError` rejects all). These 8 tests cover partial failures (one API fails, one succeeds) and HTTP error responses (`ok: false`).

### Fail evidence

```
FAIL  src/__tests__/KanbanBoard_933.test.tsx
Error: Failed to resolve import "../KanbanBoard" — Does the file exist?
Test Files  1 failed | Tests  no tests (module-level failure)
```

[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/web/src/KanbanBoard.tsx` (created, 198 lines)

### Test results

- 33 tests passed (25 from KanbanBoard.test.tsx + 8 from KanbanBoard_933.test.tsx)
- TypeScript: clean (0 errors)
- No Python suite changes needed

### Implementation summary

- `useBoard()` hook: parallel `Promise.all` fetch of `/api/board` + `/api/tasks`; both-or-nothing error handling — `ok: false` responses throw, caught by try/catch → error state
- `loading=true` on initial render (synchronous) → `[data-testid="loading-indicator"]` shown immediately
- Error state: `[data-testid="error-message"]` with recovery text, no columns rendered
- `Column` component: `[data-column]` attr, `[data-testid="column-count"]`, `[data-testid="empty-column"]`
- `Card` component: `[data-testid="task-card"]` with `data-id`, `data-priority`; `[data-testid="card-title"]` with `title` attr; `[data-testid="block-badge"]` (title + aria-label = block_reason); `[data-testid="running-indicator"]` for claimed tasks
- Priority sort: `priorities.indexOf(b.priority) - priorities.indexOf(a.priority)` (descending by index)
- Context menu: right-click → `[data-testid="context-menu"]` with `[data-testid="transition-item"][data-status]` per valid transition

### Commit

`53c4e7fc` feat: implement KanbanBoard surface (#933, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- npm test (Vitest): 33 passed, 0 failed (25 × KanbanBoard.test.tsx + 8 × KanbanBoard_933.test.tsx)

### Lint

- TypeScript (via build script `tsc -b`): clean (0 errors)
- ESLint: not configured in project — skipped
- ruff: Python-only, not applicable to TypeScript

### Coverage

- @vitest/coverage-v8 not installed — not available

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC#1 — fetch hook `{board, tasks, loading, error}` | Loading/error/column tests (indirect) | Partial — hook shape not directly asserted | LAX |
| AC#2 — columns in board-config order **via CSS Grid or flexbox** | "renders columns in board-config order" (KanbanBoard.test.tsx) | DOM order YES; CSS layout NO | **MISSING** |
| AC#3 — cards sorted by priority descending | "sorts cards within a column by priority descending" | YES | COVERED |
| AC#4 — priority-coded **left border**, block badge, running indicator | Block badge + running indicator covered; **zero tests for left border** | NO for left border | **MISSING** |
| AC#5 — context menu valid transitions | 4 context menu tests | YES | COVERED |
| AC#6 — `[data-testid="column-count"]` | "shows correct task count in column header" | YES | COVERED |
| AC#7 — empty state, loading, error state | 5 tests covering all three states | YES | COVERED |
| AC#8 — both-or-nothing | 8 tests in KanbanBoard_933.test.tsx | YES | COVERED |
| AC#9 — all 25 RED tests pass | quality-runner: 33 passed, 0 failed | YES (confirmed by execution) | COVERED |

**MISSING × 2 = FAIL (§5.0).**

#### Security Review

- No hardcoded secrets, tokens, or credentials.
- `fetch('/api/board')`, `fetch('/api/tasks')` — no user-controlled URL components.
- Context menu position (`e.clientX`/`e.clientY`) applied as numeric inline style — no injection vector.
- No `eval()`, `dangerouslySetInnerHTML`, or unsafe deserialization.
- No new dependencies.

No issues.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All `TestFromAC_KanbanBoard` methods | No changes | PRESERVED |
| All `TestFromAC_KanbanBoardBothOrNothing` methods | No changes | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | ADEQUATE | `.not.toBeNull()` minimum-viable; count + order assertions strong where it matters |
| Negative/error-path | STRONG | All positive paths have mirrored negatives; 4 partial-failure permutations distinct |
| Manual mutation | STRONG | Sort comparator flip caught by sort test; `ok: false` check caught by KanbanBoard_933 tests |
| Test independence | STRONG | `renderBoard()` fresh per test; `vi.unstubAllGlobals()` in afterEach |
| Descriptive names | STRONG | All test names explicit |

No WEAK ratings.

#### Data Safety

- `cancelled` flag in `useBoard` effect prevents setState after unmount — race condition handled correctly (KanbanBoard.tsx:44).
- `Promise.all()` ensures atomic fetch — no partial-success state possible.

No issues.

#### Implementation-Aware Gaps

**GAP 1 — AC#4 priority-coded left border (CRITICAL):**
`Card` component (KanbanBoard.tsx:82–98) renders a `<div>` with no `className` and no `style` attribute. The `data-priority` attribute is present but drives no visual treatment. No CSS file exists for this component. Neither test file asserts a border style or priority-colour class. The priority-coded left border is entirely absent from the implementation.

**GAP 2 — AC#2 CSS Grid or flexbox (CRITICAL):**
The columns container (KanbanBoard.tsx:169) is a plain `<div>` with no `className` and no `style`. No inline `display: flex` or `display: grid` applied. No CSS import. Column DOM order is correct but the layout mechanism required by AC#2 is not present.

**GAP 3 — Empty context menu for terminal status (informational):**
No test exercises right-click on a `done`-status card with `valid_transitions['done'] = []`. The `?? []` fallback is correct but the empty-menu state is untested.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL

- **6.1 Wrong AC references in comments:** KanbanBoard.test.tsx labels context-menu block "AC #7" (should be AC#5), loading state "AC #10" and error state "AC #11" (neither exists; both belong under AC#7). Doesn't affect execution.
- **6.2 `useBoard` unnecessarily exported:** KanbanBoard.tsx:37 exports `useBoard` — no external consumer visible in workspace. Internal-only; removing export reduces public API surface.
- **6.3 No context menu dismissal:** No document `onClick` or Escape `onKeyDown` handler. Not required by this task's AC; flagged for awareness before #958.

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC#1 — fetch hook `{board, tasks, loading, error}` | KanbanBoard.tsx:37–73 — hook returns all 4 fields | DOM-proxy tests | PASS |
| AC#2 — columns in board-config order via CSS Grid/flexbox | DOM order correct (KanbanBoard.tsx:169–179); **no flex/grid applied** | "renders columns in board-config order" | **FAIL** |
| AC#3 — cards sorted descending by priorities index | KanbanBoard.tsx:122 `priorities.indexOf(b.priority) - priorities.indexOf(a.priority)` | "sorts cards within a column by priority descending" | PASS |
| AC#4 — priority-coded left border | **No border style or className on Card div (KanbanBoard.tsx:82–98)** | None | **FAIL** |
| AC#5 — context menu valid transitions, display-only | KanbanBoard.tsx:183–196; transitions from `valid_transitions` | 4 context menu tests | PASS |
| AC#6 — `[data-testid="column-count"]` | KanbanBoard.tsx:131 | "shows correct task count in column header" | PASS |
| AC#7 — empty state, loading, error state | KanbanBoard.tsx:145–162, 150–156 | 5 state tests | PASS |
| AC#8 — both-or-nothing | KanbanBoard.tsx:49–50 throws on `!ok` caught by try/catch | 8 tests in KanbanBoard_933.test.tsx | PASS |
| AC#9 — 25 RED tests pass | quality-runner: 33 passed, 0 failed | KanbanBoard.test.tsx × 25 | PASS |

### Confidence: .62

### Verdict: FAIL

---

### Action Required (builder)

Two AC compliance failures — route back to **in-progress**:

1. **AC#4 — priority-coded left border:** Add a priority→colour mapping in `Card` (e.g., `borderLeft` inline style computed from `task.priority` and a priority colour map). Must be verifiable in jsdom — use inline style or a `data-` attribute that encodes the colour, not a CSS class with an external stylesheet.

2. **AC#2 — CSS Grid or flexbox:** Add `style={{ display: 'flex', gap: '...' }}` (or equivalent) to the columns container `<div>` at KanbanBoard.tsx:169. Must be testable — use inline style so jsdom can assert `container.style.display`.

3. **Tests:** Once implementation is in place, add test assertions for both:
   - Priority left border: check `card.style.borderLeft` or equivalent per priority level.
   - Column layout: check the wrapping div has `style.display === 'flex'` or `'grid'`.
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/web/src/KanbanBoard.tsx` — added `PRIORITY_COLORS` map, `borderLeft` inline style on `Card`, `display: flex` + `gap: 16px` on columns container
- `serve/cockpit/web/src/__tests__/KanbanBoard_933.test.tsx` — added `TestBuilderDiscovered` class (3 tests) + `stubFetchSuccessMulti` helper

### Test results

- 36 tests passed (25 × KanbanBoard.test.tsx + 11 × KanbanBoard_933.test.tsx [8 TestFromAC + 3 TestBuilderDiscovered])
- 0 failed
- TypeScript: clean (build passes, 0 errors)

### Fixes applied (reviewer action items)

1. **AC#4 — priority-coded left border:** Added `PRIORITY_COLORS` record mapping all 5 priority levels to distinct hex colours. `Card` applies `style={{ borderLeft: '4px solid COLOR' }}` using the map, with `#888888` fallback.
2. **AC#2 — CSS Grid or flexbox:** Columns container `<div>` now has `style={{ display: 'flex', gap: '16px', overflowX: 'auto' }}` — inline so jsdom can assert it.

### TDD discipline

- Wrote 3 `TestBuilderDiscovered` tests first → all RED (columns container `style.display` was `''`, card `style.borderLeft` was empty)
- Fixed implementation → all 3 GREEN
- Full suite: 36 passed, 0 failed

### Commit

`38b1c023` fix: add priority left border and flex layout to KanbanBoard (#933, builder)
[[2026-04-18]]

## Review Evidence

### Test Results

- Vitest (independent run): **36 passed, 0 failed** (25 × KanbanBoard.test.tsx + 11 × KanbanBoard_933.test.tsx [8 TestFromAC + 3 TestBuilderDiscovered])

### Lint

- TypeScript (`tsc -b`): clean, 0 errors
- ESLint: not configured — pre-existing project state, not new regression

### Coverage

- @vitest/coverage-v8 not installed — N/A

### Cycle Context

Second review cycle. Cycle 1 (FAIL) identified AC#2 (no flex/grid) and AC#4 (no left border). Builder fixed both in cycle 2 and added 3 `TestBuilderDiscovered` tests.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC#1 — useBoard() `{board, tasks, loading, error}` | KanbanBoard.tsx:37–73 — all 4 fields returned | Loading/error/data DOM tests | PASS |
| AC#2 — columns in board-config order via CSS Grid/flexbox | KanbanBoard.tsx:169 `style={{ display: 'flex', gap: '16px', overflowX: 'auto' }}` | "columns container has flex or grid display" | PASS |
| AC#3 — priority sort descending | KanbanBoard.tsx:122 `priorities.indexOf(b.priority) - priorities.indexOf(a.priority)` | "sorts cards within a column by priority descending" | PASS |
| AC#4 — priority-coded left border, block badge, running indicator | KanbanBoard.tsx:82–98; PRIORITY_COLORS (5 levels) + borderLeft inline style; block badge title+aria-label; running-indicator span | TestBuilderDiscovered borderLeft pair; block/running tests in KanbanBoard.test.tsx | PASS |
| AC#5 — context menu valid transitions, display-only | KanbanBoard.tsx:183–196 `board.valid_transitions[contextMenu.taskStatus] ?? []` | 4 context menu tests | PASS |
| AC#6 — `[data-testid="column-count"]` | KanbanBoard.tsx:131 | "shows correct task count in column header" | PASS |
| AC#7 — empty-column, loading-indicator, error-message + no columns | KanbanBoard.tsx:145–162 | 5 state tests | PASS |
| AC#8 — both-or-nothing | KanbanBoard.tsx:49–50 throws on `!ok`; Promise.all ensures atomic failure | 8 TestFromAC_KanbanBoardBothOrNothing tests | PASS |
| AC#9 — 25 RED tests pass | 36 tests pass; KanbanBoard.test.tsx untouched | All 25 KanbanBoard.test.tsx tests | PASS |

### Test-Writer Audit

| AC Line | Verdict |
|---------|---------|
| AC#1 | COVERED (indirect via state tests) |
| AC#2 | COVERED (dom order + flex display test) |
| AC#3 | COVERED |
| AC#4 | COVERED (badge/running + borderLeft truthy + different-priorities pair) |
| AC#5 | COVERED |
| AC#6 | COVERED |
| AC#7 | COVERED |
| AC#8 | COVERED (8 partial-failure permutations) |
| AC#9 | COVERED |

No MISSING entries.

### Test Integrity

All 25 `TestFromAC_KanbanBoard` tests: PRESERVED (KanbanBoard.test.tsx not in changed files). All 8 `TestFromAC_KanbanBoardBothOrNothing` tests: PRESERVED.

### Test Quality

| Dimension | Rating |
|-----------|--------|
| Assertion specificity | ADEQUATE — `toBeTruthy()` on borderLeft compensated by `criticalBorder !== somedayBorder` pair |
| Negative/error-path | STRONG — 8 partial-failure permutations |
| Manual mutation | STRONG — removing flex/border breaks tests; removing throw breaks error-state tests |
| Test independence | STRONG — `vi.unstubAllGlobals()` in afterEach, fresh render per test |
| Descriptive names | STRONG |

No WEAK ratings.

### Security

Clean. No hardcoded secrets, no injection vectors, no new dependencies. Error messages expose HTTP status codes only. `block_reason` rendered into `title`/`aria-label` attributes (not innerHTML).

### Builder Process

FRICTION (2 cycles). Cycle 1: initial implementation. Cycle 2: targeted fix for reviewer-identified AC gaps. Approach variation present. No loop.

### Informational

- `useBoard` is exported (KanbanBoard.tsx:37) but has no external consumer yet — unnecessary export creates implicit public API surface
- `PRIORITY_COLORS` fallback `?? '#888888'` and `valid_transitions ?? []` fallback are untested (minor — not exploitable)
- `"card has a non-empty borderLeft style"` could be strengthened to assert specific hex value for critical card (e.g., `toContain('#e00000')`)

### Deductions

- `toBeTruthy()` assertion (compensated): −0.02
- ESLint not configured (pre-existing): −0.01
- Minor untested defensive fallback paths: −0.02
- 2-cycle build: −0.02

### Confidence: .93 → PASS

[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | New frontend component only — no stack attributes, endpoints, or conventions in copilot-instructions.md changed |
| 2 | Module docstrings | No | N/A | TypeScript/React only; no Python modules created or modified |
| 3 | External attribution | Yes | Verified | `sources/overview.md` already contains `## Kanban Board GREEN Phase (Task #933)` with 4 rows: @dnd-kit/react, @dnd-kit/core, @atlaskit/pragmatic-drag-and-drop, dnd-kit React 19 issues |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/933-kanban-board-green.md` exists, linked in task body, follow-up tasks #958/#959/#960/#961 created |

### Files Updated

- None

### Scratch Files Cleaned

- None found (`933-*` glob returned no results)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC#1 — useBoard() `{board, tasks, loading, error}` | KanbanBoard.tsx:38–77, all 4 fields returned | PASS |
| AC#2 — columns via CSS Grid/flexbox | KanbanBoard.tsx:169 `display: 'flex'`; TestBuilderDiscovered flex test | PASS |
| AC#3 — priority sort descending | KanbanBoard.tsx:122 `priorities.indexOf(b.priority) - priorities.indexOf(a.priority)` | PASS |
| AC#4 — priority left border, block badge, running indicator | KanbanBoard.tsx:94 `borderLeft: 4px solid`; PRIORITY_COLORS L82–88; block badge L97–103; running L104 | PASS |
| AC#5 — context menu valid transitions | KanbanBoard.tsx:183–196; 4 context menu tests in KanbanBoard.test.tsx | PASS |
| AC#6 — column-count testid | KanbanBoard.tsx:131 | PASS |
| AC#7 — empty/loading/error states | KanbanBoard.tsx:145–162; 5 state tests | PASS |
| AC#8 — both-or-nothing | KanbanBoard.tsx:49–50 throws on !ok; Promise.all atomic; 8 partial-failure tests | PASS |
| AC#9 — 25 RED tests pass | Quality-runner: 36 frontend tests passed (25+11), 0 failed | PASS |

### Test Results

- Vitest (frontend): 36 passed, 0 failed
- Full suite (quality-runner): 593 passed, 6 failed — all failures in serve/mcp-knowledge/tests/ (pre-existing, unrelated to #933)
- ruff: clean

### Architect Quality: 4/5

Specific, testable AC with clear data-testid contracts. Good refinement: removed 2 out-of-scope items, fixed 3 factual errors, added both-or-nothing constraint, separated visual guidance from testable AC. Minor gap: AC#4 left-border had no RED test from #931 (caught by reviewer in cycle 1, filled by builder-discovered tests). Follow-up tasks (#958, #959, #960, #961, #962) properly scoped.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 9 PASS)
- Lint violations: 0 (ruff clean, tsc clean)
- AC quality ≤ 3: 0 (score 4/5)
- Missing reviewer evidence: 0 (detailed, two-cycle review)
- Full-suite failures in task scope: 0 (6 failures all in mcp-knowledge)

### Confidence: .98

### Action: archive
