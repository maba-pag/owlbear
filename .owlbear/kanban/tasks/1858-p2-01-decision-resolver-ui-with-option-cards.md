---
id: 1858
title: 'P2-01: Decision resolver UI with option cards'
status: backlog
priority: needed
created: 2026-05-24T20:59:10.619728+02:00
updated: 2026-05-24T21:00:29.501454+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1850
depends_on:
  - 1857
ac:
  - 'Decision resolver renders one card per option showing: label, confidence as a
    proportional-width bar (0-100%), rationale text, and a "Recommended" badge when
    recommended=true.'
  - Selecting an option card highlights it and sets selected_option_id in the 
    submit payload; submitting without a selection sends selected_option_id=null
    with free_text from the text area.
  - Submit button is enabled when an option is selected OR free_text input is 
    non-empty; disabled when neither condition is met.
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
- Option card component: label, confidence bar, rationale, recommended badge
- Card selection state management
- free_text textarea as alternative input
- Submit button enabled/disabled logic
- Integration with existing resolve submission flow (POST /api/requests/{id}/resolve)

**Out of scope:**
- Action resolver (P2-02)
- List view (P2-03)
- Backend changes (already complete in P1-06)

## Test scope
`npm test` in `serve/cockpit/web/`