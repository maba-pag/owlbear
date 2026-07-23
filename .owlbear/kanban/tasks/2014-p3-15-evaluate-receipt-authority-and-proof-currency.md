---
id: 2014
title: 'P3-15: Evaluate receipt authority and proof currency'
status: verify
priority: high
created: 2026-07-23T14:41:02.860272+02:00
updated: 2026-07-23T15:50:56.400078+02:00
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
archival_reason:
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
