---
id: 2059
title: 'P9-05: Prove acceptance rejection and minimum correction'
status: build
priority: high
created: 2026-07-25T17:19:59.273509+02:00
updated: 2026-07-25T17:19:59.273509+02:00
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