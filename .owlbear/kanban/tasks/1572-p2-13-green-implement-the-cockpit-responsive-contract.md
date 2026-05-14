---
id: 1572
title: 'P2-13 GREEN: Implement the Cockpit responsive contract'
status: backlog
priority: needed
created: 2026-05-14T18:26:54.868007+00:00
updated: 2026-05-14T18:36:15.336076+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - responsive
  - visual-remediation
parent: 1559
depends_on:
  - 1566
  - 1568
  - 1569
  - 1570
  - 1571
  - 1575
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Implements the failing proof from #1566 after the main visible surfaces are redesigned. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 4, 6, and 8.

## Scope
In scope: viewport composition for 320px, tablet, and desktop across shell, board, sidecar or sheet, filters, overlays, and cards.
Out of scope: changing backend APIs, redesigning card metadata, and replacing individual filter controls beyond completed predecessor work.

## Acceptance Criteria
AC-1: Given 320px viewport, document width does not exceed viewport width and board columns are reachable through the intended scroll container; verify with the named measurements from #1566.
AC-2: Given tablet viewport, shell, sidecar or sheet, filters, overlays, cards, and board remain reachable without content overlap; verify with screenshot and locator assertions from #1566.
AC-3: Given selected task detail at mobile viewport, Cockpit follows the #1560 mobile contract branch and exposes full detail, sidecar sheet, or controlled unsupported state; verify with the branch-specific test from #1566.

Proof bundle: behavioral

## Evidence Expectations
Passing #1566 responsive tests and viewport screenshot evidence.


## Planner Audit Amendment — Column Dependency
Responsive implementation now also waits on #1575 because column body focusability, empty-state sizing, and column/card spacing affect the 320px/tablet contract.

Additional AC-4: Responsive proof includes the polished column/empty-state behavior from #1575 at 320px, tablet, desktop, and dark-mode smoke screenshots.