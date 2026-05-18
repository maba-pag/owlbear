---
id: 1664
title: 'P2-03: IdeasPage — unsaved-changes guard'
status: backlog
priority: important
created: 2026-05-18T17:42:08.375696+02:00
updated: 2026-05-18T18:13:22.034107+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1658
depends_on:
  - 1638
  - 1662
ac:
  - Route navigation is blocked with a confirmation dialog when IdeasPage 
    textarea content is dirty; confirming proceeds, canceling stays
  - '`beforeunload` event listener prevents accidental browser tab/window close when
    content is dirty'
  - Guard is inactive (does not block navigation or fire beforeunload) when 
    content is clean
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

Brief: see parent #1658 (`.owlbear/briefs/draft-cockpit-ideas/brief.md`)

Uses React Router's navigation blocking API (`useBlocker` or equivalent from #1638's router setup) for SPA route transitions. `beforeunload` for browser close/refresh.

Dialog text: "You have unsaved changes. Leave anyway?"

## In Scope

- Route navigation blocking via React Router when dirty
- `beforeunload` event listener when dirty
- Confirmation dialog with proceed/cancel actions
- Cleanup of event listeners on unmount

## Out of Scope

- Dirty-state tracking itself (owned by P2-01)
- External-edit conflict resolution (separate task)
- Custom dialog styling beyond PDS defaults