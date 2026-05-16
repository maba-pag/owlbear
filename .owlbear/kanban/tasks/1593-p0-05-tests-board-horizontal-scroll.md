---
id: 1593
title: 'P0-05: Tests — board horizontal scroll'
status: research
priority: critical
created: 2026-05-16T03:34:43.248583+00:00
updated: 2026-05-16T03:34:43.248583+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on: []
ac:
  - Playwright test asserts scrollWidth > clientWidth on board container when 6+
    columns are rendered
  - Test asserts columns maintain fixed minimum width instead of shrinking to 
    fit viewport
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for board horizontal scroll behavior.
Out of scope: PDS foundation, token migration, implementation.