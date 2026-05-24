---
id: 1836
title: Review Ideas conflict notice decision context
status: research
priority: important
created: 2026-05-24T12:24:57.808395+02:00
updated: 2026-05-24T12:24:57.808395+02:00
tags:
  - scope:cockpit-web
  - ideas
  - ux
  - conflict-resolution
  - discussion
parent: 1773
depends_on: []
ac:
  - Evaluate whether Ideas conflict resolution gives users enough visible 
    information to choose Overwrite vs Discard & Reload.
  - Any approved change preserves local draft protection and avoids silent 
    overwrite/discard behavior.
  - Any approved change uses the existing Ideas API data or an explicitly 
    approved API extension.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
When Ideas detects an external update while the local draft is dirty, the page disables Save and shows a conflict notice with `Overwrite` and `Discard & Reload`. The notice tells the user to choose which version becomes the saved baseline, but it does not show the remote version, a local/remote comparison, an updated timestamp, or enough context to judge which action preserves the intended content.

## Evidence
- Screenshot: `.owlbear/scratch/1773-audit-continue/ideas-conflict-notice.png`
- Runtime report: `.owlbear/scratch/1773-audit-continue/ideas-conflict-report.json`
- Runtime facts: Save is disabled during conflict; textarea still shows the local draft; the remote-only line is absent from the DOM; the conflict notice contains no local/remote labels, diff indicators, or timestamp.
- Code surface: `serve/cockpit/web/src/pages/IdeasPage.tsx` stores `conflictSnapshot.content` and `updatedAt`, blocks save while `hasConflict`, and renders only the generic notice text plus `Overwrite` / `Discard & Reload` buttons.
- API surface: `serve/cockpit/src/owlbear_cockpit/routes/ideas.py` returns `content` and `updated_at` from `GET /api/ideas`; the conflict is client-side background refetch state, not a PUT-time server conflict response.

## Observed User Impact
Ideas is a shared notebook. In a real external-edit conflict, the user is forced to choose between overwriting the server baseline with their local draft or discarding local work, but the screen does not reveal what would be overwritten or discarded. That makes the decision depend on memory instead of visible evidence and increases the risk of losing useful notes.

## Boundary
This is an audit finding only. Do not implement without explicit user approval. The review should decide whether the conflict state needs an inline comparison, remote preview, timestamp/context copy, or a different save/merge flow.
