---
id: 2020
title: 'P3-16B: Classify receipt code-revision currency'
status: verify
priority: high
created: 2026-07-23T17:39:16.311514+02:00
updated: 2026-07-23T22:09:11.371414+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - receipts
  - validity
  - git
  - impact-closure
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-K
parent: 2003
depends_on:
  - 2015
ac:
  - 'AC-1: Given identical existing tested and candidate commits, code-revision evaluation
    returns `CURRENT` without querying changed paths.'
  - 'AC-2: Given an existing candidate descendant whose normalized Git name-status
    paths do not intersect the frozen impact closure, evaluation returns `CURRENT`;
    rename and copy source and destination paths both participate.'
  - 'AC-3: Given a missing tested or candidate commit, evaluation returns `ERR_RECEIPT_CODE_REVISION_MISSING`;
    given an existing candidate that is not a descendant, it returns `ERR_RECEIPT_CODE_REVISION_NOT_DESCENDANT`.'
  - 'AC-4: Given a normalized changed path intersecting a frozen file or tree selector,
    evaluation returns `ERR_RECEIPT_CODE_PATH_STALE` and identifies the changed path
    and selector.'
  - "AC-5: Given malformed status or arity, strict-UTF-8 decode failure, a path rejected
    by task #2015's shared validator, or repository-query failure, evaluation returns
    `ERR_RECEIPT_CODE_HISTORY_UNAVAILABLE` and never `CURRENT`."
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The receipt evaluator classifies exact and descendant commits against a frozen typed impact closure through one deterministic repository-history contract.

## Scope
In scope: tested/candidate commit existence; descendant ancestry; NUL-delimited Git name-status changes; rename/copy source and destination paths; file/tree selector intersection; stable code-currency results; malformed, undecodable, unsafe, ambiguous, and unavailable history.

Changed paths are decoded and normalized through the public path validator produced by task #2015; this task does not reimplement selector validation. Repository history is engine-owned below the evaluator. Proof-checkout creation and cleanup remain DN-004 responsibilities.

Out of scope: receipt closure parsing/issuance, local authority/proof currentness, predecessor recursion, supersession, lifecycle operations, and proof checkout lifecycle.

## Current Foundation And Ownership
Consume the immutable `ImpactClosure` and shared path validator from task #2015. This task owns `RepositoryHistory`, the code-currency evaluator, and the `CURRENT`, `ERR_RECEIPT_CODE_REVISION_MISSING`, `ERR_RECEIPT_CODE_REVISION_NOT_DESCENDANT`, `ERR_RECEIPT_CODE_PATH_STALE`, and `ERR_RECEIPT_CODE_HISTORY_UNAVAILABLE` results.

## Authority
Resolve behavior from `REQ-009`, `NEG-010`, `IF-003`, `RISK-003`, `PROOF-003`, accepted `DEC-021`, and design sections 4.3.2 and 12.

## Proof Guidance
Exercise the public evaluator over a bounded temporary Git history containing exact, missing, non-descendant, disjoint descendant, intersecting file/tree, rename, and copy cases. Inject malformed status/arity, strict-UTF-8 failure, unsafe path, and repository-query failure below the evaluator; do not replace the evaluator or the shared path validator.

## Packet Identity Correction
- Stable packet identity: `DN-003-PK-004-K`.
- This unused suffix distinguishes code-revision currency from #2016 predecessor/supersession packet `DN-003-PK-004-G`. The existing Markdown filename is a stable Kanban storage path and is not packet identity.

[[2026-07-23T22:09:11+02:00]]
## Builder Notes
- Change envelope: extend the receipt validity boundary with deterministic Git-backed code-revision currency only; preserve local-currentness and later composition ownership.
- Files changed: `serve/kanban/src/owlbear_kanban/receipt.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_change_receipts.py`.
- Change Module Map: no shaped map was supplied. Source confirmed the existing receipt module owns `ReceiptValidity` and local currentness; added `RepositoryHistory`, `GitRepositoryHistory`, and `evaluate_code_revision_currency` there. No deviation.
- Proof selected: durable behavioral test passes the Rent Test because receipt currency is a shared, fail-closed evidence-validity boundary with non-obvious Git status parsing.
- Commands run: `uv run pytest serve/kanban/tests/test_change_receipts.py -q` (56 passed); `uv run ruff check` on all touched files (passed); `uv run ruff format --check` on all touched files (passed); `git diff --check` on task-owned files (passed).
- AC evidence: AC-1 exact existing revisions return `CURRENT` before name-status; AC-2 real descendant, rename, and copy histories evaluate both source and destination paths; AC-3 real missing and side-branch revisions produce the specified results; AC-4 file/tree intersections return stale result with path and selector; AC-5 malformed arity, invalid UTF-8, unsafe path, and query failure return history unavailable.
- Current failure-key resolutions: none.
- Builder-challenger: pass; independently ran the focused receipt suite (56 passed) and found no concrete blocker.
- Follow-up risks: complete currentness composition remains owned by task #2016.
