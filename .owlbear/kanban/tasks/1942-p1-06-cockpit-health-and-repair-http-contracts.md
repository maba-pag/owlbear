---
id: 1942
title: 'P1-06: Cockpit health and repair HTTP contracts'
status: build
priority: high
created: 2026-07-17T02:32:17.957866+02:00
updated: 2026-07-17T02:33:38.556130+02:00
tags:
  - phase-1
  - scope:cockpit-backend
  - api
  - health
parent: 1945
depends_on:
  - 1937
  - 1939
  - 1940
  - 1941
  - 1938
ac:
  - Through the assembled FastAPI app, GET /health/live performs no workspace 
    scan; GET /health and focused task/request/memory/ideas reads return typed 
    module results and HTTP 200 when findings exist; absent/empty ideas are 
    healthy; non-UTF-8 content or ideas-file I/O failure is unhealthy; ideas 
    bytes/mtime remain unchanged; one checker exception becomes check-failed 
    without erasing sibling results.
  - Through POST /health/tasks/repair, the HTTP response is withheld until the 
    Kanban operation and post-scan end, then returns timing, terminal 
    counts/outcomes, unresolved findings, and post-repair task health; 
    orchestration failure returns non-2xx without refreshed-health data.
  - The assembled route inventory omits old task scan/repair/cleanup endpoints 
    and retains explicit claim sweep and activity compaction outside Workspace 
    Status.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Expose the root health resource family, ideas integrity, aggregate failure isolation, synchronous task repair receipt, and explicit maintenance routes through the assembled Cockpit backend.

## Scope
In scope: Cockpit Python response models, root route assembly, ideas checking, domain-health aggregation, synchronous repair orchestration, obsolete task scan/repair/cleanup route removal, and explicit maintenance route retention. Out of scope: core Kanban/memory algorithms and frontend state or rendering.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted root route family and synchronous repair contract. Domain behavior is supplied by dependencies #1937, #1938, #1939, #1940, and #1941.

## Complexity Waiver
The three high-proof criteria share one HTTP assembly and failure-isolation domain. Keeping route assembly, typed envelopes, repair orchestration, and obsolete-route inventory together avoids a forwarding-only wiring task and remains one backend pipeline pass.

## Proof Guidance
Use the assembled FastAPI application with real domain engines; inject only one lower checker to prove failure isolation. Exercise route inventory and repair completion at the HTTP boundary. Add durable integration coverage for public contract regressions where current coverage is insufficient.