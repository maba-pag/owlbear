---
id: 2003
title: 'P3-04: Record claims and immutable attempts'
status: build
priority: high
created: 2026-07-22T21:58:44.211108+02:00
updated: 2026-07-22T21:58:44.211108+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - claims
  - attempts
  - lifecycle
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004
parent: 1979
depends_on:
  - 2002
ac:
  - 'AC-1: Given an open current job with prerequisite receipts whose computed validity
    is current and no pending request, `start_job` atomically records one claim and
    open attempt; a second active claimant, stale authority, unmet prerequisite, terminal
    disposition, or pending request returns a stable reason with no additional attempt.'
  - 'AC-2: Given the owning attempt, `release_job` or failed/crashed finalization
    appends an immutable outcome, clears the claim, and leaves graph and receipts
    unchanged; a later `start_job` creates a new attempt while prior attempts remain
    inspectable in order.'
  - 'AC-3: Given an expired claim at a supplied clock, the public recovery operation
    closes that attempt as crashed and releases only that job; replay produces the
    same state, and global writer compatibility or wave replanning is absent.'
proof_bundle: behavioral+challenge
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
- `packet_id`: `DN-003-PK-004`

## Outcome
Per-job claim, release, expiry, and attempt history are orthogonal runtime state: failed or crashed attempts remain immutable and an open job can be retried without changing its purpose.

## Scope
In scope: public start, release, failed-finalization, and expired-claim recovery operations; process and agent identity; claim timestamps; append-only attempts and activity; current-authority, prerequisite, pending-request, and terminal-disposition guards.

Out of scope: wave selection, global writer compatibility or lease, successful purpose-specific receipts, invalidation, corrective jobs, agent dispatch, and MCP.

## Current Foundation And Ownership
Use the native transaction coordinator and stores from preceding packets behind the transport-free runtime facade. Do not reuse the legacy `start_work` or `end_work` status-moving semantics.

## Authority
Resolve behavior from `REQ-009`, `IF-003`, `PROOF-003`, design sections 7.2 and 8.6, and the operational-property decision in `decisions.yaml`. Global dispatch and writer policy remain DN-004.

Proof guidance: exercise public lifecycle operations with replaceable clock and process identity, including concurrent claim, release, crash, expiry, retry, and idempotent recovery.