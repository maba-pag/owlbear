---
id: 2059
title: 'P9-05: Prove acceptance rejection and minimum correction'
status: collect
priority: high
created: 2026-07-25T17:19:59.273509+02:00
updated: 2026-07-25T19:11:02.739662+02:00
tags:
  - phase-9
  - scope:test
  - acceptor
  - rejection
  - corrective-work
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-008
  - packet:DN-008-PK-004
  - interface:IF-009
  - proof:PROOF-007
parent: 1985
depends_on:
  - 2058
ac:
  - 'AC-1: Real-accept scenarios for local defect, missing harness, boundary bypass,
    and stale receipt make the shipped workflow emit canonical finding classes, targets,
    and evidence; `plan_corrective_route` returns the admitted `build-repair | node-plan-revision
    | design-reentry` route with the minimum jobs for each target.'
  - 'AC-2: `AcceptanceRejected` through public `reject_accept` publishes findings,
    one supersession receipt, only planned corrective jobs, failed terminal attempt,
    superseded affected closure, reader release, no accept receipt, and checkout cleanup;
    unrelated receipt bytes remain unchanged and replay is idempotent.'
  - 'AC-3: A tracked acceptor edit produces `AcceptanceBlocked`, write denial, unchanged-identity
    public release, no finding, receipt, or corrective job, and checkout cleanup;
    self-authored tracked state cannot pass.'
  - 'AC-4: Malformed evidence, stale authority, cleanup failure, or injected transaction
    failure returns stable public diagnostics; complete snapshots prove no partial
    finding, event, receipt, job, coordination, or checkout publication.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-008-PK-004`. Resolve behavior from WF-004, IF-009, NEG-003/NEG-009, RISK-008/RISK-009, and PROOF-007.

## Outcome
Complete PROOF-007's rejection, minimum correction, independence, failure atomicity, and cleanup matrix.

## Envelope
In: real accept jobs, shipped dispositions, public reject/release, typed findings/routes, snapshots, replay, and cleanup.

Out: new semantics, auditor, Cockpit, setup, and seed work.

[[2026-07-25T18:59:31+02:00]]
## Builder Notes
- Added the canonical PROOF-007 failure matrix to the shipped node-acceptance workflow, distinguishing finding class/kind/identity from the `plan_corrective_route` target and exact minimum result.
- AC-1: real-accept fixtures cover local defect, missing planned harness, admitted-boundary bypass, and stale receipt. Strict `Finding`/`CorrectiveRoute` objects prove canonical class, target, evidence identity, route, design-reentry flag, and zero-or-one minimum job. The initial challenger failure `AC-1/design-reentry-flag` was repaired with direct boolean and empty-job assertions; rechallenge passed.
- AC-2: public `reject_accept` proves failed terminal attempt, superseded accept job and affected build closure, one supersession receipt, only the planned build repair, no accept receipt, unchanged unrelated receipt, stale affected receipts, finding queries, reader/checkout cleanup, and mutation-free replay.
- AC-3: an actual denied tracked write in the engine checkout yields the shipped `AcceptanceBlocked` shape and unchanged-identity public release. The test proves no finding, receipt, or corrective job publication plus checkout and coordination cleanup.
- AC-4: malformed invalidation, cleanup failure, and injected rejection transaction conflict return stable diagnostics with complete snapshots and checkout manifests unchanged. Native regression scopes retain all-stage publication failure injection.
- Validation: acceptance module 10 passed; full MCP Kanban package 91 passed; native invalidation/runtime/dispatch/checkout scopes 95 passed; focused lint and skill validation passed; diagnostics were empty; final builder challenger passed.

### Required Follow-up
None.

[[2026-07-25T19:11:02+02:00]]
## Verifier Notes
- Verified builder commit `961c2811` and all four ACs against the public MCP path plus native invalidation, lifecycle, dispatch, and checkout owners.
- AC-1: canonical shipped classification is bound to strict finding and route models, including direct `design_reentry` booleans and the zero-job design route. Builder failure key `AC-1/design-reentry-flag` is closed.
- AC-2: rejection publication, exact invalidation closure, unrelated-state preservation, no accept receipt, cleanup, and replay are directly observable through public operations and persistent stores.
- AC-3: verifier repair now parses and exactly compares the shipped `AcceptanceBlocked` mapping, requires the complete shipped orchestration mapping sentence, and proves public release preserves every event identity field before clearing both job claim and attempt pointers. It also proves no corrective publication and complete checkout/reader cleanup. Failure keys `AC-3/shipped-blocked-routing` and `AC-3/exact-field-pointer-clear` are closed.
- AC-4: public malformed/cleanup/transaction diagnostics preserve complete snapshots; native all-stage injected failures cover deeper publication boundaries.
- Final independent scope: 105 tests passed; focused lint and skill validation passed; diagnostics were empty; exact commit inspection was clean; final verifier challenger passed.

### Required Follow-up
None.
