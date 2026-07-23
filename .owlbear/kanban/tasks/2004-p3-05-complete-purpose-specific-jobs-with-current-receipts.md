---
id: 2004
title: 'P3-05: Complete purpose-specific jobs with current receipts'
status: build
priority: medium
created: 2026-07-22T21:58:55.620202+02:00
updated: 2026-07-23T14:54:49.789874+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - transitions
  - receipts
  - validity
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-005
parent: 1979
depends_on:
  - 2003
ac:
  - 'AC-1: Given a current shape attempt and a caller-supplied packet DAG contained
    by its delivery node, `finish_shape` atomically writes only that node-plan namespace,
    its digest and shape receipt, the packet build jobs, one dependency-gated accept
    job, one `succeeded` activity event for the owning attempt, and the archived shape-job
    disposition; out-of-bound references or transaction failure publish none of them.'
  - 'AC-2: Given a current build, accept, or audit attempt with kind-specific evidence,
    its finish operation accepts only current delivery and node-plan digests, predecessor
    receipts whose computed validity is current, and the required target, code, and
    proof fields, then atomically creates one immutable receipt, appends one `succeeded`
    activity event, and archives the same-kind job; replay writes no second receipt
    or success event.'
  - 'AC-3: Given stale authority or node plan, an invalidated or superseded predecessor,
    or a later code revision touching the receipt boundary, receipt validity reports
    the stable failing reason and dependent jobs remain unreleased; a permitted descendant
    with no touched-boundary change remains current.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-005`

## Outcome
Shape, build, accept, and audit completion validates current authority and predecessor closure, atomically records kind-specific evidence plus the owning attempt's `succeeded` activity event, and archives the immutable-purpose job without backward movement.

## Scope
In scope: node-plan digest computation; assembled receipt-validity consumption; public finish-shape, finish-build, finish-accept, and finish-audit transaction policies; successful attempt finalization; predecessor release; authority, node-plan, supersession, code-revision, and touched-boundary staleness.

Finish-shape atomically records one caller-supplied packet DAG contained by the target node, its digest and shape receipt, build jobs, one dependency-gated accept job, the owning attempt's `succeeded` event, and the archived shape-job disposition.

Out of scope: node-plan semantic review and agent contracts, corrective routing, dispatch and writer leases, proof-checkout creation, MCP, and UI.

## Current Foundation And Ownership
Use the contracts and stores from archived #2000/#2001, the transaction kernel from #2002, and the attempt/activity and receipt-currentness boundaries exported by #2003. #2003 owns and exports the reusable receipt-currentness evaluator produced by tasks #2014-#2016. #2004 owns assembled `finish_shape`/`finish_build`/`finish_accept`/`finish_audit` policy, invokes that evaluator, records `succeeded`, archives the job, and proves the evaluator through its public finish/validity boundary. DN-006 through DN-008 and DN-014 later provide the agents and semantic evidence that call these generic engine operations.

## Authority
Resolve behavior from `REQ-009`, `REQ-016`, `NEG-002`, `NEG-010`, `IF-003`, `RISK-003`, `PROOF-003`, and design sections 4.2, 4.3, 6, 7, and 13.

Proof guidance: exercise the public finish and receipt-validity boundaries with temporary Git revisions below the engine. For shape, build, accept, and audit, verify one transaction invokes the exported evaluator and publishes the kind-specific receipt, archived job disposition, and one `succeeded` activity event. Include stale authority, node-plan, predecessor, supersession, touched-boundary, replay, and transaction-failure cases.

[[2026-07-23T11:29:01+02:00]]
## Shape Notes
- Repair classification: local contract alignment inside the user-authorized connected reshape. Task #2003 already assigns successful completion's `succeeded` event to #2004, but #2004's operative AC omitted it.
- Repair: replaced the complete operative body and AC so `finish_shape`, `finish_build`, `finish_accept`, and `finish_audit` atomically publish the kind-specific receipt, archived job disposition, and one `succeeded` event for the owning attempt. Replay and transaction failure cannot leave a duplicate or partial success record.
- Dependency closure: #2004 consumes the transaction kernel through #2002 and attempt/activity contract through #2003. Node-plan, receipt-validity, and successful completion behavior are owned here; no request or invalidation producer is required.
- Board audit: remains `build`, parent #1979, depends on #2003, and is correctly dependency-blocked.

[[2026-07-23T14:54:49+02:00]]
## Ownership Clarification
- The earlier Shape Notes sentence assigning receipt-validity behavior to #2004 is superseded by the current operative contract. #2003 owns and exports the reusable receipt-currentness evaluator produced by #2014-#2016. #2004 consumes and proves that evaluator through its public finish/validity boundary while alone owning assembled `finish_shape`/`finish_build`/`finish_accept`/`finish_audit` policy, `succeeded` publication, receipt creation, and job archival.
- Outcome, AC-1 through AC-3, status `build`, parent #1979, and dependency #2003 remain unchanged.
