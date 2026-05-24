---
id: 1860
title: 'P2-03: Request list rendering from structured fields'
status: backlog
priority: needed
created: 2026-05-24T20:59:27.659879+02:00
updated: 2026-05-24T21:13:13.836553+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1850
depends_on:
  - 1857
ac:
  - 'Request list renders cards with: kind badge ("Decision" / "Action"), title, summary,
    agent name, created_at as relative time, option count for decision-kind requests,
    and confidence bars (proportional-width, one per option) visible at card level
    for decision-kind requests.'
  - Clicking a card opens the corresponding resolver component (DecisionResolver
    or ActionResolver) based on the kind field value.
  - List re-fetches from GET /api/requests/pending after a resolve submission 
    completes; empty state displays a "No pending requests" message.
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
- Request list component with card rendering
- Kind badge visual distinction
- Relative time formatting for created_at
- Card click → resolver routing by kind
- Empty state handling
- Re-fetch after resolution

**Out of scope:**
- Resolver UI internals (P2-01, P2-02)
- Resolved request browsing (explicitly excluded in Brief)
- Backend changes

## Test scope
`npm test` in `serve/cockpit/web/`