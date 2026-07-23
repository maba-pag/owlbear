---
id: 2016
title: 'P3-17: Resolve predecessor and supersession validity'
status: build
priority: high
created: 2026-07-23T14:41:23.761134+02:00
updated: 2026-07-23T14:41:23.761134+02:00
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
  - 2015
ac:
  - 'AC-1: Given a locally current and code-current receipt whose predecessor receipt
    IDs are recursively current and which has no later supersession, complete evaluation
    returns current.'
  - 'AC-2: Given a missing, invalid, or cyclic predecessor, or a later supersession,
    evaluation returns the stable reason identifying the blocking receipt.'
  - 'AC-3: Given a receipt graph with a shared predecessor, repeated evaluation is
    deterministic, returns the same projection, and does not change any receipt.'
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