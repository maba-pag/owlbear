---
id: 1643
title: 'P1-03: Route-conditional sidecar — suppress sidecar DOM on non-kanban routes'
status: research
priority: needed
created: 2026-05-18T00:49:27.343819+02:00
updated: 2026-05-18T00:49:27.343819+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1639
ac:
  - Sidecar aside element is not rendered in the DOM when the active route is 
    not `/` (kanban); sidecar renders normally when active route is `/`
  - Switching from `/` to `/decisions` removes the sidecar from the DOM; 
    switching back to `/` restores it with its previous collapse state intact
  - Shell grid layout adjusts columns when sidecar is absent — workspace 
    occupies full remaining width on non-kanban routes
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Route-conditional sidecar suppression in Shell.tsx and Shell.css — sidecar DOM removed on non-kanban routes, grid column adjustment.

**Out:** Route config creation (P1-01), sidecar content changes (P2-04), nav-rail (P1-02).

## Context

Shell.tsx currently renders the `<aside>` sidecar unconditionally in a 3-column grid (`56px 1fr 360px`). On non-kanban routes, the sidecar is not needed and should be removed from the DOM entirely. The CSS grid columns should adapt (e.g. `56px 1fr` on non-kanban routes). The brief notes this is the highest-complexity P1 work.