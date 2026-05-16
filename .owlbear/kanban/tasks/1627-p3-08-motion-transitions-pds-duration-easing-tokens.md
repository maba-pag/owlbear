---
id: 1627
title: 'P3-08: Motion/transitions — PDS duration + easing tokens'
status: research
priority: important
created: 2026-05-16T03:37:44.829874+00:00
updated: 2026-05-16T03:37:44.829874+00:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on:
  - 1622
ac:
  - Expand/collapse animations use --p-transition-duration and 
    --p-transition-timing-function tokens
  - "Zero 'transition: all' declarations in authored CSS"
  - Route transitions smooth (no flash of unstyled content)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

PDS duration/easing tokens for state changes (expand/collapse, route transitions).

Scope: Motion/transitions only.
Out of scope: Dark mode, focus-visible, accessibility sweep.