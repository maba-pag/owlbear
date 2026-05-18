---
id: 1644
title: 'P1-04: Lazy loading — React.lazy() with Suspense boundary for tab components'
status: research
priority: important
created: 2026-05-18T00:49:27.367267+02:00
updated: 2026-05-18T00:49:27.367267+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1639
ac:
  - Tab components in route config are loaded via React.lazy() wrapped in a 
    Suspense boundary with a fallback element
  - DecisionsPage component is code-split into a separate chunk — the dynamic 
    import path is verified by build output or test instrumentation
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** `React.lazy()` wrapping of route-config tab components, `<Suspense>` boundary in Shell.tsx routing.

**Out:** Route config creation (P1-01), component implementation.

## Context

Route config entries from P1-01 reference tab components directly. This task wraps them in `React.lazy()` for code-splitting and adds a `<Suspense>` fallback around the `<Routes>` output. KanbanBoard may remain eagerly loaded since it is the default route.