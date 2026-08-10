# Brief — Filter/Search UX for Kanban Board

**Task:** 1232
**Tier:** Tool
**Type:** existing-feature/refactor — pure frontend

---

## Problem

The cockpit kanban board renders all 1200+ tasks with no filtering or search. Users cannot focus on a subset. All tasks are always visible in every column, making task discovery and board navigation impractical at scale.

## Scope

Client-side filtering of the existing task set inside `KanbanBoard.tsx`. No backend changes, no new endpoints, no persistence layer. Four filter dimensions applied with AND semantics.

**In scope:**
- Filter state management in KanbanBoard
- Pure filter function (`lib/filterTasks.ts`)
- FilterPanel component (controlled, expandable)
- Result count display
- PDS component integration (Select, MultiSelect, Switch)
- Accessibility contract (aria-live, focus management)
- Flexbox layout adaptation

**Out of scope:**
- URL parameter persistence
- localStorage persistence
- Backend/API changes
- Blocked task triage view (separate future feature)
- PDS version upgrade (task 1230)

---

## Architecture

### State

```ts
// In KanbanBoard.tsx
const [filter, setFilter] = useState<FilterState>({
  text: '',
  priority: '',
  tags: [],
  blocked: false,
})
const [panelOpen, setPanelOpen] = useState(false)
```

Board owns both `filter` and `panelOpen`. No custom hook.

### Filter Logic

Single pure function in `lib/filterTasks.ts`:

```ts
interface FilterState {
  text: string        // '' = no filter; substring match on title, case-insensitive
  priority: string    // '' = no filter; exact match on task.priority
  tags: string[]      // [] = no filter; AND — task must have ALL selected tags
  blocked: boolean    // false = no filter; true = task.blocked must be true
}

function filterTasks(tasks: Task[], filter: FilterState): Task[] {
  return tasks.filter(task => {
    if (filter.text && !task.title.toLowerCase().includes(filter.text.toLowerCase())) return false
    if (filter.priority && task.priority !== filter.priority) return false
    if (filter.tags.length > 0 && !filter.tags.every(t => task.tags.includes(t))) return false
    if (filter.blocked && !task.blocked) return false
    return true
  })
}
```

Exported for direct unit testing. No React dependency.

### Derived Data

```ts
const filteredTasks = filterTasks(tasks, filter)
const availableTags = Array.from(new Set(tasks.flatMap(t => t.tags)))
const activeCount = [
  filter.text !== '',
  filter.priority !== '',
  filter.tags.length > 0,
  filter.blocked,
].filter(Boolean).length
```

- `availableTags` derived from **full** task set (not filtered) — prevents AND-filter dead-ends
- React Compiler handles memoization — no manual `useMemo`
- If `availableTags` is empty, hide the tag filter control entirely

### Component Structure

```
KanbanBoard.tsx (orchestrator)
├── Filter toggle button + result count
├── FilterPanel (controlled)
│   ├── Text input (PDS text field or plain input)
│   ├── PDS Select (priority, single-select)
│   ├── PDS MultiSelect (tags, type-to-filter)
│   ├── PDS Switch (blocked toggle)
│   └── Reset button (visible when activeCount > 0)
├── Columns container (flex: 1, overflow-y: auto)
│   └── Column × N (unchanged)
└── Context menu overlay (unchanged)
```

`FilterPanel` props:

```ts
interface FilterPanelProps {
  filter: FilterState
  onFilterChange: (filter: FilterState) => void
  priorities: string[]
  availableTags: string[]
  open: boolean
}
```

### Layout

Replace the board root's horizontal-only flex with a vertical flex-column:

```
┌─────────────────────────────────────────────┐
│ [Filter (2)]  142 / 1,247 tasks             │  ← toggle + result count
├─────────────────────────────────────────────┤
│ [text____] [priority ▾] [tags ▾▾] [□ blocked] [Reset] │  ← FilterPanel (horizontal, 1-2 rows)
├─────────────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ...    │  ← columns container (flex:1, overflow)
│ │ col1 │ │ col2 │ │ col3 │ │ col4 │        │
│ └──────┘ └──────┘ └──────┘ └──────┘        │
└─────────────────────────────────────────────┘
```

The columns container gets `flex: 1` + `overflow-x: auto` + `overflow-y: auto`. Replace any hardcoded `calc(100vh - ...)` heights in Column with flex-based sizing.

---

## UI Specification

### Toggle Button

- Label: "Filter" when `activeCount === 0`; "Filter (N)" when N > 0
- Position: Above the columns, left-aligned
- Uses PDS button (secondary variant)

### Result Count

- Text: `"{filteredTasks.length} / {tasks.length} tasks"`
- Visible only when `activeCount > 0`
- Adjacent to toggle button (same row, right of button)

### Filter Panel

- Visible when `panelOpen === true`
- Horizontal layout: controls in one or two rows (flexbox wrap)
- Controls:
  - **Text search**: Input with placeholder "Search by title…"
  - **Priority**: PDS Select populated from `board.priorities`; empty option = "All priorities"
  - **Tags**: PDS MultiSelect populated from `availableTags`; hidden when `availableTags.length === 0`
  - **Blocked**: PDS Switch with label "Show only blocked tasks"
  - **Reset**: Button labeled "Clear all"; visible when `activeCount > 0`

### Empty State

When all columns are empty after filtering: columns remain visible with existing "No tasks" placeholder. Result count shows "0 / 1,247 tasks" — sufficient signal that filters are active.

---

## Interaction Rules

| Event | Behavior |
|-------|----------|
| Toggle button click | Toggle `panelOpen` |
| Any filter control change | Update `filter` state immediately; board re-renders with new `filteredTasks` |
| Reset button click | `setFilter({ text: '', priority: '', tags: [], blocked: false })` |
| Filter change while dragging | Clear `dragSourceStatus` (cancels board-side drop logic) |
| Filter change while context menu open | Dismiss context menu (`setContextMenu(null)`) |
| Polling refresh changes task data | Derived values recompute automatically; filter state unchanged |
| Selected tag vanishes from task set | Filter stays active; user sees 0-result state and clears manually |

---

## Accessibility Contract

| Requirement | Implementation |
|-------------|---------------|
| Toggle button | `aria-expanded={panelOpen}`, `aria-controls="filter-panel"` |
| Filter panel | `id="filter-panel"`, `role="region"`, `aria-label="Task filters"` |
| Result count | `aria-live="polite"` — announces on **user-initiated** filter changes only (not polling) |
| Debounce | aria-live announcement fires 300ms after last keystroke in text field |
| Focus on expand | First control in panel receives focus |
| Focus on collapse | Toggle button receives focus |
| Labels | Explicit: "Search tasks by title", "Filter by priority", "Filter by tags", "Show only blocked tasks" |

---

## Testing Strategy

### Unit — `filterTasks`

- Each dimension filters correctly in isolation
- AND combination across multiple dimensions
- Empty filter returns all tasks
- Case-insensitive text search
- Tag AND semantics (partial match fails)
- Edge: empty tags array on task vs selected tag filter

### Component — FilterPanel

- Renders all controls when open
- Hides tag control when `availableTags` is empty
- Reset button visible only when `activeCount > 0`
- Reset clears all filter values
- Calls `onFilterChange` on each control interaction

### Integration — KanbanBoard with filters

- Filtered tasks appear in correct columns
- Empty columns show placeholder
- Result count updates
- Toggle button badge reflects active count
- Filter change dismisses context menu
- Filter change cancels drag state
- Accessibility attributes present and correct

---

## Implementation Sequence

1. **`lib/filterTasks.ts`** — pure function + types + unit tests
2. **`FilterPanel.tsx`** — controlled component + component tests
3. **KanbanBoard integration** — state, derived data, layout refactor, panel wiring
4. **Accessibility** — aria attributes, focus management, aria-live
5. **Integration tests** — full board flow with filters

---

## Dependencies

- Task 1225 (KanbanBoard split) — **complete** ✓
- Task 1230 (PDS migration) — **not blocking**; filter uses PDS 3.34 components directly
- No backend dependencies

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| PDS MultiSelect API differs from expected | Low | Fallback to custom chip-toggle group |
| Column height regression from layout refactor | Medium | Integration test verifies columns render at expected height |
| 1200-task filter perf on low-end devices | Low | Pure `.filter()` on flat array is O(n); React Compiler prevents unnecessary re-renders |
