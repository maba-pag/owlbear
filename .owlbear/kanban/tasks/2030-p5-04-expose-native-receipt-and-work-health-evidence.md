---
id: 2030
title: 'P5-04: Expose native receipt and work-health evidence'
status: verify
priority: high
created: 2026-07-24T23:22:11.791167+02:00
updated: 2026-07-25T10:58:23.988547+02:00
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
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-004`. Resolve normative behavior from `DN-009`, `IF-003`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Expose immutable receipt lookup and bounded native work integrity through `show_receipt` and `work_health`.

## Envelope
In: strict MCP response/error models, `ReceiptStore.read`, `NativeRuntime.work_health`, and focused storage-integrity proof.

Out: admission writes, job lifecycle, request mutation, corrective invalidation, change health, legacy removal, and core engine changes.

Proof guidance: invoke the public tools over real receipt, work, and proof-checkout stores in temporary roots; assert stable findings and no mutation.

[[2026-07-25T09:16:55+02:00]]
## Shape Notes
Connected partial-commit repair is summarized in #1981. Refreshed this packet to admitted digest `3f6c65628991`; outcome, AC, parent, dependency on #2027, priority, and build route remain the approved T4 contract. Current receipt/health producers were source-checked and the concrete graph passed shaper challenge.

[[2026-07-25T10:58:23+02:00]]
Implemented show_receipt and work_health MCP tools over ReceiptStore.read and NativeRuntime.work_health.

**Implementation:**
- Added ShowReceiptParams and WorkHealthParams models to models.py
- Implemented show_receipt tool: returns immutable ReceiptRecord or distinct stable errors (ERR_RECEIPT_MISSING for missing, other ReceiptDiagnosticCode for malformed)
- Implemented work_health tool: returns bounded WorkHealthResult with findings, checked_paths, stable cursor pagination
- Both tools follow existing MCP patterns: read-only, idempotent, stable error codes
- Updated __all__ exports and EXPECTED_TOOLS deployment contract

**Validation:**
- Added 5 tests to test_mcp_native_query_tools.py covering AC-1 (receipt read, missing/malformed errors) and AC-2 (work health structure, pagination, cursor errors)
- All 449 mcp-kanban tests pass
- Ruff lint clean
- Builder-challenger passed: "5 tests passed in 1.58s. The new read-only MCP tools are registered, the receipt and work-health behaviors are exercised, and the deployment-contract snapshot remains aligned."

**AC Evidence:**
- AC-1: show_receipt returns ReceiptRecord for existing receipts; distinct ERR_RECEIPT_MISSING vs other ReceiptDiagnosticCode errors; no path leak; read-only
- AC-2: work_health returns bounded WorkHealthResult with sorted findings, checked_paths, stable next_cursor; ERR_CURSOR_STALE on invalid cursor; read-only
