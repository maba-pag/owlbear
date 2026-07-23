---
id: 2018
title: 'P3-19: Release or fail owning attempts'
status: build
priority: high
created: 2026-07-23T14:41:48.715516+02:00
updated: 2026-07-23T14:41:48.715516+02:00
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
  - packet:DN-003-PK-004-I
parent: 2003
depends_on:
  - 2017
ac:
  - 'AC-1: Given the owning active attempt, release atomically appends one `released`
    event, clears only the matching claim pointers, leaves the job open, and leaves
    graph and receipts unchanged.'
  - 'AC-2: Given the owning active attempt, failed finalization atomically appends
    one `failed` event with supplied detail and evidence references, clears only the
    matching claim pointers, and preserves prior attempt history.'
  - 'AC-3: Given a non-owner, no active claim, or replay of an already committed outcome,
    the operation returns the stable rejection or existing outcome and creates no
    duplicate event or job mutation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The native runtime lets only the owning attempt release or fail its active claim while preserving immutable history and job purpose.

## Scope
In scope: owner identity; released and failed events; supplied failure detail and evidence references; atomic matching-claim clear; open-job preservation; idempotent replay; non-owner and no-active-claim diagnostics; graph and receipt immutability.

Out of scope: start eligibility, expiry recovery, successful completion, receipt creation, corrective routing, dispatch, MCP, and Cockpit.

## Current Foundation And Ownership
Deepen the native runtime facade from task #2017. Reuse its claim identity and mixed transaction boundary. This task owns release and failed-finalization semantics only.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, design sections 2.2, 2.3, 7.2, 8.6, 13, and 14, and accepted `DEC-007` and `DEC-009`.

## Proof Guidance
Exercise public release and fail operations over owner, non-owner, no-active-claim, and replay states. Do not repeat start guards or transaction failure injection.