---
id: 2013
title: 'P3-14: Serialize mixed job and attempt transactions'
status: build
priority: high
created: 2026-07-23T14:40:53.788290+02:00
updated: 2026-07-23T14:40:53.788290+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - transactions
  - attempts
  - concurrency
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-D
parent: 2003
depends_on:
  - 2011
  - 2012
ac:
  - 'AC-1: Given a mixed plan containing one replacement `JobRecord` and one immutable
    attempt event, interruption followed by runtime reopen yields the complete pair
    or the pre-transaction state, never a strict subset.'
  - 'AC-2: Given two processes using the same expected job bytes with different attempt
    events, exactly one process commits its matching job/event pair; the rival receives
    the stable OCC or conflict outcome and publishes no rival event.'
  - 'AC-3: Given byte-equivalent replay of a committed mixed plan, the operation returns
    the existing pair and creates no duplicate event.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A mixed transaction atomically couples one OCC `JobRecord` replacement with one immutable attempt event and serializes competing processes.

## Scope
In scope: mixed replacement/create participant plans; reopen recovery; same-expected-bytes process races; stable loser outcome; byte-equivalent replay; no strict-subset visibility.

Out of scope: replacement-manifest primitives, attempt model/store behavior, readiness guards, receipt validity, and lifecycle policy.

## Current Foundation And Ownership
Compose the immutable attempt store from task #2011 with the recoverable replacement primitive from task #2012. This task owns only mixed participant serialization and process-race proof.

## Authority
Resolve behavior from `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, `PROOF-003`, and design sections 7.2, 9.5, 12, and 13.

## Proof Guidance
Exercise a mixed job/event plan over explicit temporary roots. Inject one mixed interruption and run a two-process same-expected-job race; lower primitive failure matrices remain in their owning tasks.