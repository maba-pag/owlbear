---
id: 2012
title: 'P3-13: Recover OCC replacement transaction participants'
status: build
priority: high
created: 2026-07-23T14:40:46.644783+02:00
updated: 2026-07-23T14:40:46.644783+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - transactions
  - occ
  - recovery
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-C
parent: 2003
depends_on:
  - 2002
ac:
  - 'AC-1: Given a replacement participant whose destination matches its expected
    bytes, commit publishes the replacement; when the destination already matches
    the replacement, replay returns the committed outcome; any other bytes return
    the stable conflict diagnostic without mutation.'
  - 'AC-2: Given interruption before publication, after replacement publication, or
    before manifest cleanup, `recover_all` completes the replacement and removes the
    manifest; repeated recovery is inert.'
  - 'AC-3: Given a malformed replacement manifest, altered content digest, or unsafe
    participant path, recovery raises the existing manifest or path diagnostic and
    leaves the destination and outside paths unchanged.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
`RuntimeTransaction` supports recoverable optimistic-concurrency replacement participants without weakening its existing immutable publication guarantees.

## Scope
In scope: expected-byte and replacement-byte participant metadata; contained mutable replacement; idempotent replay; conflict diagnostics; manifest schema and digest validation; interruption recovery before publication, after replacement publication, and before cleanup.

Out of scope: mixed job/event process races, attempt storage, lifecycle guards, receipt validity, and domain-specific transaction policy.

## Current Foundation And Ownership
Deepen the reusable transaction kernel delivered by archived task #2002. Preserve all existing immutable participant behavior and diagnostics. Consume `JobStore` byte/OCC semantics without moving job ownership into the kernel.

## Authority
Resolve behavior from `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, `PROOF-003`, and design sections 9.5, 12, and 13. The user-approved architecture preserves persisted `JobRecord.claim_id` and `attempt_id` while adding reusable recoverable replacement participants.

## Proof Guidance
Use the transaction boundary directly. Cover expected, already-replaced, conflicting, malformed, unsafe, and all three interruption phases; do not add mixed process races to this task.