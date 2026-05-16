---
id: 1599
title: 'P1-06: Tests — computeSignal unknown state'
status: research
priority: important
created: 2026-05-16T03:35:25.284760+00:00
updated: 2026-05-16T03:35:25.284760+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on: []
ac:
  - Test asserts computeSignal(null) and computeSignal({}) return an object with
    state 'unknown'
  - Test asserts existing 5-state behavior unchanged for valid inputs 
    (green/yellow/red/gray/stale)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for computeSignal unknown state extension.
Out of scope: Implementation, formatting utilities, token migration.