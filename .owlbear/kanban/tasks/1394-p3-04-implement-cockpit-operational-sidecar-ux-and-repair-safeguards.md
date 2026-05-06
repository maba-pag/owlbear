---
id: 1394
title: 'P3-04: Implement Cockpit operational sidecar UX and repair safeguards'
status: backlog
priority: needed
created: 2026-05-06T01:09:39.582140+00:00
updated: 2026-05-06T01:12:22.957395+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:fix
- frontend
- sidecar
- activity
- health
- repair
- interface-contract
parent: 1363
depends_on:
- 1393
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Implement operational sidecar UX, frontend type fixes, and repair safeguards proven by #1393.

## Problem Evidence
- Activity rows lack proper interactive semantics, active filter state, and human-readable timing.
- Frontend session assumptions do not match backend nullable fields.
- Sidecar subtab routing has drifted, leaving HistorySubtab unused or unreachable.
- Repair confirmation does not sufficiently disclose affected files, quarantine destination, or consequences.

## Acceptance Criteria
- Activity and session frontend types match the backend SessionRecord nullability for task_id and agent.
- Activity and session surfaces provide clear filters, active filter state, formatted durations and times, loading states, empty states, error states, and safe row navigation semantics.
- HistorySubtab is either integrated into the sidecar navigation model or removed cleanly with tests updated to match the chosen product shape.
- Health and repair admin flow shows scan and error state from #1373, lists affected files before repair when available, explains fixed, quarantined, and failed outcomes, and makes destructive or quarantine consequences explicit.
- Repair retry, dismiss, and refetch behavior is covered by #1393 and uses the frontend error contract from #1375.
- No valid dashboard, task detail, decision, or health behavior is removed while tightening sidecar behavior.

## Scope
- In scope: Cockpit frontend activity/session types, activity/session sidecar UX, history subtab integration or removal, health repair confirmation and outcomes, and tests needed to satisfy #1393.
- Out of scope: responsive dashboard layout from #1392, global accessibility remediation from #1396, backend health scanner changes, docs, delivery packaging, and cache/SSE invalidation from #1346.

## Counterpart
Test task: #1393.
