---
id: 1645
title: 'P2-01: Decisions list page with empty state'
status: backlog
priority: needed
created: 2026-05-18T00:49:44.974074+02:00
updated: 2026-05-19T20:26:58.124858+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1639
  - 1643
ac:
  - DecisionsPage renders a full-width single-column list of pending DRs from 
    useDRState().items; each list item displays agent, request_type, relative 
    age, task_id, and body_preview (truncated to 200 characters)
  - When useDRState().items is empty, DecisionsPage renders an empty-state 
    element with a clear "nothing to decide" message and a data-testid attribute
  - DecisionsPage list items have generous vertical spacing (not dense rows); 
    each item is a clickable region identified by data-testid
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** Full DecisionsPage component replacing the skeleton from P1-01 — pending DR list with item rendering, empty state.

**Out:** ResolveModal integration (P2-02), sidecar DecisionViewport removal (P2-04), badge (P2-03).

## Context

The skeleton page from P1-01 gets replaced with the real decisions list. Data comes from `useDRState()` (already available via CockpitProvider — no new state fields needed). DecisionViewport.tsx has similar rendering logic for the sidecar that can inform the list item structure, but the tab version uses full-page width with generous spacing.

[[2026-05-19T20:26:58+02:00]]
## Research

**Findings:** T1-Autonomous frontend component task. All data sources verified:
- `useDRState()` provides `items: PendingDR[]` with all required fields (agent, request_type, created, task_id, body_preview)
- `DecisionViewport.tsx` has reusable `formatAge()` utility and item rendering pattern
- No new state, hooks, or API endpoints needed

**Implementation approach:** Replace skeleton with component calling `useDRState()` directly; render single-column flex list with `<article>` items; extract/reuse `formatAge()` for relative age; enforce 200-char body_preview truncation; empty state with data-testid.

**Doc:** `.owlbear/research/1645-decisions-list-page.md`
**Follow-ups:** None — task is self-contained, ready for todo.
