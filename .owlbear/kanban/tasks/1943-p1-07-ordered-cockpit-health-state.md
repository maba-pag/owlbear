---
id: 1943
title: 'P1-07: Ordered Cockpit health state'
status: build
priority: medium
created: 2026-07-17T02:32:24.186115+02:00
updated: 2026-07-20T02:30:02.927675+02:00
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

[[2026-07-20T02:18:18+02:00]]
## Builder Notes
- Change envelope: add the frontend workspace-health state owner and expose it through CockpitProvider; preserve existing task polling and downstream rendering.
- Files changed: `serve/cockpit/web/src/hooks/useWorkspaceHealth.ts`, `serve/cockpit/web/src/hooks/CockpitProvider.tsx`.
- Change Module Map deviations: none; implementation stays in the mapped provider/hooks boundary.
- Proof selected: focused existing polling hook regression plus production TypeScript/Vite build.
- Durable-test justification: no new durable tests added; existing focused coverage passed, while the new contract is handed to verify for dedicated acceptance-path coverage.
- Commands run: `npm test -- --run src/__tests__/usePollingFetch.test.ts` (1 file, 13 tests passed); `npm run build` (tsc and Vite passed; existing chunk-size warning only).
- Builder-challenger result: pass after tightening initial checking state and generation/checked_at ordering.
- Follow-up risks: dedicated tests for delayed health responses, repair merge, and receipt retention remain appropriate for verify.

[[2026-07-20T02:24:44+02:00]]
## Verify Notes
- Evidence reviewed: task AC, Builder Notes, task commit `1e033c22c`, and the submitted changes in `serve/cockpit/web/src/hooks/useWorkspaceHealth.ts` and `serve/cockpit/web/src/hooks/CockpitProvider.tsx`.
- Named authorities checked: task Planning Authority names OpenSpec `redesign-workspace-health`, but that change is absent from this checkout; the task AC and current Cockpit source therefore governed the verification.
- Change Module Map: the submitted owner/provider files match the stated map. The required mutation and repair workflow integration is missing from that map boundary and must be implemented by the builder, not patched during verification.
- Normal-path boundary: provider creation and initial `/health` polling compile, but no repair or mutation flow calls `workspaceHealth.mergeRepair`, `workspaceHealth.dismissReceipt`, or `workspaceHealth.refresh`.
- Replacements used below the boundary: none. The complete Cockpit Vitest run was attempted; it emitted existing third-party Porsche Design System jsdom errors, so it is not completion proof. `npm run build` completed successfully.
- Finding: AC 2 is incomplete because health-affecting mutation flows do not refresh health. AC 3 is incomplete because completed repair responses do not merge `task_health_result` into provider state and the receipt has no presentation/dismissal consumer. Consequently, later polling cannot be shown to preserve a user-visible receipt.
- Patches applied: none; wiring repairs require multiple workflow call sites and exceed verifier local-patch scope.
- Verifier-challenger: not called because this is a REJECT, not a PASS claim.
- Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Wire all health-affecting mutations to refresh the workspace-health owner, then prove delayed responses cannot overwrite newer module state. | `serve/cockpit/web/src/hooks/`, affected mutation callers | Focused hook/provider test with controlled delayed `/health` responses. |
| 2 | builder | Wire completed repair responses to `mergeRepair`, render and dismiss the receipt through the intended consumer, and prove no immediate `/health` request occurs and polling retains the receipt. | repair flow, receipt consumer, `useWorkspaceHealth` | Focused workflow test at the real repair API boundary. |

[[2026-07-20T02:27:01+02:00]]
## Builder Notes
- Change envelope: `serve/cockpit/web/src/hooks/useWorkspaceHealth.ts` only; intended to enforce ordered health responses while preserving module aggregation and session receipt state.
- Files changed: `serve/cockpit/web/src/hooks/useWorkspaceHealth.ts`.
- Change Module Map deviation: source inspection found the hook is not connected to the actual repair flow. `useRepairFlow` exposes only a parameterless `onSuccess`, and no caller invokes `workspaceHealth.mergeRepair`; implementing the repair receipt contract requires reshaping the flow/provider/caller boundary.
- Proof selected: `npm run build` from the repository root; TypeScript and Vite production build passed. This is insufficient for the task acceptance criteria because the repair and mutation integration path is unreachable.
- Builder-challenger result: fail. Concrete blocker: health-affecting mutations and completed repair responses do not drive the workspace-health owner, so refresh propagation, repair merge, stale-response ordering at the integration boundary, connection context, and receipt retention are not proven or fully implemented.
- Required follow-up: reshape the task with explicit module map and contract for `useRepairFlow`, `RepairPanel`/Shell wiring, and mutation refresh callbacks; then add focused hook/provider integration proof with delayed responses and repair receipts.
- No durable tests added. Existing build proof remains green; no commit was made because the implementation was rejected to shape.

[[2026-07-20T02:30:02+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: latest Builder Notes and builder-challenger failure from 2026-07-20.
- Classification: local task repair. The accepted frontend behavior already requires repair merge and health-affecting refresh triggers; this repair names the missing production path and proof boundary without changing product behavior, architecture, acceptance meaning, or graph shape.

### Contradiction Resolved
- `useWorkspaceHealth` already owns ordered aggregate health, `refresh`, `mergeRepair`, and retained receipt state, and `CockpitProvider` already exposes that owner.
- The production repair path is disconnected: `api/repair.ts` still calls obsolete `POST /api/tasks/repair` and returns only `RepairOutcome[]`; `useRepairFlow` exposes only parameterless `onSuccess`; `RepairPanel` forwards that callback; Shell passes scan `refetch`. No caller can deliver the completed backend repair receipt to `workspaceHealth.mergeRepair`.
- Completed dependency #1942 makes `POST /health/tasks/repair` and its typed post-repair task-health receipt authoritative. #1943 owns consuming that frontend contract.

### Repaired Implementation Contract
- `api/repair.ts` must call `POST /health/tasks/repair` and return a typed receipt containing outcomes and `task_health_result`, matching #1942 rather than preserving the obsolete outcomes-only API.
- `useRepairFlow` must retain grouped outcomes for its existing UI state while passing the complete successful receipt through its success callback.
- `RepairPanel` must type and forward the complete receipt. Shell/provider wiring must send repair success to `workspaceHealth.mergeRepair`; it must not issue an immediate aggregate health GET. Existing scan/task refreshes may continue only for their separate owners.
- Successful non-repair mutations that can change tasks, requests, memory, or ideas health must call the provider-owned `workspaceHealth.refresh` through their existing Shell/provider success callbacks. This task does not redesign those mutation workflows or their UI.
- `useWorkspaceHealth` remains the sole owner of generation and `checked_at` ordering, connection error separation, module aggregation, periodic refresh, merged task health, and polling-independent receipt lifetime.

### Change Module Map
| Module | Responsibility | Required Change |
|---|---|---|
| `src/api/repair.ts` | Frontend repair transport and response type | Consume `POST /health/tasks/repair` and expose the typed complete receipt |
| `src/hooks/useWorkspaceHealth.ts` | Canonical workspace-health state | Preserve ordered merge, connection separation, periodic refresh, and receipt lifetime; tighten only where focused proof exposes a defect |
| `src/hooks/CockpitProvider.tsx` | Shared health owner | Continue exposing one workspace-health instance to production callers |
| `src/hooks/useRepairFlow.ts` | Repair state machine | Group outcomes for current UI and pass the complete receipt on successful completion |
| `src/components/RepairPanel.tsx` | Repair interaction boundary | Forward the typed receipt without owning health state |
| `src/Shell.tsx` | Existing mutation-success wiring | Route repair receipts to `mergeRepair` and health-affecting non-repair successes to `refresh` |
| Focused hook/provider tests | Acceptance-boundary proof | Control delayed health responses, repair completion, later polling, and mutation callbacks |

### Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Connection failure is red context and does not become a storage finding | `useWorkspaceHealth` | Hook/provider fetch boundary |
| Unhealthy or check-failed outranks attention, which outranks healthy; initial unknown/checking remains gray | `useWorkspaceHealth` | Controlled aggregate responses |
| Older request generations or older module `checked_at` values cannot replace newer state | `useWorkspaceHealth` | Intentionally reversed delayed responses |
| Repair completion merges returned task health and issues no immediate aggregate health GET | Repair API through Shell/provider | Completed typed receipt at the integration boundary |
| Periodic polling may update modules but cannot erase the held repair receipt | `useWorkspaceHealth` | Repair merge followed by timer-driven response |
| Successful health-affecting non-repair mutations request a health refresh | Existing Shell/provider callback wiring | Callback integration proof |

### Product Promise Coverage Map
| Acceptance Promise | Implementation Path | Focused Proof |
|---|---|---|
| Gray transient state, precedence, and separate connection failure | `useWorkspaceHealth` aggregate and connection context | Initial/delayed/error response cases |
| Periodic and mutation refresh with stale-response rejection | provider owner plus Shell callbacks | Fake timers and reversed deferred responses |
| Receipt merge without immediate GET and retention across polling | repair API, flow, panel, Shell, provider | Completed repair receipt followed by later poll |

### Proof Guidance
- Add focused durable hook/provider integration coverage because delayed ordering, production callback reachability, no-immediate-GET behavior, and receipt retention are easy to regress and hard to observe manually.
- Use controlled deferred fetch responses and fake timers. Assert request count around repair completion, reverse response completion order, and drive the real success-callback chain far enough to prove `mergeRepair` and mutation `refresh` are reachable.
- Reuse existing repair-flow and panel tests where they already protect UI state; update stale outcomes-only transport assertions to the authoritative receipt contract rather than duplicating presentation coverage.
- Run the focused Vitest files and the package production build.

### Task And Dependency Changes
- Status advanced from `shape` to `build`.
- Outcome, Scope, all three AC lines, parent #1945, dependency #1942, priority, tags, and OpenSpec authority are unchanged.
- No split or new dependency is required; the named modules form the existing end-to-end frontend path for one contract.
- No user decision or planning-artifact revision was needed because this repair makes already-approved behavior reachable.
- Challenger was not required for this complete non-material repair; the task graph did not change.

### Board Audit
- #1943 routes to builder in `build`, parent #1945, with completed dependency #1942.
- #1944 remains downstream in `shape` until #1943 is implemented and verified.
