---
id: 1606
title: 'P1-09: Shell layout — sticky header + responsive sidebar'
status: research
priority: important
created: 2026-05-16T03:36:07.069416+00:00
updated: 2026-05-16T03:36:07.069416+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on:
  - 1601
ac:
  - Header remains visible at scroll position > viewport height (Playwright 
    isVisible() after scroll)
  - Sidebar collapses to icon-only state at viewport width < 1024px
  - Layout uses CSS Grid or Flexbox via Tailwind utilities (no inline style={{}}
    for layout structure)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Sticky header, sidebar responsive collapse, CSS grid structure via Tailwind utilities.

Scope: Shell layout only.
Out of scope: Sidecar structure, card components, token migration.