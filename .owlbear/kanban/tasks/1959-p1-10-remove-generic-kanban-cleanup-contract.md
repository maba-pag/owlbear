---
id: 1959
title: 'P1-10: Remove generic Kanban cleanup contract'
status: build
priority: medium
created: 2026-07-17T16:24:21.021571+02:00
updated: 2026-07-17T16:24:21.021571+02:00
tags:
  - phase-1
  - scope:kanban
  - maintenance
  - api
parent: 1945
depends_on:
  - 1942
ac:
  - Given the Kanban package public interface after Cockpit migration, its 
    callable, exported, and documented maintenance inventory contains explicit 
    claim sweep and activity compaction and contains no cleanup operation or 
    CleanupResult.
  - Given a board containing expired claims, stale sessions, archive drift, or 
    duplicate task records, explicit claim sweep changes only eligible claim and
    session state while task repair owns archive and duplicate changes.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Delete the generic Kanban cleanup contract after Cockpit no longer consumes it, leaving explicit claim sweep, activity compaction, and task repair as the only maintenance owners.

## Scope
In scope: Kanban public API, cleanup result model and exports, package documentation, and directly stale Kanban cleanup tests. Out of scope: Cockpit routes and forwarding, frontend cleanup UI, task repair algorithms, and changes to claim lease or activity-compaction semantics.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, Design decision 8 and task 4.4. Dependency #1942 removes the Cockpit cleanup consumer before this task deletes the Kanban contract.

## Proof Guidance
Run focused Kanban behavior checks plus an exhaustive production-consumer and public-inventory scan. Preserve explicit sweep coverage for expired claims and stale-session reconciliation when removing cleanup-specific tests; add no compatibility alias.