---
id: 1553
title: 'P4-03: PDS component dark-mode compatibility verification'
status: research
priority: important
created: 2026-05-13T18:43:53.233186+00:00
updated: 2026-05-13T18:43:53.233186+00:00
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
claimed_at:
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