# Research Notes — Filter/Search UX (Task 1232)

_Phase 1 output for mediator. Verified findings, implications, and open questions._

---

## Verified Findings

### V1 — All data is client-side

`useBoard` fetches all tasks via `GET /api/tasks` and stores them in `tasks: Task[]`
state. Polling keeps them fresh (mtime-based). Filtering is client-side: filter `tasks`
before the `tasksByStatus = tasks.reduce(...)` grouping. No round-trips needed.

### V2 — Task wire shape supports all filter dimensions

```ts
interface Task {
  id: number
  title: string
  status: string
  priority: string       // single value — single-select filter
  updated: string
  tags: string[]         // multi-value — multi-select filter
  blocked: boolean       // boolean — toggle filter
  block_reason: string | null
  claimed: boolean
}
```

All four filter dimensions (`text`, `priority`, `tags`, `blocked`) are present in the
client-side `Task` shape. No API changes needed. (First-principles challenge #3
about `blocked` is already satisfied by the existing wire shape.)

### V3 — `/api/tasks` already has server-side filter params

`GET /api/tasks` accepts `?status=`, `?priority=`, `?tag=`, `?blocked=`. These are not
used by `useBoard` (fetches all). This is informational: server-side filtering is
available for future non-board consumers (agents, tooling). For the board, client-side
is correct.

### V4 — Board response has `priorities` but no tag enumeration

`BoardOut.priorities: list[str]` — already available for the priority dropdown.
Available tags must be derived client-side: `Array.from(new Set(tasks.flatMap(t => t.tags)))`.
If no tags exist in the task set, the tag filter control should be hidden.

### V5 — Existing modal pattern: `ResolveModal.tsx`

The codebase has an established modal + form pattern (`ResolveModal`). No direct
precedent for filter panels or collapsible controls. PDS components should be used
where available (PDS 3.34.0 in scope — see task 1230 PDS migration).

### V6 — Current `KanbanBoard` render loop

```ts
const tasksByStatus = tasks.reduce<Record<string, Task[]>>((acc, task) => {
  if (!acc[task.status]) acc[task.status] = []
  acc[task.status].push(task)
  return acc
}, {})
```

Filter state filters `tasks` before this reduce. The rest of the render is unchanged.
Empty columns already render ("0 tasks" placeholder confirmed in existing tests:
`data-testid="empty-column"`).

---

## Confirmed Design (post M1 + M2 + challenger pass)

### Filter State Shape

```ts
interface FilterState {
  text: string          // substring match on task.title, case-insensitive
  priority: string      // '' = no filter; else task.priority === priority
  tags: string[]        // [] = no filter; else task.tags includes ALL selected tags (AND)
  blocked: boolean      // false = no filter; true = task.blocked must be true
}
```

Active filter count = number of dimensions with non-default values (text ≠ '', priority ≠ '', tags.length > 0, blocked === true).

### Filter Logic

```ts
const filteredTasks = tasks.filter(task => {
  if (filter.text && !task.title.toLowerCase().includes(filter.text.toLowerCase())) return false
  if (filter.priority && task.priority !== filter.priority) return false
  if (filter.tags.length > 0 && !filter.tags.every(t => task.tags.includes(t))) return false
  if (filter.blocked && !task.blocked) return false
  return true
})
```

### UI Components

| Control | Type | Data source |
|---------|------|-------------|
| Toggle button | PDS button | Active count from FilterState |
| Text search | `<input type="text">` or PDS text field | User input |
| Priority | Single-select PDS Select | `board.priorities` |
| Tags | Multi-select (custom or PDS) | Derived: `new Set(tasks.flatMap(t => t.tags))` |
| Blocked | PDS Switch or checkbox | Static boolean |

### Active Filter Display

Badge on the toggle button: "Filter" when count=0; "Filter (2)" when 2 dimensions active. No chips row.

### Empty Columns

Kept visible with existing `data-testid="empty-column"` placeholder. No change to column rendering.

---

## Candidate Implications

### I1 — Filter panel is a new collapsible component

There is no existing collapsible/expandable component in the codebase. Options:
- HTML `<details>/<summary>` (accessible, no JS) — but styling limited
- `useState(panelOpen)` + conditional render (`panelOpen && <div>...</div>`) — simple
- PDS accordion component if available in PDS 3.34.0

### I2 — Tag multi-select with no PDS precedent

PDS 3.34.0 may or may not have a native multi-select. If not, a custom chip-based tag
selector (click to toggle, selected = highlighted) is the fallback. Should be derived
from existing task data and hidden when no tags are present.

### I3 — Task 1225 dependency (KanbanBoard split)

Task 1225 (split KanbanBoard into Card + Column + Board) is in-progress. The filter
bar naturally belongs to the Board component (i.e., the top-level orchestrator). If
1232 lands before 1225 completes, filters go into `KanbanBoard.tsx`. If 1225 lands
first, they go into the new Board component. Mediator should note this dependency.

### I4 — "blocked view" as a future flat-list enhancement (not this task)

First-principles correctly observes that blocking status shown across 8 sparse columns
is not an ideal view. A flat task list filtered to `blocked: true` would be more
useful. This is a separate surface — not in scope for 1232, but worth noting as a
follow-up task (blocked task list view / triage view).

---

## Open Research Questions (for mediator)

### Q1 — PDS multi-select availability

Does PDS 3.34.0 have a native multi-select or chip-group component? If yes, use it.
If no, define fallback approach for tag multi-select (custom chip toggle group).

### Q2 — Filter panel: `<details>` vs `useState`

Should the expandable panel use `<details>/<summary>` (CSS-only, accessible, but
less control over animation) or `useState` + conditional render (more control, standard
pattern in this codebase)?

### Q3 — Filter clear-all button

When filters are active, should there be a "clear all" button (reset all to defaults)
or is per-dimension reset sufficient (user can reopen panel and manually clear)?

### Q4 — Task 1225 sequencing

Can 1232 be developed independently of 1225, or should it wait? The filter bar is
logically part of the Board-level component that 1225 is creating. Landing 1232 first
means an extra refactor when 1225 lands.

---

## Implementation Shape

**`KanbanBoard.tsx` (or future `Board.tsx` from task 1225):**
1. Add `const [filter, setFilter] = useState<FilterState>({text: '', priority: '', tags: [], blocked: false})`
2. Add `const [filterPanelOpen, setFilterPanelOpen] = useState(false)`
3. Derive `filteredTasks = tasks.filter(...)`
4. Derive `availableTags = Array.from(new Set(tasks.flatMap(t => t.tags)))`
5. Render filter toggle button with active-count badge
6. Conditionally render filter panel with controls
7. Pass `filteredTasks` (not `tasks`) to `tasksByStatus` reduce

**No backend changes. No new endpoints. No new hooks.**
