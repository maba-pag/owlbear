---
id: 2075
title: 'P15-05: Re-accept frontier planning and reconciliation at the candidate digest'
status: build
priority: high
created: 2026-07-26T01:59:09.251790+02:00
updated: 2026-07-26T01:59:09.251790+02:00
tags:
  - phase-15
  - candidate-reacceptance
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-006
  - scope:core
  - type:test
  - rigor:thorough
  - proof:PROOF-005
parent: 1968
depends_on:
  - 1983
  - 2071
  - 2072
  - 2073
  - 2074
ac:
  - 'AC-1: Given candidate plan-ready nodes, the assembled planner selects the stable
    frontier and atomically publishes one reviewed, digested packet DAG per node without
    changing admitted obligations.'
  - 'AC-2: Given an accepted predecessor with new implementation evidence, dependent
    planning becomes reconciliation-required and blocks dependent builds until a current
    superseding plan is published; material expansion returns to Specification.'
  - 'AC-3: The task records candidate digest, tested SHA, commands, and results for
    DN-006; a failing planner/reconciliation contract produces a scoped corrective
    implementation before re-acceptance.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; candidate re-acceptance of unchanged `DN-006` under `PROOF-005`.

## Outcome
Initial frontier planning and acceptance-triggered reconciliation are re-proven against candidate graph, runtime, orchestration, design, and MCP contracts.

## Envelope
In: plan-ready selection, per-node packet plans, expansion gates, reconciliation-required state, PROOF-005.

Out: packet building, acceptance, Cockpit, cutover.

Proof guidance: exercise planner entry through real engine selection and node-scoped atomic publication; a fixture may provide repository inputs but not replace planner assembly.