---
id: 1605
title: 'P1-07: Extend computeSignal with unknown state'
status: research
priority: important
created: 2026-05-16T03:36:07.039801+00:00
updated: 2026-05-16T03:36:07.039801+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1599
ac:
  - computeSignal(null) and computeSignal({}) return an object with state 
    'unknown'
  - Existing 5-state behavior unchanged for valid inputs 
    (green/yellow/red/gray/stale)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Add 'unknown' state for malformed/missing inputs.

Scope: computeSignal extension only.
Out of scope: Formatting utilities, token migration, layout.