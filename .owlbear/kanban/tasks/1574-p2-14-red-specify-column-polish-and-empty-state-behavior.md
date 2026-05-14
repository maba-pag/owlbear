---
id: 1574
title: 'P2-14 RED: Specify column polish and empty-state behavior'
status: backlog
priority: needed
created: 2026-05-14T18:33:43.120318+00:00
updated: 2026-05-14T18:36:45.296729+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - columns
  - empty-states
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
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8. Planner audit found the initial remediation graph under-owned column polish: empty states, status labels, and scrollable column-body focusability could otherwise be buried inside responsive work.

## Scope
In scope: column headers, status label display names, empty-state treatment, count badge clarity, keyboard focusability for scrollable column bodies, and column/card spacing interaction.
Out of scope: card metadata content, sidecar layout, filter controls, and mobile shell contract beyond column-specific assertions.

## Acceptance Criteria
AC-1: Test-writer adds a focused test that verifies every column uses a polished display label rather than leaking internal API strings such as `in-progress`; verify by named test output.
AC-2: Test-writer adds visual/DOM assertions for quiet but intentional empty states in empty columns, including spacing and text hierarchy; verify by named test output.
AC-3: Test-writer adds an accessibility proof that scrollable column bodies are keyboard-focusable or otherwise satisfy axe `scrollable-region-focusable`; verify by axe or Playwright output.
AC-4: Test-writer records current failing/weak evidence from the audit screenshots and E2E failure; verify by task-body Test Evidence.

Proof bundle: behavioral

## Evidence Expectations
Failing column-polish tests, axe/focusability evidence, and screenshot references from `.owlbear/scratch/cockpit-visual-audit/`.