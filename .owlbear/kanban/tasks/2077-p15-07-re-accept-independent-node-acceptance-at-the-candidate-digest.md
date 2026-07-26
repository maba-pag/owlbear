---
id: 2077
title: 'P15-07: Re-accept independent node acceptance at the candidate digest'
status: collect
priority: high
created: 2026-07-26T01:59:26.362933+02:00
updated: 2026-07-26T07:29:56.036729+02:00
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

[[2026-07-26T06:28:36+02:00]]
Verifier rejected committed candidate 398c352899e4b4423826b19a4949593cd4c94e6f after independent review found two mandatory lifecycle defects: the canonical checkout SHA was not retained in durable dispatch authority, permitting coordinated manifest/HEAD tamper; and proof cleanup still ran before RuntimeTransaction publication, so non-OCC interruption could strand an active claim without checkout. Return to build for scoped repair and re-verification.

[[2026-07-26T07:08:33+02:00]]
Builder repair after verifier rejection of 398c352899e4b4423826b19a4949593cd4c94e6f.

Canonical resolved checkout SHA is now persisted in immutable dispatch coordination and finish_accept rejects any request/manifest/HEAD substitution that differs from dispatched authority. Acceptance and audit publication now commit atomically before proof checkout cleanup; a cleanup failure returns a stable orphan diagnostic after publication, and exact replay retries cleanup without duplicating receipt/event/job publication. Receipt evidence now requires one ordered successful nonempty result per declared assembled command. Public audit fixtures were corrected to use fresh checkout-aware attempt identities rather than native-start bypasses.

Focused validation with explicit existing .venv and system PATH: MCP acceptance/rejection 37 passed; dispatch acceptance/audit 8 passed; native acceptance + proof checkout 44 passed, 18 deselected; Ruff clean. Added manifest-tamper and post-publication cleanup-replay scenarios both pass. Independent lifecycle repair challenge: PASS, no mandatory defects. Owner-equivalent transient mutate/restore is outside the durable-state threat boundary; terminal guard, read-only modes, exact checkout SHA, immutable coordination authority, assembled evidence and final Git state remain enforced.

[[2026-07-26T07:16:17+02:00]]
Final committed review rejected d88c0f75ae5d1150f5a1715c21edadc5e8eddd46 on two mandatory gaps: start_with_checkout could reuse an orphaned checkout at SHA A when a new claim requested SHA B, silently replacing caller authority; and tracked-mutation detection stopped at ERR_PROOF_TRACKED_MUTATION without exercising the required typed reject_accept finding/minimum correction path. Return to build for scoped repair.

[[2026-07-26T07:26:07+02:00]]
Final builder repair closes the last two verifier findings. start_with_checkout now resolves the requested candidate and refuses an existing proof checkout whose canonical commit differs before any claim; it never substitutes stale orphan authority. The tracked-mutation public scenario now continues from ERR_PROOF_TRACKED_MUTATION into immutable implementation-defect finding, packet-implementation route, exactly one corrective build job, cleanup, and no accept receipt.

Validation: both new regressions pass; full public acceptance/rejection file passed 37 before the two additions and focused additions pass; native acceptance/rejection 36 passed, 18 deselected; dispatch acceptance/audit 8 passed; Ruff clean. Final focused challenger: PASS, no mandatory defects.

[[2026-07-26T07:29:56+02:00]]
Verifier acceptance at committed HEAD 2465c771c3a3460c5fe5062fdffdb28efe1cbd66. Exact final regressions: tracked checkout mutation -> typed finding/minimum build correction and stale checkout SHA mismatch -> typed stale authority, 2 passed in 8.43s. Final independent signoff PASS; aggregate Ruff and diff check clean.
