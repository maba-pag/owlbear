---
id: 1642
title: 'P1-02: Nav-rail tab navigation — dynamic buttons from route config'
status: research
priority: needed
created: 2026-05-18T00:49:27.319192+02:00
updated: 2026-05-18T00:49:27.319192+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1639
ac:
  - Nav-rail element has role="navigation" and renders one button per route 
    config entry; each button triggers useNavigate() to its route path on click
  - Active route's nav-rail button has aria-current="page"; inactive buttons do 
    not have aria-current; switching routes updates aria-current accordingly
  - 'Validation gate: adding a third entry to the route config array produces a third
    nav-rail button that navigates to the new route path'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Nav-rail `<nav>` element wiring in Shell.tsx — render buttons from route config, `useNavigate()` handlers, `aria-current="page"` on active route, `role="navigation"` semantics.

**Out:** Route config creation (P1-01), sidecar conditioning (P1-03), lazy loading (P1-04), badge (P2-03).

## Context

Shell.tsx nav-rail currently has a single hardcoded `<button>` with `data-surface="kanban"` and static `aria-current="page"`. This task replaces it with dynamic buttons driven by route config, using `useLocation()` or `useMatch()` to determine the active state.