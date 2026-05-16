---
id: 1606
title: 'P1-09: Shell layout — sticky header + responsive sidebar'
status: backlog
priority: important
created: 2026-05-16T03:36:07.069416+00:00
updated: 2026-05-16T15:11:19.311024+00:00
tags:
  - frontend
  - pds
  - phase-1
parent: 1590
depends_on: []
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

[[2026-05-16T17:11:19+02:00]]
## Research
- Research doc: .owlbear/research/1606-shell-layout-sticky-header-responsive-sidebar.md
- Sources: 8 studied, 5 high-relevance
- Recommendation: Hybrid approach — thin Shell.css (grid-template-areas + semantic aliases) + Tailwind utilities for all layout properties (confidence: 0.85)

Key findings:
1. **Sticky header:** Add `sticky top-0 z-10` — header is already effectively fixed via 100vh grid but belt-and-suspenders approach ensures robustness
2. **"Sidebar" = sidecar (right panel):** Nav-rail is already icon-only; AC means sidecar auto-collapses to ~48px icon strip at < 1024px
3. **Tailwind migration:** Reduce Shell.css from ~217 → ~40 lines; move layout utilities to className; keep grid-template-areas in CSS (Tailwind has no native areas support)
4. **p-canvas rejected:** PDS experimental component would require full Shell.tsx + E2E test rewrite
5. **PDS Porsche Grid rejected:** Designed for full-viewport content pages, not application shells
6. **Test absorbed:** #1601 archived into #1606; builder owns test responsibility
