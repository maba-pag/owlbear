---
id: 1388
title: 'P2-13: Test Cockpit decision viewport and resolution UX'
status: backlog
priority: needed
created: 2026-05-06T01:04:50.731483+00:00
updated: 2026-05-06T01:06:57.315899+00:00
tags:
- cockpit
- audit-remediation
- phase-2
- scope:cockpit-web
- type:test
- frontend
- decisions
- ux
parent: 1363
depends_on:
- 1387
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests for a central Cockpit decision viewport and safer resolution UX.

## Problem Evidence
- DRStatusIndicator is a tiny decision count popover rather than a central decision viewport.
- ResolveModal defaults to approved, has terse lower-case choices, and lacks a visible consequence summary.
- Pending decisions need clear task context, body preview, and loading/error/empty states.

## Acceptance Criteria
- Tests prove the decision UI shows pending decisions with task link/context, agent or request type, age, body or preview content, and clear loading, error, and empty states.
- Tests prove resolution choices explain consequences for approved, rejected, and needs-info outcomes.
- Tests prove accidental approval is not the easiest path, including no unsafe approved default.
- Tests prove action labels and modal state are meaningful and PDS-compatible.
- Tests include keyboard/focus expectations for the decision workflow, leaving the final global accessibility gate to a separate task.
- Tests prove expected decision errors use the frontend error contract from #1375.
- The proof fails against the audited tiny-popover/default-approved behavior and is suitable for #1389 to satisfy.

## Scope
- In scope: Cockpit frontend decision viewport and resolution-modal UX tests.
- Out of scope: backend decision lifecycle from #1385, data/refetch plumbing from #1387, task detail workflows, global accessibility audit, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1389.
