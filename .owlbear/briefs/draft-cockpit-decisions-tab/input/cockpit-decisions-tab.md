# Cockpit Decisions Tab

## Problem

Decision requests (DRs/ARs) are currently shown as a popup or secondary view within the kanban tab. This limits their visibility and makes the resolution flow feel like an interruption rather than a first-class workflow. An audit noted the cockpit has only one tab (kanban) — DRs deserve equal standing.

## Proposed Feature

A dedicated "Decisions" tab in the cockpit top-level navigation, peer to the kanban board tab.

### Layout

**List → Detail pattern:**

1. **List view (left panel or initial view):** All DRs, pending first, then resolved. Shows: task ID, agent, request type (decision/action), title/preview, created date, status badge (pending/resolved).

2. **Detail view (main panel):** Selected DR's full body, response field, resolve button. On wider screens, show the associated task's summary alongside (title, status, AC, recent body excerpt). On mobile/narrow, just the DR.

### Backend changes

- Existing `GET /api/decisions/pending` may need expansion to include resolved DRs for the full list view
- Consider `GET /api/decisions` returning all (pending + resolved), with a `status` filter param
- Each DR response enriched with task summary: `{task_id, task_title, task_status, task_priority, task_ac}` (once AC is in frontmatter)
- `POST /api/decisions/{id}/resolve` already exists — no change needed

### Frontend changes

- New top-level route: `/decisions`
- Navigation entry alongside the kanban board tab
- List-detail responsive layout
- Pending count badge on the tab itself (like email unread count)
- Task context panel (conditional on viewport width)

### Responsive behavior

- **Desktop (>1024px):** Three-column: DR list | DR detail | Task context
- **Tablet (768-1024px):** Two-column: DR list | DR detail (task context collapsed/expandable)
- **Mobile (<768px):** Single column: list → detail (tap to navigate), task context as expandable section

### V1 scope

- Tab with list/detail views
- Pending/resolved filter
- Task title + status shown inline with DR
- Resolve form with freeform text response

### V2 extensions

- Quick response templates ("Approved", "Rejected", "Deferred")
- DR history per task (threaded view)
- Badge indicator on task cards in the kanban tab showing pending DR count
- DR creation from cockpit (for user-initiated questions to agents)
