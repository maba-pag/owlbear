---
id: 1853
title: 'P1-03: Engine API — resolve_request with conditional unblock'
status: backlog
priority: needed
created: 2026-05-24T20:58:16.414102+02:00
updated: 2026-05-24T21:13:13.803310+02:00
tags:
  - phase-1
  - scope:kanban
  - api
parent: 1850
depends_on:
  - 1852
ac:
  - resolve_request(request_id, selected_option_id, free_text) sets resolved_at 
    to current UTC ISO 8601 timestamp and moves file from pending/ to resolved/ 
    atomically.
  - resolve_request validates selected_option_id against existing option_id 
    values in the request; raises ValidationError when the ID does not match any
    option. For action-kind requests (empty options list), any non-null 
    selected_option_id raises ValidationError.
  - 'resolve_request appends write-back summary to the task body using four format
    variants: (1) decision with selected option: "## DR: {title}\n- **Selected:**
    {label}"; (2) decision with selected option AND free_text: "## DR: {title}\n-
    **Selected:** {label}\n- **Notes:** {free_text}"; (3) decision without selected
    option (free_text only): "## DR: {title}\n- **Answer:** {free_text}"; (4) action:
    "## AR: {title}\n- **Outcome:** {free_text}".'
  - resolve_request unblocks the task only when zero sibling pending requests 
    remain for that task_id; leaves task blocked when other pending requests 
    exist for the same task_id.
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
- `resolve_request` engine function
- Resolution validation (option_id cross-check)
- `resolved_at` timestamp insertion
- Atomic move from pending/ to resolved/
- Write-back summary append to task body (3 format variants)
- Conditional unblock logic (sibling pending check)

**Out of scope:**
- List/filter (P1-04)
- Sweep (P1-04)
- MCP/Cockpit layers

## Test scope
`serve/kanban/tests/`