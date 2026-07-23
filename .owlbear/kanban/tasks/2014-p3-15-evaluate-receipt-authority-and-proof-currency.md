---
id: 2014
title: 'P3-15: Evaluate receipt authority and proof currency'
status: build
priority: high
created: 2026-07-23T14:41:02.860272+02:00
updated: 2026-07-23T14:41:02.860272+02:00
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