---
id: 2097
title: 'P17-04: Execute the fresh-consumer native delivery workflow'
status: build
priority: high
created: 2026-07-27T19:45:12.576115+02:00
updated: 2026-07-27T19:45:12.576115+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T4
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on: []
ac:
  - 'AC-1: Given a temporary consumer initialized by public setup and a representative
    admitted two-node/two-module change, installed design contracts plus public MCP
    `show_change`, `validate_change`, and `admit_change` publish digest-bound frontier
    plan jobs while a plan outside admitted authority fails without a plan receipt
    or packet job.'
  - 'AC-2: Given engine-selected jobs, public MCP pick, start, and purpose-specific
    finish operations run plan and reviewed build work under shared writer coordination;
    a read-only proof checkout rejects one implementation defect, publishes the minimum
    corrective build job, then the corrected commit is independently accepted while
    stale or superseded receipts release no work.'
  - 'AC-3: Given accepted nodes at the corrected commit, public audit starts in a
    disposable read-only checkout and publishes one final audit receipt whose predecessor
    IDs, delivery/node-plan digests, code revision, impact closure, evidence IDs,
    and corrective history match persisted stores; native health reports no unresolved
    claim, writer, request, finding, or active legacy execution path.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
One temporary fresh consumer runs a representative two-module change from installed design contracts through public admission and engine-selected plan, reviewed build, independent acceptance, one corrective cycle, and final audit.

## Scope
In scope: MOD-008 assembled Python proof using public setup and real MCP, engine, writer, Git, and proof-checkout boundaries. Out of scope: live OwlBear carrier mutation, production fixes, and mocked lifecycle completion.

## Authority
DN-013, REQ-018, WF-007, PROOF-013, IF-002/003/005/009/010/013/014, RISK-003/RISK-005/RISK-009 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Complexity waiver: PROOF-013 requires one assembled design-to-audit boundary; splitting lifecycle phases would bypass it. A two-node fixture keeps the matrix bounded.

Proof guidance: reuse the current assembled MCP harness over a temporary Git consumer; replace only repository location, never public setup, MCP, engine, writer, or checkout boundaries.