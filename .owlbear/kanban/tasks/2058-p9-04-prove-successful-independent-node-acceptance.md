---
id: 2058
title: 'P9-04: Prove successful independent node acceptance'
status: build
priority: high
created: 2026-07-25T17:19:52.292139+02:00
updated: 2026-07-25T17:19:52.292139+02:00
tags:
  - phase-9
  - scope:test
  - acceptor
  - proof-checkout
  - success
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-008
  - packet:DN-008-PK-003
  - interface:IF-009
  - proof:PROOF-007
parent: 1985
depends_on:
  - 2057
ac:
  - 'AC-1: Given a real admitted accept job with current packet receipts, public `start_job`
    selects `acceptor`, creates an engine proof checkout at candidate SHA, preserves
    job, claim, digest, and node-plan identity, and keeps a tracked writer unavailable
    while the reader attempt is active.'
  - 'AC-2: The shipped acceptor evaluates node contract, packet coverage, changed
    surfaces, assembled proof, exact SHA, clean checkout, and prerequisite currentness;
    declared lower replacements plus write denial and before/after Git state prove
    the acceptor made no tracked edit.'
  - 'AC-3: `AcceptorSuccess` through public `finish_accept` persists receipt, evidence,
    replacements, and SHA, cleans checkout, releases reader coordination, and creates
    required dependent reconciliation plan jobs; replay returns the same receipt,
    event, and jobs without duplicate mutation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-008-PK-003`. Resolve behavior from WF-004, IF-009, RISK-008/RISK-009, and PROOF-007.

## Outcome
Maintain the successful exact-commit half of PROOF-007 over shipped acceptor artifacts and public lifecycle.

## Envelope
In: real accept job, engine checkout, contract and receipt evaluation, read-only proof, finish receipt, reconciliation, replay, and cleanup.

Out: rejection routes, new runtime behavior, auditor, Cockpit, setup, and seed work.