---
id: 2061
title: 'P10-02: Atomically reject whole-change audit attempts'
status: build
priority: high
created: 2026-07-25T19:53:21.715434+02:00
updated: 2026-07-25T19:53:21.715434+02:00
tags:
  - phase-10
  - scope:kanban
  - audit
  - rejection
  - invalidation
  - transaction
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-014
  - packet:DN-014-PK-002
  - interface:IF-014
parent: 1986
depends_on:
  - 2060
ac:
  - 'AC-1: Given an owned active audit and strict findings, routes, and invalidation,
    public `reject_audit` publishes the findings, one failed terminal event, and one
    supersession receipt; it supersedes the audit and affected closure and creates
    only plan jobs declared by `affected-node-correction`, or zero jobs for `design-reentry`,
    while preserving unrelated receipt bytes.'
  - 'AC-2: Dispatch rejection removes the matching reader and proof checkout within
    the successful publication boundary; cleanup failure, malformed references, non-owner
    identity, stale authority, or transaction conflict returns a stable diagnostic
    and complete snapshots show no partial finding, event, receipt, job, coordination,
    or checkout publication.'
  - 'AC-3: Replaying the same request returns the persisted rejection identity, findings,
    supersession closure, and corrective jobs without duplicate mutation; changing
    replay identity returns an identity-conflict diagnostic.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-014-PK-002`. Resolve behavior from REQ-008, WF-005, IF-014, DEC-009, and current finding, invalidation, transaction, coordination, and checkout authority.

## Outcome
Publish rejected audits, precise invalidation, and minimum whole-change corrective work as one native operation.

## Envelope
In: active audit identity, strict findings and routes, selected accepted receipts, supersession, affected-node correction or design re-entry, failed attempt, reader release, and proof-checkout cleanup.

Out: MCP adapter, auditor prose contract, Cockpit, cutover, and complete-system proof.

Proof guidance: run focused native invalidation, runtime, dispatch, and proof-checkout checks plus a downstream impact scan.