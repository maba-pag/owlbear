---
id: 1859
title: 'P2-02: Action resolver UI with Complete button'
status: backlog
priority: needed
created: 2026-05-24T20:59:19.178037+02:00
updated: 2026-05-24T21:00:29.517738+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1850
depends_on:
  - 1857
ac:
  - Action resolver renders title, summary, and markdown body with no option 
    cards; a "Complete" button is present and enabled without requiring user 
    input.
  - 'Clicking "Complete" submits {selected_option_id: null, free_text: null} to POST
    /api/requests/{id}/resolve; if user typed in the free_text area before clicking,
    that value is sent as free_text.'
  - After successful resolve submission (200 response), the action is removed 
    from the pending list without full page reload.
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
- Action resolver component: title, summary, body display
- "Complete" button (always enabled)
- Optional free_text textarea
- Submission logic (null payload for bare complete, free_text when provided)
- List refresh after resolution

**Out of scope:**
- Decision resolver (P2-01)
- List view cards (P2-03)
- Backend changes

## Test scope
`npm test` in `serve/cockpit/web/`