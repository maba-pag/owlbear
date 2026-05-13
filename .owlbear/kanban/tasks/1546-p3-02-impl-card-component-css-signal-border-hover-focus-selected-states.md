---
id: 1546
title: 'P3-02: impl — card component CSS: signal border, hover, focus, selected states'
status: research
priority: important
created: 2026-05-13T18:43:23.784270+00:00
updated: 2026-05-13T18:46:30.664456+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1538
  - 1543
  - 1544
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Card CSS: 4px left border from signal model, hover/focus/selected visual states, `data-signal` and `data-selected` attributes in JSX, `overflow-wrap: break-word`, transparent background
- **Out:** Signal computation logic (done in P1-04 #1544), column/shell CSS

## Acceptance Criteria

- AC-1: Card renders with 4px left border colored by signal model via `[data-signal]` CSS selectors (orange/red/purple/grey/theme-default)
- AC-2: Card has hover state (PDS `state-hover` token), focus state (PDS focus ring), and selected state (`[data-selected]` box-shadow) — selected styling is additive, not replacing the signal border
- AC-3: Card uses `overflow-wrap: break-word` for title text with no fixed height constraint; background is transparent

Proof bundle: behavioral

- AC-4: Card element has `opacity: 0.5` (or similar muted state) while being dragged (`[dragging]` or equivalent attribute)