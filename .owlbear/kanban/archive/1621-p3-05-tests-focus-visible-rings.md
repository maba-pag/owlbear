---
id: 1621
title: 'P3-05: Tests — focus-visible rings'
status: archived
priority: medium
created: 2026-05-16T03:37:25.145759+00:00
updated: 2026-05-16T15:05:08.430561+00:00
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
  - Playwright test asserts visible focus ring (outline or box-shadow non-none) 
    on each interactive element during :focus-visible
  - Tests assert focus ring styles reference PDS focus tokens (not custom ring 
    definitions)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1626
---
Brief: see parent #1590.

Scope: Failing tests for PDS focus-visible ring styling on interactive elements.
Out of scope: Implementation, dark mode, motion, accessibility sweep.