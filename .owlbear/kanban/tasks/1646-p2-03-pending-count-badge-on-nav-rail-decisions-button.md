---
id: 1646
title: 'P2-03: Pending count badge on nav-rail decisions button'
status: research
priority: important
created: 2026-05-18T00:49:44.996891+02:00
updated: 2026-05-18T00:49:44.996891+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1642
ac:
  - Nav-rail decisions button displays a badge sub-element showing 
    useDRState().count when count is greater than 0
  - Badge element is not rendered (absent from DOM) when pending DR count is 0
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Pending count badge on the decisions nav-rail button — renders count from `useDRState().count`, visibility conditional on count > 0.

**Out:** Nav-rail button creation (P1-02), DR list (P2-01).

## Context

The nav-rail buttons from P1-02 are driven by route config. The decisions button needs a badge overlay showing the pending DR count. The badge is a small sub-element of the nav button, not a separate component. `useDRState()` from CockpitProvider already provides `count`.