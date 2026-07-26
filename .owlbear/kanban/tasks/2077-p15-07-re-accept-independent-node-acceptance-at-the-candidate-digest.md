---
id: 2077
title: 'P15-07: Re-accept independent node acceptance at the candidate digest'
status: build
priority: high
created: 2026-07-26T01:59:26.362933+02:00
updated: 2026-07-26T01:59:26.362933+02:00
tags:
  - phase-15
  - candidate-reacceptance
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-008
  - scope:core
  - type:test
  - rigor:thorough
  - proof:PROOF-007
parent: 1968
depends_on:
  - 1985
  - 2072
  - 2073
  - 2075
  - 2076
ac:
  - 'AC-1: Given current packet receipts at a candidate code revision, the independent
    acceptor verifies node authority, plan, interfaces, migration/risk/proof obligations,
    and assembled behavior in a read-only exact-commit checkout.'
  - 'AC-2: Acceptance success publishes a candidate-bound accept receipt and cleans
    proof state; failure publishes typed findings plus minimum corrective jobs without
    tracked-file mutation or reuse of stale receipts.'
  - 'AC-3: The task records candidate digest, tested SHA, commands, and results for
    DN-008; a failing acceptance contract produces a scoped corrective implementation
    before re-acceptance.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; candidate re-acceptance of unchanged `DN-008` under `PROOF-007`.

## Outcome
Independent exact-commit node acceptance and typed corrective routing are re-proven against the candidate runtime, planner, builder, and MCP boundaries.

## Envelope
In: accepted packet receipts, read-only proof checkout, authority/plan/assembly checks, findings, corrective routing, PROOF-007.

Out: whole-change audit, Cockpit, cutover.

Proof guidance: exercise the public accept workflow in a disposable exact-commit checkout; replacement may prepare fixture inputs but may not replace acceptance assembly or edit tracked files.