---
id: 1857
title: 'P1-07: Cockpit frontend — minimal resolver wiring to new API'
status: backlog
priority: critical
created: 2026-05-24T20:59:01.793534+02:00
updated: 2026-05-24T21:00:29.486858+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
parent: 1850
depends_on:
  - 1856
ac:
  - Resolve modal fetches from GET /api/requests/pending and displays request 
    title and summary from structured response fields (no body-text regex 
    inference for title extraction).
  - Resolve action submits to POST /api/requests/{id}/resolve with 
    selected_option_id or free_text payload; on 200 response, modal closes and 
    pending list refreshes.
  - For decision-kind requests, option labels from the structured response are 
    displayed; for action-kind requests, a "Complete" button is rendered instead
    of option controls.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Adapt existing resolve modal to consume new `/api/requests/pending` response shape
- Submit to new `/api/requests/{id}/resolve` endpoint
- Basic display of structured fields (title, summary, options labels)
- Functional but not polished (Step 2 handles full design)

**Out of scope:**
- Confidence bars, recommended badges (P2-01)
- Full option card design (P2-01)
- List view cards (P2-03)
- Removal of old regex-based title extraction (P2-06)

## Test scope
`npm test` in `serve/cockpit/web/`