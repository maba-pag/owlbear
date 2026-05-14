---
id: 1554
title: 'consolidation test: board visual design'
status: backlog
priority: important
created: 2026-05-13T18:43:53.303013+00:00
updated: 2026-05-14T07:21:26.327598+00:00
tags:
  - phase-5
  - scope:cockpit
  - consolidation-test
  - frontend
parent: 1534
depends_on:
  - 1543
  - 1544
  - 1545
  - 1546
  - 1547
  - 1548
  - 1549
  - 1550
  - 1555
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** End-to-end integration verification that the board renders coherently in both light and dark themes with signal model, styled components, and theme switching
- **Out:** Individual component fixes (tracked in their respective tasks)

## Acceptance Criteria

- AC-1: Board renders in light theme with visible column surfaces, card signal borders matching operational state, and functional theme toggle
- AC-2: Board renders in dark theme with correct token overrides applied via `[data-theme="dark"]` selectors and no visual artifacts (white-on-white text, invisible borders, wrong colors)
- AC-3: Card signal model displays correct left-border color for each operational state (dr-pending=orange, blocked=red, claimed=purple, deps-unmet=grey, ready=theme-default)

Proof bundle: critical