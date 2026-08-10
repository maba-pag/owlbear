# Context — Filter/Search UX for Kanban Board (Task 1232)

_Phase 1 — Discovery snapshot. Updated at moment boundaries._

## Problem

With 1200+ tasks on the board, there is currently no way to find or focus on a subset.
All tasks are always rendered in every column. The user cannot filter by priority, tag,
blocked status, or search by text. No UX means to narrow the view.

## Existing Code — Verified

| Concern | Current state |
|---------|--------------|
| Data availability | All tasks fetched client-side in `useBoard` hook |
| Task shape | `{id, title, status, priority, updated, tags: string[], blocked, block_reason, claimed}` |
| Board render | `tasksByStatus = tasks.reduce(...)` → all tasks grouped → `<Column>` per status |
| No filter state | `KanbanBoard` has no filter-related state |
| No persistence | No localStorage or URL param usage |

## Project Type

`existing-feature/refactor` — pure frontend. No backend changes needed.

## Filter Dimensions (from task description)

- Priority (dropdown/chip: select one or more priorities)
- Tag (multi-select or chip group from available tags)
- Text search (title match, case-insensitive, client-side)
- Blocked status (toggle: show only blocked)

## M1/M2 — Confirmed Decisions (all locked)

- **Filter combinator**: AND across all dimensions
- **Tag filter**: Multi-select, AND (task must have ALL selected tags)
- **Priority filter**: Single-select dropdown (consistent — single-value field)
- **Blocked filter**: Toggle (show only blocked)
- **Text search**: Case-insensitive substring on title
- **Empty columns**: Keep visible with "0 tasks" placeholder
- **Persistence**: None — in-memory only
- **UI shape**: Expandable panel, toggle button with active-count badge ("Filter (2)")
- **Active filter display**: Badge on toggle button only (no chips row)
- **Filter panel location**: Inside `KanbanBoard` (above columns)

## Active Tensions → Resolved

1. **Tag AND vs OR**: Held AND — deliberate, consistent with other dimensions
2. **Filter chips vs badge**: Changed to badge only (simplifier accepted)
3. **Empty column show/hide**: Held visible (overrides simplifier Cut 3)
4. **Blocked view as wrong surface**: Noted as future follow-up (flat task list), not in scope

## Phase 1 Complete

Artifacts in this directory ready for `@ideation-mediator`.
