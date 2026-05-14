---
id: 1570
title: 'P2-11 GREEN: Add compact operational metadata to task cards'
status: backlog
priority: needed
created: 2026-05-14T18:26:42.531941+00:00
updated: 2026-05-14T18:27:14.734428+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - cards
  - visual-remediation
parent: 1559
depends_on:
  - 1565
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Implements the failing proof from #1565. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8.

## Scope
In scope: visible and accessible card metadata for id, priority or status, tags, blocked, claimed, and DR-pending states.
Out of scope: sidecar detail rendering, filter workflow, column topology changes, and drag-and-drop behavior changes.

## Acceptance Criteria
AC-1: Given a task has id, priority, status, tags, blocked, claimed, or DR-pending state, its card displays compact metadata and state cue without hiding the title; verify with the named rendering tests from #1565.
AC-2: Given a task has more tags than the card preview permits, the card shows a tag preview and overflow indicator; verify with the fixture from #1565.
AC-3: Given keyboard focus lands on a card, visible focus and accessible text include the card title plus state cue; verify with the accessibility check from #1565.

Proof bundle: behavioral

## Evidence Expectations
Passing #1565 card tests and card-state screenshot evidence.