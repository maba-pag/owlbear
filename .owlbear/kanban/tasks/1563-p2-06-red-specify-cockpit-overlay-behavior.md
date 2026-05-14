---
id: 1563
title: 'P2-06 RED: Specify Cockpit overlay behavior'
status: backlog
priority: needed
created: 2026-05-14T18:26:23.435162+00:00
updated: 2026-05-14T18:35:33.614835+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - overlay
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
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6, 7, and 8. This lane waits on the overlay strategy captured by #1560.

## Scope
In scope: Health, DR, Cleanup, ConfirmDialog, ResolveModal, and ArchivalModal overlay behavior.
Out of scope: sidecar layout, filter contents, card metadata, and PDS CDN asset policy.

## Acceptance Criteria
AC-1: Test-writer adds E2E checks that open Health, DR, Cleanup, resolve, and archival surfaces and compare shell/status-bar dimensions before and after each trigger; verify by quality-runner output for named tests.
AC-2: Test-writer adds dialog semantics checks for blocking workflows that observe modal or sheet semantics plus focus return to the trigger after close; verify by Playwright accessibility locators.
AC-3: Test-writer records current failing evidence for Health, DR, and Cleanup inline expansion from the audit; verify by artifact inspection of Test Evidence.

Proof bundle: behavioral

## Evidence Expectations
Failing overlay E2E proof and task-body mapping to audit P0 overlay findings.


## Planner Audit Amendment — Context Menu Coverage
The audit flagged the task context menu as only barely styled, but the initial overlay RED task did not name it.

Additional AC-4: Test-writer includes the task context menu / transition menu in overlay-style checks: it must be layered, visually composed, keyboard-focusable, and have item hover/focus treatment without reflowing board layout.

Evidence expectation: failing current context-menu screenshot/DOM proof from `.owlbear/scratch/cockpit-visual-audit/03-light-context-menu-1440.png`.