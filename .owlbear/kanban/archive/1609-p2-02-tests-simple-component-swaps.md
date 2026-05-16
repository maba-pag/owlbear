---
id: 1609
title: 'P2-02: Tests — simple component swaps'
status: archived
priority: important
created: 2026-05-16T03:36:42.305002+00:00
updated: 2026-05-16T15:04:38.228996+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1608
ac:
  - Tests assert zero raw <select elements in source files outside test files
  - Tests assert PDS React wrappers (PButton, PIcon, PHeading, PText) used for 
    interactive/display elements classified as simple-swap in inventory
  - Tests assert raw <button> elements exist only where inventory documents them
    as intentional native
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1614
---
Brief: see parent #1590.

Scope: Failing tests for simple PDS component swaps. Preserve intentional native controls per inventory classification.
Out of scope: Implementation, complex integrations, cards, sidecar IA, filter panel.