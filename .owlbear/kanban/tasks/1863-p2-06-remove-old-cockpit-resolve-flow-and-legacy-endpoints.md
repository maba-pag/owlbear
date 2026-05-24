---
id: 1863
title: 'P2-06: Remove old Cockpit resolve flow and legacy endpoints'
status: backlog
priority: important
created: 2026-05-24T21:00:04.160667+02:00
updated: 2026-05-24T21:00:29.574432+02:00
tags:
  - phase-2
  - scope:cockpit
  - cleanup
parent: 1850
depends_on:
  - 1856
  - 1858
  - 1859
  - 1860
ac:
  - Old resolve_decision endpoint (POST /decisions/{id}/resolve with 
    response=approved/needs-info/rejected payload) is removed from Cockpit 
    routes; requests to old endpoint path return 404.
  - Old list_pending_decisions endpoint (GET /decisions/pending returning 
    PendingDRResponse with body-text regex title extraction) is removed from 
    Cockpit routes.
  - Frontend code referencing old resolve patterns (regex title extraction via 
    _extract_title, approve/reject/needs-info button set) is removed; only new 
    structured resolver components remain.
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
- Remove `resolve_decision` endpoint from `serve/cockpit/src/owlbear_cockpit/routes/decisions.py`
- Remove `list_pending_decisions` endpoint and related models (`PendingDRItem`, `PendingDRResponse`, `ResolveRequest`)
- Remove old frontend resolve modal components that use regex-based title extraction
- Remove helper functions only used by old flow (`_extract_title`, `_format_plain_title`, `_append_response_section`, `_rewrite_response`)

**Out of scope:**
- `parse_dr` and `move_to_resolved` engine helpers (may still be used by new code)
- New endpoints and UI (already shipped)

## Downstream impact
- `tests/test_cockpit_decisions_api.py` — update or remove tests for old endpoints
- `tests/test_cockpit_decisions_pydantic_1640.py` — review for old model references
- Frontend test files covering old resolve modal

## Test scope
`tests/test_cockpit_*` and `npm test` in `serve/cockpit/web/`