---
id: 2099
title: Complete DN-008 corrective build authority
status: shape
priority: high
created: 2026-07-28T02:34:32.523427+02:00
updated: 2026-07-28T02:53:16.471069+02:00
tags:
  - phase-17
  - scope:core
  - type:fix
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-008
  - proof:PROOF-007
parent: 1968
depends_on:
  - 1985
ac:
  - "AC-1: Given `InvalidationRuntime` applies a `build-repair` route for a delivery
    node with a persisted current node plan, the published corrective `build` job
    records that node's canonical `compute_node_plan_digest`; corrective `plan` jobs
    record no node-plan digest until their replacement plan is completed."
  - 'AC-2: Given a corrective build job created by public `reject_accept`, public
    `start_job` and `finish_build` at a corrected descendant commit publish a build
    receipt with the same current node-plan digest; replacing the job digest with
    a stale value returns `ERR_FINISH_AUTHORITY_STALE` with lower code `ERR_RECEIPT_NODE_PLAN_DIGEST_STALE`
    and publishes no receipt.'
  - 'AC-3: Given replay, identity conflict, or interruption before publication, `InvalidationRuntime`
    preserves prior receipts and jobs, returns the prior corrective identity on replay,
    and publishes neither a supersession receipt nor a corrective job after interruption.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Archived DN-008 #1985 and PROOF-007 proved corrective-job publication but not corrective-build completion through public `finish_build`; this late corrective leaf closes that gap without reopening #1985.

## Scope
In scope: the DN-008 acceptance/invalidation boundary in `serve/kanban/src/owlbear_kanban/invalidation.py` plus focused Kanban and MCP proof. Out of scope: DN-013 assembled proof ownership, Cockpit behavior, live carrier mutation, stale-authority weakening, and unrelated production changes.

## Authority
DN-008, REQ-006/REQ-008/REQ-014, IF-009, PROOF-007, RISK-008/RISK-009 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; late discovery is the #2097 red assembled proof at `8d03bff43dd92e733a4f1432a72b976ec3b14adc`.

## Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact |
|---|---|---|---|
| `serve/kanban/src/owlbear_kanban/invalidation.py` | Construct and atomically publish minimum corrective jobs. | Bind corrective build jobs to canonical current node-plan authority. | No public schema or operation change. |
| `serve/kanban/src/owlbear_kanban/receipt.py` | Compute canonical node-plan digest. | Read-only authority. | None. |
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Enforce start/finish authority currency. | Read-only stale-gate authority. | None. |
| Focused Kanban/MCP tests | Protect invalidation and public corrective completion. | Add current/stale/replay/interruption proof. | Test only. |

## Product Invariant Map
| Product Invariant | Owner | Normal Boundary | Proof |
|---|---|---|---|
| Corrective build work remains bound to admitted current node-plan authority. | This task | Public `reject_accept` then `start_job` then `finish_build` | Real runtime/MCP with temporary stores; no replacement of invalidation/runtime. |

## Dependency Closure Map
| Input | Authority | Predecessor |
|---|---|---|
| Corrective route and job identity | `InvalidationRequest`, `plan_corrective_route`, `JobRecord` | #1985 lineage |
| Current node-plan digest | `compute_node_plan_digest(ChangeRevision, node)` | None; current source |
| Stale finish diagnostics | `FinishJobDiagnosticCode.AUTHORITY_STALE`, `ReceiptValidityCode.NODE_PLAN_DIGEST_STALE` | None; current source |
| Atomic replay/conflict/interruption | `RuntimeTransaction`, `InvalidationRuntime` | #1985 lineage |

## Scenario Closure Map
| Risk Boundary | Classes | Owning AC |
|---|---|---|
| Corrective job construction | `build-repair` with current digest; plan revision without digest until plan completion | AC-1 |
| Public corrective finish | current digest success; stale digest fail closed with no receipt | AC-2 |
| Atomic invalidation | replay; identity conflict; interrupted publication | AC-3 |

Proof guidance: begin from the #2097 red public workflow and the normal `_prepare_plan` digest precedent. Make the minimum change in `_corrective_jobs`; preserve the finish-time stale gate and public literals. The first focused check must include the red proof or an equally public causal slice.

[[2026-07-28T02:53:16+02:00]]
## Builder Notes
REJECT: the scoped corrective digest defect is fixed, but the accepted one-owner premise is insufficient for AC-2 in current source.

- Changed `serve/kanban/src/owlbear_kanban/invalidation.py`: corrective `build` jobs now receive canonical `compute_node_plan_digest`; corrective `plan` jobs remain `None` until plan completion. No stale gate changed.
- Changed `serve/kanban/tests/test_invalidation.py`: durable assertions protect the observed build omission and the plan non-binding branch. Existing replay, conflict, interruption, and immutable-history proof remains green.
- Immediate public proof: `uv run pytest serve/mcp-kanban/tests/test_complete_native_delivery.py::test_fresh_consumer_completes_native_delivery_and_audit -q` now passes public `reject_accept` and `start_job`, proving the stale-digest construction defect is repaired, but `finish_build` returns `ERR_FINISH_AUTHORITY_STALE`, detail `build job does not correspond to a packet`, lower code `None`, and no receipt.
- Current-source cause: `NativeRuntime._finish_closure` maps ordinary build jobs to packet closures by sorted same-node/same-digest sibling job IDs. A corrective build shares the canonical digest with its archived original, so the one packet closure cannot index the corrective job. The persisted `finding_id` identifies a canonical packet finding, but current finish logic does not use it.
- Proof: focused invalidation `37 passed`; full Kanban `379 passed` with four multiprocessing deprecation warnings; MCP acceptance subset `45 passed` before its configured 300-second session timeout and no failures; Ruff check and format check clean; editor diagnostics clean; `git diff --check` clean.
- Builder-challenger: `reconsider`. It confirmed AC-2 remains false through the named public boundary and expanding into the read-only `native_runtime.py` owner would exceed the accepted minimum-change map.
- Memory: all 20 recalled entries assessed successfully. No new memory candidate: the remaining defect is task-specific architecture evidence that belongs in this task.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | AC-2/corrective-packet-authority | shaper | Expand the accepted production map to define how a corrective build's existing `finding_id` binds it to the canonical packet closure at finish time, while retaining digest stale/tamper failure and no-receipt behavior; then require the public current and stale causal matrix. | `serve/kanban/src/owlbear_kanban/native_runtime.py`, focused Kanban/MCP tests | Public proof reaches corrected `start_job` then fails `finish_build` with `build job does not correspond to a packet`; builder-challenger `reconsider`. |
