---
id: 1571
title: 'P2-09 GREEN: Recompose Cockpit filters and visible form controls'
status: backlog
priority: needed
created: 2026-05-14T18:26:50.109551+00:00
updated: 2026-05-14T20:11:17.324043+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - filters
  - forms
  - visual-remediation
parent: 1559
depends_on:
  - 1564
  - 1569
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Implements the failing proof from #1564 after #1560 records the PDS control policy and #1569 provides the overlay primitive strategy. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6, 7, and 8.

## Scope
In scope: filter workflow controls, active filter summary, clear action, and task-editor visible form-control consistency.
Out of scope: overlay primitive behavior, card metadata, and mobile/tablet layout contract.

## Acceptance Criteria
AC-1: Given filter trigger opens, Cockpit presents search, status or priority select, blocked binary control, active filter count or chips, and clear action; verify with the named tests from #1564.
AC-2: Given a filter value changes, board task count and active filter summary update without shell/status-bar reflow; verify with E2E assertions from #1564.
AC-3: Given #1560 policy allows only named exceptions, filter and visible form controls use mapped PDS controls or cite the exception; verify with DOM assertions plus policy diff inspection.

Proof bundle: behavioral

## Evidence Expectations
Passing #1564 tests and policy exception evidence when used.


## Content Audit Amendment — Task Editor Form Controls
Implementation must apply the #1560 visible-control policy to task-editor form controls, not only the filter panel.

Additional AC-4: Task-editor visible form controls are grouped, labeled, keyboard-reachable, and implemented with mapped PDS controls or recorded exceptions for title/body fields, status/priority controls, tags/dependencies, and confirm/destructive actions; verify with the named #1564 tests.

Evidence expectation: passing editor/form-control tests plus screenshot evidence for an edit/detail workflow with visible form controls.