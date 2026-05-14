---
id: 1565
title: 'P2-10 RED: Specify task card information density'
status: backlog
priority: needed
created: 2026-05-14T18:26:23.493454+00:00
updated: 2026-05-14T18:27:14.696549+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - cards
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
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8. Cards currently communicate too little beyond title and rail color.

## Scope
In scope: task-card metadata, state cues, accessible naming, and overflow behavior.
Out of scope: column layout, sidecar detail rendering, filter workflow, and drag-and-drop behavior beyond preserving existing reachability.

## Acceptance Criteria
AC-1: Test-writer adds E2E rendering fixtures for task cards with id, title, priority or status tag, tag preview with overflow indicator, blocked cue, claimed cue, and DR-pending cue; verify by quality-runner output for named tests.
AC-2: Test-writer adds an accessibility check that blocked, claimed, and DR-pending states are perceivable without relying on rail color; verify by axe or locator assertions.
AC-3: Test-writer records current failing evidence that cards are title-only in the production board; verify by artifact inspection of Test Evidence.

Proof bundle: behavioral

## Evidence Expectations
Failing card-density proof and accessible-state evidence.