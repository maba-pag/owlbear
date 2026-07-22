---
id: 1994
title: 'P2-02: Atomically publish admission and initial shape jobs'
status: build
priority: low
created: 2026-07-22T05:49:48.187184+02:00
updated: 2026-07-22T05:49:48.187184+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - storage
  - transactions
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-002
parent: 1978
depends_on:
  - 1993
ac:
  - 'AC-1: Given an error-free admission assessment and an empty temporary native
    job store, `validate_and_admit` returns one immutable receipt tied to the exact
    digest and one `shape` job per authored delivery node; each job targets that node,
    requires the receipt, stores only operational identity/state, and copies no authority
    prose.'
  - 'AC-2: Given any evaluation error, stale source identity or digest, unsafe path,
    conflicting receipt/job identity, or injected persistence failure, the operation
    returns stable diagnostics and leaves zero newly visible jobs and no newly valid
    receipt; verify pre/post inventories and bytes at every staged-publication boundary.'
  - 'AC-3: Given concurrent attempts for one change and digest, exactly one complete
    generation commits with no overwrite, duplicate node job, partial generation,
    or temporary residue; replay returns the existing generation only when every receipt/job
    identity matches, otherwise the existing ReceiptStore conflict path reports without
    mutation.'
  - 'AC-4: Given success and forced failures before, during, and after publication,
    public readback observes either the complete receipt-plus-job generation or no
    admitted generation; success returns only after durable identity-bound records
    are readable, and failure cleanup is limited to the current admission attempt.'
  - 'AC-5: The focused admission, ChangeRevision, and receipt suites pass with Ruff
    clean on touched files; inspection confirms claims, attempts, transitions, requests,
    invalidation, supersession, generalized recovery/health, MCP, HTTP, and UI remain
    absent from this packet.'
proof_bundle: existing+challenge
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
- `packet_id`: `DN-002-PK-002`

## Outcome
The public validate/admit operation commits one immutable schema-version-1 admission receipt plus exactly one initial shape job per delivery node as one observable generation, or returns stable findings with no newly visible admission or jobs.

## Scope
In scope: validate/admit composition over the real evaluator; minimal native shape-job identity/state required at admission; staged receipt/job publication; conflict-safe all-or-none commit, replay, concurrency, scoped cleanup, durable readback, public exports, and focused transaction/failure tests.

Out of scope: shape execution; claims, attempts, completion, requests, activity, invalidation, supersession, generalized transaction recovery or health; build/accept/audit job creation; MCP, HTTP, and UI contracts.

## Authority
Resolve normative behavior from `DN-002`, `REQ-002`, `REQ-003`, `IF-002`, `RISK-003`, `RISK-007`, and `PROOF-002` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`, plus the job-record and transaction constraints in sections 7, 9, and 13 of `design.md`. This bootstrap task cannot add, weaken, or supersede those obligations.

Proof guidance: exercise the assembled public validate/admit operation before any native jobs exist. Use temporary repository/job stores and failure injection only below admission; do not mock the evaluator. Run the focused admission, ChangeRevision, and receipt suites plus Ruff on touched files. Durable tests are required by the atomic no-work-before-admission boundary.