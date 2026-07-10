---
name: h-decision-requests
description: "Handbook: Decision request helper — create DR/AR records and follow lifecycle semantics"
user-invocable: false
---

# Decision/Action Requests Handbook

Use structured request tools when an agent needs a user decision or user action to unblock work.

Tool in scope for pipeline agents:

- `create_request`
- `list_requests`
- `show_request`

## When To Create A Structured Request

Create a structured request only when work is blocked on a user choice or user action that cannot be derived from:

- task AC
- existing project standards
- existing resolved request records

If `r-pipeline-protocol` Decision Tiers route you to a DR/AR, use `create_request`.

## MCP Tool Contracts

### `create_request`

Signature:

```text
create_request(
 task_id: str | int,
 kind: str,
 title: str,
 summary: str,
 agent: str,
 options: list[dict[str, object]] | None = None,
 body: str = "",
) -> dict[str, object]
```

Parameters:

- required: `task_id`, `kind`, `title`, `summary`, `agent`
- optional: `options`, `body`

Behavior:

- validates payload through structured models (`kind` routes to decision/action rules)
- creates a UUID4-backed request file in `decisions/pending/`
- sets owning task to blocked with `block_reason="DR pending"`
- returns full structured request payload, including `resolution` and `guidance`

Usage example:

```json
{
 "task_id": 1861,
 "kind": "decision",
 "title": "Choose rollout order",
 "summary": "Pick whether to land backend or frontend first.",
 "agent": "builder",
 "options": [
  {
   "option_id": "backend-first",
   "label": "Backend first",
   "confidence": 0.7,
   "recommended": true,
   "rationale": "Reduces API churn before UI work."
  },
  {
   "option_id": "frontend-first",
   "label": "Frontend first",
   "confidence": 0.45,
   "recommended": false,
   "rationale": "Can validate UX quickly but may require API rework."
  }
 ],
 "body": "Extended context and trade-offs."
}
```

### `list_requests`

Signature:

```text
list_requests(
 status: str = "pending",
 task_id: str | int | None = None,
) -> list[dict[str, object]]
```

Parameters:

- required: none
- optional: `status`, `task_id`

Behavior:

- `status` supports `pending`, `resolved`, or `all`
- optional `task_id` filters by owning task
- returns summaries only (`body` omitted)

Usage example:

```json
{
 "status": "pending",
 "task_id": 1861
}
```

### `show_request`

Signature:

```text
show_request(
 request_id: str,
) -> dict[str, object]
```

Parameters:

- required: `request_id` (UUID4)
- optional: none

Behavior:

- resolves request from either `decisions/pending/` or `decisions/resolved/`
- returns full structured payload, including `body` and `resolution`

Usage example:

```json
{
 "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Data Model Fields

Structured request records contain these top-level fields:

- `request_id`: UUID4 string, canonical request identity
- `task_id`: integer owning task id
- `kind`: `decision` or `action`
- `title`: short heading (max 120 chars)
- `summary`: concise card-level summary
- `agent`: creating agent identifier
- `options`: array of option objects
- `resolution`: resolution object

Option object fields (`options[]`):

- `option_id`: slug (`^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$`, length 2-63)
- `label`: max 120 chars
- `confidence`: float in `[0.0, 1.0]`
- `recommended`: boolean
- `rationale`: max 500 chars

Resolution fields:

- `selected_option_id`: string or null
- `free_text`: string or null
- `resolved_at`: ISO datetime string or null

## Validation Rules

Model-level rules:

- all request models use `extra="forbid"`
- `request_id` must be UUID4
- `created_at` must be ISO 8601 with timezone

Kind-specific rules:

- `kind="decision"`: `options` required, minimum 2 and maximum 10 entries
- `kind="action"`: `options` must be empty (max length 0)
- at most one option may have `recommended=true`

Resolution constraints:

- request cannot resolve with both `selected_option_id=null` and `free_text=null`
- for action requests, `selected_option_id` must remain null
- for decision requests, non-null `selected_option_id` must match an existing `option_id`

## Lifecycle

### 1) Create (pending)

`create_request` writes a structured file to `decisions/pending/{request_id}.md` with frontmatter + markdown body and sets task blocked (`DR pending`).

### 2) Resolve (pending -> resolved)

Resolution is user/Cockpit driven (or sweep fallback), not MCP-tool driven.

- engine sets `resolution.resolved_at`
- engine writes `decisions/resolved/{request_id}.md` then removes `decisions/pending/{request_id}.md`
- request becomes visible via `list_requests(status="resolved")`

### 3) Write-back to task body

On resolution, engine appends a summary to task body:

- decision + selected option: `## DR: ...` with `Selected` and optional `Notes`
- decision + free-text only: `## DR: ...` with `Answer`
- action: `## AR: ...` with `Outcome`

### 4) Conditional unblock

Task unblocks only when no sibling structured pending requests remain for the same `task_id`.

## Agent Usage Pattern

1. Create request with `create_request` when blocked on a user choice/action.
2. End current work per pipeline routing (reject or block, depending on tier).
3. Later, consume the answer with `show_request` (structured `resolution`, no markdown scraping).

## Important Limits

- No MCP `resolve_request` tool is exposed. Resolution remains Cockpit/user mediated.
- Do not parse free-form task body text for decisions when a structured request exists; use `show_request`.
