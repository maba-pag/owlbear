---
id: 1564
title: 'P2-08 RED: Specify filter and form control behavior'
status: backlog
priority: needed
created: 2026-05-14T18:26:23.465310+00:00
updated: 2026-05-14T18:27:14.689061+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - filters
  - forms
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
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6, 7, and 8. This lane waits on the PDS control policy captured by #1560.

## Scope
In scope: filter trigger, search, select controls, blocked binary control, active filter summary, clear action, and task-editor visible form controls.
Out of scope: overlay primitives, card metadata, and responsive layout changes.

## Acceptance Criteria
AC-1: Test-writer adds E2E checks for filter workflow controls: search, status or priority select, blocked binary control, active filter count or chips, and clear action; verify by quality-runner output for named tests.
AC-2: Test-writer adds DOM assertions that core filter controls avoid native text input, checkbox or radio, and native option usage when the #1560 policy forbids them; verify by named test output.
AC-3: Test-writer records current failing evidence for the bolted-on filter workflow from the audit; verify by artifact inspection of Test Evidence.

Proof bundle: behavioral

## Evidence Expectations
Failing filter/form tests and explicit policy linkage to #1560.