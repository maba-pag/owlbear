---
id: 1575
title: 'P2-15 GREEN: Polish kanban columns and empty states'
status: backlog
priority: needed
created: 2026-05-14T18:34:00.455181+00:00
updated: 2026-05-14T18:36:45.315974+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - columns
  - empty-states
  - visual-remediation
parent: 1559
depends_on:
  - 1574
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Implements the failing proof from #1574. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8.

## Scope
In scope: column display labels, empty-state styling/copy, column-body focusability, count badge polish, and spacing consistency between columns and cards.
Out of scope: card metadata, filter controls, sidecar layout, and broad responsive shell changes.

## Acceptance Criteria
AC-1: Given the board renders all statuses, column headers use intentional display labels and count badges with consistent hierarchy; verify with the named tests from #1574.
AC-2: Given a column has no tasks, it shows a quiet, designed empty state that does not dominate the board and does not leak raw internal status strings; verify with the visual/DOM tests from #1574.
AC-3: Given a column body is scrollable, keyboard and axe checks pass for scrollable-region focusability; verify with the accessibility proof from #1574.
AC-4: Given desktop, dark, tablet, and mobile screenshots, column surfaces remain visually coherent with the surrounding shell and cards; verify with screenshot evidence or consolidation hooks.

Proof bundle: behavioral

## Evidence Expectations
Passing #1574 tests, axe/focusability evidence, and before/after screenshot references.