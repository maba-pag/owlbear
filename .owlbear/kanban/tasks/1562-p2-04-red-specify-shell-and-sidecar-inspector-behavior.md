---
id: 1562
title: 'P2-04 RED: Specify shell and sidecar inspector behavior'
status: backlog
priority: needed
created: 2026-05-14T18:26:23.406539+00:00
updated: 2026-05-14T18:35:00.392865+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - sidecar
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
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8. This lane waits on the PDS/redesign policy in #1560.

## Scope
In scope: E2E and accessibility proof for visible product identity, sidecar inspector layout, decision queue composition, and collapse behavior.
Out of scope: overlay internals, filter controls, card metadata, and mobile contract implementation.

## Acceptance Criteria
AC-1: Test-writer adds a desktop Cockpit E2E check for a selected task that observes visible product identity plus separate sidecar header, metadata, body, activity, and action regions; verify by quality-runner output for the named test.
AC-2: Test-writer adds a check that pending decisions render as composed decision items or the chosen DR surface from #1560, not raw document bullets; verify by DOM assertions in the named test.
AC-3: Test-writer adds a keyboard check that sidecar collapse and expansion preserves selected task detail visibility; verify by quality-runner output and task-body evidence.

Proof bundle: behavioral

## Evidence Expectations
Failing E2E proof against the current sidecar and references to audit P0 sidecar findings.


## Planner Audit Amendment — Chrome And Activity Coverage
The initial shell/sidecar RED task covered the inspector but under-specified Cockpit chrome and activity rows.

Additional AC-4: Test-writer verifies status bar and nav rail have intentional hierarchy: visible product identity, active nav affordance, distinguishable Health/DR/Cleanup/Theme roles, and no awkward text overflow in the nav rail.

Additional AC-5: Test-writer verifies activity/history rows and activity filters render as composed operational rows/controls, not raw clickable divs or a loose row of unrelated buttons.

Evidence expectation: failing screenshots/DOM proof for status/nav chrome and activity row hierarchy.