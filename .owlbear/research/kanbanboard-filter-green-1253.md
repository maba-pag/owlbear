# KanbanBoard Filter Integration — GREEN Phase

> **Owning task:** #1253 — P3-02: GREEN — KanbanBoard filter state and layout integration
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1253 is the GREEN TDD phase for KanbanBoard filter integration. The RED tests (#1252, 10 tests in `KanbanBoard_1252.test.tsx`) are confirmed failing. The question: what changes to `KanbanBoard.tsx` (and optionally `Column.tsx`) are needed to make all 10 tests pass, and are there any risks?

## 2. Sources Studied

| Source | Relevance | Notes |
|--------|-----------|-------|
| `src/KanbanBoard.tsx` (current, 280 lines) | 1.0 | No filter state, no FilterPanel import, horizontal flex layout |
| `src/__tests__/KanbanBoard_1252.test.tsx` | 1.0 | 10 RED tests, all fail on missing `filter-toggle` testid |
| `src/utils/filterTasks.ts` | 1.0 | Pure function + `FilterState` type — complete, tested |
| `src/components/FilterPanel.tsx` | 1.0 | Controlled component — complete, tested |
| `src/components/Column.tsx` | 0.8 | Hardcoded `calc(100vh - 56px)` — needs flex-based replacement |
| Brief `draft-filter-search-ux/brief.md` | 1.0 | Architecture, layout spec, interaction rules |
| Research `kanbanboard-filter-integration-red-1252.md` | 0.9 | RED phase strategy, mock pattern, selector conventions |

## 3. Analysis

### Implementation Checklist (mapped to AC)

| AC | Change | File | Risk |
|----|--------|------|------|
| useState for FilterState + panelOpen | Add 2 state hooks | KanbanBoard.tsx | None — straightforward |
| Derived filteredTasks | `filterTasks(tasks, filter)` before `tasksByStatus` | KanbanBoard.tsx | None — pure function, tested |
| Derived availableTags | `Array.from(new Set(tasks.flatMap(t => t.tags)))` from full set | KanbanBoard.tsx | Edge: tasks with undefined tags — `flatMap` needs guard |
| Filter toggle button | `<button data-testid="filter-toggle">` | KanbanBoard.tsx | None |
| Active filter count badge | Compute from 4 dimensions | KanbanBoard.tsx | None |
| Result count | `<span data-testid="filter-result-count">` when active | KanbanBoard.tsx | None |
| FilterPanel rendered | Import + wire props | KanbanBoard.tsx | None |
| Layout flex-column | Wrap existing columns in container div | KanbanBoard.tsx | Medium — Column.tsx hardcoded height |
| Filter dismisses context menu | `setContextMenu(null)` in filter change handler | KanbanBoard.tsx | None |
| Filter cancels drag | `setDragSource(null)` in filter change handler | KanbanBoard.tsx | None |

### Layout Refactor Detail

Current structure:
```
<div data-testid="kanban-board" style="display:flex; gap:16px; overflow-x:auto">
  <Column /> × N
  {moveError}
  {archivalModal}
  {contextMenu}
</div>
```

Target structure (from brief):
```
<div data-testid="kanban-board" style="display:flex; flex-direction:column; height:100%">
  <div> [toggle] [result-count] </div>
  <FilterPanel />
  <div style="display:flex; gap:16px; flex:1; overflow-x:auto; overflow-y:auto">
    <Column /> × N
  </div>
  {moveError}
  {archivalModal}
  {contextMenu}
</div>
```

**Column.tsx change:** Remove `maxHeight: 'calc(100vh - 56px)'` — parent flex container handles height. Tests don't assert Column height directly, so this is safe.

### Interaction Handler Pattern

The `onFilterChange` callback needs a wrapper to handle side effects:

```ts
const handleFilterChange = (newFilter: FilterState) => {
  setFilter(newFilter)
  setContextMenu(null)   // AC6
  setDragSource(null)    // AC7
}
```

Tests drive this via the captured `onFilterChange` mock prop.

### Risk: `availableTags` with undefined tags

`Task.tags` can be `string[] | undefined` per the `useBoard` type. The derivation `tasks.flatMap(t => t.tags)` would include `undefined` entries. Fix: `tasks.flatMap(t => t.tags ?? [])`.

### Confidence Assessment

| Dimension | Score | Notes |
|-----------|-------|-------|
| Test coverage | 1.0 | 10 RED tests cover all 8 AC lines |
| Implementation complexity | 0.95 | ~40 lines of additions, no new abstractions |
| Layout regression risk | 0.85 | Column height change could affect scroll — verify with existing tests |
| Overall | 0.90 | Straightforward GREEN; all building blocks exist and are tested |

## 4. Recommendation

**Proceed directly to implementation** (confidence: 0.90). This is a T1 (autonomous) GREEN task with:
- All dependencies met (filterTasks + FilterPanel complete and tested)
- Clear AC mapped to specific code changes
- Well-defined test contract (10 failing tests with precise selectors)
- Brief provides exact layout and interaction specs

The only non-trivial aspect is the flex-column layout refactor, which should be validated against existing KanbanBoard test suites after implementation.

Challenge: Skipped — T1 GREEN task with clear contract; no recommendation trade-offs to challenge.

## 5. Follow-up Tasks

None needed — #1253 is ready for the builder. Successor tasks (#1254–#1256) already exist in the decomposition chain.
