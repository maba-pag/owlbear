---
id: 1629
title: 'Consolidation test: cockpit visual redesign'
status: backlog
priority: important
created: 2026-05-16T03:37:57.297125+00:00
updated: 2026-05-17T22:31:42.387623+02:00
tags:
  - frontend
  - pds
  - consolidation-test
parent: 1590
depends_on:
  - 1594
  - 1595
  - 1596
  - 1603
  - 1604
  - 1605
  - 1606
  - 1607
  - 1614
  - 1615
  - 1616
  - 1617
  - 1618
  - 1624
  - 1625
  - 1626
  - 1627
  - 1628
  - 1636
ac:
  - Vitest unit tests (npm test) and Playwright e2e tests (npm run test:e2e) 
    pass with zero failures
  - Inline style={{}} count in serve/cockpit/web/src/ is 3 or fewer (justified 
    exceptions documented)
  - Both .scheme-light and .scheme-dark themes render correctly; axe-core 
    reports zero WCAG 2.1 AA violations
proof_bundle: critical
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Full-surface consolidation test across all 4 batches of the cockpit visual redesign. Verifies cross-cutting quality: test suites green, inline style budget, theme correctness, accessibility compliance.

Scope: Integration verification of all component migration, token migration, layout, and polish work.
Out of scope: Individual component behavior (covered by per-task tests).