---
id: 2078
title: 'P15-08: Re-accept independent whole-change audit at the candidate digest'
status: verify
priority: high
created: 2026-07-26T01:59:33.060377+02:00
updated: 2026-07-26T09:49:56.100134+02:00
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

[[2026-07-26T08:55:05+02:00]]
Builder re-acceptance at digest bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357, tested base SHA c411e193a67db05752b7462bd2b42869010d368a. Initial 23-test audit matrix was false-green because PROOF-008 evidence validation was absent. Repair binds DN-014 audit receipts to exact Product Promise, JSON decisions, workflows, migrations, PROOF-008 boundary/durable outputs/replacements, no pending requests, exact stored accepted-receipt bodies and code SHA, ordered successful commands, and clean before/after Git state. finish_audit now enforces immutable dispatch SHA and tracked state; late linked requests block finalization under job OCC; tracked edits publish typed minimum correction. Observed cross-node/migration/planning failures drive public rejection. Validation: Ruff clean; 37 audit scenarios passed, 84 deselected in 303.55s. Final challenger PASS.

[[2026-07-26T09:12:51+02:00]]
Verifier rejected 47a9c42a0a39d018aa762d6abc6ef99ce45b9f09: the audit command only loaded authority and counted receipts, so valid-looking irrelevant commands could satisfy the evidence envelope without exercising PROOF-008 workflow/migration/cross-node coverage. Return to build for an engine-owned exact-checkout whole-change audit probe and machine-verifiable coverage binding.

[[2026-07-26T09:49:56+02:00]]
Verifier repair replaces the weak digest/count probe with candidate-local whole_change_audit_report. The exact command identity is fixed; python -I imports serve/kanban/src from the proof checkout and loads checkout authority. Accepted receipts are explicit immutable inputs. Runtime independently derives and byte-compares canonical JSON covering full decisions, workflows, migrations, all nodes/proofs, PROOF-008 boundary/methods, and accepted receipt closure. Irrelevant command labels/output are rejected. No-wrap receipt YAML preserves exact replay. Bootstrap validation before commit: Ruff clean; report enumerates 14 nodes, 7 workflows, 4 migrations. Exact-checkout public proof will run immediately after commit.
