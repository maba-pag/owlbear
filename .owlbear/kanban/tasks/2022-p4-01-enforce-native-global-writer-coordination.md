---
id: 2022
title: 'P4-01: Enforce native global writer coordination'
status: build
priority: high
created: 2026-07-24T16:49:45.233828+02:00
updated: 2026-07-24T17:13:40.804366+02:00
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
  - 'AC-1: Given empty coordination, `DispatchRuntime.start` for `shape | build` atomically
    publishes its exact holder, claimed job, and started event; a rival writer or
    read-only start returns `ERR_DISPATCH_WRITER_CONFLICT` and leaves coordination,
    jobs, and events byte-identical.'
  - 'AC-2: Given valid active `accept | audit` reader holders and no writer, another
    read-only start atomically records its holder, claim, and event; a writer start
    returns `ERR_DISPATCH_WRITER_CONFLICT` without mutation. A holder not matching
    active claim/event identity returns `ERR_DISPATCH_LEASE_STALE`.'
  - 'AC-3: Given an exact active holder, dispatch finish, release, or fail clears
    it in the IF-003 lifecycle transaction. Exact replay after clearing returns the
    persisted IF-003 outcome; stale or non-owner requests cannot clear another holder.'
  - 'AC-4: Given interruption or strict-expiry recovery, transaction recovery exposes
    complete matching coordination/claim/event state or complete cleared/crashed state
    without duplicate events or a stranded holder; equality at the expiry boundary
    remains active.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; `DN-004-PK-001`. Normative authority remains `DN-004`, `IF-004`, `RISK-002`, `PROOF-014`, and accepted `DEC-014`; this task only projects the implementable packet.

## Public Contract
Deepen existing `owlbear_kanban.dispatch` with `DispatchRuntime`. Its `start`, `release`, `fail`, `finish_shape`, `finish_build`, `finish_accept`, `finish_audit`, and `recover_expired_claims` accept the corresponding frozen IF-003 request models and return the corresponding IF-003 result or a strict `DispatchDiagnostic`. Dispatch-owned codes are `ERR_DISPATCH_WRITER_CONFLICT` for a valid incompatible holder and `ERR_DISPATCH_LEASE_STALE` when persisted coordination does not exactly match active job claim plus sequence-one started-event identity. Diagnostics include detail and sorted holder job IDs. Do not add codes to IF-003 enums.

## Durable Coordination
Add strict immutable models and a contained store in `dispatch.py` for singleton `dispatch/coordination.yaml` under the native work root:

- `CoordinationHolder`: `job_id`, `kind`, `attempt_id`, `claim_id`, `actor_id`, `process_id`, `claimed_at`.
- `WriterCoordination`: `schema_version: 1`, optional `writer`, and deterministically sorted unique `readers`.
- Writer kinds are `shape | build`; reader kinds are `accept | audit`. Exactly zero/one writer or zero/many readers is valid, never both.

The store idempotently materializes one empty record, returns an OCC token, and supplies replacement participants. It does not add lease fields to `JobRecord`. Claim expiry is constructor-owned by `NativeRuntime`; holder `claimed_at` is identity/provenance, not a second expiry policy.

## Atomic Composition
Refactor `NativeRuntime` behind unchanged public methods to package-private variants that accept additional transaction participants; recovery accepts a per-recovered-claim participant factory. Public IF-003 methods pass none. `DispatchRuntime` validates coordination, builds the matching add/remove participant, and invokes that seam so coordination, job replacement, and attempt event share one `RuntimeTransaction`. On OCC conflict it rereads current state: incompatible starts return writer conflict without mutation; compatible reader starts may retry from fresh state. Finish/release/fail clear only an exact matching holder. Exact IF-003 replay with an already-cleared holder returns its persisted outcome. Non-owner requests leave coordination untouched. Recovery uses IF-003's strict boundary (`recovered_at <= claimed_at + claim_expiry` stays active) and atomically removes only each successfully crashed claim's holder.

## Envelope And Proof
In: `dispatch.py`, minimal private composition in `native_runtime.py`, exports, focused public dispatch tests. Out: wave planning, proof checkout, orchestration, MCP/Cockpit, and legacy removal. Prove real job/attempt/coordination/transaction storage under controlled writer-reader orderings and interruption recovery; replacements are limited to clock/concurrency control below PROOF-014.

[[2026-07-24T17:13:40+02:00]]
## Shape Notes

Local task repair of the builder rejection; no authority or packet-graph change. Replaced the complete operative body and AC rather than appending over stale scope. Resolved the missing lease protocol with strict `CoordinationHolder`/`WriterCoordination` models at singleton `dispatch/coordination.yaml`; resolved the public boundary with `DispatchRuntime` methods reusing frozen IF-003 requests/results plus dispatch-owned conflict/stale diagnostics; represented accept/audit as sorted reader holders; fixed strict-expiry, replay, and non-owner semantics; and named a package-private participant-injection seam so lease, job, and event share one transaction. Checked current `dispatch.py`, `native_runtime.py`, `jobs.py`, and `runtime_transaction.py`; no `JobRecord` field or `dispatch_runtime.py` is authorized. Evidence: task contract tests 2 passed, all AC under 500 characters, diff check clean, shaper-challenger `pass`, and ten recalled memories assessed. Board audit: parent/dependency unchanged; route is build.
