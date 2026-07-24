---
id: 2022
title: 'P4-01: Enforce native global writer coordination'
status: build
priority: high
created: 2026-07-24T16:49:45.233828+02:00
updated: 2026-07-24T16:49:45.233828+02:00
tags:
  - phase-4
  - scope:core
  - runtime
  - dispatch
  - writer-lease
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-004
  - packet:DN-004-PK-001
parent: 1980
depends_on:
  - 1979
ac:
  - 'AC-1: Given no active writer or read-only claim, `DispatchRuntime.start` for
    `shape | build` atomically publishes the singleton lease, claimed job, and started
    event; a rival writer or read-only start returns `ERR_DISPATCH_WRITER_CONFLICT`
    and leaves those stores byte-identical.'
  - 'AC-2: Given active `accept | audit` claims and no writer lease, another read-only
    start records its claim and started event; a `shape | build` start returns `ERR_DISPATCH_WRITER_CONFLICT`
    and leaves lease, jobs, and events unchanged.'
  - 'AC-3: Given a matching leased attempt, dispatch finish, release, or fail clears
    the lease in the lifecycle transaction. Exact replay returns the persisted outcome;
    stale or non-owner requests cannot clear another holder.'
  - 'AC-4: Given interruption during lease/job/event publication or strict-expiry
    recovery, transaction recovery exposes the complete matching lease/claim/event
    state or the complete cleared/crashed state without duplicate events or a stranded
    lease.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; node `DN-004`; packet `DN-004-PK-001`. Resolve normative behavior from `DN-004`, `IF-004`, `RISK-002`, `PROOF-014`, and accepted `DEC-014`; this record is not specification authority.

## Outcome
Deepen `owlbear_kanban.dispatch` with `DispatchRuntime` and one durable singleton writer-lease participant. Lease-aware start/finalization composes frozen IF-003 lifecycle primitives atomically without changing `NativeRuntime.start_job` or its diagnostics.

## Envelope
In: `serve/kanban/src/owlbear_kanban/dispatch.py`, minimal private reuse in `native_runtime.py`, package exports, focused native dispatch tests. Out: wave planning, proof checkout, agent orchestration, MCP, Cockpit, and legacy removal.

Proof guidance: public `DispatchRuntime` over real job, attempt, lease, and transaction storage; controlled writer/read-only orderings plus interruption recovery. Durable proof is justified by the shared-worktree data-integrity boundary.