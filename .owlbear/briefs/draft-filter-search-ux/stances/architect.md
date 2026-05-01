# Architectural Stance — Filter/Search UX (Task 1232)

## Architectural Stance

**No custom hook. One `useState`, one pure function, one extracted component.** The filter feature slots into KanbanBoard with minimal structural change: a `FilterState` useState, a call to a pure `filterTasks()` function before the existing reduce, and a controlled `FilterPanel` component rendered above the columns.

## Structural Reasoning

### 1. State Placement — Inline in KanbanBoard

Filter state belongs in `KanbanBoard` as a fourth `useState`:

```ts
const [filter, setFilter] = useState<FilterState>({ text: '', priority: '', tags: [], blocked: false })
```

**Why not a custom hook?** The filter state has no lifecycle logic, no effects, no subscriptions. It's a single state atom with a setter. Wrapping it in `useFilterState()` adds a file and an import for zero encapsulation benefit — the hook would still need `tasks` passed in to return derived data, making it a function pretending to be a hook. YAGNI.

### 2. Pure Filter Function — `lib/filterTasks.ts`

```ts
export function filterTasks(tasks: Task[], filter: FilterState): Task[] {
  return tasks.filter(task => {
    if (filter.text && !task.title.toLowerCase().includes(filter.text.toLowerCase())) return false
    if (filter.priority && task.priority !== filter.priority) return false
    if (filter.tags.length > 0 && !filter.tags.every(t => task.tags.includes(t))) return false
    if (filter.blocked && !task.blocked) return false
    return true
  })
}
```

This is the **single authority** for filter semantics. Unit-testable without React. The hook/component boundary is not needed here because there's no React-specific behavior — it's a predicate over data.

### 3. Component Extraction — `FilterPanel.tsx`

Controlled component. Does NOT own filter state.

```ts
interface FilterPanelProps {
  filter: FilterState
  onChange: (filter: FilterState) => void
  availableTags: string[]
  priorities: string[]
  activeCount: number
}
```

The panel owns only its **expand/collapse** UI state internally. Everything else flows through props. This keeps the panel testable in isolation (render with props, assert UI) without coupling it to the board's data-fetching or polling logic.

### 4. Layout Integration — Explicit Height Contract

The current board root is the horizontal flex scroller:
```tsx
<div data-testid="kanban-board" style={{ display: 'flex', gap: '16px', overflowX: 'auto' }}>
```

This changes to a **vertical flex container** that stacks the panel above the columns:

```tsx
<div data-testid="kanban-board" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
  <FilterPanel ... />
  <div style={{ display: 'flex', gap: '16px', overflowX: 'auto', flex: 1 }}>
    {columns}
  </div>
  {moveError overlay}
  {contextMenu overlay}
</div>
```

Column `maxHeight: calc(100vh - 56px)` must be updated to account for the filter panel height. Use a CSS custom property or fixed known height (collapsed: ~40px, expanded: ~120px).

### 5. Derived Data — Inline Computation

```ts
const filteredTasks = filterTasks(tasks, filter)
const availableTags = Array.from(new Set(tasks.flatMap(t => t.tags))).sort()
const activeCount = [filter.text !== '', filter.priority !== '', filter.tags.length > 0, filter.blocked].filter(Boolean).length
const tasksByStatus = filteredTasks.reduce<Record<string, Task[]>>(...)
```

**No manual `useMemo`.** React Compiler auto-memoizes these expressions when their inputs (`tasks`, `filter`) are unchanged between renders. When `filter.text` changes on keystroke, `filterTasks` re-runs — 1200 items × string `.includes()` is ~0.1ms, well under frame budget.

`availableTags` is derived from the **full unfiltered** `tasks` array, not the filtered set. This prevents AND-filtered tags from disappearing from the selector (dead-end UX).

### 6. Edge Case Behaviors

| Event | Rule |
|-------|------|
| Filter changes during active drag | Clear `dragSourceStatus` → cancel drag. Prevents orphaned drag state pointing at a now-hidden card. |
| Filter changes with open context menu | Dismiss context menu (`setContextMenu(null)`). Simpler than checking if the specific card is still visible. |
| All tasks filtered out in a column | Existing "No tasks" empty-column placeholder renders. No change needed. |
| Filter active + polling refetch | Filter re-applies to new task data automatically (derived inline). No stale-filter bug. |

Implementation: a single `useEffect` watching `filter` that calls `setContextMenu(null)` and `setDragSourceStatus(null)` when filter state changes.

### 7. Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | `filterTasks()` predicate logic | Import function, test all dimension combos, AND semantics, edge cases (empty filter = passthrough) |
| Component | `FilterPanel` interactions | RTL: render with props, toggle expand, change inputs, verify `onChange` calls |
| Integration | Full filter flow in KanbanBoard | RTL: render board with mock tasks, interact with filter panel, assert column counts change |

## Key Trade-offs

| Choice | Gains | Costs |
|--------|-------|-------|
| No custom hook | Less indirection, one fewer file, state is obvious | Filter logic slightly increases KanbanBoard length (~8 lines) |
| Pure function in `lib/` | Testable without React, single authority for semantics | One import; function must stay in sync with `FilterState` type |
| Controlled FilterPanel | Testable, reusable, clear data flow | Two props (filter + onChange) thread through KanbanBoard |
| Tags from full task set | No dead-end UX, tag list is stable | Tag list includes tags only on hidden tasks (acceptable) |
| Cancel drag on filter change | Prevents impossible state | Rare UX interruption (user filtering mid-drag is unlikely) |

## Warnings

1. **Column height contract is fragile.** The `calc(100vh - 56px)` in Column.tsx is a hardcoded viewport assumption. Adding the filter panel breaks it unless updated. This should be addressed with a CSS variable or a layout that doesn't depend on magic numbers.

2. **Text input at 5000+ tasks.** Current approach is fine at 1200. If the task count grows 4×, consider debouncing text input (150ms). Do NOT pre-optimize now — add it when measurable.

3. **PDS component availability.** The brief mentions PDS 3.34.0 migration (task 1230). If PDS provides filter/chip components, use them for the panel internals. If not, plain controlled inputs. The component boundary (`FilterPanel` props interface) is stable either way.

## Confidence

**0.80** — Strong structural position. Layout integration is the riskiest piece (CSS contract), but the component boundaries and data flow are clean. No over-engineering, testable at every layer.
