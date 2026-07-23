---
id: 2016
title: 'P3-17: Resolve predecessor and explicit supersession validity'
status: verify
priority: high
created: 2026-07-23T14:41:23.761134+02:00
updated: 2026-07-23T22:20:36.718602+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - receipts
  - validity
  - graph
  - supersession
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-G
parent: 2003
depends_on:
  - 2014
  - 2020
ac:
  - 'AC-1: Given a locally `CURRENT` and code-revision `CURRENT` receipt whose predecessor
    receipt IDs recursively return `CURRENT` in authored order and which is absent
    from supersession `invalidated_receipt_ids`, complete evaluation returns `CURRENT`.'
  - 'AC-2: Given a missing, non-current, or cyclic predecessor, evaluation returns
    `ERR_RECEIPT_PREDECESSOR_MISSING`, `ERR_RECEIPT_PREDECESSOR_INVALID`, or `ERR_RECEIPT_PREDECESSOR_CYCLE`
    with the blocking receipt ID; a supersession receipt naming the target in `invalidated_receipt_ids`
    returns `ERR_RECEIPT_SUPERSEDED` regardless of receipt ID or `issued_at`.'
  - 'AC-3: Given a receipt graph with a shared predecessor, memoized and repeated
    evaluation returns the same projection and leaves receipt bytes unchanged.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The receipt layer computes complete currentness across predecessor receipt graphs and later supersession while preserving immutable receipt data.

## Scope
In scope: recursive predecessor evaluation; missing and invalid predecessor reasons; cycle detection; later supersession; deterministic shared-predecessor evaluation; stable blocking-receipt identity; composed local and code currentness.

Out of scope: local field/proof rules, Git boundary classification, job readiness policy, completion transactions, and invalidation writes.

## Current Foundation And Ownership
Compose local evaluation from task #2014 with code-revision currency from task #2015 using the current `ReceiptStore`. This task owns predecessor/supersession closure only and does not mutate receipts.

## Authority
Resolve behavior from `REQ-009`, `REQ-015`, `NEG-002`, `NEG-010`, `IF-003`, and design sections 4.3, 6, and 13.

## Proof Guidance
Use a finite receipt graph table containing current chains, missing nodes, invalid nodes, cycles, later supersession, and shared predecessors. Lower evaluator matrices remain in tasks #2014 and #2015.

## Operative Contract Amendment
This section supersedes the earlier Outcome, Scope, Foundation, Authority, and Proof Guidance for the next build attempt.

### Outcome
The receipt layer composes local, code-revision, predecessor, and explicit supersession currentness while preserving immutable receipt bytes.

### Scope And Ownership
Consume local currentness from task #2014 and code-revision currency from task #2020. Evaluate predecessor receipt IDs in authored order with memoization. A supersession is causal only when its `invalidated_receipt_ids` explicitly names the target; receipt ID order and `issued_at` are not ordering authority. Own the complete currentness projection and supersession-reference index, but do not write invalidation or corrective work.

### Authority
Resolve behavior from `REQ-009`, `NEG-002`, `NEG-010`, `IF-003`, `RISK-003`, `PROOF-003`, and design sections 4.3.3 and 13. `REQ-015` is not receipt-currentness authority.

### Proof Guidance
Exercise the public evaluator over a finite receipt graph containing a current chain, missing predecessor, stale predecessor, cycle, explicit supersession reference, and shared predecessor. Lower local and Git matrices remain in tasks #2014 and #2020.

[[2026-07-23T18:16:46+02:00]]
## Shape Notes
- Task now consumes #2014 local currentness and #2020 code currency; #2015 is transitive through #2020.
- Supersession is causal only through `invalidated_receipt_ids`; receipt ID order and `issued_at` are not ordering authority.
- AC now enumerates missing, non-current, cyclic predecessor, and explicit supersession results with blocking receipt identity.
- Final concrete challenge passed. Task remains `build`, dependency-blocked behind #2020.

[[2026-07-23T22:20:36+02:00]]
## Builder Notes
- Change envelope: add complete immutable receipt currentness only in `ReceiptStore`, composing existing local and repository-history evaluators; preserve receipt bytes and do not add invalidation writes or lifecycle policy.
- Files changed: `serve/kanban/src/owlbear_kanban/receipt.py`; `serve/kanban/tests/test_change_receipts.py`.
- Change Module Map: no deviation. `ReceiptStore` is the mapped receipt owner; the existing local and code evaluators remain their lower-layer owners.
- Implementation: `ReceiptStore.evaluate_currentness()` builds an explicit supersession-reference index, evaluates predecessors in authored order with per-call memoization and cycle detection, and returns the required stable codes with blocking receipt identities.
- Durable-test justification: the finite receipt graph test protects shared runtime semantics that are easy to regress and not previously covered: missing, invalid, cyclic, superseded, and shared predecessor paths plus immutable-byte proof.
- Commands run: `uv run pytest serve/kanban/tests/test_change_receipts.py -q` (57 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/receipt.py serve/kanban/tests/test_change_receipts.py` (passed).
- AC evidence: AC-1 current chain and shared predecessor return `CURRENT`; AC-2 missing, invalid, cycle, and explicit supersession return their specified code and blocking receipt identity; AC-3 repeated projection equality and receipt-byte snapshots prove deterministic immutable evaluation.
- Current failure keys: none on entry. Focused proof found stale predecessor identity initially returned a lower-layer node ID; repaired to return the blocking predecessor receipt ID, then the focused suite passed.
- Builder challenger: pass. It reran the focused complete-currentness/immutability selection (2 passed) and found no blockers.
- Follow-up risks: none identified within scope.
