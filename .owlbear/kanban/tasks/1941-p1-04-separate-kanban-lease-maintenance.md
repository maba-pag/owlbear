---
id: 1941
title: 'P1-04: Separate Kanban lease maintenance'
status: build
priority: medium
created: 2026-07-17T02:32:09.437681+02:00
updated: 2026-07-17T02:33:38.539235+02:00
tags:
  - phase-1
  - scope:kanban
  - maintenance
parent: 1945
depends_on:
  - 1940
ac:
  - Given expired claims and stale activity sessions, the explicit sweep 
    operation releases eligible claims and reconciles their sessions without 
    moving archived tasks or resolving duplicate files.
  - Given task repair on a board with expired claims and activity history, claim
    fields and activity-retention content remain unchanged.
  - The Kanban public maintenance surface has no generic cleanup operation 
    combining claim release, archive reconciliation, duplicate correction, and 
    activity work; claim sweep and activity compaction remain independently 
    callable.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Remove generic cleanup responsibility without losing explicit expired-claim, stale-session, or activity-compaction maintenance.

## Scope
In scope: Kanban engine maintenance APIs and the separation of lease/session work from task health repair. Out of scope: task-health detection, duplicate/archive repair algorithms, Cockpit routes, and frontend controls.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted maintenance separation and generic-cleanup removal. Task repair is supplied by dependency #1940.

## Proof Guidance
Use a focused Kanban engine behavior and public-API inventory check. Include the downstream consumers of the removed cleanup surface in the impact scan; add durable coverage only for a meaningful separation regression.