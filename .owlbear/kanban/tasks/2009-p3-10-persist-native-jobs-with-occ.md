---
id: 2009
title: 'P3-10: Persist native jobs with OCC'
status: build
priority: high
created: 2026-07-23T02:23:45.208534+02:00
updated: 2026-07-23T02:23:45.208534+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - jobs
  - storage
  - occ
  - security
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-010
parent: 2001
depends_on:
  - 2000
ac:
  - 'AC-1: Given an empty explicit work root and accepted `JobGeneration`, public
    materialization writes one active shape job per target using supplied IDs and
    digest/receipt references, then lists records and OCC tokens by job ID. Replay
    returns the same records, tokens, and bytes; a differing occupied ID raises `JobConflictError`
    with `code == "ERR_JOB_CONFLICT"`, and traversal or symlink substitution preserves
    committed bytes.'
  - 'AC-2: Given a current OCC token, one public operational update or active-to-archive
    move commits one complete `JobRecord` with a new token. Given a stale token or
    two processes using the same token, one call succeeds and each loser raises `JobConcurrencyError`
    with `code == "ERR_JOB_OCC_STALE"`; one readable record remains in active or archive
    storage with no temporary or partial file.'
proof_bundle: critical+challenge
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
- `packet_id`: `DN-003-PK-010`

## Outcome
Contained active/archive job storage materializes accepted `JobGeneration` and updates one operational job record under optimistic concurrency control without copying normative authority.

## Scope
In scope: explicit work-root job topology; active/archive create, read, and list operations; generation materialization with supplied positive monotonic IDs; immutable OCC tokens; operational updates; active-to-archive moves; deterministic ordering; path and symlink containment; and no-overwrite behavior.

Out of scope: attempts, findings, and receipts; cross-record transactions and recovery manifests; lifecycle predicates; requests; invalidation; dispatch; proof checkout; and live workspace data creation.

## Current Foundation And Ownership
Deepen the native `jobs.py` contracts delivered by packet `DN-003-PK-001` behind one cohesive job-store owner. Reuse descriptor-relative, no-follow, no-overwrite, fsync, and stable-diagnostic patterns from `receipt.py` and `storage_io.py` when current source supports them. Replace neither legacy task storage nor its callers.

Public writes return a frozen `JobRecord` plus its current OCC token. A differing record at an occupied job ID raises exported `JobConflictError` with `code == "ERR_JOB_CONFLICT"`; a stale token raises exported `JobConcurrencyError` with `code == "ERR_JOB_OCC_STALE"`. Byte-equivalent replay returns the same record, token, and bytes.

## Authority
Resolve behavior from `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, design sections 2, 7.1, and 13, and packet `DN-003-PK-001`.

Proof guidance: exercise public job-store APIs over a temporary explicit work root for idempotent materialization, stale-token and real two-process OCC races, containment, no-overwrite, deterministic listing, and durable readback. Store-level proof supplements later public transaction proof and does not claim the complete `PROOF-003` boundary.