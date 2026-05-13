---
id: 1547
title: 'P3-04: impl — column component CSS: fixed header, scroll body, empty text
  fallback'
status: research
priority: important
created: 2026-05-13T18:43:23.829051+00:00
updated: 2026-05-13T18:46:30.674972+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1539
  - 1543
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Column CSS: PDS surface background, border-radius, fixed header with name + count badge, scrollable body, empty state text fallback, minimum width 200px
- **Out:** Empty state illustrations (user-supplied), card CSS, DnD column highlighting (minimal)

## Acceptance Criteria

- AC-1: Column has PDS `background-surface` background, `border-radius-md`, and subtle border; minimum width 200px
- AC-2: Column header (name + task count badge) is fixed outside the scrollable area; body scrolls with `overflow-y: auto`
- AC-3: Empty columns display centered "No {status} tasks" text fallback (image placeholder infrastructure ready but images not required)

Proof bundle: behavioral

- AC-4: Column shows visible drop-target highlight (border color or background shift) on `[data-drag-over="true"]` when a valid card is dragged over it