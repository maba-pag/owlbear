---
id: 1649
title: 'Consolidation test: Cockpit Decisions Tab multi-tab infrastructure'
status: backlog
priority: needed
created: 2026-05-18T00:50:31.900068+02:00
updated: 2026-05-18T00:50:36.209392+02:00
tags:
  - consolidation-test
  - scope:cockpit-web
  - scope:cockpit
parent: 1638
depends_on:
  - 1639
  - 1640
  - 1641
  - 1642
  - 1643
  - 1644
  - 1645
  - 1646
  - 1647
  - 1648
ac:
  - 'End-to-end navigation: rendering Shell at `/` shows KanbanBoard with sidecar;
    navigating to `/decisions` shows DecisionsPage without sidecar; nav-rail buttons
    reflect active state; badge shows pending count when > 0'
  - 'Entry path convergence: both DecisionsPage list item click and DRStatusIndicator
    popover item click open the same Shell-level ResolveModal; modal snapshot guard
    prevents SSE data mutation during open modal'
  - 'Backend contract: GET /api/decisions/pending returns typed PendingDRResponse
    with validated items; POST /api/decisions/{id}/resolve rejects notes exceeding
    10,000 characters with 422'
proof_bundle: critical
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1638 and `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md`

## Scope

Integration verification across all P1 + P2 subtasks. Ensures the tab system, decisions content, entry path convergence, and backend contracts work together.

## Sibling Tasks

- #1639 P1-01 routing infra
- #1642 P1-02 nav-rail
- #1643 P1-03 sidecar conditional
- #1644 P1-04 lazy loading
- #1645 P2-01 decisions list
- #1646 P2-03 badge
- #1647 P2-02 ResolveModal + SSE guard
- #1648 P2-04 sidecar DR removal
- #1640 P2-05 Pydantic response model
- #1641 P2-06 notes cap