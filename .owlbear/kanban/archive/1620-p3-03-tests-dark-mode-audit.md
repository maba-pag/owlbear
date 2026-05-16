---
id: 1620
title: 'P3-03: Tests — dark mode audit'
status: archived
priority: important
created: 2026-05-16T03:37:25.101843+00:00
updated: 2026-05-16T15:05:03.886426+00:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on:
  - 1614
  - 1615
  - 1616
  - 1617
  - 1618
ac:
  - Tests assert adjacent surface panels have visually distinct borders in 
    .scheme-dark (contrast ratio >= 1.3:1 between surfaces)
  - Tests assert zero hardcoded border-color values in authored CSS files (grep 
    verification — all use PDS color tokens)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1625
---
Brief: see parent #1590.

Scope: Failing tests for dark mode border contrast and token compliance.
Out of scope: Implementation, focus-visible, motion, accessibility sweep.