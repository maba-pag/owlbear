---
id: 1665
title: 'P2-04: IdeasPage — external-edit awareness and conflict resolution'
status: backlog
priority: important
created: 2026-05-18T17:42:08.396906+02:00
updated: 2026-05-18T18:13:22.044503+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1658
depends_on:
  - 1638
  - 1662
ac:
  - IdeasPage re-fetches content via GET `/api/ideas` on `visibilitychange` 
    event (tab becomes visible) and on route activation (navigating to Ideas tab
    from another cockpit route)
  - When content is clean at re-fetch time, fetched content silently replaces 
    textarea content and updates the last-saved baseline
  - When content is dirty at re-fetch time, a conflict notice appears with 
    Overwrite and Discard & Reload buttons; Save button is disabled while the 
    notice is showing
  - Overwrite dismisses the conflict notice and re-enables Save (keeping local 
    content); Discard & Reload adopts fetched content, resets dirty state, and 
    dismisses notice
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Re-fetch triggers:
1. `visibilitychange` — fires when alt-tabbing back to the browser
2. Route activation — fires when navigating back to the Ideas tab from another cockpit route

Conflict notice forces an explicit choice before Save is re-enabled. This prevents accidental overwrite of external edits made in VS Code or another editor.

## In Scope

- `visibilitychange` event listener for re-fetch
- Route activation detection for re-fetch
- Silent update when clean
- Conflict notice UI with Overwrite / Discard & Reload
- Save button disabled during conflict notice
- Cleanup of event listeners on unmount

## Out of Scope

- File-watcher / real-time sync (not in scope per brief)
- SSE push notifications
- OCC / versioning headers