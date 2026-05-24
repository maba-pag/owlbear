---
id: 1856
title: 'P1-06: Cockpit API — GET /api/requests/pending and POST /api/requests/{id}/resolve'
status: backlog
priority: needed
created: 2026-05-24T20:58:51.312492+02:00
updated: 2026-05-24T21:13:13.846282+02:00
tags:
  - phase-1
  - scope:cockpit
  - api
parent: 1850
depends_on:
  - 1854
ac:
  - GET /api/requests/pending returns JSON array of pending requests with 
    structured fields (request_id, task_id, kind, title, summary, agent, 
    created_at, options); imports engine list_requests directly.
  - POST /api/requests/{id}/resolve accepts {selected_option_id?, free_text?}, 
    delegates to engine resolve_request, returns 200 with resolved request 
    summary on success; returns 404 when request_id not found; returns 422 when 
    resolution payload fails validation.
  - POST /api/requests/{id}/resolve accepts both-null payload for action-kind 
    requests (bare Complete); for decision-kind requests, requires at least one 
    of selected_option_id or free_text to be non-null, returning 422 otherwise.
  - GET /api/requests/pending triggers sweep before returning results — any 
    pending file with non-null resolution fields is processed (moved to 
    resolved/, write-back appended, conditional unblock) before the response is 
    assembled.
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
- `GET /api/requests/pending` endpoint
- `POST /api/requests/{id}/resolve` endpoint
- Pydantic request/response models for both endpoints
- Direct engine import (no HTTP between Cockpit backend and engine)
- Sweep trigger on Cockpit startup/cleanup cycle

**Out of scope:**
- Frontend rendering (P1-07, P2-01/02/03)
- Old `/decisions/` endpoints (retained until P2-06 removal)
- MCP layer

## Test scope
`tests/test_cockpit_*`