---
id: 1378
title: 'P2-03: Test Cockpit task detail edit validation and dirty state'
status: backlog
priority: critical
created: 2026-05-06T01:04:32.576780+00:00
updated: 2026-05-06T01:06:57.255127+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- task-detail
- validation
parent: 1363
depends_on:
- 1377
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests for explicit parent/dependency validation and intentional save behavior in the task detail editor.

## Problem Evidence
- parseDependsOn silently drops invalid dependency entries.
- parseParent turns invalid input into null, risking accidental parent clearing.
- Detail fields are mostly hidden-label or raw controls with no dirty-state model.

## Acceptance Criteria
- Tests prove invalid parent input is shown to the user and never converted into a null parent update.
- Tests prove invalid dependency entries are shown to the user and never silently dropped from the intended edit.
- Tests prove saves are disabled or blocked while validation errors exist.
- Tests prove dirty state is tracked so unsaved edits are visible and saves are intentional.
- Tests prove validation errors render through the frontend error-contract behavior from #1375.
- The proof fails against the audited parser behavior and is suitable for #1379 to satisfy.

## Scope
- In scope: Cockpit frontend task detail editor validation, dirty-state, and save-intent tests.
- Out of scope: task-detail model expansion from #1377, action gating, conflict resolution, backend validation changes, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1379.
