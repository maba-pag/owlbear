---
id: 2095
title: 'P17-02: Prove generated graph admission properties'
status: build
priority: high
created: 2026-07-27T19:45:12.509746+02:00
updated: 2026-07-27T19:45:12.509746+02:00
tags:
  - phase-17
  - scope:test
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-013
  - packet:T2
  - module:MOD-008
  - proof:PROOF-013
parent: 1990
depends_on: []
ac:
  - 'AC-1: Given deterministic generated acyclic graph families spanning single-node,
    branching, joining, and hundreds-of-node topologies, public admission succeeds,
    creates plan jobs in stable delivery-topology order, and replay preserves digest,
    finding, and job identities.'
  - 'AC-2: Given one generated mutation in each class `dangling reference`, `dependency
    cycle`, `disconnected obligation`, `duplicate owner`, `interface omission`, `migration
    gap`, `risk disposition`, and `proof authorization`, public validation returns
    respectively `DV-002`, `DV-008`, `DV-003`, `DV-003`, `DV-004`, `DV-005`, `DV-006`,
    and `DV-007` before a receipt or job exists.'
  - 'AC-3: Given the same seed and generated authority, repeated loading and validation
    produce the same canonical delivery digest and sorted findings; YAML key order
    and document wrapping do not change semantic identity.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Deterministically generated graph families demonstrate that native admission is general rather than tailored to bootstrap fixtures.

## Scope
In scope: MOD-008 generators and tests over canonical models, hashing, admission, and plan-job publication. Out of scope: receipt lifecycle, browser behavior, and product changes.

## Authority
DN-013, REQ-018, WF-007, PROOF-013, IF-002, RISK-006/RISK-011 at admitted digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`.

Proof guidance: run a deterministic seeded generator/property matrix through the canonical loader and admission boundary; add no property-test dependency solely for naming.