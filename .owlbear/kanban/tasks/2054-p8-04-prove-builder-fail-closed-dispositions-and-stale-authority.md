---
id: 2054
title: 'P8-04: Prove builder fail-closed dispositions and stale authority'
status: build
priority: high
created: 2026-07-25T16:14:38.333700+02:00
updated: 2026-07-25T16:14:38.333700+02:00
tags:
  - phase-8
  - scope:test
  - builder
  - findings
  - stale-authority
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-007
  - packet:DN-007-PK-004
  - interface:IF-008
  - proof:PROOF-006
parent: 1984
depends_on:
  - 2053
ac:
  - "AC-1: Given `unforeseeable-discovery`, `planning-omission`, or `scope-change`,
    the shipped builder returns `SpecificationReentry` with the typed class, target,
    finding, and evidence; the orchestrator releases the claim, halts native mode,
    and publishes no build receipt. The scenario enumerates the three literals and
    preserves prior receipt bytes; `implementation-defect` remains P8-03's repair
    case."
  - 'AC-2: Given scoped commit failure, the shipped builder returns `CommitFailed`
    with command, error, and bounded changed-path evidence; the orchestrator releases
    the matching claim and halts before fresh dispatch, and no build receipt is published.
    A deterministic runner scenario verifies the failed commit cannot become success.'
  - 'AC-3: Given reviewer context missing authority, diff or changed paths, proof,
    or commit identity, the reviewer output is malformed and the builder returns `BuildBlocked`;
    declaration checks and the assembled scenario verify reviewer write denial, identity-preserving
    release, and no receipt.'
  - 'AC-4: Given a build job whose node-plan digest differs from current authority,
    public `start_job` returns `ERR_START_AUTHORITY_STALE` with `ERR_RECEIPT_NODE_PLAN_DIGEST_STALE`
    before builder dispatch; the scenario verifies no claim, commit, reviewer call,
    or receipt mutation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-007-PK-004`. Resolve normative behavior from `IF-008`, `NEG-009`, `RISK-003`, `RISK-008`, and `PROOF-006`; this record is not specification authority.

## Outcome
Complete PROOF-006's material contradiction, commit failure, malformed review, and stale digest matrix, covering the four canonical finding classes across warm repair and specification re-entry.

## Envelope
In: assembled shipped builder dispositions, identity-preserving public release, no-receipt assertions, stale start diagnostics, and preservation of prior receipts. A sample module and deterministic runner may replace lower layers.

Out: new finding persistence or corrective-job operations, runtime semantics, acceptor or auditor work, and setup or seed propagation.

Proof guidance: exercise shipped builder and orchestrator contracts plus public start, release, receipt, and diagnostic boundaries.