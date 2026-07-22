---
id: 2002
title: 'P3-03: Commit and recover runtime transactions'
status: build
priority: high
created: 2026-07-22T21:58:33.866396+02:00
updated: 2026-07-22T21:58:33.866396+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - transactions
  - recovery
  - concurrency
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-003
parent: 1979
depends_on:
  - 2001
ac:
  - 'AC-1: Given an admitted revision, complete evidence, and empty explicit change/work
    roots, public admission publishes one immutable admission receipt plus one active
    shape job per delivery node in one transaction; replay returns the same identities
    and writes no duplicate generation or job record.'
  - 'AC-2: Given injected failure before publication, after a published component,
    or before manifest cleanup, reopening the runtime deterministically restores the
    pre-transaction state or completes the committed transaction; no observable state
    contains a current receipt without its required graph, job, request, or activity
    counterpart.'
  - 'AC-3: Given stale OCC input, concurrent processes, unsafe path substitution,
    or a conflicting immutable destination, the transaction aborts with a stable diagnostic,
    preserves previously committed bytes, and repeated recovery produces the same
    state.'
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
- `packet_id`: `DN-003-PK-003`

## Outcome
One native transaction coordinator commits graph, job, request, receipt, activity, and invalidation mutations as one durable operation or leaves a deterministic recoverable manifest.

## Scope
In scope: transaction plans and manifests; locks and OCC preconditions; staged durable publication; deterministic recovery during runtime open/read; activity participation; and admission receipt plus initial work-plane shape-job integration.

Out of scope: job lifecycle decisions, request resolution semantics, invalidation closure, dispatch waves, global writer leases, proof checkout, MCP, and Cockpit.

## Current Foundation And Ownership
Generalize the narrow DN-002 `AdmissionTransaction` publication behavior over the native stores from packet `DN-003-PK-002`. Admission must target explicit change and work roots; it must not retain a change-local generation manifest as the operational job store. Keep the legacy engine and storage path untouched.

## Authority
Resolve behavior from `REQ-016`, `IF-003` failure semantics, `KEEP-007`, `RISK-002`, `PROOF-003`, and design sections 9.5, 12, and 13.

Proof guidance: exercise the public admission and transaction boundary over temporary roots with two processes and phase-by-phase failure injection. Verify recovery after reopening, not merely cleanup in the same process.