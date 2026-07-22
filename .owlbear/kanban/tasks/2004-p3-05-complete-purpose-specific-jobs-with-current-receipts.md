---
id: 2004
title: 'P3-05: Complete purpose-specific jobs with current receipts'
status: build
priority: medium
created: 2026-07-22T21:58:55.620202+02:00
updated: 2026-07-22T21:58:55.620202+02:00
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
    its digest and shape receipt, the packet build jobs, and one dependency-gated
    accept job, then archives the shape job; out-of-bound references or transaction
    failure publish none of them.'
  - 'AC-2: Given current build, accept, or audit attempts with kind-specific evidence,
    each finish operation accepts only current delivery/node-plan digests, predecessor
    receipts whose computed validity is current, and required target/code/proof fields,
    then creates one immutable receipt and archives the same-kind job; job kind never
    changes and no backward transition exists.'
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
Shape, build, accept, and audit completion validates current authority and predecessor closure, commits kind-specific evidence, and archives the immutable-purpose job without backward movement.

## Scope
In scope: node-plan digest computation; receipt-validity engine; public finish-shape, finish-build, finish-accept, and finish-audit transaction policies; predecessor release; authority, node-plan, supersession, code-revision, and touched-boundary staleness.

Finish-shape atomically records one caller-supplied packet DAG contained by the target node plus its shape receipt, build jobs, and dependency-gated accept job.

Out of scope: node-plan semantic review and agent contracts, corrective routing, dispatch and writer leases, proof-checkout creation, MCP, and UI.

## Current Foundation And Ownership
Use the contracts, stores, transaction coordinator, and attempt ownership from preceding packets. Completion policy is generic engine behavior; DN-006 through DN-008 and DN-014 later provide the agents and semantic evidence that call it.

## Authority
Resolve behavior from `REQ-009`, `NEG-002`, `NEG-010`, `IF-003`, `RISK-003`, `PROOF-003`, and design sections 4.2, 4.3, 6, 7, and 13.

Proof guidance: exercise the public finish and receipt-validity boundaries with temporary Git revisions below the engine. Include stale authority, node-plan, predecessor, supersession, touched-boundary, replay, and transaction-failure cases.