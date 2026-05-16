---
id: 1623
title: 'P3-09: Tests — accessibility sweep'
status: archived
priority: important
created: 2026-05-16T03:37:25.230397+00:00
updated: 2026-05-16T15:05:50.277949+00:00
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
  - axe-core scan via Playwright reports zero WCAG 2.1 AA violations
  - Tests assert keyboard Tab navigation reaches each interactive element 
    without focus traps
  - Tests assert color contrast meets 4.5:1 for normal text and 3:1 for large 
    text (automated check)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1628
---
Brief: see parent #1590.

Scope: Failing tests for WCAG 2.1 AA compliance — axe-core automated scan, keyboard navigation, color contrast.
Out of scope: Implementation, dark mode, focus-visible, motion.