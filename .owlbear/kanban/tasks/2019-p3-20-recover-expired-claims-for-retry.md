---
id: 2019
title: 'P3-20: Recover expired claims for retry'
status: build
priority: high
created: 2026-07-23T14:42:08.799937+02:00
updated: 2026-07-23T14:42:08.799937+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - claims
  - attempts
  - recovery
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-J
parent: 2003
depends_on:
  - 2017
  - 2018
ac:
  - 'AC-1: Given an active claim whose supplied recovery time is strictly beyond its
    claim timestamp plus configured expiry duration, recovery atomically appends one
    `crashed` event, clears only that claim, and leaves the job open and eligible
    for a later attempt.'
  - 'AC-2: Given a claim before or exactly at the expiry boundary, or a job whose
    claim was already released or failed, recovery is a no-op and emits no event.'
  - 'AC-3: Given reopen with an expired claim, runtime recovery reaches the same retryable
    job/crashed-event outcome; repeated recovery returns that outcome without duplicate
    events.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The native runtime deterministically converts an expired active claim into immutable crash evidence and an open retryable job.

## Scope
In scope: supplied recovery time; configured positive expiry duration; strict expiry boundary; crashed event; atomic matching-claim clear; retryability; reopen-driven recovery; idempotent repeated sweep; non-expired and already-resolved no-op behavior.

Out of scope: process liveness probing, successful completion, dispatch policy, global writer leases, receipt creation, MCP, and Cockpit.

## Current Foundation And Ownership
Compose start identity from task #2017 with owner-finalization behavior from task #2018. Deepen the same native runtime facade; preserve its mixed transaction and immutable event semantics.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, design sections 2.2, 2.3, 7.2, 8.6, 13, and 14, and accepted `DEC-007` and `DEC-009`.

## Proof Guidance
Exercise public recovery at just before, exactly at, and just after expiry; then reopen and repeat recovery. Keep process-race and transaction interruption matrices in tasks #2013 and #2012.