---
id: 1997
title: 'P2-05: Replay historical admission failures'
status: build
priority: medium
created: 2026-07-22T13:46:19.736647+02:00
updated: 2026-07-22T13:46:19.736647+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - fixtures
  - regression
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-005
parent: 1978
depends_on:
  - 1996
ac:
  - 'AC-1: The R1 defective fixture returns `DV-004` or `DV-007` for missing retained-page
    lifecycle or composition ownership; the R2 defective fixture returns the applicable
    `DV-004`, `DV-005`, and `DV-006` findings for missing transport/callback, deletion,
    and destructive-safety obligations; corrected pairs have no error findings.'
  - 'AC-2: The R3 defective fixture returns `DV-007` for absent assembled frontend/API/engine
    proof ownership; the R4 defective fixture returns `DV-004` or `DV-007` for absent
    generated/frontend contract and clean-build predecessor; corrected pairs have
    no error findings.'
  - 'AC-3: The public evaluator loads eight tracked four-file fixtures through `load_change`;
    repeated evaluation returns identical code/target ordering, and fixture entities
    use general graph fields rather than browser, workspace, or memory-specific validator
    branches.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-002`
- `packet_id`: `DN-002-PK-005`

## Outcome
Eight durable four-file change fixtures preserve the four historical defective/corrected plan pairs and prove the general admission evaluator rejects the original omissions without incident-specific code.

## Scope
In scope: R1 browser retained-page lifecycle/composition; R2 workspace transport/callback, final deletion, and destructive safety; R3 memory purge assembled frontend/API/engine proof; R4 memory lifecycle generated/frontend contract and clean-build predecessor; loader/evaluator integration and stable finding expectations.

Out of scope: new browser, workspace, or memory-specific validator fields or branches; generic invariant design; receipt/job mutation; atomic publication.

## Authority
Fixture behavior comes from section 4.2 of `.owlbear/research/planning-workflow-root-cause-and-redesign.md` and section 17.2 of `design.md`. Fixture structure uses the admitted four-file authority schema and `DV-004` through `DV-007` category meanings.

Proof guidance: load tracked defective/corrected packages through `load_change`, then call the public evaluator with complete T1 evidence. Run the focused fixture suite and admission regression; these fixtures are a named durable output of `PROOF-002`.