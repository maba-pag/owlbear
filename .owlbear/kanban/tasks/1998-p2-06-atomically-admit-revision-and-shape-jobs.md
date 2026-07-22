---
id: 1998
title: 'P2-06: Atomically admit revision and shape jobs'
status: build
priority: low
created: 2026-07-22T13:46:36.783681+02:00
updated: 2026-07-22T14:10:35.123875+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - transactions
  - concurrency
  - storage
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-006
parent: 1978
depends_on:
  - 1994
  - 1997
ac:
  - 'AC-1: Given a passing evidence assessment, completed graph diagnostics, one tracked
    corrected fixture, the corresponding initial shape-job generation, and an empty
    native job store, public validate/admit returns one receipt bound to the revision
    digest plus that complete generation; receipt and jobs are durable and readable
    before success returns.'
  - 'AC-2: An evaluator error, stale source identity or digest, unsafe path, identity
    conflict, or injected failure at a staged publication boundary returns stable
    diagnostics; public readback exposes neither a newly admitted receipt nor a job
    created by that attempt.'
  - 'AC-3: Concurrent attempts commit one complete generation without overwrite, duplicate
    jobs, partial visibility, or temporary residue; replay returns the existing generation
    only when receipt and job identities match, otherwise it reports conflict without
    mutation.'
  - 'AC-4: Running the R1 through R4 defective fixtures and representative `DV-003`
    through `DV-011` cases through the real public validate/admit boundary leaves
    job and receipt inventories unchanged; corrected fixtures create complete generations.'
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
- `delivery_node_id`: `DN-002`
- `packet_id`: `DN-002-PK-006`

## Outcome
The assembled public validate/admit transaction publishes one immutable admission receipt plus the initial shape-job generation as one all-or-none observable commit.

## Scope
In scope: real evaluator composition; contained live job storage; admission receipt assembly; staged multi-file publication; source/digest binding; conflict-safe replay; concurrent attempts; failure injection, cleanup, durability, complete-generation readback, and zero mutation for rejected revisions.

Out of scope: shape execution; claims, attempts, completion, requests, activity, invalidation, supersession, generalized transaction recovery or health; build/accept/audit job creation; MCP, HTTP, and UI.

## Authority
Resolve normative behavior from `DN-002`, `IF-002`, and `PROOF-002` in `graph.yaml` plus sections 7, 9, and 13 of `design.md`. Reuse #1997's tracked fixtures at the assembled boundary; do not re-author them. General runtime remains DN-003.

Complexity waiver: four high-proof AC are inseparable observations of one receipt-plus-jobs atomicity invariant; splitting publication, rollback, and concurrency would permit partial behavior to pass independently.

Proof guidance: exercise the real public validate/admit operation over temporary workspaces with failures injected below admission. Reuse the real evaluator, job generation, ReceiptStore, and tracked incident fixtures; run focused admission/transaction plus existing ChangeRevision and receipt regressions.

[[2026-07-22T14:10:35+02:00]]
## Shape Notes
- AC-1 now names assembled input states rather than the ambiguous task-number range `#1993 through #1997`. Atomic validate/admit ownership is unchanged.
- #1999 supplies the evidence assessment transitively through #1994 and #1995/#1997. Route remains dependency-gated build.
