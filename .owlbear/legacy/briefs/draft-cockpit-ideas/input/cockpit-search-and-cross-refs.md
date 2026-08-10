# Cockpit Task Search and Cross-References

## Problem

Finding tasks by content requires manual scanning. `list_tasks` has a `search` parameter for text matching, but the cockpit UI doesn't expose it prominently. Cross-referencing (reverse dependencies, sibling tasks, related tasks) requires mental reconstruction.

## Proposed Features

### 1. Search bar in cockpit

- Prominent search input at the top of the board view
- Searches across: title, body text, tags, task ID
- Results displayed as a filtered board or a result list
- Debounced input — search as you type
- Backed by existing `list_tasks(search=...)` API parameter

### 2. Cross-reference / related tasks endpoint

A new endpoint: `GET /api/tasks/{id}/related` returning:

- **Dependents (reverse deps):** Tasks that have this task in their `depends_on` list — "who's waiting for me?"
- **Siblings:** Tasks sharing the same `parent` — "what else is in this feature?"
- **Same-tag peers:** Tasks with overlapping tags — "what's related?"
- **Body references:** Tasks that mention this task's ID (e.g., `#1234`) in their body text — "who references me?"

Response shape:
```json
{
  "dependents": [{"id": 1235, "title": "...", "status": "..."}],
  "siblings": [{"id": 1233, "title": "...", "status": "..."}],
  "same_tag": [{"id": 1240, "title": "...", "tags": ["cockpit"]}],
  "body_refs": [{"id": 1250, "title": "...", "snippet": "...see #1234..."}]
}
```

### 3. Cockpit task detail: related panel

When viewing a task detail, show a collapsible "Related" section:
- Dependents waiting on this task
- Sibling tasks (same parent)
- Other tasks referencing this one

### Backend

- Search: already supported by `list_tasks(search=...)`. May need to verify it searches body text, not just title.
- Cross-refs: new engine method `related_tasks(task_id)` that scans active tasks for reverse deps, same parent, body mentions. O(n) scan but fine for <100 active tasks.
- New cockpit route: `GET /api/tasks/{id}/related`

### Frontend

- Search bar component at top of board
- "Related" panel in task detail view
- Link from related task summaries to full task detail

### Scope

- Backend: one new engine method + one new API route
- Frontend: search bar + related panel
- No schema changes
