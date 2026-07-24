---
id: 2030
title: 'P5-04: Expose native receipt and work-health evidence'
status: build
priority: high
created: 2026-07-24T23:22:11.791167+02:00
updated: 2026-07-24T23:22:44.354923+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - evidence
  - health
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-004
  - interface:IF-010
parent: 1981
depends_on:
  - 2027
ac:
  - 'AC-1: Given an existing `receipt_id`, public `show_receipt` returns its immutable
    `ReceiptRecord`; a missing receipt and malformed receipt storage return distinct
    stable `ToolError` codes without exposing internal paths or changing storage.'
  - 'AC-2: Given healthy, corrupt, and orphan-checkout work paths, public `work_health`
    returns bounded sorted `WorkHealthResult` findings and checked paths with stable
    cursors and leaves those paths unchanged.'
proof_bundle: existing+challenge
blocked: true
block_reason: 'PARTIAL_GRAPH_COMMIT: #2032 creation rejected by ERR_AC_ITEM_TOO_LONG;
  recovery owner shaper must create approved T6 with each AC <=500 chars, complete
  #1981 projection/dependency routing, audit #2027-#2032, then clear blocks.'
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `b56fedd21a54a670b5e192ef88a86d6cb4434597b264135ae6a9fd330458bdca`; `DN-009-PK-004`. Resolve normative behavior from `DN-009`, `IF-003`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Expose immutable receipt lookup and bounded native work integrity through `show_receipt` and `work_health`.

## Envelope
In: strict MCP response/error models, `ReceiptStore.read`, `NativeRuntime.work_health`, and focused storage-integrity proof.

Out: admission writes, job lifecycle, request mutation, corrective invalidation, change health, legacy removal, and core engine changes.

Proof guidance: invoke the public tools over real receipt, work, and proof-checkout stores in temporary roots; assert stable findings and no mutation.