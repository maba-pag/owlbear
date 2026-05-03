# KanbanBoard Filter Integration — RED Phase Test Strategy

> **Owning task:** #1252 — P3-01: RED — KanbanBoard filter integration tests
> **Date:** 2026-05-02 **Status:** Complete

## 1. Context and Question

Task #1252 requires writing failing Vitest + Testing Library integration tests for KanbanBoard filter wiring. The GREEN successor (#1253) will add `useState<FilterState>`, `filterTasks()` call, toggle button, result count, and interaction rules (dismiss context menu, cancel drag) on filter change. Tests must fail because KanbanBoard currently has no filter-related code.

Research question: What test structure, mock strategy, and selector conventions fit the existing KanbanBoard test patterns and the GREEN implementation plan?

## 2. Sources Studied

| Source | Relevance | Notes |
|--------|-----------|-------|
| `src/KanbanBoard.tsx` (current) | 1.0 | No filter state, no FilterPanel import, no toggle — all tests will fail |
| `src/__tests__/KanbanBoard_1229.test.tsx` | 0.9 | Drag-and-drop test: prop-driven board, ArchivalModal mocked, fireEvent.drag* |
| `src/__tests__/KanbanBoard_1246.test.tsx` | 0.9 | ArchivalModal intercept: captures callback props via mock, drives lifecycle |
| `src/__tests__/KanbanBoard.test.tsx` | 0.9 | Column/card selectors: `[data-column="X"]`, `[data-testid="task-card"]` |
| `src/components/FilterPanel.tsx` | 1.0 | Props: `filter, onFilterChange, priorities, availableTags, open` |
| `src/utils/filterTasks.ts` | 1.0 | `filterTasks(tasks, filter)` — pure function, already implemented |
| Task #1253 AC (GREEN successor) | 1.0 | Defines exactly what KanbanBoard will add: state, derivations, layout |

## 3. Analysis

### Test Plan (8 AC lines → 10 test cases)

| AC Line | Tests | Selector Strategy |
|---------|-------|-------------------|
| Board renders filter toggle button | 1 | `[data-testid="filter-toggle"]` |
| Toggle opens/closes FilterPanel | 2 | Click toggle → FilterPanel mock renders; click again → absent |
| Filter state → filtered columns | 2 | Trigger `onFilterChange` via mock capture → assert task cards by column |
| availableTags from full set | 1 | Assert FilterPanel mock receives all tags from ALL tasks |
| Result count "N / M tasks" | 1 | `[data-testid="filter-result-count"]` text content |
| Filter change dismisses context menu | 1 | Open context menu → trigger filter change → `[data-testid="context-menu"]` absent |
| Filter change cancels drag state | 1 | Start drag → trigger filter change → drop targets deactivated |
| Empty filter shows all tasks | 1 | Empty FilterState → all tasks visible in columns |

### Mock Strategy — FilterPanel

Follow the ArchivalModal mock pattern from `KanbanBoard_1246.test.tsx`:

```typescript
let capturedOnFilterChange: ((filter: FilterState) => void) | null = null

vi.mock('../components/FilterPanel', () => ({
  default: vi.fn(({ filter, onFilterChange, availableTags, open }) => {
    capturedOnFilterChange = onFilterChange
    if (!open) return null
    return (
      <div
        data-testid="filter-panel-stub"
        data-available-tags={JSON.stringify(availableTags)}
        data-filter={JSON.stringify(filter)}
      />
    )
  }),
}))
```

This captures `onFilterChange` so tests can programmatically trigger filter state changes and assert downstream effects (filtered tasks, dismissed menu, cleared drag).

### Testid Conventions (aligned with GREEN #1253 AC)

| Element | `data-testid` | Rationale |
|---------|---------------|-----------|
| Toggle button | `filter-toggle` | Button that opens/closes FilterPanel |
| Result count | `filter-result-count` | Shows "N / M tasks" when filter active |
| FilterPanel stub | `filter-panel-stub` | Mock renders this when open=true |
| Active filter badge | `filter-badge` | Badge on toggle showing active count |

### Why Tests Will Fail (RED)

1. No `[data-testid="filter-toggle"]` in current KanbanBoard → toggle queries return null
2. No FilterPanel import/render → mock never called → stub absent
3. No `filterTasks()` call → all tasks always in columns regardless of filter
4. No interaction rules → context menu / drag state unaffected by filter changes

### File Placement

`src/__tests__/KanbanBoard_1252.test.tsx` — follows `{Component}_{taskId}.test.tsx` convention.

## 4. Recommendation

Proceed with implementation (confidence: 0.92). This is a direct application of established test patterns (mock component, capture callbacks, assert state effects). No competing approaches — the only question was mock strategy, and the ArchivalModal pattern provides exact precedent.

Challenge: FALLBACK — T1 task following exact established patterns, no competing options.

## 5. Follow-up Tasks

None needed. #1253 (GREEN — implementation) already exists as the natural successor with `depends_on: [1252]`.
