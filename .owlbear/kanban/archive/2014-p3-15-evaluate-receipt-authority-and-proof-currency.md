---
id: 2014
title: 'P3-15: Evaluate receipt authority and proof currency'
status: archived
priority: high
created: 2026-07-23T14:41:02.860272+02:00
updated: 2026-07-23T16:36:27.190213+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - receipts
  - validity
  - proof
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-E
parent: 2003
depends_on:
  - 2002
ac:
  - 'AC-1: Given a supported receipt whose target exists, whose delivery and required
    node-plan digests equal the loaded `ChangeRevision`, and whose evidence satisfies
    the target `Proof`, local evaluation returns current.'
  - 'AC-2: Given an unsupported schema, absent target, stale delivery digest, stale
    required node-plan digest, or unsatisfied proof, local evaluation returns the
    stable invalid reason for that class.'
  - 'AC-3: Given an admission receipt, evaluation uses delivery authority without
    a node-plan requirement; given a purpose-specific receipt, evaluation enforces
    the target, node-plan, and evidence fields required for that receipt kind.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
The receipt layer computes deterministic local currentness from schema support, target existence, loaded authority digests, and the target proof contract.

## Scope
In scope: supported schema; target existence; delivery and node-plan digest equality; evidence-to-proof satisfaction; admission receipt exception to node-plan requirements; kind-specific required fields; stable local-invalid reasons.

Out of scope: Git ancestry and touched-boundary currency, recursive predecessor validity, supersession, lifecycle guards, and completion transactions.

## Current Foundation And Ownership
Deepen the current `receipt.py` models and store using `ChangeRevision`, delivery-node, and `Proof` authority delivered through archived tasks #2000-#2002. This task owns local receipt authority/proof evaluation only.

## Authority
Resolve behavior from `REQ-009`, `REQ-015`, `REQ-016`, `NEG-002`, `NEG-010`, `IF-003`, and design sections 4.2, 4.3, 6, and 13.

## Proof Guidance
Use a finite evaluator table over receipt kind, schema, target, digest, and proof-satisfaction classes. Do not introduce Git history or predecessor graph cases here.

[[2026-07-23T15:09:52+02:00]]
## Builder Notes

- Change envelope: local receipt authority/proof currentness only. Added deterministic evaluation for schema support, target existence, delivery and node-plan digest equality, target proof evidence, and the admission exception; intentionally excluded Git code currency, predecessor recursion, supersession, lifecycle guards, and completion transactions.
- Files changed: `serve/kanban/src/owlbear_kanban/receipt.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_change_receipts.py`.
- Change Module Map deviations: none. The shaped receipt owner and its existing focused public-boundary test module were the direct source owners.
- Proof selected: durable public evaluator tests passed the Rent Test because currentness is a shared runtime boundary with stable return codes. They cover current, stale delivery/node-plan digests, missing target, unsatisfied proof, and admission-without-node-plan behavior.
- Commands run: `uv run pytest serve/kanban/tests/test_change_receipts.py` (37 passed); `uv run ruff check` on all three changed files (passed); `uv run ruff format --check` on all three changed files (passed).
- Builder challenger: pass; no concrete blockers.
- Follow-up risks: downstream tasks own Git code-revision currency, predecessor/supersession validity, and receipt-producing transaction/lifecycle operations.

[[2026-07-23T15:50:56+02:00]]
## Commit Recovery
- The original scoped builder commit succeeded as `4431cac7c` and is an ancestor of current `HEAD`; its exact paths are `receipt.py`, package `__init__.py`, `test_change_receipts.py`, and this task record.
- The empty exit-130 result was a terminal transport false negative. The three implementation/test paths have no uncommitted layer. Later history changed only `__init__.py` by adding the independently owned #2010/#2011 attempt exports.
- Recovery proof against current `HEAD`: `uv run pytest serve/kanban/tests/test_change_receipts.py` (37 passed); Ruff check passed; Ruff format check passed.
- Cleared `COMMIT_FAILED` without changing status `verify`; verification may resume from commit `4431cac7c`.

[[2026-07-23T16:29:14+02:00]]
## Verify Notes

- Evidence reviewed: Builder Notes; task AC-1 through AC-3; commit `4431cac7c`; current `HEAD`; focused receipt evaluator and its public test boundary.
- Named authorities checked: `.owlbear/changes/replace-delivery-pipeline/design.md` sections 4.2 and 4.3; `graph.yaml` REQ-009, REQ-015, REQ-016, NEG-002, NEG-010, and IF-003. The evaluator correctly stays in the local-currentness slice: it uses current delivery and node-plan digest authority and target `Proof`; predecessor validity, supersession, and code-revision currency remain excluded by task scope.
- Change Module Map: no deviation. The changed receipt owner, package export, and focused receipt test module are the direct mapped boundary. Later commits have not changed `receipt.py` or `test_change_receipts.py` since `4431cac7c`.
- Normal-path boundary exercised: parsed current target receipt through public `evaluate_receipt_currentness`; the focused suite also exercises stale delivery digest, stale node-plan digest, absent target, unsatisfied proof, and admission without node-plan/evidence.
- Checks run: `uv run pytest serve/kanban/tests/test_change_receipts.py` (37 passed); `uv run ruff check` on the three changed files (passed); `uv run ruff format --check` on the three changed files (passed); VS Code diagnostics reported no errors.
- Prior same-AC rejection check: no earlier `## Verify Notes` or verifier rejection exists for this task.
- Finding: AC-2 is unproven and unreachable at the intended evaluator boundary. `ReceiptRecord.schema_version` is `Literal[1]`, so the normal public parser rejects an unsupported schema with `SCHEMA_INVALID`; `evaluate_receipt_currentness` cannot receive such a record, although it advertises `SCHEMA_UNSUPPORTED`. The focused tests validate parser/store rejection only, not evaluator behavior.
- Patch applied: none. Resolving this requires builder-owned contract alignment: either admit the intended unsupported-schema evaluator input or revise the evaluator/AC boundary to make parsing the supported authority, with focused proof for the selected contract.
- Verifier-challenger: fail, confirming the AC-2 evaluator-boundary gap.
- Final route: REJECT to build.

[[2026-07-23T16:31:40+02:00]]
## Builder Notes

- Change envelope: receipt parsing/evaluator and strict store validation for unsupported schema versions. The behavior changes only at the local evaluator boundary: unsupported integer schemas now reach `evaluate_receipt_currentness` and return `ERR_RECEIPT_SCHEMA_UNSUPPORTED`; immutable store admission remains `ERR_RECEIPT_SCHEMA_INVALID`.
- Files changed: `serve/kanban/src/owlbear_kanban/receipt.py`; `serve/kanban/tests/test_change_receipts.py`.
- Change Module Map deviations: none. The existing receipt owner and its focused public-boundary test module remain the direct owners.
- Proof selected: added one durable regression test because the evaluator return code is a shared runtime contract and the previously unreachable branch could regress without observable parser-to-evaluator coverage. The existing store-envelope rejection test protects the strict persistence boundary.
- Commands run: `uv run pytest serve/kanban/tests/test_change_receipts.py` (38 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/receipt.py serve/kanban/tests/test_change_receipts.py` (passed); `uv run ruff format --check serve/kanban/src/owlbear_kanban/receipt.py serve/kanban/tests/test_change_receipts.py` (passed); `git diff --check` on changed files (passed); VS Code diagnostics reported no errors.
- Builder challenger: pass; no concrete blockers.
- Follow-up risks: none within local-currentness scope. Git code-revision currency, predecessor recursion, and supersession remain explicitly outside this task.

[[2026-07-23T16:35:20+02:00]]
## Verify Notes

- Evidence reviewed: AC-1 through AC-3; Builder Notes and commit `4c5dea7c`; the prior verifier rejection; the current receipt evaluator and its focused public test module.
- Named authorities checked: `.owlbear/changes/replace-delivery-pipeline/design.md` sections 4.2 and 4.3 and `graph.yaml` entries REQ-009, REQ-015, REQ-016, NEG-002, NEG-010, and IF-003. The evaluator correctly remains in this task's local-currentness slice: schema, target, loaded delivery/node-plan digest, and target Proof only. Predecessor, supersession, code-revision, lifecycle, and transaction behavior remain outside scope.
- Change Module Map: no deviation. The receipt owner, public export, and focused receipt tests are the direct mapped boundary. The verifier patch stayed within the evaluator and its existing regression table.
- Normal-path boundary exercised: parsed public receipt mappings flow into `evaluate_receipt_currentness`; the suite proves current target receipts, stale delivery and node-plan digests, absent targets, unsatisfied proof, unsupported schema, and admission without node-plan or evidence.
- Checks run: `uv run pytest serve/kanban/tests/test_change_receipts.py` passed 39 tests; Ruff check and Ruff format check passed for `receipt.py` and `test_change_receipts.py`; `git diff --check` passed for the verifier patch.
- Finding and local patch: verifier-challenger found `evidence.methods: null` could raise `TypeError` despite AC-2's stable invalid-result contract. Updated `_evaluate_target_receipt` to accept only tuples of strings and return `ERR_RECEIPT_PROOF_UNSATISFIED` otherwise; added the focused public-boundary regression. This is a local evaluator correction, not a scope expansion.
- Prior same-AC rejection check: the only earlier verifier rejection concerned unreachable unsupported-schema evaluation. Builder commit `4c5dea7c` resolved it, and the current suite exercises the parser-to-evaluator case. No repeated rejection family remains.
- Verifier-challenger: pass after the malformed-evidence patch; no remaining task defect.
- Final route: PASS to collect.

[[2026-07-23T16:36:27+02:00]]
## Collect Notes
- Classification: leaf. Task has no child tasks; its `type:build` receipt-authority scope contains no aggregate intent.
- Latest leaf verification evidence: newest `## Verify Notes` records PASS after the local malformed-evidence correction. `uv run pytest serve/kanban/tests/test_change_receipts.py` passed 39 tests; Ruff check, Ruff format check, and `git diff --check` passed. Verifier-challenger passed.
- Intent and invariant coverage: task Outcome and Scope define deterministic local receipt currentness. The verifier records coverage for supported schemas, targets, delivery and node-plan digest equality, target Proof satisfaction, admission exception, receipt-kind fields, and stable invalid reasons across AC-1 through AC-3.
- Child coverage: none; `list_tasks(parent=2014)` returned no tasks.
- Dependency gate: dependency #2002 is archived completed; task dependency state is ok.
- Residual decisions: `list_requests` found no pending or resolved structured requests for #2014.
- Archive rationale: latest verifier PASS is controlling evidence, with no later unresolved follow-up or request state. Archive as completed.
