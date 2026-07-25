---
id: 2035
title: 'P1-C4: Enforce acceptance-triggered plan reconciliation'
status: shape
priority: high
created: 2026-07-25T02:46:46.300991+02:00
updated: 2026-07-25T05:32:04.750937+02:00
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
  - 'AC3: Given a dependent build without current predecessor accept receipts, start
    returns `ERR_START_PREDECESSOR_INVALID` without mutation; after predecessor acceptance
    and a current superseding plan receipt, the dependency-ready build can start.'
  - 'AC4: Given successful `finish_accept`, one transaction issues the accept receipt,
    creates or releases dependent plan work, and prevents prior-plan builds from starting
    until superseding plan receipts are current.'
  - 'AC5: Given invalidation of a predecessor accept receipt, dependent reconciled
    plan/build closure becomes stale and minimum corrective plan work is created;
    a node outside that dependency closure retains current evidence.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Publish isolated plans and causally reconcile dependent plans before build, with minimum invalidation closure.

## Scope
In scope: `finish_plan`, build/accept creation, initial plan eligibility, predecessor-accept build gating, `finish_accept` dependent-plan release, currentness, invalidation, and query projection.

Out of scope: planner-agent policy, dispatch ordering/profile assignment, MCP transport, and full DN-006 completion.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-032; DEC-033; DN-003; IF-003; IF-004; PROOF-003; engine-side support for REQ-025.

Complexity waiver: five AC cover one causal lifecycle matrix; splitting its transaction and currentness assertions would bypass the public runtime boundary.

Proof guidance: run one native-runtime scenario from initial plan through publication, predecessor acceptance, reconciliation, build release, accept invalidation, and replay.

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
