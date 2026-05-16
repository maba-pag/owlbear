---
id: 1598
title: 'P1-04: Tests — formatting utilities'
status: research
priority: important
created: 2026-05-16T03:35:25.261581+00:00
updated: 2026-05-16T04:19:55.611271+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on: []
ac:
  - Unit tests assert format*(null) and format*(undefined) return defined 
    fallback strings (not undefined/null/throw)
  - Tests assert no formatter return value appears in any fetch() or mutation 
    call path
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at: 2026-05-16T04:19:55.611271+00:00
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for null-safe formatting utilities (relative time, priority label, status label, signal description). Canonical/display partition (C8).
Out of scope: Implementation, token migration, layout.