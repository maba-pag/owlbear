---
id: 2039
title: Compose native dispatch completion participants
status: verify
priority: high
created: 2026-07-25T08:00:32.540861+02:00
updated: 2026-07-25T08:15:52.013826+02:00
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

[[2026-07-25T08:15:52+02:00]]
## Builder Notes

- Change envelope: Correct only `DispatchRuntime._finish` so plan, build, and audit pass coordination replacements through NativeRuntime's participant-factory contract. Preserve the accepted finish callback composition; no MCP, picker/profile, reconciliation, or sibling-task changes.
- Files changed: `serve/kanban/src/owlbear_kanban/dispatch.py`; `serve/kanban/tests/test_dispatch_runtime.py`.
- Change Module Map: matched exactly; no deviations. `dispatch.py` owns coordination-to-native lifecycle composition, and the direct dispatch-runtime test file owns the durable behavior proof.
- Implementation: `_finish` always supplies a callable. It yields the coordination participant tuple and, when present, appends the existing native participant factory result. This removes the raw-tuple-as-callable defect while preserving accept composition.
- Durable-test justification: Existing direct dispatch tests did not exercise completion. The two added tests protect the shared, data-transactional completion path: real NativeRuntime plus DispatchRuntime plan/build/audit publication and diagnostic/OCC no-partial-publication controls.
- Commands run:
  - `uv run pytest serve/kanban/tests/test_dispatch_runtime.py -q --tb=short` — 8 passed.
  - `uv run pytest serve/mcp-kanban/tests/test_mcp_surface_contract.py::TestProof014NativeMcpScenario::test_profiles_release_recovery_and_replanning_use_native_tools -q --tb=short` — moved past `TypeError: 'tuple' object is not callable`; expected downstream failure at #2037's generic FinishAcceptRequest MCP boundary: `NativeRuntime._accept_participants` receives `FinishJobRequest` and asserts `FinishAcceptRequest`.
  - `uv run lint serve/kanban/src/owlbear_kanban/dispatch.py serve/kanban/tests/test_dispatch_runtime.py` — passed.
  - Scoped `git diff --check` — passed; editor diagnostics clean.
- AC-to-evidence:
  - AC1: Direct real-store plan, build, and audit finishes publish receipts and succeeded attempts, with writer/reader coordination holders released in the same completion transaction.
  - AC2: Direct non-owner diagnostic and real stale-token coordination OCC control preserve the active job/holder and leave no terminal attempt event or receipt publication.
- Current failure-key resolution: `dispatch-finish/participant-callback` resolved by callable composition; the direct suite proves callback invocation and atomic state effects.
- Builder-challenger: Initial review identified only the explicitly out-of-scope #2037 downstream adapter failure. Scoped recheck: `pass`; accepted #2039 boundary complete.
- Memory: all recalled entries assessed; one recalled stale ID could not be found by the assessment tool.
- Follow-up risk: PROOF-014 remains blocked after this task only at #2037's known generic FinishAcceptRequest adapter boundary; no scope change made here.
