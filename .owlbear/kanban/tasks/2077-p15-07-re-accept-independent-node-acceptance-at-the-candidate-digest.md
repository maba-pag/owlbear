---
id: 2077
title: 'P15-07: Re-accept independent node acceptance at the candidate digest'
status: verify
priority: high
created: 2026-07-26T01:59:26.362933+02:00
updated: 2026-07-26T06:18:11.626061+02:00
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

[[2026-07-26T06:18:11+02:00]]
Builder evidence for candidate re-acceptance and corrective implementation.

Candidate authority: replace-delivery-pipeline at bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357. Tested base revision: 2b351a3c5faf3e37023d731fd11703e2dc526b38.

The initial maintained PROOF-007 matrix passed 69 scenarios but independent challenge falsified it: finish_accept could bind a receipt to a different revision than its proof checkout, methods-only evidence passed, tracked edits were not engine-detected, cleanup preceded completion validation, and canonical rejection cases were synthetic. The correction now requires an existing clean exact-full-SHA checkout; engine-owned HEAD/tracked-state validation; transactional cleanup with exact snapshot restoration on diagnostics/OCC; successful replay after cleanup; complete node contract/modules/interfaces/interface-linked migrations/risks/proof/boundary/durable outputs/allowed replacements; exact node-plan packet IDs, predecessor receipts and impact closure; nonempty successful assembled command results; and unchanged before/after Git state. Public tests execute the assembled ChangeRevision + ReceiptStore boundary inside the disposable checkout. Local-defect, missing-harness, boundary-bypass, stale-receipt and tracked-mutation failures are observed before public typed rejection and minimum correction publication.

Validation: uv run ruff check on the eight changed source/test files => All checks passed. uv run pytest -q -n0 -o session_timeout=600 serve/mcp-kanban/tests/test_mcp_acceptance_tools.py serve/kanban/tests/test_native_runtime.py serve/kanban/tests/test_dispatch_runtime.py serve/kanban/tests/test_proof_checkout.py -k 'accept or proof_checkout or reject' => 86 passed, 27 deselected in 234.87s. Final independent false-green probe => PASS, no mandatory defects. No stale candidate receipt was reused and unrelated dirty paths were untouched.
