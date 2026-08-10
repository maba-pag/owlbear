# Cockpit UX-Driven Decision Request Model

Task: #1723
Created: 2026-05-23
Intended use: input material for a future ideation run and Brief about expanding OwlBear decision/action requests across storage, engine APIs, MCP tools, and Cockpit UX.

This is not the final architecture. It is a problem statement plus candidate requirements, grounded in the Cockpit Decisions route work where good UX currently requires parsing meaning out of plain markdown request bodies.

## Triggering Observation

The live pending decision request for task #1558 was stored as a single plain paragraph. Cockpit had to infer these separate UX concepts from body text:

- concise request title
- decision timing/context
- options to choose from
- full request text
- whether the request is a decision vs an action
- what response controls should be shown

That inference made the UI better, but it is a frontend workaround. The backend should expose these concepts structurally so agents can create useful requests and Cockpit can render the right resolver without brittle body parsing.

## Problem

Decision requests currently behave like markdown files with a small amount of frontmatter. The human-facing UX needs richer structure than that:

- Multiple requests can belong to one task, so `task_id` alone is not enough identity.
- `created` can be date-only, but Cockpit and agents need full date, time, and timezone.
- Requests can ask for different kinds of human intervention: choose an option, approve/reject, perform an action, provide text, confirm a fact, or unblock with missing information.
- Options and recommendations are embedded in prose, so Cockpit cannot reliably render option cards, confidence, rationale, or machine-readable resolution output.
- Agents need a durable, machine-readable resolution they can consume without scraping notes.
- Cockpit should adapt the response UI to the request shape instead of always showing Approve / Reject / Needs info.

## Product Goal

Create a structured decision/action request model that lets agents ask humans for the right kind of input, lets Cockpit render an ergonomic resolver, and lets subsequent agents consume the answer mechanically.

Good UX should be achieved through explicit data, not markdown heuristics.

## Core Concepts

### Request Identity

Every request should have a stable request ID in addition to task ID.

Candidate fields:

```yaml
request_id: drq_20260523_001
sequence: 1
task_id: 1558
parent_request_id: null
supersedes_request_id: null
```

Notes:

- `request_id` is the canonical resolver endpoint key.
- `task_id` links to the work item, but does not identify the request.
- `sequence` is optional but useful for human display when multiple requests exist for one task.
- `parent_request_id` allows follow-up clarification requests.
- `supersedes_request_id` supports replacing stale or malformed requests without losing audit history.

### Full Timestamp

Use full ISO 8601 date-time with timezone for created and resolved timestamps.

```yaml
created_at: 2026-05-23T02:07:23+02:00
updated_at: 2026-05-23T02:09:10+02:00
resolved_at: null
```

Avoid date-only values because relative age, ordering, concurrent requests, and audit trails need time precision.

### Request Kind

Distinguish what the human is being asked to do.

Candidate enum:

```yaml
kind: decision        # decision | action | approval | clarification | confirmation
```

Meanings:

- `decision`: choose among alternatives or provide a new choice.
- `action`: the user must do something outside the agent, then mark it complete or provide result data.
- `approval`: approve or reject a proposed agent action.
- `clarification`: answer a question before work can proceed.
- `confirmation`: verify an inferred fact or state.

This should replace overloaded freeform `request_type` values where possible. `request_type` can remain as a more specific subtype if useful.

### Prompt and Summary

Separate display summary from full body.

```yaml
title: Choose ownership model for knowledge source lifecycle
summary: Choose how knowledge source lifecycle ownership should be handled after the ingestion/enrichment contracts are repaired.
body_markdown: |
  Full context, links, evidence, and detailed rationale.
```

Notes:

- `title` is short and human-scannable.
- `summary` is the card/modal brief.
- `body_markdown` is the full request, not the only source of structured meaning.

### Options

Decision-like requests should provide structured options.

```yaml
options:
  - option_id: mcp-tools
    label: MCP tools
    description: Expose source lifecycle operations through MCP tools and let agents invoke them directly.
    recommended: false
    confidence: 0.62
    rationale: Fits agent workflows, but may hide important user-facing lifecycle state from Cockpit.
    impact: More powerful automation, less visible governance unless paired with UI.
  - option_id: cockpit-surface
    label: Cockpit surface
    description: Manage source lifecycle primarily through Cockpit UI.
    recommended: false
    confidence: 0.58
    rationale: Better visibility for users, but agents may still need machine-operable hooks.
  - option_id: hybrid
    label: Hybrid
    description: Use MCP for operations and Cockpit for visibility, review, and manual correction.
    recommended: true
    confidence: 0.74
    rationale: Balances agent automation with human oversight.
```

Option requirements:

- Stable `option_id`, not just labels.
- Human label and optional description.
- Optional `recommended` flag.
- Optional `confidence` score in a defined range, likely 0.0 to 1.0.
- Rationale and impact fields for Cockpit expansion panels.
- Optional `risk`, `cost`, `reversibility`, or `default` fields if ideation finds them useful.

### Response Mode

The request should define what responses are allowed.

```yaml
response_mode: select_option   # select_option | select_or_free_text | approval | free_text | action_result | confirmation
allow_free_text: true
allow_multiple_options: false
```

Candidate modes:

- `select_option`: user must choose one provided option.
- `select_or_free_text`: user can choose an option or write a custom answer.
- `approval`: approve/reject/needs-info for a specific proposal.
- `free_text`: open answer required.
- `action_result`: user records completion/result of an external action.
- `confirmation`: yes/no/needs-correction.

Cockpit should render controls from this mode:

- option cards or radio buttons for `select_option`
- option cards plus custom answer textarea for `select_or_free_text`
- approve/reject controls for `approval`
- textarea for `free_text`
- done/blocked/result fields for `action_result`
- confirm/correct controls for `confirmation`

### Resolution Payload

Resolution should be machine-readable, not only notes.

```yaml
resolution:
  status: pending       # pending | resolved | cancelled | superseded
  response_kind: null   # selected_option | free_text | approval | action_completed | needs_info
  selected_option_id: null
  free_text: null
  approved: null
  action_result: null
  notes_markdown: null
  resolved_by: null
  resolved_at: null
```

For a resolved select-option decision:

```yaml
resolution:
  status: resolved
  response_kind: selected_option
  selected_option_id: hybrid
  free_text: null
  notes_markdown: Hybrid gives agents tools while preserving Cockpit visibility.
  resolved_by: markus
  resolved_at: 2026-05-23T02:30:00+02:00
```

Agents should receive the structured fields directly in `pick_tasks`, `show_task`, or a dedicated request-read API.

### Blocking Semantics

Requests should state whether they block the task or are advisory.

```yaml
blocking: true
blocks_status_transition: true
required_before:
  - implementation
```

Questions:

- Should a task have many non-blocking advisory requests?
- Can one blocking request block multiple tasks?
- Should a resolved request automatically unblock a task, or only provide evidence for an agent to unblock it?

### Audience and Ownership

Requests should say who can answer and who created it.

```yaml
created_by_agent: copilot
assigned_to: user        # user | agent:{name} | role:{name}
visibility: cockpit      # cockpit | pipeline | all
```

This matters for future multi-agent or multi-user Cockpit behavior.

## Storage Direction

A request file should probably remain markdown/frontmatter for clone = install simplicity, but with richer structured frontmatter.

Candidate file shape:

```markdown
---
request_id: drq_20260523_001
task_id: 1558
sequence: 1
kind: decision
request_type: source-lifecycle-ownership
created_at: 2026-05-23T02:07:23+02:00
created_by_agent: copilot
assigned_to: user
blocking: true
title: Choose ownership model for knowledge source lifecycle
summary: Choose how source lifecycle ownership should work after ingestion/enrichment contracts are repaired.
response_mode: select_or_free_text
allow_free_text: true
allow_multiple_options: false
options:
  - option_id: mcp-tools
    label: MCP tools
    confidence: 0.62
    recommended: false
  - option_id: cockpit-surface
    label: Cockpit surface
    confidence: 0.58
    recommended: false
  - option_id: hybrid
    label: Hybrid
    confidence: 0.74
    recommended: true
resolution:
  status: pending
  response_kind:
  selected_option_id:
  free_text:
  notes_markdown:
  resolved_by:
  resolved_at:
---

Full markdown context, evidence, trade-offs, links, and anything too long for frontmatter.
```

Key design question for ideation: how much should live in frontmatter vs body vs companion JSON? Frontmatter keeps the format readable, but nested option/resolution structures may become awkward.

## Engine Interface Direction

The kanban engine should own request parsing, validation, creation, and resolution semantics. Cockpit and MCP should not duplicate file-format logic.

Candidate engine functions or protocol methods:

```python
create_request(task_id: int, request: RequestCreate) -> DecisionRequest
list_requests(status: RequestStatus | None = None, task_id: int | None = None) -> list[DecisionRequest]
get_request(request_id: str) -> DecisionRequest
resolve_request(request_id: str, resolution: RequestResolution) -> DecisionRequest
cancel_request(request_id: str, reason: str) -> DecisionRequest
supersede_request(request_id: str, replacement: RequestCreate) -> DecisionRequest
list_task_requests(task_id: int, include_resolved: bool = False) -> list[DecisionRequest]
```

Validation belongs here:

- request ID format and uniqueness
- task existence
- full timestamp parsing with timezone
- option ID uniqueness
- response mode compatibility with options
- resolution compatibility with request mode
- state transitions
- atomic file move/update between pending/resolved/cancelled/superseded states

## MCP Interface Direction

MCP should expose structured tools that are comfortable for agents.

Candidate tools:

### `create_request`

Input:

```json
{
  "task_id": 1558,
  "kind": "decision",
  "request_type": "source-lifecycle-ownership",
  "title": "Choose ownership model for knowledge source lifecycle",
  "summary": "Choose how source lifecycle ownership should work after ingestion/enrichment contracts are repaired.",
  "body_markdown": "Full context...",
  "response_mode": "select_or_free_text",
  "blocking": true,
  "options": [
    {"option_id": "mcp-tools", "label": "MCP tools", "confidence": 0.62},
    {"option_id": "cockpit-surface", "label": "Cockpit surface", "confidence": 0.58},
    {"option_id": "hybrid", "label": "Hybrid", "confidence": 0.74, "recommended": true}
  ]
}
```

Output:

```json
{
  "request_id": "drq_20260523_001",
  "task_id": 1558,
  "status": "pending",
  "path": "decisions/pending/drq_20260523_001.md"
}
```

### `list_requests`

Filter by status, task ID, kind, assigned target, or blocking.

### `show_request`

Return full structured request and body markdown.

### `resolve_request`

Input depends on response mode:

```json
{
  "request_id": "drq_20260523_001",
  "response_kind": "selected_option",
  "selected_option_id": "hybrid",
  "notes_markdown": "Use MCP for operations and Cockpit for visibility."
}
```

### `cancel_request` / `supersede_request`

Useful when an agent created a bad or obsolete request.

## Cockpit UX Direction

Cockpit should render based on `kind` and `response_mode`, not prose detection.

List/card view:

- request title
- request kind tag
- task tag
- full relative age from `created_at`
- creating agent
- blocking/advisory signal
- concise summary
- option count and recommended option if applicable

Resolver modal:

- title and metadata
- summary
- options as selectable cards with confidence and rationale
- free-text custom answer if allowed
- response controls matched to kind/mode
- notes field only when useful, not as the primary machine-readable answer
- full request markdown disclosure
- clear resolved output preview before submit

Resolved view later:

- selected option / entered answer
- resolver identity and timestamp
- notes
- request body snapshot
- supersession/cancellation chain

## Agent UX Direction

Agents should be able to create a request without writing a perfect markdown paragraph. They should provide structured intent and let Cockpit handle UX.

Agent benefits:

- Can choose the right kind of user input.
- Can give concrete options with confidence and rationale.
- Can consume the answer without body scraping.
- Can create multiple requests per task safely.
- Can supersede or cancel stale requests.
- Can tell whether a task is blocked by unresolved user input.

## Backward Compatibility and Migration

Current pending decision files should still load as legacy requests.

Possible migration behavior:

- If only old fields exist, derive `request_id` from file stem.
- If `created` is date-only, treat it as legacy and expose `created_at` with an explicit fallback policy.
- If no structured options exist, Cockpit may continue best-effort parsing temporarily, but mark the request as `legacy_unstructured`.
- New MCP tools should write the structured model only.
- Existing `create_dr` can become a compatibility wrapper around `create_request`.

Design question: should old files be migrated in place, or should compatibility be read-only until they resolve naturally?

## Risks and Constraints

- Do not overfit the model to Cockpit; agents and CLI/MCP consumers also need it.
- Do not make request creation so verbose that agents avoid it.
- Do not require JSON-only storage if markdown/frontmatter remains adequate.
- Keep resolution atomic and auditable.
- Avoid optional-field chaos by making response modes define which fields are required.
- Preserve clone = install and human-readable board files.

## Suggested Ideation Questions

1. What is the smallest request model that removes Cockpit body-parsing hacks while staying easy for agents to create?
2. Should `decision` and `action` be separate models or one model with `kind` and `response_mode`?
3. Should options be first-class for all requests or only decision-like requests?
4. How should confidence be represented: per option, per recommendation, or both?
5. What response modes are essential for V1?
6. Where should the full body markdown live relative to structured fields?
7. How should request IDs be generated and displayed?
8. How should multiple active requests per task affect task blocked state and Cockpit badges?
9. Should resolving a request mutate the linked task, or only create evidence for a later agent action?
10. What compatibility behavior is acceptable for existing pending DR files?

## Candidate V1 Scope

In:

- request ID
- task ID
- kind
- title
- summary
- body markdown
- created_at with timezone
- created_by_agent
- blocking flag
- response mode
- structured options for decision requests
- selected option or free text resolution
- engine create/list/get/resolve
- MCP create/list/show/resolve
- Cockpit cards and resolver controls based on structured fields
- legacy read compatibility

Out for V1:

- threaded conversation history
- multi-user assignment routing beyond `assigned_to`
- recurring requests
- complex multi-select decision matrices
- rich evidence attachments beyond markdown links
- resolved request browsing unless needed by implementation sequence

## Seed Scenario

An agent needs user input before implementing knowledge source lifecycle ownership.

Instead of writing:

> Decision needed later: choose ownership model for knowledge source lifecycle after #1556 and #1557 complete... Options to evaluate: MCP tools, manifest workflow, Cockpit surface, or hybrid...

It creates:

```yaml
kind: decision
response_mode: select_or_free_text
title: Choose ownership model for knowledge source lifecycle
summary: Choose how lifecycle ownership should work after ingestion/enrichment contracts are repaired.
options:
  - option_id: mcp-tools
    label: MCP tools
    confidence: 0.62
  - option_id: manifest-workflow
    label: Manifest workflow
    confidence: 0.55
  - option_id: cockpit-surface
    label: Cockpit surface
    confidence: 0.58
  - option_id: hybrid
    label: Hybrid
    confidence: 0.74
    recommended: true
```

Cockpit renders option cards. The user chooses `hybrid` or writes a custom answer. The next agent receives `selected_option_id: hybrid` plus notes, with no markdown scraping.
