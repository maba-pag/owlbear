---
id: 1592
title: 'P0-03: Tests — Tailwind v4 Vite plugin + Stylelint config'
status: research
priority: critical
created: 2026-05-16T03:34:43.226946+00:00
updated: 2026-05-16T03:34:43.226946+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on: []
ac:
  - Test asserts PDS Tailwind utility classes (bg-canvas, text-contrast-high, 
    gap-md, rounded-sm) compile without error in vite build
  - Test asserts light-dark() CSS functions are preserved in build output (not 
    compiled away)
  - Test asserts npm run lint:css passes on files containing @theme, @utility, 
    @apply at-rules
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for Tailwind v4 Vite plugin integration and Stylelint at-rule recognition.
Out of scope: Token migration, layout, board scroll, implementation.