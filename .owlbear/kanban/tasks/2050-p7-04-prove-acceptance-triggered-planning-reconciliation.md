---
id: 2050
title: 'P7-04: Prove acceptance-triggered planning reconciliation'
status: build
priority: high
created: 2026-07-25T15:09:49.416616+02:00
updated: 2026-07-25T15:09:49.416616+02:00
tags:
  - phase-7
  - scope:test
  - planner
  - reconciliation
  - invalidation
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-006
  - packet:DN-006-PK-004
  - interface:IF-007
  - proof:PROOF-005
parent: 1983
depends_on:
  - 2049
ac:
  - 'AC-1: Given accepted predecessor implementation evidence, `finish_accept` atomically
    creates or releases the declared dependent reconciliation plan jobs, and previously
    generated dependent builds remain blocked with source-declared stale-authority
    diagnostics until superseding plans publish.'
  - 'AC-2: Given the engine-selected reconciliation job, the shipped planner contract
    folds the current predecessor accept receipt and evidence into a superseding node
    plan, `finish_plan` records predecessor receipt IDs and a new node-plan digest,
    and only new digest-bound builds become startable.'
  - 'AC-3: Given invalidation of that predecessor accept receipt through the existing
    corrective and invalidation runtime, the dependent reconciled plan receipt and
    build closure become stale while a disjoint node plan remains byte-identical.'
  - 'AC-4: The maintained `PROOF-005` suite covers initial topology, per-node atomic
    failure, accepted-evidence fold-in, blocked dependent builds, and predecessor-accept
    invalidation through real planner and runtime boundaries; only repository-search
    results are replaced.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-006-PK-004`. Resolve normative behavior from `DN-006`, `IF-007`, `REQ-025`, `WF-002`, and `PROOF-005`; this record is not specification authority.

## Outcome
Complete `PROOF-005` with acceptance-triggered reconciliation, accepted-evidence fold-in, stale dependent-build blocking, superseding plan publication, and predecessor-accept invalidation.

## Envelope
In: shipped planner contract over real native runtime transactions and public tools where exposed; repository search results may be replaced below the planner.

Out: new runtime semantics, acceptance implementation, planner workflow changes, setup/seed work, and unrelated invalidation classes.

Proof guidance: exercise the current `finish_accept`, reconciliation plan, `finish_plan`, readiness, and invalidation owners; direct store mutation cannot replace the claimed lifecycle boundary.