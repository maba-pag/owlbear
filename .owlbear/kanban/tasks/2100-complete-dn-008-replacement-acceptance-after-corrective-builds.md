---
id: 2100
title: Complete DN-008 replacement acceptance after corrective builds
status: build
priority: high
created: 2026-07-28T05:20:51.823233+02:00
updated: 2026-07-28T05:20:51.823233+02:00
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
  - 2099
ac:
  - 'AC-1: Given public MCP `reject_accept` with one or more same-node `build-repair`
    routes and a positive unused replacement ID, rejection persists one new current-digest
    `accept` job whose predecessors are the corrective build IDs and leaves the original
    superseded; `pick_jobs` omits the replacement until those receipts are current,
    then exposes it as the sole current accept.'
  - 'AC-2: Plan-only correction or design re-entry forbids a replacement ID and persists
    no eager accept. Mixed plan/build or cross-node work, a missing/nonpositive required
    ID, an unexpected ID, or an active/archived collision returns public parameter,
    invalidation, or identity failure before persisting rejection state.'
  - 'AC-3: Replaying an all-build rejection returns the same replacement accept; changing
    its ID returns identity conflict without mutation. Injected rejection interruption
    leaves no finding, supersession receipt, corrective job, replacement accept, failed
    event, or partial archive.'
  - 'AC-4: In a temporary public MCP scenario, finishing only a strict subset of one
    or two corrective builds keeps the replacement out of `pick_jobs`; finishing the
    remainder exposes and starts it at the corrected commit. The proof never invokes
    final audit, DN-015, `setup/finalize.py`, or a live carrier path.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A public delivery-node rejection with one or more same-node build-repair routes atomically publishes one immutable replacement `accept` job gated on the complete corrective-build closure, so corrected work can return to independent acceptance without reopening the rejected job.

## Scope
In scope: accept-only continuation identity at public MCP `reject_accept` and `NativeRuntime`; all-build route classification; atomic replacement publication; dependency readiness; replay, conflict, interruption; focused temporary-workspace proof. Out of scope: `reject_audit`, Cockpit mutation routes, plan-generated replacement acceptance, design re-entry continuation, DN-013 final audit, live carrier mutation, and compatibility/backfill behavior.

## Authority
DN-008, REQ-006, REQ-008, IF-009, DEC-009, PROOF-007, RISK-008, and RISK-009 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`. Archived DN-008 #1985 and corrective packet-authority repair #2099 are lineage dependencies. Late discovery is #2097's resumed-dispatch failure after successful corrective finish.

## Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact |
|---|---|---|---|
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Validate and atomically publish accept rejection, replay, findings, invalidation, events, and cleanup. | Add accept-only replacement identity; classify all-build/plan-only/design/malformed closures; prepare, publish, replay, and expose one replacement accept for eligible all-build corrections. | `RejectAcceptRequest` gains `replacement_accept_job_id`; `RejectAuditRequest` must not expose it. |
| `serve/kanban/src/owlbear_kanban/invalidation.py` | Prepare immutable corrective routes/jobs and supersession participants. | Read-only corrective job-kind and identity authority consumed by rejection preparation. | None. |
| `serve/kanban/src/owlbear_kanban/jobs.py` | Define immutable job identity and readiness dependencies. | Reuse existing `accept` record with predecessor IDs and current node-plan digest. | No schema field addition. |
| `serve/kanban/src/owlbear_kanban/dispatch.py` | Select jobs whose authority and predecessor receipts are current. | Read-only eligibility boundary used by focused proof. | None. |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` | Validate public MCP reject parameters. | Expose replacement identity only for `reject_accept`; keep `reject_audit` unchanged. | Public reject-accept schema changes. |
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | Adapt public MCP reject operations to runtime requests. | Forward accept-only replacement identity without leaking it to reject-audit. | Public `reject_accept` gains one conditional field. |
| Focused Kanban/MCP tests | Protect rejection atomicity, replay, and public dispatch. | Add parameterized readiness and malformed-route controls; retain #2097 as downstream assembled proof. | Test-only. |

Complexity waiver: route classification, replacement identity, transaction atomicity, replay, and dispatch readiness are inseparable properties of one public rejection transaction. Splitting them would allow an under-gated or non-replayable continuation to pass component proof. Use parameterized existing harnesses rather than one test per criterion.

## Scenario Matrix
- One and multiple same-node build-repair routes.
- Replacement omitted before any corrective receipt and after partial completion; sole eligible accept after all corrective receipts are current.
- Exact replay, changed identity, active/archived collision, missing/nonpositive identity.
- Plan-only correction and design re-entry with no eager accept.
- Mixed plan/build and cross-node closure fail closed.
- Injected rejection interruption leaves no partial state.
- Focused temporary public MCP rejection-to-replacement-dispatch proof; downstream #2097 retains complete correction-to-audit ownership.

## Repair Closure Map
| Failure Key | Claimed Production Boundary | Current-Source Artifacts | Cheapest Disconfirming Check | Causal Proof Or Negative Control | Executor Availability |
|---|---|---|---|---|---|
| `DN-013/resumed-dispatch-no-accept-job` | Public `reject_accept` preserves immutable failed acceptance while creating a dependency-gated path to re-acceptance for an all-build corrective closure. | `native_runtime.py::{RejectAcceptRequest,_prepare_accept_rejection,_commit_accept_rejection,_reject_accept_replay}`, `invalidation.py::{PreparedInvalidation,InvalidationRequest}`, `runtime_transaction.py::RuntimeTransaction`, MCP models/server, existing `JobRecord`/`DispatchRuntime.pick_waves`, and `test_complete_native_delivery.py`. | Reject an accept with two corrective builds and an explicit replacement ID. The replacement exists but is omitted immediately and after one corrective finish; after both receipts become current, `pick_jobs` exposes it alone. Current HEAD has no replacement and empty resumed waves. | Positive: same target/current digest, both corrective predecessors, sole eligibility after both receipts. Negative: malformed identity, mixed/cross-node route, plan-only/design no eager accept, replay mismatch, and interruption leave no partial continuation. | Existing NativeRuntime, MCP reject/start/finish/pick tools, JobStore, RuntimeTransaction hooks, and temporary acceptance/PROOF-013 harnesses are available; no new engine or route is required. |

## Proof Guidance
Use public MCP `reject_accept`, `pick_jobs`, `start_job`, and purpose-specific finish boundaries over a temporary workspace. Prove replacement existence through persisted `JobStore` and readiness through public dispatch. Do not complete #2097's final audit here and never pass the live carrier, live change root, or finalizer input.