---
id: 2001
title: 'P3-02: Persist native work records with OCC'
status: shape
priority: high
created: 2026-07-22T21:58:20.087459+02:00
updated: 2026-07-23T00:51:49.600768+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - storage
  - occ
  - security
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-002
parent: 1979
depends_on:
  - 2000
ac:
  - 'AC-1: Given an empty explicit work root and one accepted `JobGeneration`, the
    store materializes one active shape job per generated target with the supplied
    monotonic IDs and digest/receipt references; exact replay is idempotent, while
    conflicting identity or payload returns a stable conflict and leaves committed
    records unchanged.'
  - 'AC-2: Given a current job OCC token, one operational update or active-to-archive
    move commits a new token atomically; a stale token or two-process race permits
    one winner and preserves one complete readable record without overwrite.'
  - 'AC-3: Given attempt, finding, or receipt creation plus traversal, symlink, and
    existing-destination cases, immutable create/read/list operations preserve deterministic
    identity and order, reject escape or overwrite, and leave no temporary or partial
    record.'
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
- `packet_id`: `DN-003-PK-002`

## Outcome
Contained native work-plane stores materialize generated jobs, update operational job state under optimistic concurrency control, archive terminal jobs, and append immutable evidence without overwriting history.

## Scope
In scope: explicit work-root topology; active/archive job storage; immutable attempt, finding, and receipt create/read/list behavior; monotonic ID materialization; OCC tokens; path and symlink containment; deterministic ordering.

Out of scope: multi-record business transactions and recovery manifests, lifecycle predicates, request semantics, invalidation closure, dispatch, proof checkout, and live workspace data creation.

## Current Foundation And Ownership
Reuse the hardened descriptor-relative and no-overwrite patterns in native `receipt.py`. Replace neither legacy task storage nor its callers. Store-level OCC proof supplements the later public engine proof; it does not claim the complete `PROOF-003` boundary.

## Authority
Resolve behavior from `IF-003`, `REQ-016`, `KEEP-007`, `RISK-002`, design sections 2, 7.1, and 13, and the contracts delivered by packet `DN-003-PK-001`.

Proof guidance: use a temporary work root and public store APIs for exact replay, stale-token, two-process, containment, no-overwrite, and durable readback checks.

[[2026-07-23T00:51:49+02:00]]
## Builder Notes
- Change envelope: a native `serve/kanban` work-store owner for active/archive jobs with OCC and immutable evidence; no legacy carrier, lifecycle, dispatch, MCP, or Cockpit changes.
- Files changed: none.
- Change Module Map deviations: no Shape Notes/module map was supplied. Source inspection identified `jobs.py` and `receipt.py` as the local contract owners.
- Rejection reason: the shaped scope and AC require receipt create/read/list behavior in an explicit work root, but design sections 2, 3, and 7.1 place immutable receipts in `.owlbear/changes/<change-id>/receipts/` (the authority plane), and the delivered `ReceiptStore` is intentionally bound to `ChangeRevision` rather than a work root. A work-root receipt store would create a second canonical receipt authority, contradicting IF-003 and design section 13's no-independent-store-mutation rule. Shape must choose one canonical receipt location and identify whether this packet extends `ReceiptStore` (including its required list API) or limits this packet to jobs/attempts/findings in the work root.
- Proof selected: authority-versus-source contract inspection; no implementation was safe to validate.
- Commands run: exact authority searches; `uv run --project . test-root serve/kanban/src/owlbear_kanban/jobs.py` (resolved `uv run pytest`).
- Builder-challenger result: not invoked; a DONE verdict was not proposed.
- Follow-up risk: acceptance criteria currently require stable conflict behavior but do not name the public result/error contract for work-root records; shape should specify it alongside the receipt-location decision.
