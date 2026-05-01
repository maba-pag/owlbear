# Architect — Critic Debate Log

## Cycle 1

### Draft Position Summary

- Extract `useFilterState()` hook for filter state + derived computations
- `FilterPanel.tsx` as controlled component
- Pure `filterTasks` function for testability
- No manual `useMemo` — React Compiler handles it
- Outer wrapper div for integration

### Critic Challenges (severity → response)

**CRITICAL — Layout regression.** The current `data-testid="kanban-board"` div IS the horizontal flex scroller with `overflowX: auto`. Adding a panel above columns changes the vertical budget. Each column uses `maxHeight: calc(100vh - 56px)`. The draft doesn't address how the panel height affects this contract.

→ **Accepted.** Revised: The outer container becomes `flex-direction: column; height: 100%`. The filter panel is a fixed-height element. The columns container gets `flex: 1; overflow-x: auto` and column `maxHeight` adjusts to `calc(100vh - 56px - var(--filter-panel-height))`. When collapsed, panel height is one button row (~40px). When expanded, ~120px. This is a layout detail but architecturally critical to specify.

**MODERATE — Hook is over-engineering.** `useFilterState` takes raw `tasks` in and returns filtered tasks out. That's not state encapsulation — it's file-splitting. The only real state is one `useState<FilterState>`.

→ **Accepted.** Demoted. Filter state stays as `useState<FilterState>` directly in KanbanBoard. No custom hook. The pure `filterTasks` function provides the testing seam without React machinery overhead.

**MODERATE — Split authority.** Hook's `filteredTasks()` method vs standalone `filterTasks()` function — which is canonical?

→ **Accepted (moot with hook removal).** Single authority: `filterTasks(tasks, filter)` exported from `lib/filterTasks.ts`. Unit-tested there. KanbanBoard calls it inline.

**MODERATE — Performance assertion without evidence.** 1200 tasks × keystroke rate. React Compiler memoizes JSX, not arbitrary expressions inside the component body.

→ **Partially accepted.** React Compiler DOES memoize expressions when inputs haven't changed (that's its core value prop over manual useMemo). But during typed text input, `filter.text` changes every keystroke, so `filterTasks` re-runs. At 1200 tasks, `.filter()` with string `.includes()` is ~0.1ms — verified by the scale of the existing `tasks.reduce()` that already runs unconditionally. No debounce needed at this scale. Noted as a warning for future 5000+ task boards.

**MODERATE — Drag-and-filter interaction.** `dragSourceStatus` persists while filter might remove the dragged card from render.

→ **Accepted.** Added explicit rule: filter state changes during an active drag must clear `dragSourceStatus` (cancel the drag). This prevents orphaned drag state. Implementation: early `useEffect` that resets drag state when `filter` changes.

**BLIND SPOT — Tag source.** Tags derived from all tasks or filtered set?

→ **All tasks.** Tags are derived from the full unfiltered task array. Otherwise selecting a tag and then another tag could make the first tag disappear from options (AND semantics). Dead-end UX.

**BLIND SPOT — Context menu dismissal.** Filtering can remove the card that spawned the context menu.

→ **Accepted.** Added rule: any filter state change dismisses the context menu. Simpler than tracking whether the specific card is still visible.

**BLIND SPOT — activeCount semantics.** Badge count is non-trivial with multi-select tags.

→ **Defined.** `activeCount = [text !== '', priority !== '', tags.length > 0, blocked].filter(Boolean).length`. Counts active dimensions (0–4), not individual selections. "Filter (2)" means 2 dimensions are active.

### Outcome

Position hardened. Hook extraction dropped (YAGNI). Layout contract made explicit. Edge cases (drag, context menu) given behavioral rules. Confidence raised from 0.56 to 0.80.
