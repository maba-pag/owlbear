---
id: 2076
title: 'P15-06: Re-accept packet building and inline review at the candidate digest'
status: build
priority: high
created: 2026-07-26T01:59:18.946549+02:00
updated: 2026-07-26T01:59:18.946549+02:00
tags:
  - phase-15
  - candidate-reacceptance
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-007
  - scope:core
  - type:test
  - rigor:thorough
  - proof:PROOF-006
parent: 1968
depends_on:
  - 1984
  - 2072
  - 2073
  - 2075
ac:
  - 'AC-1: Given one selected candidate build job, the assembled builder acquires
    the writer lease, implements one outcome-cohesive packet, runs proportional proof,
    and creates an owned commit without overlapping another writer.'
  - 'AC-2: The builder invokes mandatory read-only review while context is warm, repairs
    concrete findings in the same attempt, and publishes a build receipt only after
    review passes; reviewer mutation remains impossible.'
  - 'AC-3: The task records candidate digest, tested SHA, commands, and results for
    DN-007; a failing builder/reviewer contract produces a scoped corrective implementation
    before re-acceptance.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; candidate re-acceptance of unchanged `DN-007` under `PROOF-006`.

## Outcome
One engine-selected packet build with warm mandatory read-only review is re-proven against candidate planner, orchestration, and MCP contracts.

## Envelope
In: build-job selection, global writer lease, scoped commit, reviewer findings, repair loop, build receipt, PROOF-006.

Out: node acceptance, frontend, cutover.

Proof guidance: run the assembled builder/reviewer workflow over a contained fixture repository; mocks may replace the subagent runner but not writer policy, commit, review visibility, or receipt publication.