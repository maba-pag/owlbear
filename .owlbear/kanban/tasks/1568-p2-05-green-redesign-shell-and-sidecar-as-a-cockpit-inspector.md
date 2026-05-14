---
id: 1568
title: 'P2-05 GREEN: Redesign shell and sidecar as a Cockpit inspector'
status: backlog
priority: needed
created: 2026-05-14T18:26:42.445078+00:00
updated: 2026-05-14T18:35:17.768383+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - sidecar
  - visual-remediation
parent: 1559
depends_on:
  - 1562
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Implements the failing proof from #1562 after #1560 records the redesign policy. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8.

## Scope
In scope: Cockpit chrome identity, sidecar inspector layout, decision item placement per #1560, activity/detail hierarchy, and collapse behavior.
Out of scope: overlay primitives, filter controls, card metadata, and mobile-specific responsive contract.

## Acceptance Criteria
AC-1: Given desktop viewport with a selected task, Cockpit displays visible product identity plus sidecar header, metadata, body, activity, and action regions; verify with the named E2E test from #1562.
AC-2: Given pending decisions exist, Cockpit renders them as composed decision items or in the chosen DR surface from #1560, not raw document bullets; verify with the named DOM assertions from #1562.
AC-3: Given keyboard activation collapses then expands the sidecar, selected task context and focus target remain observable; verify with the keyboard test from #1562.

Proof bundle: behavioral

## Evidence Expectations
Passing #1562 tests and screenshot evidence for selected-task sidecar.


## Planner Audit Amendment — Chrome And Activity Coverage
Implementation must satisfy #1562 AC-4 and AC-5 in addition to the original inspector ACs.

Additional AC-4: Status bar and nav rail use the #1560 visual target: visible product identity, active nav state, role-specific status/action treatment for Health, DR, Cleanup, and Theme, and no nav text overflow.

Additional AC-5: Activity/history rows and filters are recomposed as designed operational controls/rows that match the sidecar hierarchy and PDS policy.

Evidence expectation: desktop and sidecar screenshots showing chrome, selected detail, and activity/history hierarchy.