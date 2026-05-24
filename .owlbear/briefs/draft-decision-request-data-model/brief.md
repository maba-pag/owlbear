# Brief — Structured Decision/Action Request Data Model

## Summary

Replace the unstructured markdown-body decision request system with a structured data model that flows through all four layers: storage (YAML frontmatter) → engine (Pydantic-validated API) → MCP tools → Cockpit (adapted resolver UI). The result is a real choice system where agents express structured intent, Cockpit renders adapted controls, and resolution flows back mechanically.

## Problem

Decision requests currently store options, recommendations, and question type in prose body text. Cockpit extracts titles via regex. Resolution is limited to approve/reject/needs-info. Agents read task bodies to find answers. Every consumer parses meaning from unstructured text.

## Promise

Working on a decision or action request in Cockpit feels like a real choice system: option cards for decisions, a "Complete" button for actions, free text always available, one click to submit. Resolution writes a summary to the task body and unblocks the task mechanically. Agents create well-formed requests via MCP and consume structured answers via `show_request`.

## Data Model

### Storage Format (YAML frontmatter + markdown body)

```yaml
---
request_id: "550e8400-e29b-41d4-a716-446655440000"
task_id: 1558
kind: decision
title: "Choose ownership model for knowledge source lifecycle"
summary: "Decide how lifecycle ownership works after contracts are repaired."
created_at: "2026-05-23T02:07:23+02:00"
agent: "copilot"
options:
  - option_id: "mcp-tools"
    label: "MCP tools own lifecycle"
    confidence: 0.62
    recommended: false
    rationale: "Fits agent workflows but hides state from Cockpit."
  - option_id: "hybrid"
    label: "Hybrid ownership"
    confidence: 0.74
    recommended: true
    rationale: "Balances automation with human oversight."
resolution:
  selected_option_id: null
  free_text: null
---

Extended context, evidence, and reasoning in markdown body.
```

### Field Definitions

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `request_id` | UUID4 string | yes | Canonical identity. Filename = `{request_id}.md` |
| `task_id` | int | yes | Parent task |
| `kind` | `decision` \| `action` | yes | Determines UI controls and validation rules |
| `title` | string | yes | Max ~120 chars, displayed as card heading |
| `summary` | string | yes | Card-level description |
| `created_at` | ISO 8601 with timezone | yes | Machine-set on creation |
| `agent` | string | yes | Creating agent identifier |
| `options` | list | decision: ≥2, max 10; action: absent/empty | Structured choices |
| `options[].option_id` | slug string | yes | `^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$`, max 63 |
| `options[].label` | string | yes | Max 120 chars |
| `options[].confidence` | float | yes | 0.0–1.0, independent (not sum-to-1) |
| `options[].recommended` | bool | yes | At most one `true` per request |
| `options[].rationale` | string | yes | Max 500 chars |
| `resolution.selected_option_id` | string \| null | no | Must match an `option_id` if set |
| `resolution.free_text` | string \| null | no | Custom answer, notes, or action outcome |
| `resolution.resolved_at` | ISO 8601 | no | Machine-set on resolution. Not present in pending files. |

### Lifecycle

Binary: file in `decisions/pending/` = not yet answered. File in `decisions/resolved/` = answered. No status enum. Resolution semantics derived from content:

- Decision + `selected_option_id` set = structured answer from menu
- Decision + `selected_option_id` null + `free_text` set = custom answer
- Action + `free_text` set = outcome report
- Any resolution with free_text like "need more context" = user asking for improvement (agent reads, creates new DR if needed)

### Validation Rules (Pydantic, `extra="forbid"`)

- `kind=decision` requires `options` with ≥2 items
- `kind=action` requires `options` absent or empty
- At most one `options[].recommended = true`
- `confidence` ∈ [0.0, 1.0]
- On resolution: if `selected_option_id` is set, must match an existing `option_id`
- Resolution detected by sweep: `selected_option_id != null` OR `free_text != null`
- `resolved_at` is added by the engine on resolution (not present in pending files)

## Engine API

### `create_request(task_id, kind, title, summary, agent, options?, body?)`

- Validates input via Pydantic model
- Generates UUID4 `request_id`
- Writes file atomically (`O_EXCL`) to `decisions/pending/{request_id}.md`
- Resolution block present with all-null values (self-documenting for manual edit)
- Sets `task.blocked = True` with `block_reason = "DR pending"`
- Returns the created request (full model)

### `resolve_request(request_id, selected_option_id?, free_text?)`

- Validates resolution against the request (option_id exists if provided)
- Sets `resolved_at` to current timestamp
- Renames file from `pending/` to `resolved/` (atomic move)
- Appends write-back summary to task body
- Conditionally unblocks task (only if no sibling pending requests remain for that task_id)

### `list_requests(status?, task_id?)`

- `status` filter: `pending` | `resolved` | `all` (default: `pending`)
- Optional `task_id` filter
- Returns list of request models

### `get_request(request_id)`

- Returns single request with full detail including resolution
- Searches both `pending/` and `resolved/` directories

### Sweep (fallback)

- Triggered on: `pick_tasks` call AND Cockpit workspace cleanup
- Scans `pending/` for files where `selected_option_id != null` OR `free_text != null`
- For each: sets `resolved_at`, processes normally (move + write-back + conditional unblock)
- Handles: manual file edits, crash recovery

## Write-back Format

Appended to task body on resolution:

```markdown
## DR: Choose ownership model
- **Selected:** Hybrid ownership
- **Notes:** Also ensure Cockpit shows source health.
```

For actions:
```markdown
## AR: Update test fixtures
- **Outcome:** Done, all fixtures updated.
```

For custom answers (no option selected):
```markdown
## DR: Choose ownership model
- **Answer:** Actually, let's defer this until the API stabilizes.
```

## MCP Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `create_request` | task_id, kind, title, summary, agent, options?, body? | Created request model |
| `list_requests` | status?, task_id? | List of request summaries |
| `show_request` | request_id | Full request detail + resolution |

No `resolve_request` MCP tool. Resolution is human-only via Cockpit.

**Gate conditions for future MCP resolve:** documented requirement for explicit user opt-in, rate limiting, and audit trail before unlocking agent-to-agent resolution.

## Cockpit API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/requests/pending` | GET | List pending requests with full structured data |
| `/api/requests/{id}/resolve` | POST | Submit resolution payload (`selected_option_id?`, `free_text?`) |

Cockpit imports engine functions directly (single-writer invariant: only engine writes DR files).

## Cockpit Frontend

### Decision Resolver
- Displays: title, summary, option cards (label + confidence bar + rationale + recommended badge)
- Controls: select an option OR type in free_text area, then submit
- Submit enabled when: option selected OR free_text non-empty
- One button: "Submit" (no approve/reject distinction)

### Action Resolver
- Displays: title, summary, body (extended context)
- Controls: "Complete" button + optional free_text area
- "Complete" resolves immediately (free_text=null = done, no notes)
- If user types first, free_text carries their notes

### List View
- Cards showing: kind badge, title, summary, agent, created_at, option count (decisions)
- Confidence bars visible at card level for decisions

## Architecture Invariants

- **Single engine writer** — no layer except the engine writes to `decisions/`
- **Pydantic `extra="forbid"`** — unknown fields in frontmatter are validation errors, surfaced not dropped
- **Resolved files are immutable** — audit trail, never modified after move to `resolved/`
- **CORS invariant** — localhost-only, tested
- **Conditional unblock** — task unblocks only when zero sibling pending requests remain

## Delivery Sequence

### Step 1: Foundation (model + engine + interfaces)
- Pydantic models in engine (`decisions.py` or new module)
- Engine API: `create_request`, `resolve_request`, `list_requests`, `get_request`
- Sweep updated for new schema + wired into `pick_tasks` and Cockpit cleanup
- MCP tools: `create_request`, `list_requests`, `show_request`
- Cockpit API endpoints: GET pending, POST resolve
- Minimal wiring: existing resolve modal adapted to new endpoint (functional, not pretty)
- Tests for all engine operations, MCP tools, API endpoints

### Step 2: Experience (Cockpit UI + instructions)
- New resolver UI: option cards for decisions, Complete button for actions
- List rendering from structured fields (no body-text inference)
- Confidence bars, recommended badges, free_text area
- Agent instruction updates (`h-decision-requests` skill)
- Remove old `create_dr` MCP tool and old resolve flow

## Explicitly Excluded

- Threaded conversation history on requests
- Multi-user assignment routing
- Recurring requests
- Complex multi-select decision matrices
- Rich evidence attachments beyond markdown links
- Resolved request browsing UI
- MCP resolve tool (deferred, gate conditions documented)
- Quick-confirm mode / pre-selection (deferred)
- `parent_request_id` / `supersedes_request_id` (no observed chains)
- `resolved_by` field (always "user" in single-user system — add if agent resolution unlocked)
- Defined parallel request blocking semantics (sequential safe, parallel unspecified)
