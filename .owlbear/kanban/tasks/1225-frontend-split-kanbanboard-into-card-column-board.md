---
id: 1225
title: Frontend — split KanbanBoard into Card + Column + Board
status: in-progress
priority: needed
created: 2026-04-30 16:31:18.609234+00:00
updated: 2026-04-30T22:24:33.012590+00:00
tags:
- cockpit
- frontend
- refactor
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Break the 270-line KanbanBoard.tsx monolith into focused component files.

## Acceptance Criteria
- [ ] `Card` component and `CardProps` interface extracted to `serve/cockpit/web/src/components/Card.tsx`; `PRIORITY_COLORS` constant co-located there as it is `Card`'s only consumer; `Task` type imported from `../hooks/useBoard` (td:1)
- [ ] `Column` component and `ColumnProps` interface extracted to `serve/cockpit/web/src/components/Column.tsx`; imports `Card` from `./Card` and `Task` from `../hooks/useBoard` (td:1)
- [ ] `KanbanBoard.tsx` retains default export and `export { useBoard }` re-export; imports `Card` and `Column` from `./components/Card` and `./components/Column` respectively; does NOT re-export `Card` or `Column` (no in-repo consumer imports them directly) (td:0)
- [ ] `Card.tsx` and `Column.tsx` do not introduce `React.memo()`, `useMemo()`, or `useCallback()` wrappers — React Compiler handles memoisation automatically per the constraint in `test_cockpit_react_compiler_1015.py` (td:1)
- [ ] All existing Vitest suites (`KanbanBoard.test.tsx`, `KanbanBoard_933.test.tsx`, `KanbanBoard_959.test.tsx`) pass without modification (td:0)
- [ ] All existing pytest suites that reference KanbanBoard source (`test_cockpit_react_compiler_1015.py`, `test_occ_frontend_wire_1137.py`) continue to pass without modification (td:0)
- [ ] `useBoard.test.ts` `import { useBoard } from '../KanbanBoard'` resolves without change — re-export preserved (td:0)
- [ ] No net change to rendered DOM — same `data-testid` attributes, event handlers, and inline styles (td:0)

## Files
- `serve/cockpit/web/src/KanbanBoard.tsx`
- `serve/cockpit/web/src/components/Card.tsx` (new)
- `serve/cockpit/web/src/components/Column.tsx` (new)

[[2026-04-30]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Card (render a task card), Column (render a status column), KanbanBoard (orchestration/state) — three clear concerns, each gets its own file |
| Interface clarity | PASS (after REFINE) | CardProps, ColumnProps, PRIORITY_COLORS placement, Task import paths, and useBoard re-export all now explicit in AC |
| Dependency correctness | PASS | No depends_on needed — this is a pure within-package refactor |
| Module layering | PASS | All three files remain in `serve/cockpit/web/src/`; components/ imports from hooks/useBoard (peer directory), no circular deps |
| TDD compliance | PASS | Existing Vitest suites provide full coverage of rendered output; React compiler pytest suite covers source-shape constraints; td:1 lines give the test-writer concrete smoke-test targets |
| KISS/YAGNI | PASS | Pure extraction, no new logic, no new abstractions; PRIORITY_COLORS stays with its only consumer |
| Premise challenge | PASS | components/ directory already contains 8 other components; Card and Column follow the same structural pattern; splitting is standard React project org |
| Pattern consistency | PASS | Matches existing component files (e.g. HealthBadge.tsx, DetailTab.tsx) — exported function + exported Props interface in same file |
| Security surface | N/A | Pure UI refactor, no new system boundaries |
| Single domain | PASS | Frontend only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Column imports Card | Broken relative import after move | TS compile error | Caught at build time | Build fails, no runtime impact |
| KanbanBoard imports Card/Column | Stale import path | TS compile error | Caught at build time | Build fails |
| useBoard re-export dropped | useBoard.test.ts breaks | Module not found | Covered by AC + existing test | CI red |

### Design Diverge
- Trigger: skipped — single clear extraction approach, no competing designs

### Challenger
- Outcome: `reconsider` (confidence 0.67)
- Key findings addressed:
  1. **React compiler source-shape gap** — AC now mandates Card.tsx and Column.tsx must not introduce React.memo/useMemo/useCallback (td:1)
  2. **Pytest scope omitted** — AC now lists both Vitest and pytest suites
  3. **Export surface ambiguity** — AC now explicit: Card/Column not re-exported from KanbanBoard.tsx, named exports available from their own files only
  4. **Task body authority** — AC refinement persisted before advancing

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Card extracted to components/Card.tsx with PRIORITY_COLORS and Task import | PASS | td:1 — test-writer writes import smoke test |
| Column extracted to components/Column.tsx, imports Card from ./Card | PASS | td:1 — test-writer writes import smoke test |
| KanbanBoard.tsx retains default + useBoard re-export, no Card/Column re-export | PASS | td:0 — mechanical, covered by existing useBoard.test.ts |
| Card.tsx and Column.tsx no memo wrappers | PASS | td:1 — test-writer can add source-shape assertion mirroring react-compiler test pattern |
| All existing Vitest suites pass without modification | PASS | td:0 — verification |
| All existing pytest suites pass without modification | PASS | td:0 — verification |
| useBoard import from KanbanBoard resolves | PASS | td:0 — covered by existing test |
| No net DOM change | PASS | td:0 — covered by existing Vitest render assertions |
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_kanban_board_split_1225.py
- Classes: TestFromAC_CardExtraction, TestFromAC_ColumnExtraction, TestFromAC_NoMemoWrappers
- Tests per category: happy 8, edge 0, error 0, boundary 0
- Total: 8 tests, all FAIL (AssertionError / FileNotFoundError — Card.tsx and Column.tsx absent)
- ruff: clean

### AC Coverage

| AC Line | td | Test(s) |
|---------|-----|---------|
| Card extracted to components/Card.tsx with PRIORITY_COLORS and Task import | 1 | test_card_tsx_exists, test_card_tsx_has_priority_colors, test_card_tsx_imports_task_from_useboard |
| Column extracted to components/Column.tsx, imports Card from ./Card and Task from ../hooks/useBoard | 1 | test_column_tsx_exists, test_column_tsx_imports_card_from_card, test_column_tsx_imports_task_from_useboard |
| KanbanBoard.tsx retains default + useBoard re-export, no Card/Column re-export | 0 | skipped |
| Card.tsx and Column.tsx no memo wrappers | 1 | test_card_tsx_no_memo_wrappers, test_column_tsx_no_memo_wrappers |
| All existing Vitest suites pass without modification | 0 | skipped |
| All existing pytest suites pass without modification | 0 | skipped |
| useBoard import from KanbanBoard resolves | 0 | skipped |
| No net DOM change | 0 | skipped |