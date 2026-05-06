---
id: 1393
title: 'P3-03: Test Cockpit operational sidecar UX and repair safeguards'
status: backlog
priority: needed
created: 2026-05-06T01:09:38.127439+00:00
updated: 2026-05-06T01:12:20.967140+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:test
- frontend
- sidecar
- activity
- health
- repair
- interface-contract
parent: 1363
depends_on:
- 1367
- 1373
- 1375
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write frontend tests proving the operational sidecar has correct session types, usable activity navigation, and safe health repair safeguards.

## Problem Evidence
- ActivityTab rows are clickable divs with raw spans, no active filter state, and raw numeric durations.
- The frontend Session type assumes task_id is a number and agent is a string, while the backend allows null values.
- ActivityTab passes subtab history, but Shell ignores the subtab.
- HistorySubtab appears unused.
- HealthBadge and RepairPanel expose storage repair through minimal confirmation that omits affected files, quarantine destination, and exact consequences.

## Acceptance Criteria
- Tests prove frontend session types and rendering accept null task_id and null agent values without crashing or misleading display.
- Tests prove activity and session filters show clear active state, formatted durations, formatted times, loading states, empty states, error states, and safe row navigation semantics.
- Tests prove history navigation is coherent: HistorySubtab is either reachable through the sidecar navigation model or no longer present as stale code.
- Tests prove health and repair flows show scan and error state from #1373 before repair decisions.
- Tests prove repair confirmation lists affected files when available, explains fixed, quarantined, and failed outcomes, and states destructive or quarantine consequences explicitly.
- Tests prove retry, dismiss, and refetch behavior uses the frontend error contract from #1375.
- The proof fails against the audited raw activity rows, stale history subtab, and weak repair confirmation behavior and is suitable for #1394 to satisfy.

## Scope
- In scope: Cockpit frontend activity/session types, sidecar activity UX tests, history-subtab routing/removal tests, and health repair safeguard tests.
- Out of scope: dashboard visual layout from #1392, global accessibility gate from #1396, backend health false-OK implementation from #1373, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1394.
