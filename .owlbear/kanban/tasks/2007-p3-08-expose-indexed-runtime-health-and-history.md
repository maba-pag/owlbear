---
id: 2007
title: 'P3-08: Expose indexed runtime health and history'
status: build
priority: low
created: 2026-07-22T22:07:25.462842+02:00
updated: 2026-07-22T22:07:25.462842+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - health
  - history
  - indexes
  - scale
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-008
parent: 1979
depends_on:
  - 2006
ac:
  - 'AC-1: Given current, blocked, stale, cancelled, superseded, failed-attempt, and
    completed jobs, public projections preserve immutable job kind and expose dependency
    readiness, claim, request, block, attempt, finding, receipt, validity, and disposition
    separately while authority-derived fields come from the current graph and node
    plan.'
  - 'AC-2: Given cursor/limit queries over 500 nodes and at least 2,000 combined jobs,
    attempts, findings, and receipts, list and history operations return deterministic
    bounded pages and current-validity/dependency indexes update only the affected
    closure after supersession; repeated unchanged queries return identical identities
    and order.'
  - 'AC-3: Given dangling references, stale digests, broken predecessor or supersession
    chains, orphan records, unsafe entries, unresolved transaction manifests, or index
    disagreement, `work_health` returns stable findings and checked paths or cursors
    without mutation; healthy stores return no findings.'
proof_bundle: behavioral+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-008`

## Outcome
Deterministic native runtime projections, validity indexes, paginated history, and bounded health scans make hundreds of graph, work, and evidence records inspectable without treating stale records as current.

## Scope
In scope: public job, evidence, request, and history projections; current-validity and dependency indexes with explicit invalidation; deterministic pagination; work health and recovery-manifest findings.

Out of scope: dispatch selection, MCP, HTTP, UI, and automated repair.

## Current Foundation And Ownership
Build over the native runtime facade, stores, receipt validity, requests, and invalidation closure delivered by preceding packets. This packet owns the integrated public health and projection proof for `REQ-023`, `KEEP-006`, `RISK-006`, and the remaining `PROOF-003` read boundary; lower store instrumentation is test evidence only.

## Authority
Resolve behavior from `REQ-009`, `REQ-023`, `KEEP-006`, `KEEP-007`, `IF-003`, `RISK-006`, `PROOF-003`, and design sections 7.3, 8.5, 9.7, and 13.

Proof guidance: exercise public projection and health operations over scale and corruption fixtures; instrument lower store reads only to prove index-bounded behavior.