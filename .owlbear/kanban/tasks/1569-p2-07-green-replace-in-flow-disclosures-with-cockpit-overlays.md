---
id: 1569
title: 'P2-07 GREEN: Replace in-flow disclosures with Cockpit overlays'
status: backlog
priority: needed
created: 2026-05-14T18:26:42.474114+00:00
updated: 2026-05-14T20:10:26.318208+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - overlay
  - visual-remediation
parent: 1559
depends_on:
  - 1563
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Implements the failing proof from #1563 after #1560 records the overlay strategy. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6, 7, and 8.

## Scope
In scope: Health, DR, Cleanup, ConfirmDialog, ResolveModal, and ArchivalModal overlay composition.
Out of scope: sidecar inspector redesign, filter contents, card metadata, and PDS asset delivery changes.

## Acceptance Criteria
AC-1: Given Health or DR status trigger opens, Cockpit shows a floating disclosure anchored to the trigger and shell/status-bar dimensions remain unchanged; verify with the named E2E dimension checks from #1563.
AC-2: Given Cleanup, resolve, or archival workflow opens, Cockpit presents a blocking modal or sheet with focus trap and focus return on close; verify with the named accessibility checks from #1563.
AC-3: Given #1560 selects PPopover, PModal, or PSheet roles, the implementation follows that mapping or records a named exception in the policy artifact; verify by diff inspection plus UI test output.

Proof bundle: behavioral

## Evidence Expectations
Passing #1563 overlay tests and policy-exception diff when needed.


## Planner Audit Amendment — Context Menu Coverage
Implementation must satisfy #1563 AC-4 in addition to the original overlay ACs.

Additional AC-4: The task context menu / transition menu is treated as a composed overlay surface with stable layering, item spacing, hover/focus treatment, keyboard navigation, and no board reflow.

Evidence expectation: context-menu screenshot and named #1563 test output.


## Content Audit Amendment — RepairPanel Coverage
Implementation must satisfy #1563 RepairPanel overlay coverage in addition to Health, DR, Cleanup, ConfirmDialog, ResolveModal, ArchivalModal, and the task context menu.

Additional AC-5: `RepairPanel` confirmation/loading/result/error states are recomposed through the chosen overlay policy with stable focus behavior, no status-bar reflow, and PDS-consistent action/result treatment; verify with the named #1563 tests.

Evidence expectation: repair-flow screenshot/state evidence plus passing #1563 RepairPanel checks.