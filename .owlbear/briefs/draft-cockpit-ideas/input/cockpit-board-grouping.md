# Cockpit Board Grouping and Filtering

## Problem

With 20+ active tasks, the flat list per status column becomes hard to scan. There's no way to answer "what's left for this feature?" or "show me only frontend tasks" without mentally filtering the board. The data for grouping is already in the API (tags, parent, depends_on) but the UI doesn't expose it.

## Proposed Feature

Add grouping and filtering capabilities to the cockpit board view.

### Filtering

- **By tag:** Multi-select tag filter. Show only tasks matching selected tags. Tag list derived from all active tasks.
- **By priority:** Filter to show only critical/important/etc tasks.
- **By blocked status:** Toggle to hide/show blocked tasks.
- Filter controls at the top of the board. Filters are URL-persistent (query params) so they survive refresh and can be shared/bookmarked.

### Grouping

Two modes beyond the default flat list:

1. **Group by parent:** Tasks sharing a `parent` ID are visually grouped together under a parent header. Shows the parent task's title as the group label. Orphan tasks (no parent) appear in an "Ungrouped" section.

2. **Group by dependency chain:** Tasks connected via `depends_on` are shown as a tree/chain. This reveals the execution order: "do A, then B and C (which both depend on A), then D (depends on B+C)." Most useful for planning and identifying bottlenecks in a feature's task graph.

### Visual approach (to be designed)

- Grouping within columns: tasks in the same group get a subtle visual container (border, background shade, group header)
- Collapsible groups: click group header to collapse/expand
- Alternatively: groups as horizontal rows across all columns (swimlane pattern) — TBD based on how it looks with real data
- Dependency chain view might work better as a separate "tree view" mode rather than modifying the column layout

### Backend changes

Likely none — `GET /api/tasks` already returns `tags`, `parent`, `depends_on` for all tasks. Grouping logic lives in the frontend.

Possible: a new `GET /api/tasks/tree` endpoint that returns tasks pre-organized by parent or dependency chain, to avoid the frontend doing the graph traversal. But the frontend can do this client-side for reasonable board sizes.

### Scope

- Frontend: grouping selector (dropdown: "flat / by parent / by deps"), tag filter bar, visual containers for groups
- No backend changes for v1
- No schema changes

### Extensions

- Saved filter presets ("My frontend view")
- Dependency chain visualization as a DAG diagram (Excalidraw-style?)
- Group progress indicator (3/8 tasks done in this group)
- Collapse-all / expand-all for groups
