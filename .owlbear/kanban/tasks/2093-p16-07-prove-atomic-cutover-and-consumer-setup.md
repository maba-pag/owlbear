---
id: 2093
title: 'P16-07: Prove atomic cutover and consumer setup'
status: build
priority: high
created: 2026-07-27T08:40:26.563879+02:00
updated: 2026-07-27T08:40:26.563879+02:00
tags:
  - phase-16
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T7
  - module:MOD-008
  - proof:PROOF-009
parent: 1989
depends_on:
  - 2087
  - 2090
  - 2091
  - 2088
  - 2089
  - 2092
ac:
  - 'AC-1: Given a populated legacy repository with complete dispositions and a fresh
    consumer repository, invoking public cutover and setup produces matching manifest
    hashes and counts, clean native stores, a successful native launch, and no executable
    old runtime surface.'
  - 'AC-2: Given an existing destination, a missing disposition, a source mutation,
    or an induced publication interruption, the assembled boundary publishes no completed
    receipt, does not overwrite history, leaves a recoverable source, and succeeds
    after the cause is corrected.'
  - 'AC-3: Given a successful fixture cutover, the proof output records the invoked
    command, expected authority and code revisions, manifest and hash identities,
    finalization receipt, and returned commit paths required by DN-015 while demonstrating
    that the live self-hosting board was not an input.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
PROOF-009 exercises public setup and the public cutover command against populated legacy and fresh consumer repositories, proving atomic fixture cutover, recovery, native launch, old-surface absence, and the evidence handoff required by terminal DN-015.

## Scope
In scope: durable assembled setup, snapshot, absence, and distribution scenarios over temporary repositories at the public command boundaries.

Out of scope: historical/generic complete-system proof owned by DN-013, real self-hosting board mutation, DN-015 dispatch, and PROOF-016 exact-commit acceptance.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; PROOF-009, IF-013, IF-016, REQ-011/REQ-012/REQ-017, MIG-001 through MIG-004, RISK-001/RISK-005, DEC-036, and outputs from #2087 through #2092.

Proof guidance: invoke public setup and cutover commands without replacing those boundaries; temporary repositories and the package-install recorder are permitted below them. Record command, revisions, manifests, hashes, receipt, and returned commit-path evidence; never target the live board.