---
id: 2094
title: 'P17-01: Migrate and replay historical admission incidents'
status: build
priority: high
created: 2026-07-27T19:45:12.424338+02:00
updated: 2026-07-27T19:45:12.424338+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T1
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on: []
ac:
  - 'AC-1: Given modular defective fixtures for browser, workspace, memory purge,
    and memory lifecycle incidents with complete evidence, public validation returns
    respectively `DV-004`; `DV-004` and `DV-006`; `DV-007`; and `DV-004` and `DV-007`,
    creates no admission receipt, and materializes no job.'
  - 'AC-2: Given each corrected counterpart and complete evidence, public validation
    has zero findings and public admission publishes one digest-bound admission receipt
    plus initial plan jobs; replay returns the stored identities without duplication.'
  - 'AC-3: Given the eight durable fixture directories, canonical loading joins intent,
    design, decisions, modular obligations/contracts/nodes, and isolated plans; `graph.yaml`
    is absent and each pair preserves only its named semantic defect/correction delta.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Eight historical incident fixtures use current modular authority and expose their intended semantic findings instead of a physical-layout failure.

## Scope
In scope: MOD-008 fixture migration and public validation/admission replay. Out of scope: production loader compatibility, runtime correction, assembled workflow, and live carrier mutation.

## Authority
DN-013, REQ-018, WF-007, PROOF-013, IF-002, RISK-005 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Proof guidance: run a focused public validation/admission fixture matrix; add no production compatibility path.