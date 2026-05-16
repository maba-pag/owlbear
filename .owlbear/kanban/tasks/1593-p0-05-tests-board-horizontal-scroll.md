---
id: 1593
title: 'P0-05: Tests — board horizontal scroll'
status: backlog
priority: critical
created: 2026-05-16T03:34:43.248583+00:00
updated: 2026-05-16T04:02:49.598386+00:00
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

[[2026-05-16T06:02:49+02:00]]
## Research
- Research doc: .owlbear/research/1593-board-horizontal-scroll-tests.md
- Sources: 6 studied, 4 high-relevance (all codebase-internal)
- Recommendation: Create `e2e/board-scroll-1593.spec.ts` using established scroll measurement pattern from responsive-layout-1391.spec.ts. Two tests: (1) scrollWidth > clientWidth on board container with 7 statuses, (2) each column width >= 200px + all columns share same offsetTop (single-row assertion). RED failure mode: auto-fit grid wraps columns to multiple rows instead of scrolling. Default viewport (1280x720) sufficient — workspace ~864px < 7×200px=1400px. (confidence: 0.90)
- Challenge: skipped (trivial application of existing patterns)
