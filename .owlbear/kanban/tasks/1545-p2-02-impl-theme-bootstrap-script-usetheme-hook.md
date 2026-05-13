---
id: 1545
title: 'P2-02: impl — theme bootstrap script + useTheme hook'
status: research
priority: needed
created: 2026-05-13T18:42:22.373573+00:00
updated: 2026-05-13T18:42:22.373573+00:00
tags:
  - phase-2
  - scope:cockpit
  - theme
  - frontend
parent: 1534
depends_on:
  - 1537
  - 1543
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Synchronous bootstrap script in `index.html`, `useTheme` React hook, localStorage persistence, OS preference listener, `data-theme` DOM attribute management
- **Out:** Theme toggle UI button (separate task), PDS component compatibility verification (separate task)

## Acceptance Criteria

- AC-1: Synchronous `<script>` in `index.html` reads localStorage, validates against `["dark","light"]`, and sets `data-theme` on `<html>` before React mount — preventing flash-of-wrong-theme
- AC-2: `useTheme` hook returns `{ theme, toggle, isDark }` and manages `data-theme` DOM attribute without React Context; CSS cascade propagates theme via attribute selectors, causing zero re-renders on theme change
- AC-3: Toggle function cycles through light → dark → auto and persists choice to localStorage; absent or invalid localStorage defaults to OS preference via `prefers-color-scheme`

Proof bundle: behavioral