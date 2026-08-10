# Cockpit Memory Tab

## Problem

The memory system (ob-memory MCP server) stores institutional knowledge for agents — 14 entries currently, going through a pending → curated → approved state machine. But it's completely invisible in the cockpit. The user can only interact via MCP tools or agent-driven curation prompts. There's no UI for browsing, reading, approving, editing, or deleting memory entries.

Memory without visibility is a black box. The user can't trust what agents "remember" if they can't see it.

## Proposed Feature

A "Memory" tab in the cockpit, peer to Board, Decisions, and Ideas tabs.

### Layout: List → Detail pattern

**List view:**
- All entries sorted by state (pending first → curated → approved → deleted)
- Each row shows: title, categories (as chips/badges), confidence (number or bar), state badge (color-coded), scope_agents list
- Filter controls: by state (multi-select), by category (multi-select), by scoped agent (dropdown)
- Search: text search across title and content

**Detail view (side panel or drill-in):**
- Full content (rendered markdown)
- All metadata fields: id, source_agent, scope_agents, categories, confidence, state, timestamps
- Action buttons based on state:
  - **Pending:** Approve (skip curate), Delete
  - **Curated:** Approve, Edit (opens inline edit form), Delete
  - **Approved:** Edit (downgrades to curated), Delete
  - **Deleted:** (read-only archive view, if shown at all)

### Backend

New routes in cockpit (backed by existing memory engine — same as MCP tools use):

| Route | Method | Maps to |
|-------|--------|---------|
| `/api/memories` | GET | `engine.get_entries()` with filters |
| `/api/memories/{id}` | GET | `engine.get_entry(id)` |
| `/api/memories/{id}/approve` | POST | `tools.approve_memory(id)` |
| `/api/memories/{id}` | PUT | `tools.curate_memory(id, ...)` |
| `/api/memories/{id}` | DELETE | `tools.delete_memory(id)` |

The cockpit backend would import the memory engine (or call the MCP tools internally). The memory engine is in `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` — it can be imported as a library if the cockpit adds it as a dependency, or proxied via internal HTTP calls.

### Frontend

- New route: `/memories` in React Router
- New navigation tab: "Memory" with pending count badge
- List component with filter bar (state, category, agent dropdowns)
- Detail panel with markdown rendering + metadata display
- Approve/Delete/Edit action buttons
- Edit form: title, content (textarea), categories (multi-select), confidence (slider 0.7–1.0), scope_agents (multi-select)

### State machine enforcement

The cockpit respects the same state machine as MCP tools:
- Approve: only `curated → approved`
- Edit: any state → `curated` (downgrade on edit)
- Delete: `pending` = hard delete, `curated/approved` = soft delete (state → deleted)

### Responsive behavior

- **Desktop:** List + detail side-by-side
- **Mobile:** List → detail navigation (tap to drill in)

### Scope

- Backend: ~5 new routes, ~100 lines
- Frontend: 1 new page component, list/detail subcomponents, filter bar
- Memory engine imported as dependency (no new service)
- No changes to MCP tools or memory schema

### Extensions

- Bulk approve/delete for curation batches
- Memory diff view (show what changed in a curate edit)
- Memory creation from cockpit (for user-authored entries)
- Link memories to tasks that produced them (if task_id is tracked)
- Memory statistics: count by state, by category, by agent, growth over time
