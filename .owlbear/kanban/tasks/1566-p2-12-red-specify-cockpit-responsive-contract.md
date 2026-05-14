---
id: 1566
title: 'P2-12 RED: Specify Cockpit responsive contract'
status: backlog
priority: needed
created: 2026-05-14T18:26:23.522300+00:00
updated: 2026-05-14T18:27:14.704590+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - responsive
  - visual-remediation
parent: 1559
depends_on:
  - 1560
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 4, 6, and 8. This lane waits on the mobile contract captured by #1560.

## Scope
In scope: 320px, tablet, and desktop viewport contract for shell, board, sidecar or sheet, filters, and overlays.
Out of scope: redesigning individual cards, replacing filter controls, and changing backend APIs.

## Acceptance Criteria
AC-1: Test-writer adds E2E checks at 320px, tablet, and desktop viewports for no document-level horizontal overflow and board reachability through the intended scroll container; verify by quality-runner output for named tests.
AC-2: Test-writer adds a branch-specific test for the #1560 mobile contract: full UI, board-only with sheet sidecar, or controlled unsupported state; verify by named test output.
AC-3: Test-writer records current failing evidence for 320px overflow and scrollable-region focusability; verify by artifact inspection of Test Evidence.

Proof bundle: behavioral

## Evidence Expectations
Failing responsive proof, viewport measurements, and #1560 mobile-contract linkage.