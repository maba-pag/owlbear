---
id: 1648
title: 'P2-04: Remove DecisionViewport from sidecar'
status: research
priority: important
created: 2026-05-18T00:50:17.215196+02:00
updated: 2026-05-18T00:50:17.215196+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1645
ac:
  - DecisionViewport is no longer rendered inside the sidecar aside element — 
    import removed from Shell.tsx, component no longer appears in sidecar DOM
  - DRStatusIndicator in the status bar continues to function on all routes — 
    clicking a DR item opens ResolveModal via setSelectedDRId
  - No runtime errors or missing-import warnings after DecisionViewport removal 
    from the sidecar
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Remove `DecisionViewport` rendering from the sidecar in Shell.tsx (both mobile and desktop branches). Verify DRStatusIndicator continues working as the secondary entry path.

**Out:** DecisionViewport component file itself is retained (may be reused or deleted later). DR list page (P2-01).

## Context

Shell.tsx currently renders `<DecisionViewport>` inside the sidecar `<aside>` in both the mobile `<p-sheet>` and desktop branches. With the decisions tab providing a dedicated full-page list (P2-01), the sidecar DR list is redundant. DRStatusIndicator in the status bar remains as the secondary entry path — it calls `setSelectedDRId` to open ResolveModal from any route.