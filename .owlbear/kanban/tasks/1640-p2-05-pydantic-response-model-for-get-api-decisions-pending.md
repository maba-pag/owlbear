---
id: 1640
title: 'P2-05: Pydantic response model for GET /api/decisions/pending'
status: research
priority: important
created: 2026-05-18T00:49:02.493590+02:00
updated: 2026-05-18T00:49:02.493590+02:00
tags:
  - phase-2
  - scope:cockpit
  - backend
parent: 1638
depends_on:
- 1590
ac:
  - 'list_pending_decisions endpoint returns a Pydantic response model with typed
    fields: count (int) and items (list of PendingDRItem); PendingDRItem coerces task_id
    to int and validates required fields (id, task_id, agent, request_type, created,
    body_preview)'
  - Malformed DR files that fail PendingDRItem validation are silently excluded 
    from the items list — endpoint returns 200 with remaining valid items, not 
    500
  - Response model is declared as the response_model parameter on the route 
    decorator so FastAPI enforces serialization shape
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Pydantic response model (`PendingDRResponse`, `PendingDRItem`) on `GET /api/decisions/pending` in `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`. Type coercion for `task_id` (int), `created` (str). Validation-based exclusion of malformed items.

**Out:** Frontend changes, notes length cap (P2-06), resolve endpoint changes.

## Context

Currently `list_pending_decisions` returns `dict[str, object]` — untyped. The endpoint builds items from `parse_dr()` output with no schema enforcement. Adding a Pydantic model catches malformed DR files at the API boundary.