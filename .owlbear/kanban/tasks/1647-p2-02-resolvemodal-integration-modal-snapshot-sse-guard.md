---
id: 1647
title: 'P2-02: ResolveModal integration + modal snapshot SSE guard'
status: research
priority: important
created: 2026-05-18T00:50:17.184817+02:00
updated: 2026-05-18T00:50:17.184817+02:00
tags:
  - phase-2
  - scope:cockpit-web
  - frontend
parent: 1638
depends_on:
  - 1645
ac:
  - Clicking a DR list item in DecisionsPage calls setSelectedDRId with the 
    item's id, which opens the Shell-level ResolveModal with that DR's data — 
    same ResolveModal instance used by DRStatusIndicator
  - DR data is copied into modal-local state when ResolveModal opens; subsequent
    SSE-triggered useDRState() refetches do not update the data displayed in the
    open modal
  - Closing and reopening the modal for the same DR picks up any data changes 
    that occurred while the modal was closed
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

**In:** DecisionsPage click → ResolveModal wiring via `setSelectedDRId`. Modal snapshot (SSE guard) — DR data copied to modal-local state on open so SSE refetches don't cause involuntary data loss.

**Out:** DR list rendering (P2-01), ResolveModal component changes (minimal — snapshot is modal-local state management).

## Context

ResolveModal currently receives `dr` as a prop from Shell, sourced from `useDRState().selectedDR`. The selectedDR reference updates on SSE refetch. The snapshot guard copies the DR data into component-local state on mount/open, decoupling the modal from live prop updates. Shell already renders ResolveModal at the top level — both DRStatusIndicator and DecisionsPage use `setSelectedDRId` to trigger it.