# FilterPanel RED Phase — Test Strategy

> **Owning task:** #1250 — P2-01: RED — FilterPanel component tests
> **Date:** 2026-05-01 **Status:** Complete

## 1. Context and Question

Task #1250 requires writing failing Vitest + Testing Library component tests for a `FilterPanel` controlled component. Research question: What component interface, test structure, and mock strategy best fit existing cockpit frontend patterns?

## 2. Sources Studied

| Source | Relevance | Notes |
|--------|-----------|-------|
| `src/utils/filterTasks.ts` (FilterState type) | 1.0 | Exact type shape from #1249: `{ text, priority, tags[], blocked }` |
| `src/__tests__/ArchivalModal_1241.test.tsx` | 0.9 | Form-control test pattern: select, input, button interactions via fireEvent |
| `src/__tests__/RepairPanel_1167.test.tsx` | 0.9 | Controlled component with mocked hook; renders in PDS provider |
| `src/__tests__/DRStatusIndicator_1191.test.tsx` | 0.8 | Callback-prop testing with `vi.fn()` and argument assertions |
| `vitest.setup.ts` | 0.7 | PDS jsdom polyfills, attachInternals mock — switch elements will work |
| `vite.config.ts` | 0.7 | globals: true, jsdom, setupFiles confirmed |

## 3. Analysis

### Component Interface (derived from AC)

```typescript
interface FilterPanelProps {
  open: boolean
  filterState: FilterState
  onFilterChange: (state: FilterState) => void
  availableTags: string[]
  activeCount: number
}
```

### Test File Placement

`src/__tests__/FilterPanel_1250.test.tsx` — follows `{Component}_{taskId}.test.tsx` convention.

### Test Coverage Matrix (from AC)

| AC Line | Tests | Approach |
|---------|-------|----------|
| Renders controls when open | 1 | Query for text input, select, multi-select, switch, reset button |
| Hides tag control when availableTags empty | 1 | Pass `availableTags=[]`, assert tag control absent |
| Reset button visible only when activeCount > 0 | 2 | activeCount=0 → absent; activeCount=1 → present |
| Reset clears all filter values | 1 | Click reset, assert `onFilterChange` called with empty state |
| Each control fires onFilterChange | 4 | Text input, priority select, tags select, blocked switch |
| No controls when open=false | 1 | `open={false}`, assert controls hidden or absent |

Total: ~10 test cases.

### Mock Strategy

No module mocks needed. FilterPanel is a presentational controlled component — all state lives in props. PDS components render real DOM in jsdom with existing polyfills. Use `data-testid` selectors (established pattern).

### Interaction Pattern

Use `fireEvent.change` for inputs/selects (established in ArchivalModal tests). Assert `onFilterChange` with `expect(fn).toHaveBeenCalledWith(expected)`.

## 4. Recommendation

Proceed with implementation (confidence: 0.90). T1 — trivial controlled-component test file following exact established patterns. No competing options.

Challenge: FALLBACK — trivial T1 task, no competing options to challenge.

## 5. Follow-up Tasks

None needed. #1251 (GREEN — FilterPanel implementation) already exists as the successor.
