---
id: 1549
title: 'P3-08: impl — sidecar collapse toggle'
status: research
priority: important
created: 2026-05-13T18:43:23.907745+00:00
updated: 2026-05-13T18:43:23.907745+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1541
  - 1543
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Sidecar collapse/expand toggle button, CSS transition for smooth animation, default-open state, React state management
- **Out:** Sidecar content (DetailTab/ActivityTab styling done separately), responsive breakpoints

## Acceptance Criteria

- AC-1: Sidecar has a collapse/expand toggle button; clicking it hides or shows the sidecar panel
- AC-2: CSS transition animates the collapse/expand smoothly
- AC-3: Default state is open; collapsed state maintained in component local state across re-renders

Proof bundle: behavioral