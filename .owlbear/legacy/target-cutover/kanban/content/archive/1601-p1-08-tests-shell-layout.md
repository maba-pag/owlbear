---
id: 1601
title: 'P1-08: Tests — shell layout'
status: archived
priority: medium
created: 2026-05-16T03:35:41.083212+00:00
updated: 2026-05-16T15:04:29.982833+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1594
  - 1595
  - 1596
ac:
  - Playwright test asserts header remains visible (isVisible()) after scrolling
    past viewport height
  - Test asserts sidebar collapses to icon-only state at viewport width < 1024px
  - Test asserts shell layout uses CSS Grid or Flexbox classes (no inline 
    style={{}} for layout structure)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1606
---
Brief: see parent #1590.

Scope: Failing tests for shell layout behavior — sticky header and responsive sidebar collapse.
Out of scope: Implementation, sidecar structure, token migration.