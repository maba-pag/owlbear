---
id: 2055
title: 'P9-01: Atomically reject accept attempts into corrective work'
status: verify
priority: high
created: 2026-07-25T17:19:27.594283+02:00
updated: 2026-07-25T17:38:29.741130+02:00
tags:
  - phase-9
  - scope:kanban
  - acceptance
  - invalidation
  - transaction
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-008
  - packet:DN-008-PK-001
  - interface:IF-009
parent: 1985
depends_on: []
ac:
  - 'AC-1: Given a current owned accept attempt, typed findings and corrective routes,
    affected receipts, stable output IDs, evidence replacements, and code revision,
    public `DispatchRuntime.reject_accept` atomically publishes the findings, failed
    terminal attempt, supersession receipt, minimum corrective jobs, superseded affected
    jobs, reader release, and proof-checkout cleanup; returned and persisted state
    match.'
  - 'AC-2: Replaying the same rejection identity returns the persisted outcome without
    duplicate finding, event, receipt, or job; changing one immutable identity returns
    the stable conflict diagnostic and complete artifact snapshots remain unchanged.'
  - 'AC-3: Missing or stale claim, digest, receipt, finding target, route, job identity,
    checkout cleanup failure, or injected transaction failure returns a stable diagnostic;
    finding, attempt, receipt, job, coordination, and checkout snapshots prove no
    partial publication.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-008-PK-001`. Resolve behavior from WF-004, IF-009, REQ-008, DEC-009, and PROOF-007.

## Outcome
Add one purpose-specific core rejection transaction for an active accept attempt.

## Envelope
In: finding transaction participation, composable invalidation preparation, terminal attempt state, minimum corrective jobs, reader release, checkout cleanup, replay, and stable diagnostics.

Out: MCP exposure, agent workflow, new finding taxonomy, accept success, Cockpit, setup, and seed work.

[[2026-07-25T17:38:29+02:00]]
## Build Notes

Implemented the atomic accept-rejection boundary across native finding, invalidation, attempt, job, receipt, dispatch coordination, and proof-checkout owners. `FindingStore.create_participant` and `InvalidationRuntime.prepare/complete` are non-mutating composition APIs; existing `apply` behavior remains intact. `RejectAcceptRequest/Result` validates finding/route identity, current authority and ownership, requires the active accept job in the affected closure, publishes one failed terminal event plus findings/supersession/minimum corrective jobs in one `RuntimeTransaction`, and resolves exact replay before ownership. `DispatchRuntime.reject_accept` removes the matching reader in the same transaction and performs validated pre-commit checkout cleanup; cleanup failure publishes nothing. Also refreshed `InvalidationRuntime` when `finish_plan` adopts a new `ChangeRevision`.

Proof: finding tests 5 passed; invalidation/rejection slice 41 passed; rejection matrix 10 passed; dispatch rejection 2 passed; independent builder challenger reran 92 focused tests and Ruff, decision `pass`; focused repository lint clean; `git diff --check` clean; full Kanban package excluding the unrelated legacy `graph.yaml` historical fixture module 1015 passed. The unexcluded run had the same 1015 passes plus 8 unrelated historical-fixture failures because the current loader intentionally rejects legacy `graph.yaml` authority. Complete snapshots prove no partial findings, attempts, receipts, jobs, coordination, or cleanup mutation for stale target/authority, missing receipt/job, route mismatch, non-owner, checkout cleanup failure, and injected transaction failures.
