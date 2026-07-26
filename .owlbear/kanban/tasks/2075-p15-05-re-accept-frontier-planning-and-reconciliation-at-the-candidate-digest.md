---
id: 2075
title: 'P15-05: Re-accept frontier planning and reconciliation at the candidate digest'
status: collect
priority: high
created: 2026-07-26T01:59:09.251790+02:00
updated: 2026-07-26T03:41:48.202064+02:00
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

[[2026-07-26T03:35:25+02:00]]
## Builder Notes
DONE: Re-accepted unchanged DN-006/PROOF-005 at candidate digest `bf5edd...`, tested SHA `9be7018bbef8718a847b7df7c75d02ea275a0348`.

Focused planner/native/dispatch proof: 12 passed. Builder challenger independently ran complete three-file boundary: 72 passed. Evidence covers candidate admission, stable topological frontier, atomic per-node plan/jobs and replay, invalid expansion zero-partial with prior-node preservation, acceptance-triggered reconciliation, old-build blocking, predecessor evidence, digest supersession, and precise invalidation preserving disjoint state. Product/proof clean; lint passed. No correction needed. Memories assessed.

[[2026-07-26T03:41:48+02:00]]
## Verify Notes
PASS: DN-006 candidate re-acceptance is complete. Tested SHA `9be7018bbef8718a847b7df7c75d02ea275a0348` and builder `7c829c9bbb184e9db0033a4fb951c778d66f5542` are ancestors. Builder focused 12 and challenge 72 passed; verifier reran both assembled PROOF-005 scenarios (2 passed). Causal linkage covers topology, atomic publication, invalid expansion, predecessor acceptance, reconciliation job, old-build block, evidence consumption, digest supersession, and precise invalidation/disjoint preservation. Product/proof clean; lint and verifier challenge passed. Memories assessed.
