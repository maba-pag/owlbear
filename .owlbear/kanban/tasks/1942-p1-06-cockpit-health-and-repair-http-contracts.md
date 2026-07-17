---
id: 1942
title: 'P1-06: Assemble Cockpit workspace health contracts'
status: build
priority: high
created: 2026-07-17T02:32:17.957866+02:00
updated: 2026-07-17T16:31:53.628436+02:00
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
In scope: Cockpit Python response models, root route assembly, ideas checking, domain-health aggregation, synchronous repair orchestration, obsolete task scan/repair/cleanup route removal, shallow cleanup-view forwarding removal, and explicit maintenance route retention. Task #1942 removes the Cockpit consumer of the temporary Kanban cleanup bridge; final deletion of that now-unconsumed Kanban contract belongs to #1959. Out of scope: core Kanban/memory algorithms, final Kanban cleanup model/API deletion, and frontend state or rendering.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted root route family, synchronous repair contract, and three-step cleanup migration. Domain behavior is supplied by dependencies #1937, #1938, #1939, #1940, and #1941.

## Complexity Waiver
The three high-proof criteria share one HTTP assembly and failure-isolation domain. Keeping route assembly, typed envelopes, repair orchestration, and obsolete-route inventory together avoids a forwarding-only wiring task and remains one backend pipeline pass.

## Proof Guidance
Use the assembled FastAPI application with real domain engines; inject only one lower checker to prove failure isolation. Exercise route inventory, repair completion, and explicit maintenance reachability at the HTTP boundary. Include a production-consumer scan proving Cockpit no longer calls the temporary Kanban cleanup bridge; #1959 owns deletion of the unconsumed Kanban API. Add durable integration coverage for public contract regressions where current coverage is insufficient.

[[2026-07-17T07:55:28+02:00]]
## Builder Notes
Change envelope: no code changes; task cannot be implemented without resolving the shaped route-inventory dependency.

Files changed: none.

Change Module Map deviations: none.

Proof selected: read-only inspection of task 1942 and dependencies, current Cockpit route inventory, and existing health/repair domain APIs.

Builder-challenger result: not run because the task was rejected before implementation; DONE proof is inapplicable.

Commands run: none.

Follow-up risks: Dependency #1941 is still in shape with an unresolved contract about whether generic cleanup is removed or migrated. Task #1942 AC3 explicitly requires omitting old task scan/repair/cleanup endpoints, so implementation would require guessing against an unresolved canonical decision. Dependency #1939 is also still in build and not closed. Resolve those planning/dependency issues, then return #1942 to build.

[[2026-07-17T16:31:53+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: Builder rejection dated 2026-07-17 on task #1942.
- Classification: local task repair. The rejection requested resolution of cleanup-route ownership and completion of domain prerequisites; no new product or architecture choice remains.

### Facts Checked
- Tasks #1937, #1938, #1939, and #1940 are archived as completed.
- Task #1941 is in build and now explicitly retains `KanbanEngine.cleanup` only as a temporary bridge for the existing Cockpit caller while establishing explicit claim/session maintenance.
- OpenSpec Design decision 8 and tasks 2.2, 4.3, and 4.4 define the runnable sequence: #1941 establishes maintenance, #1942 removes Cockpit cleanup consumers, and #1959 deletes the unconsumed Kanban cleanup API.
- The authoritative route family remains `GET /health/live`, `GET /health`, focused module GETs, and `POST /health/tasks/repair`; explicit claim sweep and activity compaction remain outside Workspace Status.

### Exact Task Changes
- Renamed placeholder title `x` to `P1-06: Assemble Cockpit workspace health contracts`.
- Clarified scope: #1942 owns obsolete Cockpit route and shallow view-forwarding removal, but not final Kanban cleanup API/model deletion.
- Clarified proof guidance: assembled FastAPI route behavior plus a production-consumer scan must prove Cockpit no longer calls the temporary cleanup bridge.
- Preserved all three acceptance criteria, dependencies, parent, priority, and tags.

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owner |
|---|---|---|---|---|
| Cockpit root application/routes | Static liveness and existing API assembly | Add root health family before SPA fallback | New and changed | #1942 |
| Cockpit health response/service layer | No assembled four-module contract | Add typed aggregation, isolation, ideas health, and synchronous repair adaptation | New | #1942 |
| Cockpit mutation routes and view | Old scan/repair/cleanup forwarding | Remove obsolete routes and cleanup consumer; retain explicit maintenance routes | Removed and changed | #1942 |
| Kanban engine cleanup contract | Temporary migration bridge | Delete only after Cockpit removal | Removed later | #1959 |

### Product Invariant Map
| Product Invariant | Owning Task | Normal-Path Boundary | Proof |
|---|---|---|---|
| Health reads expose typed module evidence without mutation and isolate one checker failure | #1942 | Assembled FastAPI app | HTTP integration with real engines and one injected failing checker |
| Task repair responds only after terminal outcomes and post-scan | #1942 | `POST /health/tasks/repair` | HTTP integration over temporary Kanban storage |
| Obsolete Cockpit cleanup consumers are absent while explicit maintenance remains reachable | #1942 | Assembled route and production-consumer inventory | Route checks plus exact source scan |
| Generic Kanban cleanup API is absent at completed change | #1959 | Kanban public inventory | Focused package checks after #1942 |

### Resulting Route And Board Audit
- Shaper challenger approval from the connected #1941 migration repair remains applicable; this task repair implements that approved graph without expansion.
- #1942 routes to build, parent #1945, with dependencies #1937, #1938, #1939, #1940, and #1941.
- Completed prerequisites are satisfied; #1941 intentionally keeps #1942 dependency-blocked until explicit lease maintenance is implemented.
- After #1942 completes, #1943 and #1959 become eligible on their respective frontend-state and Kanban-finalization branches.
