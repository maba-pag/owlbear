---
id: 2006
title: 'P3-07: Supersede evidence and create corrective work'
status: build
priority: medium
created: 2026-07-22T21:59:17.003316+02:00
updated: 2026-07-22T21:59:17.003316+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - invalidation
  - supersession
  - corrective-work
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-007
parent: 1979
depends_on:
  - 2004
  - 2005
ac:
  - 'AC-1: Given a finding against packet implementation/local proof, packet plan/dependency/proof,
    admitted design authority, node integration, or whole-change integration, the
    public planner returns respectively a build repair, node shape revision, design
    re-entry with no local job, build-owned node repair through shape correction,
    or affected-node shape/build correction route; the late-work class is `implementation-defect`,
    `unforeseeable-discovery`, `planning-omission`, or `scope-change`.'
  - 'AC-2: Given one or more invalidated receipts, the public closure includes only
    receipt and job descendants whose computed validity depends on them; applying
    it atomically appends one supersession receipt, cancels or supersedes stale open
    jobs, and creates the planned corrective jobs without rewriting prior receipts,
    attempts, findings, or jobs.'
  - 'AC-3: Replaying the same finding set and invalidation identity returns the same
    supersession and corrective identities; a conflicting set or injected write failure
    returns a stable conflict or abort and leaves the prior current chain observable
    without partial corrective work.'
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
- `packet_id`: `DN-003-PK-007`

## Outcome
Typed findings invalidate the minimum affected receipt closure, append immutable supersession evidence, dispose stale open jobs, and create exact corrective jobs while preserving prior chains.

## Scope
In scope: finding targets and late-work classes; receipt/job dependency indexes; affected-descendant closure; supersession transaction; stale-job disposition; corrective-route matrix; deterministic identities, replay, and conflict behavior.

Out of scope: global designer workflow, agent execution, dispatch waves, proof checkout, MCP, Cockpit, and mutation of prior evidence.

## Current Foundation And Ownership
Build over purpose-specific receipt validity and native request disposition from packets `DN-003-PK-005` and `DN-003-PK-006`. The runtime returns typed design re-entry when authority expansion is required; it does not perform that design work.

## Authority
Resolve behavior from `REQ-008`, `NEG-010`, `IF-003`, `RISK-003`, `PROOF-003`, and design section 10. Preserve `implementation-defect`, `unforeseeable-discovery`, `planning-omission`, and `scope-change` as distinct late-work classes.

Proof guidance: use a table-driven corrective-route matrix plus generic receipt/job DAG closure and transaction failure injection through the public invalidation operation.