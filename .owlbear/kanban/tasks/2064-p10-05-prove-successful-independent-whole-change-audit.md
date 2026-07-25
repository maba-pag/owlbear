---
id: 2064
title: 'P10-05: Prove successful independent whole-change audit'
status: build
priority: high
created: 2026-07-25T19:53:45.800696+02:00
updated: 2026-07-25T19:53:45.800696+02:00
tags:
  - phase-10
  - scope:test
  - auditor
  - success
  - proof-checkout
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-014
  - packet:DN-014-PK-005
  - interface:IF-014
  - proof:PROOF-008
parent: 1986
depends_on:
  - 2063
ac:
  - 'AC-1: In a real admitted lifecycle whose declared node set has current accept
    receipts, final public `finish_accept` creates one audit job; public `pick_jobs`
    selects `auditor`, and `start_job` returns matching active identity plus an engine
    exact-commit checkout while writer conflict remains enforced.'
  - 'AC-2: Shipped auditor artifacts in the checkout rehydrate Product Promise, accepted
    decisions, migrations and removals, admitted normal workflows, current accept
    receipts, request absence, and PROOF-008; commands and observations exercise maintained
    boundaries with disclosed allowed replacements, and before and after Git state
    shows no tracked edit.'
  - 'AC-3: `AuditorSuccess` through public `finish_audit` persists a broad impact-closure
    audit receipt at the tested SHA, successful terminal event, archived audit job
    as mechanical change closure, reader release, and checkout cleanup; replay returns
    the persisted receipt, event, and job with byte-identical stores and one terminal
    event.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-014-PK-005`. Resolve behavior from REQ-007, WF-005, IF-014, RISK-008, RISK-009, and PROOF-008.

## Outcome
Maintain the successful exact-commit half of PROOF-008 over the shipped auditor and public lifecycle.

## Envelope
In: completed accepted-node set, terminal audit creation, public dispatch/start, engine checkout, whole-change authority evaluation, successful finish, broad receipt closure, replay, and cleanup.

Out: rejection and failure matrix, new semantics, Cockpit, setup, cutover, and complete-system proof.

Proof guidance: extend one maintained public MCP and native assembled scenario; do not create a parallel harness.