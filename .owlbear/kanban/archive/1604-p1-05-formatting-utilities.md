---
id: 1604
title: 'P1-05: Formatting utilities'
status: research
priority: important
created: 2026-05-16T03:36:07.011240+00:00
updated: 2026-05-16T03:36:07.011240+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1598
ac:
  - 'utils/format.ts exports null-safe formatters for: relative time, priority label,
    status label, signal description'
  - No formatter output appears in any fetch() or mutation call path 
    (canonical/display partition C8)
  - Enum values sourced from board API config response, not hardcoded arrays 
    (C7)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Canonical/display value partition (C8): formatted display values never feed mutation APIs. Config-driven enum vocabularies (C7): statuses and priorities come from board API.

Scope: Formatting utilities only.
Out of scope: Token migration, component migration, layout.