---
id: 1943
title: 'P1-07: Ordered Cockpit health state'
status: build
priority: medium
created: 2026-07-17T02:32:24.186115+02:00
updated: 2026-07-17T02:33:38.602437+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - state
  - concurrency
parent: 1945
depends_on:
  - 1942
ac:
  - Given delayed initial aggregate health, the provider exposes gray 
    checking/unknown module state; completed module results aggregate with 
    unhealthy/check-failed over attention over healthy, while connection failure
    is red and explicitly separate from storage findings.
  - While Cockpit remains open, periodic and health-affecting mutation refreshes
    update module results; a response older than the held module 
    checked_at/request generation cannot replace newer state.
  - Given a completed repair response, the provider merges its task-health 
    snapshot without issuing an immediate GET /health and later polling does not
    remove the held repair receipt.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Provide one frontend health-state contract with gray transient states, module-aware aggregation, ordered refresh handling, and a repair receipt whose lifetime is independent of polling.

## Scope
In scope: Cockpit web API clients, provider/hooks, refresh triggers, response ordering, connection-context separation, repair-health merge, and receipt state. Out of scope: Workspace Status rendering, repair confirmation UI, and backend contracts.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted status precedence, periodic refresh, stale-response rule, and no-immediate-follow-up-GET decision. HTTP contracts are supplied by dependency #1942.

## Proof Guidance
Use focused hook/provider integration at the fetch boundary with controlled delayed responses. Add durable coverage where response ordering, repair merge, or receipt lifetime would otherwise be easy to regress and hard to observe.