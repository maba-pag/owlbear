---
id: 1610
title: 'P2-04: Tests — card visual treatment'
status: archived
priority: medium
created: 2026-05-16T03:36:42.364176+00:00
updated: 2026-05-16T15:04:42.691587+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1608
ac:
  - 'Tests assert each card renders: status chip (PTag), priority indicator, signal
    icon, tag pills, relative timestamp'
  - Tests assert priority and status colors reference PDS color tokens (not 
    hardcoded hex values)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1615
---
Brief: see parent #1590.

Scope: Failing tests for card visual treatment — metadata density, status chip, priority indicator.
Out of scope: Implementation, simple swaps, sidecar, modals.