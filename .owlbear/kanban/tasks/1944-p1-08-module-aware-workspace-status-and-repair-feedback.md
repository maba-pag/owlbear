---
id: 1944
title: 'P1-08: Module-aware Workspace Status and repair feedback'
status: shape
priority: medium
created: 2026-07-17T02:32:30.849128+02:00
updated: 2026-07-17T16:29:05.716524+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - ui
  - health
parent: 1945
depends_on:
  - 1943
ac:
  - Given checking, healthy, attention, unhealthy, and check-failed module 
    states, Workspace Status renders an overall light plus 
    task/request/memory/ideas lights and labels; repair remains available when 
    task repairable_count is positive even if unresolved findings make the task 
    row red.
  - Given a completed or partially failed task repair, closing 
    confirmation/popover leaves a dismissible receipt showing completion time 
    and removed/moved/quarantined/skipped/failed/unresolved counts; only 
    unresolved/failed item details are shown, and polling does not erase the 
    receipt.
  - The assembled Cockpit Workspace Status has no generic Cleanup control or 
    task-only scan path, and VS Code integrated-browser observation shows gray 
    initial state followed by module results without overlap or lost feedback.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Replace the task-only status and generic Cleanup experience with a four-module Workspace Status, one task-repair action, and a dismissible repair receipt that survives overlay closure and polling.

## Scope
In scope: Cockpit Workspace Status components and Shell assembly, module and overall indicators, repair availability, confirmation/result presentation, receipt dismissal, generic Cleanup removal, and integrated-browser visual/workflow proof. Out of scope: backend contracts, provider ordering internals, memory purge, and broad keyboard/accessibility expansion.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted module rows, status colors, unresolved-only detail rule, and repair receipt lifetime. Ordered frontend state is supplied by dependency #1943.

## Complexity Waiver
Package-local behavior checks and the VS Code integrated browser are both required: component checks protect state/interaction behavior, while the assembled browser proves overlay lifetime, layout, and visible state transitions. They cover one UI failure domain and should finish in one frontend pass.

## Proof Guidance
Run package-local frontend checks and use the VS Code integrated browser for the assembled workflow. Capture screenshots where they materially prove initial gray state, module layout, or retained feedback; avoid adding durable visual tests unless they protect a recurring product risk.

[[2026-07-17T08:04:08+02:00]]
## Builder Notes

**Verdict:** REJECT to shape. No product files were changed.

**Change envelope:** The shaped implementation is limited to Cockpit Workspace Status components and Shell assembly, module/overall indicators, task-repair availability, confirmation/result presentation, receipt dismissal/lifetime, generic Cleanup removal, and integrated-browser proof. Backend contracts and provider ordering internals are explicitly out of scope; ordered frontend state is supplied by dependency #1943.

**Blocking source evidence:** Dependency #1943 remains in `shape` and depends on #1942. The required health contract is not available in the current source: `GET /health` is only a `{"status":"ok"}` stub; focused `/health/tasks`, `/health/requests`, `/health/memory`, and `/health/ideas` routes are absent; `POST /health/tasks/repair` is absent. Upstream #1942 is itself blocked by the unresolved cleanup-route contradiction in #1941, where the requested cleanup removal conflicts with existing Cockpit consumers while Cockpit route changes are out of scope. Implementing #1944 now would require inventing the provider/API contract, violating the change envelope.

**Files changed:** None.

**Change Module Map deviations:** None; implementation did not begin because the mapped dependency interface is unresolved.

**Proof selected:** Dependency/source inspection was the cheapest discriminating check. It falsified the assumption that the supplied frontend health contract exists. No package tests or browser proof were run because no implementation was made.

**Durable-test justification:** None; no tests were added or changed.

**Commands run:** None; source/dependency evidence was obtained through read-only task and codebase inspection.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|-----------------|---------|----------|
| 1 | shape | Resolve the cleanup-route contradiction and define the authoritative backend health route inventory, including ownership of existing Cockpit consumers. | #1941, #1942; `serve/cockpit/src/owlbear_cockpit/view.py`; `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | Required `/health/*` routes and `POST /health/tasks/repair` are absent; existing cleanup consumers conflict with the upstream removal premise. |
| 2 | shape | Complete and advance dependency #1942, then implement and advance #1943 so the ordered module-health provider contract is available to #1944 without frontend guessing. | #1942, #1943 | #1943 is still `shape`; #1944 depends on it. |
| 3 | shape | Re-dispatch #1944 only after #1943 is build-ready and its provider/API contract is authoritative. | #1944 | Current task scope explicitly treats #1943 as the source of ordered frontend state. |

[[2026-07-17T16:29:05+02:00]]
## Shape Notes

### Repair Source And Classification
- Source: Builder rejection dated 2026-07-17 on task #1944.
- Classification: mechanical hold after rechecking the rejection chain. No product, architecture, acceptance, or dependency change is required for #1944.

### Facts Checked
- The cleanup-route contradiction cited in the rejection is resolved by the approved three-step migration recorded on #1941 and aggregate #1945. Task #1941 is now in build; final Kanban cleanup deletion is owned by #1959 after Cockpit consumer removal.
- Backend prerequisite #1939 is archived as completed.
- Task #1942 remains in shape and owns the authoritative Cockpit health and repair route inventory.
- Task #1943 remains in shape, depends on #1942, and owns the ordered frontend provider/API contract consumed by #1944.
- Task #1944 still depends directly on #1943, so its current scope and AC remain coherent and must not be implemented by inventing provider contracts.

### Change Module Map
| Module | Responsibility | Planned Change | Owner |
|---|---|---|---|
| Cockpit backend health routes | Health, repair, and explicit maintenance HTTP contract | Implement before frontend consumers | #1942 |
| Cockpit web provider/hooks | Ordered module state, refresh, repair merge, receipt state | Implement after #1942 | #1943 |
| Workspace Status and Shell UI | Module rows, repair flow, retained receipt, Cleanup removal | Implement after #1943 | #1944 |

### Product Invariant Map
| Product Invariant | Owner | Proof Boundary |
|---|---|---|
| Backend health/repair contract is authoritative before frontend consumption | #1942 | Assembled FastAPI route inventory |
| Older responses cannot replace newer health/repair state | #1943 | Provider at fetch boundary |
| Module-aware status and retained receipt use the supplied provider contract | #1944 | Assembled Cockpit UI and integrated browser |

### Resulting Route And Board Audit
- No task fields, AC, parent, or dependencies changed.
- #1944 remains in shape, parent #1945, depending on #1943.
- Required sequence remains #1942, then #1943, then #1944.
- Re-enter `/shape 1944` only after #1943 has completed its own shape repair and advanced to build; until then, retaining #1944 in shape prevents implementation against an invented interface.
