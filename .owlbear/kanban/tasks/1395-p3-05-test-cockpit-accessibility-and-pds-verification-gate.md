---
id: 1395
title: 'P3-05: Test Cockpit accessibility and PDS verification gate'
status: backlog
priority: needed
created: 2026-05-06T01:09:42.087185+00:00
updated: 2026-05-06T01:12:26.037041+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:test
- frontend
- accessibility
- pds
- visual-verification
- keyboard
parent: 1363
depends_on:
- 1392
- 1394
- 1383
- 1389
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write accessibility, keyboard, PDS, and viewport verification tests for the stabilized Cockpit dashboard workflows.

## Problem Evidence
- Cards, context menu items, and activity rows are clickable divs without full keyboard semantics.
- Drag and drop has no keyboard alternative for task movement.
- Several dialogs and popovers have weak focus handling.
- Current core UI uses hardcoded colors and inline styling contrary to frontend conventions.

## Acceptance Criteria
- Automated accessibility checks, such as axe or an equivalent, cover core dashboard workflows and pass once #1396 is implemented.
- Keyboard workflow checks cover task selection, task movement or action menus, decision resolution, activity navigation, repair flow, dialogs, and popovers.
- Tests prove dialogs and popovers have consistent focus management, meaningful accessible names, and predictable dismissal behavior.
- PDS verification rejects hardcoded hex priority colors and avoidable bespoke pseudo-controls in core Cockpit UI where design-system components or tokens exist.
- Viewport checks at 320px, 768px, 1024px, and 1440px prove there is no incoherent overlap, hidden main board, or unusable sidecar state.
- The proof fails against the audited clickable-div, missing keyboard movement, weak focus, and hardcoded styling behavior and is suitable for #1396 to satisfy.

## Scope
- In scope: automated accessibility tests, keyboard workflow checks, focus-management checks, PDS verification, and viewport verification for core Cockpit dashboard workflows.
- Out of scope: creating new task-detail features from #1383, creating new decision UX from #1389, implementing responsive dashboard design from #1392, implementing sidecar behavior from #1394, docs, delivery packaging, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1396.
