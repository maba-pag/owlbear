---
id: 2096
title: 'P17-03: Prove receipt, invalidation, and recovery properties'
status: build
priority: high
created: 2026-07-27T19:45:12.555886+02:00
updated: 2026-07-27T19:45:12.555886+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T3
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on: []
ac:
  - 'AC-1: Given histories containing current, stale-digest, superseded, intersecting-descendant,
    and proven-nonintersecting-descendant receipts, runtime dependency checks accept
    only the current unsuperseded chain and return the declared stable diagnostic
    for each rejected class without mutating jobs or receipts.'
  - 'AC-2: Given an acceptance finding classified as `implementation-defect` or `packet-boundary-defect`,
    public rejection creates respectively the minimum corrective build job or through-plan
    corrective route, freezes original attempt/receipt/finding history, and only the
    successful superseding chain releases dependencies.'
  - 'AC-3: Given interruption before transaction publication, after participant replacement,
    or during replay for graph, job, receipt, activity, and invalidation participants,
    recovery exposes neither a published receipt without its complete participant
    set nor a job split across active/archive stores; correction plus replay commits
    one state and preserves immutable prior history.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Generic generated histories prove current receipt selection, minimum correction, and transaction recovery independently of bootstrap identities.

## Scope
In scope: MOD-008 generic tests over IF-003/IF-009 and current transaction/invalidation stores. Out of scope: browser behavior, live carrier mutation, and product fixes.

## Authority
DN-013, REQ-018, WF-007, PROOF-013, RISK-003/RISK-009 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Proof guidance: run a deterministic generated receipt/invalidation/transaction matrix using public runtime operations and the shared transaction boundary.