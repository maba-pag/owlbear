---
id: 1943
title: 'P1-07: Ordered Cockpit health state'
status: build
priority: medium
created: 2026-07-17T02:32:24.186115+02:00
updated: 2026-07-19T22:00:30.886541+02:00
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

## Builder Notes
- Contradiction: dependency 1942 remains in shape and supplies the unresolved backend HTTP contract; prerequisite 1939 is also unresolved.
- Required follow-up: resolve 1942's backend contract and prerequisite 1939, then reshape 1943 before returning it to build.

[[2026-07-17T07:59:44+02:00]]
## Builder Notes
Dependency gate: task 1942 remains in shape and is the authoritative source for the backend HTTP contracts consumed by this task. Prerequisite 1939 is also unresolved. The frontend provider contract cannot be implemented without guessing those interfaces. Required follow-up: resolve and implement/verify 1942 (including its route-inventory/cleanup decision and prerequisite 1939), then reshape 1943 and return it to build. No repository files were changed; no focused build proof was run.

[[2026-07-17T08:53:52+02:00]]
Released without implementation: task is in `shape`, while builder mode only processes `build` tasks. The task body identifies unresolved dependency #1942 and prerequisite #1939; implementation would require guessing the backend contract. No files changed and no proof run.

[[2026-07-17T16:30:08+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: Builder dependency rejection recorded on task #1943.
- Classification: mechanical hold after rechecking the current prerequisite chain. No product behavior, architecture, acceptance criteria, parent link, or dependency change is required.

### Facts Checked
- Dependencies #1937, #1938, #1939, and #1940 are archived as completed.
- The cleanup-route contradiction is resolved in planning through the approved three-step migration: #1941 establishes explicit claim/session maintenance, #1942 removes Cockpit consumers, and #1959 deletes the unconsumed Kanban cleanup contract.
- Task #1941 is in build and remains the only active domain prerequisite for #1942.
- Task #1942 remains in shape and owns the authoritative Cockpit health, repair, and explicit-maintenance HTTP contract.
- Task #1943 depends directly on #1942 and its scope correctly excludes backend contracts; implementing it now would still require guessing response types and route behavior.

### Change Module Map
| Module | Responsibility | Planned Change | Owner |
|---|---|---|---|
| Kanban engine maintenance | Explicit claim/session sweep semantics | Complete before Cockpit route assembly | #1941 |
| Cockpit backend health routes | Aggregate/focused health, synchronous repair, and maintenance route inventory | Supply HTTP authority | #1942 |
| Cockpit web API/provider/hooks | Ordered module state, refresh triggers, repair merge, and receipt state | Consume #1942 contracts | #1943 |
| Workspace Status UI | Render provider state and retained repair feedback | Consume #1943 state | #1944 |

### Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Explicit lease maintenance is separate from storage-health repair | #1941 | Kanban engine maintenance API |
| Health and repair routes expose the accepted typed contract | #1942 | Assembled FastAPI application |
| Older responses cannot replace newer health or repair state | #1943 | Frontend provider at the fetch boundary |
| Module-aware status renders supplied state without losing feedback | #1944 | Assembled Cockpit UI |

### Resulting Route And Board Audit
- No task fields or planning artifacts changed.
- #1943 remains in shape, parent #1945, depending on #1942.
- Required sequence is #1941 completion, then shape and build #1942, then re-enter `/shape 1943` and route it to build once the backend contract is authoritative.
- #1944 remains downstream of #1943 and must not be advanced first.

[[2026-07-19T22:00:30+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: the latest builder dependency rejection and the prior mechanical hold recorded on #1943.
- Classification: mechanical reroute. The sole readiness gate has cleared; no product behavior, architecture, acceptance meaning, task graph, or planning artifact changed.

### Facts Checked
- #1941 is archived completed, so explicit claim/session maintenance is authoritative and remains separate from storage-health repair.
- #1942 is archived completed with verifier PASS and collector closure. Its assembled FastAPI contract supplies typed aggregate and focused health reads, isolated module failures, synchronous `POST /health/tasks/repair` with post-repair task health, and explicit maintenance routes outside Workspace Status.
- The board reports #1943 dependency status as `ok`. #1943 still owns only Cockpit web API/provider/hook state and does not need to guess backend response behavior.
- Existing Outcome, Scope, AC, Proof Guidance, parent #1945, and dependency #1942 remain correct.

### Readiness And Authorities
- Planning authority remains OpenSpec change `redesign-workspace-health`.
- HTTP authority is completed task #1942 and its assembled Cockpit backend contract.
- Build should preserve the accepted status precedence, periodic refresh, stale-response guard, repair-state merge, no immediate follow-up health GET, and polling-independent repair receipt.

### Change Module Map
| Module | Responsibility | Planned Change | Owner |
|---|---|---|---|
| Cockpit backend health routes | Typed aggregate/focused health and synchronous repair receipt | Completed contract authority | #1942 |
| Cockpit web API/provider/hooks | Ordered module state, refresh triggers, repair merge, and receipt state | Implement against #1942 | #1943 |
| Workspace Status UI | Render provider state and retained repair feedback | Remains downstream | #1944 |

### Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Connection failure remains distinct from storage findings | #1943 | Frontend provider at the fetch boundary |
| Older responses cannot replace newer module or repair state | #1943 | Controlled delayed provider responses |
| Repair merges returned task health without an immediate health GET | #1943 | Repair client/provider integration |
| Polling cannot erase the held repair receipt | #1943 | Provider integration across later refreshes |

### Task And Dependency Changes
- Status advanced from `shape` to `build`.
- No body fields, AC, parent, dependency, priority, tags, or OpenSpec artifacts changed.
- Challenger was not required for this complete non-material repair; no provisional graph or material planning decision changed.

### Board Audit
- #1943 routes to builder in `build`, parent #1945, depending on completed #1942.
- #1944 remains in `shape` downstream of #1943 and must not advance before this provider contract is verified.
- #1959 remains independently in `build` after #1942 and does not block #1943.
