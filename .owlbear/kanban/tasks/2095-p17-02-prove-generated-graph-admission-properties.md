---
id: 2095
title: 'P17-02: Prove generated graph admission properties'
status: verify
priority: high
created: 2026-07-27T19:45:12.509746+02:00
updated: 2026-07-27T20:28:55.591797+02:00
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

[[2026-07-27T20:28:55+02:00]]
## Builder Notes

DONE

- Added `serve/kanban/tests/test_generated_graph_admission.py`; no production behavior or dependency changes.
- AC-1: deterministic public `load_change` plus `validate_and_admit` coverage admits single-node, branching, joining, and 240-node families; asserts dependency-before-node publication order, persisted `JobStore` identities, exact receipt/generation/assessment replay, and one receipt/generation artifact.
- AC-2: generated mutations assert exact singleton codes `DV-002`, `DV-008`, `DV-003`, `DV-003`, `DV-004`, `DV-005`, `DV-006`, and `DV-007`; each public admission returns no receipt/generation and creates no authority or work publication.
- AC-3: seed 2095 authority with `DV-006`/`DV-007` defects is reloaded through the modular loader after recursive YAML key reversal, explicit document wrapping, and narrow line wrapping; digest and sorted findings remain identical across repeated loads.
- Focused proof: `uv run pytest serve/kanban/tests/test_generated_graph_admission.py -q --tb=short -n 0` passed 13 tests.
- Proportional proof: `uv run pytest serve/kanban/tests -q --tb=short` passed 364 tests with four existing Python multiprocessing fork deprecation warnings.
- Focused `uv run lint serve/kanban/tests/test_generated_graph_admission.py` passed all hooks; VS Code diagnostics reported no errors.
- Builder challenger decision: `pass`; it independently reran the focused test and lint.
- Assessed all 20 recalled memory entries in one batch: 19 succeeded; one concurrently absent entry (`b6c53f34-8a9d-4700-9350-9469ee81684a`) returned `Entry not found`.
