---
id: 1596
title: 'P0-06: Board horizontal scroll fix'
status: research
priority: critical
created: 2026-05-16T03:35:01.759388+00:00
updated: 2026-05-16T03:35:01.759388+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on:
  - 1593
ac:
  - Board scrolls horizontally with 6+ columns (scrollWidth > clientWidth)
  - Columns maintain fixed minimum width instead of shrinking to fit viewport
  - No regression in existing board layout tests
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Change grid template from `auto-fit` wrapping to fixed-column layout with `overflow-x: auto`. The container already has overflow set; the grid's `minmax(200px, 1fr)` causes wrapping.

Scope: Board scroll behavior only.
Out of scope: PDS foundation, token migration, component migration.