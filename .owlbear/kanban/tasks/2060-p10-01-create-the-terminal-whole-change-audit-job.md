---
id: 2060
title: 'P10-01: Create the terminal whole-change audit job'
status: verify
priority: high
created: 2026-07-25T19:53:13.954779+02:00
updated: 2026-07-25T20:12:21.742412+02:00
tags:
  - phase-10
  - scope:kanban
  - audit
  - lifecycle
  - transaction
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-014
  - packet:DN-014-PK-001
  - interface:IF-014
parent: 1986
depends_on: []
ac:
  - 'AC-1: Given current accept receipts for the declared node set except the active
    final accept attempt, `NativeRuntime.finish_accept` publishes that receipt and
    returns one pending audit job whose target is `DN-014`, digest and node-plan match
    loaded authority, and predecessors are the accepted job IDs; one transaction snapshot
    contains the job, receipt, event, and reserved sequence state.'
  - 'AC-2: Given a non-final acceptance, stale or superseded predecessor, missing
    `DN-014` authority, or an existing audit identity, `finish_accept` returns its
    stable diagnostic or normal result without a partial or duplicate audit job; store
    and receipt snapshots show unrelated state unchanged.'
  - 'AC-3: Replaying the same finish request returns the persisted accept receipt,
    event, and audit job without reserving another ID; injected participant or OCC
    failure leaves the accept receipt, archived accept job, audit job, terminal event,
    and job sequence unpublished.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-014-PK-001`. Resolve behavior from REQ-007, WF-005, IF-014, DEC-019, and current job/finish transaction authority.

## Outcome
Create the single terminal audit job atomically when acceptance completes the declared delivery-node set.

## Envelope
In: final acceptance completion, current node accept receipts, DN-014 authority, job identity reservation, receipt/event/job transaction, and replay.

Out: audit rejection, MCP, auditor workflow, Cockpit, cutover, and complete-system proof.

Proof guidance: run focused native finish-accept and audit-lifecycle checks plus a downstream impact scan.

[[2026-07-25T20:12:21+02:00]]
## Builder Notes

DONE

Implemented terminal whole-change audit creation within the existing finish-accept transaction.

- AC-1: final acceptance now evaluates current accept jobs for every declared delivery node, reserves one monotonic job ID, creates a pending DN-014 audit with current delivery and node-plan authority plus accepted predecessor job IDs, and commits the sequence, audit, accept receipt, success event, and accept archive atomically.
- AC-2: non-final acceptance returns no created jobs; missing or non-current acceptance authority does not create audit work; matching existing audit identity suppresses duplicates; a mismatched pending audit, including stale DN-014 plan digest, returns `ERR_FINISH_IDENTITY_CONFLICT` before mutation.
- AC-3: finish replay discovers and returns the persisted audit created by the original accept finish without sequence reservation; an injected transaction conflict leaves work and receipt snapshots unchanged.

Proof: focused lint passed for both changed files. The complete native-runtime module passed 43 tests. Durable proofs cover atomic creation and replay, rollback, conflicting existing audit identity with unchanged snapshots, and the existing non-final lifecycle. Builder challenger initially found missing node-plan digest equality; that defect was repaired and the repeated challenge passed.

Changed files: `serve/kanban/src/owlbear_kanban/native_runtime.py`, `serve/kanban/tests/test_native_runtime.py`.
