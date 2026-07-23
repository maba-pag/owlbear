---
id: 2008
title: 'P3-09: Define and persist native evidence records'
status: build
priority: high
created: 2026-07-23T02:23:31.452855+02:00
updated: 2026-07-23T02:23:31.452855+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - evidence
  - storage
  - security
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-009
parent: 2001
depends_on:
  - 2000
ac:
  - 'AC-1: Given schema-version-1 attempt-event and finding mappings, public parsers
    return frozen records preserving the fields defined in Scope. Unknown fields,
    malformed identities, non-positive sequences, unsupported event, target, or class
    literals, and missing required references return stable diagnostics.'
  - 'AC-2: Given public attempt/finding create, read, and list calls against an explicit
    work root, replay returns the existing record; a differing occupied identity raises
    `EvidenceConflictError` with `code == "ERR_EVIDENCE_CONFLICT"`. Traversal or symlink
    substitution returns a stable path diagnostic, lists sort by canonical identity
    and sequence, and failed writes leave no temporary or partial record.'
  - 'AC-3: Given `ReceiptStore` built from a loaded `ChangeRevision`, public list
    reads only `.owlbear/changes/<change-id>/receipts/`, returns entries sorted by
    receipt ID, and represents malformed or unsafe entries with `ReceiptDiagnostic`
    results. Existing create/read and `ReceiptConflictError` behavior remain unchanged,
    and no receipt bytes are written beneath the work root.'
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
- `packet_id`: `DN-003-PK-009`

## Outcome
Versioned immutable attempt-event and finding contracts plus contained work-evidence storage preserve operational history; canonical change-plane receipts gain public deterministic listing without work-root duplication.

## Scope
In scope: public frozen models, parsers, serializers, and stable diagnostics for attempt events and findings. An attempt event preserves attempt, job, change, digest, and target references; actor/process identity; positive monotonic sequence; event kind and timestamp; optional detail and evidence references. A finding preserves finding, source-attempt, source-job, change, and digest references; one design-enumerated target kind and ID; one design-enumerated finding class; detail; and timestamp.

Also in scope: explicit work-root attempt/finding create, read, and list operations; immutable replay; conflict, path-containment, no-overwrite, and deterministic-order behavior; and public `ReceiptStore.list` on the existing `ChangeRevision`-bound canonical store.

Out of scope: job storage or OCC; claim and lifecycle predicates; finding routing or invalidation; receipt relocation or create/read redesign; multi-record transactions and recovery; MCP; and Cockpit.

## Current Foundation And Ownership
Deepen the native job/receipt contract boundary delivered by packet `DN-003-PK-001`. Add one cohesive evidence owner under `owlbear_kanban`; extend the existing `ReceiptStore` rather than creating a second receipt store. Reuse descriptor-relative, no-follow, no-overwrite, fsync, and stable-diagnostic patterns from `receipt.py` and `storage_io.py` when current source supports them.

Public immutable evidence creation returns the existing record on byte-equivalent replay. A differing record at an occupied attempt-event or finding identity raises exported `EvidenceConflictError` with `code == "ERR_EVIDENCE_CONFLICT"`.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, design sections 2, 3.5, 7.2, 10, and 13, and packet `DN-003-PK-001`. Finding target kinds are requirements, interfaces, migrations, risks, workflows, delivery nodes, packets, proofs, receipts, and code revisions. Finding classes are `implementation-defect`, `unforeseeable-discovery`, `planning-omission`, and `scope-change`.

Proof guidance: exercise public parser round trips and public store APIs over temporary explicit change and work roots for replay, malformed-entry listing, containment, no-overwrite, deterministic order, and durable readback; run the focused check plus a downstream-impact scan.