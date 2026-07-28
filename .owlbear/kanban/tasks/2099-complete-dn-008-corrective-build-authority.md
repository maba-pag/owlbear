---
id: 2099
title: Complete DN-008 corrective build authority
status: build
priority: high
created: 2026-07-28T02:34:32.523427+02:00
updated: 2026-07-28T03:34:46.987028+02:00
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
  - 'AC-1: Given plan completion for a delivery node with two packets, each published
    normal `build` job records its corresponding packet ID and current node-plan digest;
    given a `packet-implementation` or `packet-local-proof` corrective route naming
    one admitted packet, the corrective `build` job records the same packet ID and
    current digest; `plan`, `accept`, and `audit` jobs record no packet ID.'
  - 'AC-2: Given a corrective build job created by public `reject_accept`, public
    `start_job` and `finish_build` at a corrected descendant commit select the canonical
    closure by the job packet ID and publish a build receipt with that closure and
    current node-plan digest; a corrective route naming an unknown packet or a currently
    admitted packet different from the finding packet returns `ERR_REJECT_ACCEPT_INVALIDATION_INVALID`
    before publication, while a finish request carrying the closure of a different
    admitted packet returns `ERR_FINISH_EVIDENCE_INVALID` and publishes no receipt.'
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
In scope: explicit packet authority across the DN-008 job, acceptance, invalidation, and finish boundaries plus direct serialized consumers and focused Kanban/MCP proof. Out of scope: DN-013 assembled proof ownership, Cockpit workflow changes beyond its embedded `JobRecord`, live carrier mutation, compatibility/backfill behavior, stale-authority weakening, and unrelated production changes.

## Authority
DN-008, REQ-006/REQ-008/REQ-014, IF-009, PROOF-007, RISK-008/RISK-009 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; late discovery is the #2097 red assembled proof at `8d03bff43dd92e733a4f1432a72b976ec3b14adc`.

## Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact |
|---|---|---|---|
| `serve/kanban/src/owlbear_kanban/jobs.py` | Define and parse immutable operational job identity. | Require packet identity on `build` jobs and forbid it on other job kinds. | `JobRecord` serialization changes. |
| `serve/kanban/src/owlbear_kanban/invalidation.py` | Validate routes and atomically publish minimum corrective jobs. | Require packet identity on build-repair routes, authenticate it against the immutable finding and current node plan, and persist it on corrective jobs. | `CorrectiveRouteRequest`, `CorrectiveRoute`, and `CorrectiveJobPlan` serialization changes. |
| `serve/kanban/src/owlbear_kanban/receipt.py` | Compute canonical node-plan digest. | Read-only authority. | None. |
| `serve/kanban/src/owlbear_kanban/native_runtime.py` | Construct planned jobs and enforce finish authority/evidence. | Persist packet IDs on normal build jobs and select canonical finish closure by packet identity instead of sibling position. | No operation-name change. |
| Direct job/route consumers | Serialize native jobs and corrective route requests. | Supply the required packet identity in tests, proof seeds, and acceptance guidance. | Current schema migration only; no compatibility path. |

## Product Invariant Map
| Product Invariant | Owner | Normal Boundary | Proof |
|---|---|---|---|
| Every normal or corrective build job is bound to one explicit admitted packet and its current node plan. | This task | Public plan finish or `reject_accept`, then `start_job` and `finish_build` | Real runtime/MCP with temporary stores; no replacement of invalidation/runtime. |

## Dependency Closure Map
| Input | Authority | Predecessor |
|---|---|---|
| Normal packet and job identity | Ordered node-plan packets and `FinishPlanRequest.build_job_ids` | #1985 lineage |
| Corrective packet and job identity | `Finding.target_id`, `CorrectiveRouteRequest.packet_id`, and `InvalidationRequest.corrective_job_ids` | #1985 lineage |
| Publication authentication | Finding packet equals route packet and packet belongs to the route target node plan | None; `InvalidationRuntime.prepare` |
| Persisted build authority | `JobRecord.packet_id` plus `compute_node_plan_digest(ChangeRevision, node)` | None; current source |
| Finish closure and diagnostics | Current validated node-plan packet IDs, `ERR_REJECT_ACCEPT_INVALIDATION_INVALID`, and `ERR_FINISH_EVIDENCE_INVALID` | None; current source |
| Atomic replay/conflict/interruption | `RuntimeTransaction`, `InvalidationRuntime` | #1985 lineage |

## Scenario Closure Map
| Risk Boundary | Classes | Owning AC |
|---|---|---|
| Explicit packet binding | two normal packets; valid matching corrective packet; no packet identity on non-build jobs | AC-1 |
| Public corrective binding and finish | valid matching packet; unknown packet; mismatched but admitted finding/route packets; different admitted packet closure | AC-2 |
| Atomic invalidation | replay; identity conflict; interrupted publication | AC-3 |

Proof guidance: replace positional build-to-packet inference with explicit packet identity across route planning, job persistence, and finish. Authenticate corrective route packet identity against the immutable finding and current node plan before publication. Preserve the existing digest stale gate and cite commit `73b11b7c6b863dd36bbe8a26e53ccae912384097` as its focused evidence rather than reopening that scenario axis. Update current serialized consumers directly; add no compatibility or read-time backfill. The first focused check must include the #2097 disposable public proof or an equally public causal slice.

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

## Shape Notes

Material architecture repair for failure key `AC-2/corrective-packet-authority`; user approved explicit packet authority after the digest-only fix exposed positional packet lookup.

### Repair Closure Map
| Failure Key | Claimed Production Boundary | Current-Source Artifacts | Cheapest Disconfirming Check | Causal Proof Or Negative Control | Executor Availability |
|---|---|---|---|---|---|
| AC-2/corrective-packet-authority | Public route planning and `reject_accept` publish one authenticated packet-bound build job; `start_job` and `finish_build` resolve its canonical packet closure. | `finding.py`, `jobs.py`, `invalidation.py`, `native_runtime.py`, current node plans, direct serialized consumers, #2097 disposable proof. | Use a two-packet plan and public corrective rejection, then finish the corrective job; separately submit unknown and mismatched-but-admitted route packets and a closure from the other admitted packet. | The immutable finding packet must equal the route packet before publication; the persisted job packet, not job order or request closure, selects canonical finish authority. | Python 3.14.6, `uv`, pytest, and Git temporary repositories are installed. |

- The first builder pass fixed the original missing `node_plan_digest` in `73b11b7c6b863dd36bbe8a26e53ccae912384097`; that focused stale-authority evidence remains valid and is not reopened as another scenario axis.
- The remaining defect is structural: sibling-job position cannot identify a corrective packet after the original job is archived. `JobRecord`, build-producing corrective routes, normal plan publication, and finish closure now share one explicit packet identity contract.
- `InvalidationRuntime.prepare` must authenticate the caller-supplied route packet against both the immutable finding packet and current target node plan. Unknown or mismatched packets fail as `ERR_REJECT_ACCEPT_INVALIDATION_INVALID` before publication.
- `NativeRuntime._finish_closure` selects by persisted packet identity. A closure from another admitted packet fails as `ERR_FINISH_EVIDENCE_INVALID` without a receipt.
- No compatibility or backfill path is allowed. Current direct fixtures, proof seeds, Cockpit-integrated `JobRecord` consumers, and acceptance guidance are updated to the new schema.
- Python 3.14.6 compilation and PEP 758 disconfirmed repeated challenger concerns about unparenthesized multi-exception clauses.
- Final shaper-challenger decision: `pass` after adding the finding-to-route equality gate and mismatched-but-admitted packet negative control.
- User decision: approved the recommended explicit packet identity architecture.
- Route: return #2099 to `build`; #2097 and #1990 remain gated until independent archive closure.
