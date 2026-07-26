---
id: 2078
title: 'P15-08: Re-accept independent whole-change audit at the candidate digest'
status: build
priority: high
created: 2026-07-26T01:59:33.060377+02:00
updated: 2026-07-26T01:59:33.060377+02:00
tags:
  - phase-15
  - candidate-reacceptance
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-014
  - scope:core
  - type:test
  - rigor:thorough
  - proof:PROOF-008
parent: 1968
depends_on:
  - 1986
  - 2072
  - 2073
  - 2077
ac:
  - 'AC-1: Given candidate-bound accepted-node evidence, the independent auditor evaluates
    Product Promise, accepted decisions, complete workflows, migration/removal, and
    unresolved-request/receipt state in a read-only exact-commit checkout.'
  - 'AC-2: Audit success issues the final receipt and mechanical closure once; failure
    emits typed findings and minimum corrective jobs without tracked-file edits, duplicate
    finalization, or stale-receipt acceptance.'
  - 'AC-3: The task records candidate digest, tested SHA, commands, and results for
    DN-014; a failing audit/finalization contract produces a scoped corrective implementation
    before re-acceptance.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; candidate re-acceptance of unchanged `DN-014` under `PROOF-008`.

## Outcome
The independent read-only audit/finalization control is re-proven against candidate orchestration, MCP, and node-acceptance outputs before Cockpit backend correction.

## Envelope
In: accepted-node receipts, Product Promise and decisions, whole-workflow audit, final receipt/closure or corrective findings, PROOF-008.

Out: final candidate system audit after DN-011–DN-013; this task re-accepts the audit mechanism itself.

Proof guidance: exercise public audit/finalization in an exact-commit checkout with replaced lower executors only where PROOF-008 permits; tracked product files remain read-only.