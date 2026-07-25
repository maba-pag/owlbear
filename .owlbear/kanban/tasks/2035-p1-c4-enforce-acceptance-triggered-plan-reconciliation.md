---
id: 2035
title: 'P1-C4: Enforce acceptance-triggered plan reconciliation'
status: build
priority: high
created: 2026-07-25T02:46:46.300991+02:00
updated: 2026-07-25T06:05:36.513367+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-003
  - node:DN-004
  - corrective
  - scope:core
  - runtime
  - reconciliation
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2033
  - 2034
ac:
  - 'AC1: Given an initial plan job for a dependent node before predecessor implementation,
    native start eligibility permits the plan when authority, request, claim, and
    writer gates pass; predecessor acceptance is not a plan prerequisite.'
  - 'AC2: Given `finish_plan` with one bounded packet DAG, one recoverable transaction
    writes the isolated plan, plan receipt, build jobs, accept job, and immutable
    attempt event; replay duplicates no artifact and conflicting plan identity returns
    a stable diagnostic.'
  - 'AC3: Given a build job, start/dispatch returns `ERR_START_AUTHORITY_STALE` without
    mutation when its node-plan digest differs from the isolated current plan. With
    a matching digest, an active plan job for the target, a missing or ambiguous archived
    accept job for an authored predecessor, or a non-current predecessor accept receipt
    returns `ERR_START_PREDECESSOR_INVALID` without mutation; otherwise existing packet-dependency
    gates apply.'
  - 'AC4: Given successful `FinishAcceptRequest`, caller IDs map to direct dependents
    in `nodes.yaml` declaration order; one transaction issues the accept outcome and
    creates or OCC-updates one unclaimed active plan job per dependent with current
    predecessor accept-job edges while preserving request/block state. Exact replay
    duplicates no artifact; wrong count/order/ID, collision, multiple active plan
    jobs, or a claimed plan job returns `ERR_FINISH_IDENTITY_CONFLICT` without mutation.'
  - 'AC5: Given `finish_plan` for a reconciliation job, the plan receipt contains
    current predecessor accept receipt IDs and replacement plan bytes define a new
    digest; prior-digest build jobs return `ERR_START_AUTHORITY_STALE`, while new-digest
    build jobs become eligible only after authored predecessor acceptance. Invalidating
    a predecessor accept follows job edges through dependent reconciled work and leaves
    a disjoint node current.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Publish isolated plans and causally reconcile dependent plans before build, with minimum invalidation closure.

## Scope
In scope: `FinishAcceptRequest`, `finish_plan`, build/accept creation, initial plan eligibility, dependent reconciliation plan-job creation or OCC update, build start/dispatch gates, predecessor-accept currentness, invalidation, and query projection.

Out of scope: planner content, review, or policy; dispatch ordering/profile assignment; MCP transport; and full DN-006 publication/closure.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-032; DEC-033; DN-003; DN-004; IF-003; IF-004; PROOF-003; engine-side support for REQ-025.

## Engine Handoff
- `FinishAcceptRequest` extends `FinishJobRequest` with caller-supplied `reconciliation_plan_job_ids`. IDs map to direct dependents by filtering `delivery/nodes.yaml` declaration order for nodes whose `dependencies` contain the accepted node.
- `finish_accept` derives targets. An existing unclaimed active plan job must match the supplied ID and is OCC-updated; otherwise an unused supplied ID creates one. Count, order, collision, multiple-active, or claimed-plan conflicts are atomic identity failures. Existing request/block state is preserved.
- The active plan job is the reconciliation-required marker. Its predecessor edges are current archived accept jobs for accepted direct predecessors, ordered by the dependent node's authored dependencies. Missing not-yet-accepted predecessors are omitted; ambiguous current accept identity conflicts.
- The acceptance transaction publishes the accept outcome and creates or updates reconciliation plan jobs. It does not repurpose job disposition or `superseded_by_receipt_id`.
- Build start/dispatch rejects stale node-plan digests and blocks while a reconciliation plan job is active or a predecessor accept is unavailable/non-current. Initial plan eligibility is unchanged.
- Existing `FinishPlanRequest` publishes the reconciled plan; predecessor edges become plan-receipt predecessor IDs, replacement bytes define a new digest, and new jobs reference that digest. Existing invalidation follows those job edges and retains typed supersession semantics.
- The accept receipt records reconciliation plan-job IDs for exact replay identity.

Complexity waiver: five AC cover one causal lifecycle matrix; splitting its transaction and currentness assertions would bypass the public runtime boundary.

Proof guidance: run public native-runtime scenarios for a two-node create path, a three-node two-predecessor fold-in/OCC-update path, and predecessor invalidation with a disjoint negative control. Include health proof that no non-supersession receipt is assigned to `superseded_by_receipt_id`.

[[2026-07-25T05:32:04+02:00]]
## Builder Notes

- Change envelope: expected `NativeRuntime.finish_plan`, `finish_accept`, job readiness/currentness, and nearest runtime scenario. The required behavior is acceptance-triggered dependent-plan reconciliation; the cheapest falsifier is a two-node lifecycle scenario using the public native runtime.
- Files changed: none.
- Change Module Map: source confirms `serve/kanban/src/owlbear_kanban/native_runtime.py` is the transition owner. No deviation made.
- Contract gate: rejected. `delivery/nodes.yaml` assigns REQ-025 and IF-007, including superseding-plan creation, to DN-006. This task instead directs engine-side support under DN-003/DN-004 without defining the handoff.
- Concrete blocker: `FinishJobRequest` has no reconciliation job ID, dependent-plan payload, or release command. `finish_accept` delegates to generic `_finish` and has no participant factory for dependent jobs. An initial dependent plan job is archived by `finish_plan`; therefore AC4 cannot create or release reconciliation work without inventing job identity, storage state, and a new public interface.
- Proof selected and run: `uv run pytest serve/kanban/tests/test_native_runtime.py` passed, 25 tests. It proves the existing runtime baseline but cannot prove AC3-AC5 because the required reconciliation input/owner is absent.
- AC-to-evidence: AC1 is supported by current `start_job` predecessor checks; AC2 is covered by the existing plan publication/replay test. AC3, AC4, and AC5 cannot be implemented or proved until shape defines the DN-006 to runtime handoff, reconciliation job identity/allocation, and the exact currentness relation for a superseding dependent plan.
- Current failure key resolution: no prior Verify Required Follow-up.
- Builder-challenger: not invoked because this is a planning reconsideration, not a proposed DONE route.
- Memory assessment: completed for recalled entries; one recalled entry was concurrently unavailable during assessment.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | AC3-AC5/reconciliation-handoff | shape | Define the DN-006 to native-runtime interface: who allocates or reuses reconciliation plan job IDs, what persisted marker makes a plan reconciliation-required, and how `finish_plan` proves its receipt supersedes the prior plan from current predecessor accept receipts. Split engine-only prerequisites from DN-006 planner behavior if appropriate. | `.owlbear/changes/replace-delivery-pipeline/delivery/nodes.yaml`, `delivery/contracts.yaml`, task 2035 AC | REQ-025 ownership is DN-006; `FinishJobRequest` and `NativeRuntime.finish_accept` contain no reconciliation input or participant path. |

[[2026-07-25T06:05:36+02:00]]
## Shape Notes

### Repair Classification
Connected local repair with stale DN-006 projection #1983. Builder failure key `AC3-AC5/reconciliation-handoff` exposed a missing executable handoff between IF-004 engine mechanics and DN-006/IF-007 planner publication; approved behavior and node ownership remain unchanged.

### Repair Closure Map
- Production boundary: `NativeRuntime.finish_accept` and build start/dispatch gates produce IF-004 reconciliation work; DN-006 later consumes that plan job through existing `FinishPlanRequest`/IF-007.
- Current artifacts checked: design sections 6, 8.2, and 8.4; DEC-032; REQ-025; IF-003/004/007; DN-006; `jobs.py`, `native_runtime.py`, `receipt.py`, `invalidation.py`, `runtime_query.py`; #1968 corrective notes; and #1983.
- Disconfirming checks established archived jobs cannot reopen, caller-supplied job IDs are the existing allocation pattern, active jobs are the persisted marker, predecessor edges drive receipt currentness, and `superseded_by_receipt_id` is reserved for typed supersession receipts.
- Causal proof uses two-node creation, three-node two-predecessor fold-in, and invalidation/disjoint scenarios. Negative controls cover ID mismatch/collision, claimed or multiple active plans, stale predecessor evidence, and work-health supersession invariants.

### Contract Repair
- Added `FinishAcceptRequest` caller identity, declaration-order dependent mapping, active-plan OCC fold-in, accept-job predecessor edges, replay identity, and precise build-only readiness diagnostics.
- Old build/accept job dispositions remain immutable; active reconciliation blocks builds before planning and the replacement plan digest makes prior builds authority-stale afterward.
- IF-004/DN-004 owns these engine mechanics. DN-006/IF-007 retains planner content, review, publication, and complete REQ-025 closure.
- AC3 through AC5 now map each failure condition to `ERR_START_AUTHORITY_STALE`, `ERR_START_PREDECESSOR_INVALID`, or `ERR_FINISH_IDENTITY_CONFLICT` without inference.

### Challenge And Route
Challenges caught and corrected non-supersession disposition misuse, missing fold-in proof, IF-009 overreach, stale archive discovery, DN-006 dependency direction, and an unsupported accept-start gate. Final connected challenge passed. Task advances to `build`; #1983 remains dependency-blocked in `shape` as the downstream planner consumer.
