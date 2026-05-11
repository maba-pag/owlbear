---
id: 1396
title: 'P3-06: Implement Cockpit accessibility and PDS verification gate'
status: backlog
priority: critical
created: 2026-05-06T01:09:43.591872+00:00
updated: 2026-05-11T09:19:09.553695+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:fix
- frontend
- accessibility
- pds
- visual-verification
- keyboard
parent: 1363
depends_on:
- 1395
blocked: false
block_reason:
claimed_at: 2026-05-11T09:19:09.553695+00:00
archival_reason:
archival_refs: []
---


## Purpose
Implement the accessibility, keyboard, focus, PDS, and viewport verification gate proven by #1395.

## Problem Evidence
- Core Cockpit interactions rely on clickable divs without full keyboard semantics.
- Task movement relies on drag and drop without a keyboard-accessible alternative.
- Dialog and popover focus behavior is inconsistent.
- Core UI still contains hardcoded colors and avoidable bespoke controls where PDS equivalents should carry the interaction.

## Acceptance Criteria
- Keyboard paths exist for task selection, task movement or action menus, decision resolution, activity navigation, repair flow, dialogs, and popovers.
- Dialogs and popovers have consistent focus management, meaningful accessible names, and predictable dismissal behavior.
- Automated accessibility checks and manual keyboard checks from #1395 pass for core dashboard workflows.
- PDS token and component usage is verified; no hardcoded hex priority colors or avoidable bespoke pseudo-controls remain in core Cockpit UI where PDS equivalents exist.
- Viewport checks at 320px, 768px, 1024px, and 1440px prove no incoherent overlap, hidden main board, or unusable sidecar state.
- Accessibility fixes preserve the validated task detail workflow from #1383 and decision workflow from #1389.

## Scope
- In scope: Cockpit frontend accessibility semantics, keyboard alternatives, focus handling, PDS verification, and viewport-gate fixes required to satisfy #1395.
- Out of scope: broader dashboard redesign already covered by #1392, operational sidecar behavior already covered by #1394, frontend structure cleanup from #1397, docs, delivery packaging, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1395.
