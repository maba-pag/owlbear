---
id: 2060
title: 'P10-01: Create the terminal whole-change audit job'
status: build
priority: high
created: 2026-07-25T19:53:13.954779+02:00
updated: 2026-07-25T19:53:13.954779+02:00
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