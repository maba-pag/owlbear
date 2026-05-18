---
id: 1639
title: 'P1-01: Tab routing infrastructure — route config + Routes rendering + skeleton
  page'
status: research
priority: critical
created: 2026-05-18T00:49:02.441398+02:00
updated: 2026-05-18T00:49:02.441398+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
  - infrastructure
parent: 1638
depends_on:
- 1590
ac:
  - 'Route config defines declarative entries (path, label, icon, component) with
    at least two entries: kanban at `/` and decisions at `/decisions`; Shell `<Routes>`
    selects the active tab component based on URL path'
  - Navigating to `/decisions` renders a skeleton DecisionsPage placeholder 
    component with a data-testid attribute; navigating to `/` renders 
    KanbanBoard unchanged
  - Route config is a single array — adding a new entry (path + component) is 
    sufficient to register a new routed tab without modifying Shell internals
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Route config array data structure, `<Routes>` integration in Shell.tsx, skeleton DecisionsPage component at `/decisions`, kanban route moved into route config.

**Out:** Nav-rail buttons (P1-02), sidecar conditioning (P1-03), lazy loading (P1-04), decisions content (P2).

## Context

Shell.tsx currently has a single `<Route path="/" element={<KanbanBoard ... />} />`. This task introduces the declarative route config and multi-route rendering. The skeleton page validates routing works end-to-end.