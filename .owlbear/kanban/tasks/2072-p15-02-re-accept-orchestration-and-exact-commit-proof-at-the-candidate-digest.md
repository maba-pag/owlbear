---
id: 2072
title: 'P15-02: Re-accept orchestration and exact-commit proof at the candidate digest'
status: build
priority: high
created: 2026-07-26T01:58:44.920258+02:00
updated: 2026-07-26T01:58:44.920258+02:00
tags:
  - phase-15
  - candidate-reacceptance
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-004
  - scope:core
  - type:test
  - rigor:thorough
  - proof:PROOF-014
parent: 1968
depends_on:
  - 1980
  - 2071
ac:
  - 'AC-1: Given candidate DN-003 outputs, the public orchestrator dispatches graph-selected
    `plan | build | accept | audit` jobs with writer/read-only compatibility and records
    the tested code revision in re-acceptance evidence.'
  - 'AC-2: Given expired claims, competing writers, and disposable proof checkouts,
    PROOF-014 demonstrates recovery, serialization, exact-commit materialization,
    and cleanup without relying on an old delivery digest.'
  - 'AC-3: The task records candidate digest, tested SHA, commands, and results for
    DN-004; a failing invariant produces a scoped corrective implementation before
    re-acceptance rather than a passing evidence note.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; candidate re-acceptance of unchanged `DN-004` under `PROOF-014`.

## Outcome
The existing dispatch, writer serialization, recovery, and proof-checkout implementation is re-proven against the candidate authority after DN-003 administrative controls land.

## Envelope
In: DN-004 contract, IF-004/IF-005/IF-015, PROOF-014, candidate digest, current implementation and durable proof.

Out: new orchestration behavior unless proof exposes a local defect; MCP, Cockpit, frontend, cutover.

Proof guidance: run the existing public orchestration/writer/proof-checkout boundary at a recorded code SHA and inspect authority references; repair only a concrete DN-004 defect.