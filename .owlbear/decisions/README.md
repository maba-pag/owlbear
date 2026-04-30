# Decision Requests

Decision Request (DR) files capture user choices needed to continue blocked work.

- `pending/` stores unresolved DR files.
- `resolved/` stores DR files after a user response is processed.

## File Schema (5 fields)

Each DR file uses a 5-field YAML header.

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | integer | Kanban task ID the DR belongs to |
| `agent` | string | Agent requesting the decision |
| `request_type` | string | Request category (`decision` or `action`) |
| `created` | string | Creation timestamp (ISO-8601) |
| `response` | string | User response state (`pending`, `approved`, `needs-info`, `rejected`, `completed`) |

## For Users

### Primary path: Cockpit

Use Cockpit to resolve DRs whenever available. Cockpit is the primary interaction path and keeps task state updates aligned with board operations.

Phase 3 work (#1190) completes full Cockpit-first DR handling.

### Fallback path: Edit the file

If Cockpit is unavailable, resolve the DR by editing the file in `pending/`:

1. Open the DR file.
2. Update `response` to the intended state.
3. Save the file.

Common values:

- `approved`: accept the recommendation.
- `needs-info`: request clarification and add details in notes/body content.
- `rejected`: reject options and return for re-scope.
- `completed`: action request finished.

## Processing Semantics

After a non-`pending` response is detected:

- `approved` and `completed`: unblock task and move DR to `resolved/`.
- `needs-info`: keep task blocked and request follow-up context.
- `rejected`: unblock task and route for re-scoping.

## For Agents

Use the `h-decision-requests` skill as the source of truth for DR creation, formatting, and lifecycle behavior.
