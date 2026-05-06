---
id: 1389
title: 'P2-14: Implement Cockpit decision viewport and resolution UX'
status: backlog
priority: needed
created: 2026-05-06T01:04:52.300671+00:00
updated: 2026-05-06T01:06:57.326039+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:fix
- frontend
- decisions
- ux
parent: 1363
depends_on:
- 1388
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement a central Cockpit decision viewport and safer resolution UX.

## Problem Evidence
- DRStatusIndicator is a tiny decision count popover rather than a central decision viewport.
- ResolveModal defaults to approved, has terse lower-case choices, and lacks a visible consequence summary.
- Pending decisions need clear task context, body preview, and loading/error/empty states.

## Acceptance Criteria
- The decision UI shows pending decisions with task link/context, agent or request type, age, body or preview content, and clear loading, error, and empty states.
- Resolution choices explain consequences for approved, rejected, and needs-info outcomes.
- Accidental approval is not the easiest path, including no unsafe approved default.
- Action labels and modal state are meaningful and PDS-compatible.
- Decision workflow keyboard and focus behavior meets the expectations captured in #1388, with final global accessibility verification left to a separate task.
- Expected decision errors use the frontend error contract from #1375.
- The implementation satisfies #1388 without changing backend decision lifecycle semantics.

## Scope
- In scope: Cockpit frontend decision viewport and resolution-modal UX.
- Out of scope: backend decision lifecycle from #1385, data/refetch plumbing from #1387, task detail workflows, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1388.
