---
id: 1379
title: 'P2-04: Implement Cockpit task detail edit validation and dirty state'
status: backlog
priority: critical
created: 2026-05-06T01:04:34.112524+00:00
updated: 2026-05-06T01:06:57.260410+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- task-detail
- validation
parent: 1363
depends_on:
- 1378
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement explicit parent/dependency validation and dirty-state handling for the task detail editor.

## Problem Evidence
- parseDependsOn silently drops invalid dependency entries.
- parseParent turns invalid input into null, risking accidental parent clearing.
- Detail fields are mostly hidden-label or raw controls with no dirty-state model.

## Acceptance Criteria
- Invalid parent input is preserved, shown to the user, and never sent as an accidental clearing update.
- Invalid dependency entries are preserved, shown to the user, and never silently dropped from the intended edit.
- Save controls reflect validation and dirty state so unchanged, invalid, and intentionally changed forms are distinct.
- Validation errors use the frontend error-contract behavior from #1375.
- Existing valid parent and dependency edits continue to save correctly.
- The implementation satisfies #1378 without adding action-gating or conflict-resolution behavior owned by later tasks.

## Scope
- In scope: Cockpit frontend task detail editor validation, dirty-state, and save intent.
- Out of scope: task-detail model expansion from #1377, action gating, conflict resolution, backend lifecycle work, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1378.
