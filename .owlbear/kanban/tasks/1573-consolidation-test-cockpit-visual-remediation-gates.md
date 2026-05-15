---
id: 1573
title: 'consolidation test: Cockpit visual remediation gates'
status: backlog
priority: needed
created: 2026-05-14T18:27:04.901264+00:00
updated: 2026-05-14T20:10:59.711376+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - consolidation-test
  - visual-remediation
parent: 1559
depends_on:
  - 1567
  - 1568
  - 1569
  - 1570
  - 1571
  - 1572
  - 1575
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 4, 6, 8, and 10. This consolidation task verifies the coordinated dashboard after the implementation siblings complete.

## Scope
In scope: screenshot or visual-regression coverage, structural gates for overlays and overflow, PDS-policy conformance checks, and final dashboard evidence.
Out of scope: feature implementation, redesign policy changes, and CDN asset-mode changes.

## Acceptance Criteria
AC-1: Test-writer adds or updates visual-regression coverage for desktop home, selected sidecar, filters, context menu, DR or health overlays, cleanup or resolve modal, dark mode, tablet, and mobile; verify by quality-runner report references for those states.
AC-2: Test-writer adds structural gates that fail when status disclosures render in flow, document horizontal overflow occurs at 320px, or production visible controls violate the #1560 PDS policy without a recorded exception; verify by named test output.
AC-3: Reviewer records one Review Evidence row per visual state in AC-1 and compares screenshots to the post-remediation Cockpit surface; verify by artifact inspection of Review Evidence.

Proof bundle: critical

## Evidence Expectations
Visual-regression report, named structural tests, and one review evidence row per covered state.


## Planner Audit Amendment — Added Coverage
The graph review added #1574/#1575 for column polish and tightened context-menu coverage in #1563/#1569.

Additional AC-4: Consolidation includes column header labels, count badges, empty states, and column-body focusability from #1575 in the visual/regression evidence.

Additional AC-5: Consolidation includes the task context menu / transition menu as a required visual state and structural overlay gate.

Evidence expectation: reviewer records evidence rows for columns/empty states and context menu, in addition to the original AC-1 visual states.


## Content Audit Amendment — RepairPanel Visual Gate
Consolidation must include the repair flow because the audit lists `RepairPanel` as part of the overlay remediation lane.

Additional AC-6: Consolidation evidence includes at least one repair-flow visual state, covering confirmation plus either loading/result/error, and verifies it follows the same overlay policy as Health/DR/Cleanup/resolve/archive surfaces.

Evidence expectation: reviewer records a RepairPanel evidence row alongside the other required overlay visual states.


## Content Audit Amendment — Keyboard Reachability Gate
Consolidation must guard against repeating the audit finding where visible controls were removed from normal tab flow.

Additional AC-7: Structural gates fail when core visible controls in shell, status bar, nav rail, sidecar, filters, cards, or overlays are unreachable by keyboard tab navigation, unless a `tabIndex={-1}` usage is explicitly documented as focus-management for a modal/sheet/popover.

Evidence expectation: reviewer records a keyboard reachability evidence row or links the named Playwright traversal test.