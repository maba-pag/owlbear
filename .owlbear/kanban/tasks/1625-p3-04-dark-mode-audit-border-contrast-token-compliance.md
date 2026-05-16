---
id: 1625
title: 'P3-04: Dark mode audit — border contrast + token compliance'
status: research
priority: important
created: 2026-05-16T03:37:44.735785+00:00
updated: 2026-05-16T03:37:44.735785+00:00
tags:
  - frontend
  - pds
  - phase-3
parent: 1590
depends_on:
  - 1620
ac:
  - In .scheme-dark, adjacent surface panels have visually distinct borders 
    (contrast ratio >= 1.3:1)
  - Zero hardcoded border-color values in authored CSS — all use PDS color 
    tokens
  - Light and dark modes show intentional visual differentiation (not just 
    inverted)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Border contrast, surface differentiation, ensure tokens use `light-dark()` correctly.

Scope: Dark mode audit only.
Out of scope: Focus-visible, motion, accessibility sweep.