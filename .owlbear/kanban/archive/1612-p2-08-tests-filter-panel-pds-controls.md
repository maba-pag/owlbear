---
id: 1612
title: 'P2-08: Tests — filter panel PDS controls'
status: archived
priority: important
created: 2026-05-16T03:36:42.417384+00:00
updated: 2026-05-16T15:04:50.953711+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on:
  - 1608
ac:
  - Tests assert filter inputs use PDS form components (PSelect, 
    PTextFieldWrapper, or PCheckboxWrapper)
  - Tests assert filter panel has structured layout (horizontal bar or 
    collapsible container, not inline-scattered controls)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: deprecated
archival_refs:
  - 1617
---
Brief: see parent #1590.

Scope: Failing tests for filter panel PDS form component usage and layout coherence.
Out of scope: Implementation, simple swaps, cards, sidecar IA, modals.