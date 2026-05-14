---
id: 1553
title: 'P4-03: PDS component dark-mode compatibility verification'
status: research
priority: important
created: 2026-05-13T18:43:53.233186+00:00
updated: 2026-05-14T05:57:20.124304+00:00
tags:
  - phase-4
  - scope:cockpit
  - theme
  - test
  - frontend
parent: 1534
depends_on:
  - 1545
blocked: false
block_reason:
claimed_at: 2026-05-14T05:51:34.652452+00:00
archival_reason:
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Verify PDS web components (buttons, tabs, banners) respond to `data-theme` attribute changes on `<html>`; document any components needing additional treatment
- **Out:** PDS component replacement or adoption (out of scope per brief)

## Acceptance Criteria

- AC-1: Test or manual verification confirms PDS web components (p-button, p-tabs, p-banner) switch styling when `data-theme` changes between `"light"` and `"dark"` on `<html>`
- AC-2: If any PDS component does not respond to `data-theme`, a document in the task body lists the component name and what additional CSS treatment is required

Proof bundle: behavioral
2026-05-14T05:57:20+00:00


## AC-2: Components needing additional treatment

**Finding: ALL 14 PDS components need the same treatment** — none respond to `data-theme` because PDS v4 uses CSS `color-scheme` property via `.scheme-*` classes, not `data-theme` attributes.

**Root cause:** PDS v4 removed the per-component `theme` prop. Components now inherit `color-scheme` from ancestor elements. Our Cockpit sets `data-theme` on `<html>` but never sets `color-scheme` or `.scheme-*` classes.

**Components affected (all used PDS components):** PButton, PText, PSelect, PInputText, PTextarea, PSpinner, PMultiSelect, PMultiSelectOption, PIcon, PHeading, PInlineNotification, p-tabs, p-tabs-item, PBanner.

**Required treatment (uniform for all):**
1. Import PDS v4 mandatory global styles CSS
2. Bridge `data-theme` ↔ `.scheme-*` class in `theme-bootstrap.js` and `useTheme.ts`

No per-component CSS overrides needed — PDS v4 handles dark mode uniformly via `color-scheme` inheritance once the bridge is in place.