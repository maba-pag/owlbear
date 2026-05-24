---
id: 1851
title: 'P1-01: Pydantic models for structured decision requests'
status: backlog
priority: needed
created: 2026-05-24T20:57:55.018006+02:00
updated: 2026-05-24T21:13:13.825317+02:00
tags:
  - phase-1
  - scope:kanban
  - model
parent: 1850
depends_on: []
ac:
  - RequestOption model validates option_id matching 
    ^[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$, label max 120 chars, confidence in [0.0, 
    1.0], rationale max 500 chars; invalid inputs raise ValidationError.
  - DecisionRequest model with kind="decision" requires options with 2-10 items 
    and rejects fewer than 2 or more than 10; ActionRequest model with 
    kind="action" rejects non-empty options; both use extra="forbid".
  - 'At-most-one recommended=true constraint: model raises ValidationError when two
    or more options have recommended=true.'
  - Resolution model contains only selected_option_id (str|null) and free_text 
    (str|null). resolved_at is NOT part of the Resolution model — it is added by
    the engine at resolution time and excluded from pending file serialization.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- `RequestOption`, `Resolution`, `DecisionRequest`, `ActionRequest` Pydantic models
- Kind-discriminated union type for request creation
- Field constraints per Brief data model table
- `extra="forbid"` on models
- `resolution` block with nullable fields (present but null in pending files)

**Out of scope:**
- File I/O, engine API functions (P1-02)
- MCP or Cockpit layers
- Storage format writing (handled by engine)

## Test scope
`serve/kanban/tests/`