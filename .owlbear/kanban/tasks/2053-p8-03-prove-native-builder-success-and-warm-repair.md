---
id: 2053
title: 'P8-03: Prove native builder success and warm repair'
status: build
priority: high
created: 2026-07-25T16:14:29.095921+02:00
updated: 2026-07-25T16:14:29.095921+02:00
tags:
  - phase-8
  - scope:test
  - builder
  - reviewer
  - repair
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-007
  - packet:DN-007-PK-003
  - interface:IF-008
  - proof:PROOF-006
parent: 1984
depends_on:
  - 2052
ac:
  - 'AC-1: Given a real admitted build job and available writer lease, public `start_job`
    selects profile `builder`, preserves job, claim, digest, and node-plan identity,
    and keeps a second tracked writer unavailable while the attempt is active; the
    maintained scenario uses the shipped builder workflow and agent rather than a
    fixture lifecycle adapter.'
  - 'AC-2: Given a sample module and deterministic runner, the shipped builder produces
    a scoped commit and reviewer context with non-empty authority, packet, diff, changed
    paths, proof, and commit fields; a read-only pass yields `BuilderSuccess`, and
    public `finish_build` persists a receipt bound to the packet digest, impact closure,
    evidence, and commit SHA.'
  - 'AC-3: Given one typed `implementation-defect`, the same claimed attempt repairs
    only its packet closure, creates a repair commit, regenerates context, obtains
    a fresh reviewer pass, and then completes one build receipt; the scenario verifies
    no receipt exists before the fresh pass and the reviewer remains write-denied.'
  - 'AC-4: Replaying successful `finish_build` returns the persisted outcome without
    duplicate receipt or event mutation, and releasing writer coordination makes the
    next eligible writer startable; public lifecycle observations verify atomic completion.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-007-PK-003`. Resolve normative behavior from `REQ-005`, `WF-003`, `IF-008`, `NEG-006`, `NEG-009`, and `PROOF-006`; this record is not specification authority.

## Outcome
Maintain the successful and local-repair half of PROOF-006 over shipped builder artifacts and public native lifecycle boundaries.

## Envelope
In: assembled builder claim, scoped commit, generated reviewer context, fresh local repair review, finish-build receipt, replay, and writer release behavior. A sample product module and deterministic command runner may replace lower layers.

Out: material contradiction, commit failure, malformed review, stale digest, new runtime semantics, and setup or seed work.

Proof guidance: exercise shipped roles and public MCP or native lifecycle operations; a fixture-only builder or direct store mutation does not prove this packet.