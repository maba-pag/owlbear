---
id: 2039
title: Compose dispatch completion participants through the native finish 
  callback
status: build
priority: high
created: 2026-07-25T08:00:32.540861+02:00
updated: 2026-07-25T08:00:32.540861+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-004
  - corrective
  - scope:core
  - dispatch
  - runtime
  - type:build
  - rigor:thorough
parent: 1968
depends_on: []
ac:
  - 'AC1: Given a claimed plan, build, or audit job and its matching coordination
    holder, calling the matching DispatchRuntime finish operation supplies a callable
    participant factory to NativeRuntime, publishes the purpose receipt and attempt
    outcome, and removes the holder in the same transaction without TypeError.'
  - 'AC2: Given a finish diagnostic or coordination OCC conflict, DispatchRuntime
    leaves job, attempt, receipt, and coordination state free of partial publication
    and returns the existing stable domain result, verified through the direct real-store
    dispatch boundary.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Adapt `DispatchRuntime` plan/build/audit completion to `NativeRuntime`'s participant-factory contract so coordination-holder release and finish publication remain one transaction.

## Scope
In scope: `serve/kanban/src/owlbear_kanban/dispatch.py::DispatchRuntime._finish`, its call into `NativeRuntime._finish`, coordination replacement composition, and direct dispatch-runtime proof.

Out of scope: picker kinds/profiles/readiness/order, MCP adapters, agent ecosystem, accept reconciliation policy, and planner behavior.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DN-004; IF-004; PROOF-014; current `NativeRuntime._finish` participant-factory signature.

## Proof Guidance
Use direct real `NativeRuntime` plus `DispatchRuntime` tests for plan/build/audit successful completion and finish-diagnostic/OCC no-partial-state controls. Run focused lint and diff checks.

## Shape Notes
Prescribed prerequisite split from #2036 after the assembled PROOF-014 scenario exposed an independent tuple-versus-callable transaction-composition defect before the strict MCP adapter boundary. This task owns only the core completion primitive; #2037 owns strict MCP requests and #2036 owns picker/profile/orchestrator semantics.

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact |
|---|---|---|---|
| `serve/kanban/src/owlbear_kanban/dispatch.py` | Compose coordination with native lifecycle completion | Pass coordination participants through the native callback contract | Internal correction; public results unchanged |
| `serve/kanban/tests/test_dispatch_runtime.py` | Durable dispatch-runtime behavior proof | Add direct success and no-partial-publication scenarios | Test only |

### Repair Closure Map
| Failure Key | Production Boundary | Cheapest Disconfirming Check | Causal Proof |
|---|---|---|---|
| `dispatch-finish/participant-callback` | `DispatchRuntime.finish_plan/finish_build/finish_audit` through `NativeRuntime._finish` | Execute a claimed plan finish with a coordination holder; current source raises tuple-not-callable | Receipt/event publication and coordination removal commit together; diagnostic/OCC controls preserve all stores |

Complexity waiver is unnecessary: one failure domain and one direct proof mode.