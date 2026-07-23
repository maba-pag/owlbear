---
id: 2015
title: 'P3-16: Classify receipt code-revision currency'
status: build
priority: high
created: 2026-07-23T14:41:09.745275+02:00
updated: 2026-07-23T14:41:09.745275+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - receipts
  - validity
  - git
  - proof-boundary
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-F
parent: 2003
depends_on:
  - 2014
ac:
  - 'AC-1: Given a receipt tested at the exact current commit, code-revision evaluation
    returns current.'
  - 'AC-2: Given a descendant commit whose changed paths do not intersect the receipt
    proof boundary, code-revision evaluation returns current.'
  - 'AC-3: Given a non-descendant commit, missing tested revision, or descendant whose
    changed paths intersect the receipt proof boundary, evaluation returns the stable
    stale reason for that class.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Receipt currentness classifies the tested commit and permitted untouched descendants against the receipt proof boundary with stable stale reasons.

## Scope
In scope: exact tested commit; descendant ancestry; changed paths since tested commit; proof-boundary intersection; missing and non-descendant revisions; deterministic stale reasons; supplied repository boundary below the engine.

Out of scope: local schema/authority/proof evaluation, predecessor recursion, supersession, lifecycle operations, and proof checkout creation.

## Current Foundation And Ownership
Consume local receipt evaluation from task #2014 and deepen `receipt.py` with one code-revision currency boundary. Repository and changed-path access are supplied below the engine; this task does not own Git checkout lifecycle.

## Authority
Resolve behavior from `REQ-009`, `REQ-015`, `NEG-010`, `RISK-003`, `PROOF-003`, and design sections 4.3, 9.5, and 13.

## Proof Guidance
Build a bounded temporary Git history containing exact, untouched-descendant, touched-descendant, non-descendant, and missing revision classes. Keep receipt-graph cases out of this proof.