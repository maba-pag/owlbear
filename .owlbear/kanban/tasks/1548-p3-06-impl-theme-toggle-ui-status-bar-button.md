---
id: 1548
title: 'P3-06: impl — theme toggle UI: status bar button'
status: backlog
priority: important
created: 2026-05-13T18:43:23.870309+00:00
updated: 2026-05-14T05:55:15.994996+00:00
tags:
  - phase-3
  - scope:cockpit
  - theme
  - frontend
parent: 1534
depends_on:
  - 1540
  - 1545
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Theme toggle button component in status bar (right side), wired to `useTheme().toggle`, visual indication of current theme state
- **Out:** useTheme hook implementation (done in P2-02 #1545), theme bootstrap

## Acceptance Criteria

- AC-1: Theme toggle button renders in the status bar area, right side
- AC-2: Button click invokes `useTheme().toggle` to cycle through light → dark → auto
- AC-3: Button visually indicates current theme state (light/dark/auto) via icon or label

Proof bundle: behavioral
2026-05-14T05:55:15+00:00
## Research
- Research doc: .owlbear/research/1548-theme-toggle-button.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: PButton-based ThemeToggle component with text label per state, placed as last child in Shell status bar (confidence: 0.88)
- Challenge: skipped — trivial component, no architecture decisions
- Follow-up tasks: none needed — #1548 is the impl task itself, tests exist at ThemeToggle.test.tsx
- Commit: 9f3c15c