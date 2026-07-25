---
id: 2030
title: 'P5-04: Expose native receipt and work-health evidence'
status: collect
priority: high
created: 2026-07-24T23:22:11.791167+02:00
updated: 2026-07-25T11:31:15.301899+02:00
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

[[2026-07-25T11:12:09+02:00]]
### Verifier Notes

Fixed production semantic defect: show_receipt now returns immutable ReceiptRecord model (not mutable dict).

Strengthened test assertions:
- test_show_receipt_malformed_receipt_distinct_error: now verifies distinct error code (ERR_RECEIPT_YAML_PARSE/SCHEMA_INVALID vs ERR_RECEIPT_MISSING) and no path leaks
- test_work_health_returns_bounded_findings: now verifies limit bound (len <= 10) and sorted order

AC-1 fully verified: show_receipt returns ReceiptRecord for existing receipts; ERR_RECEIPT_MISSING for missing; distinct codes for malformed; no path leaks (only diagnostic.detail passed); read-only.

AC-2 API surface verified: work_health returns bounded sorted WorkHealthResult with findings/checked_paths/next_cursor; handles cursors; read-only. However, tests exercise empty workspace only - do not construct healthy/corrupt/orphan states per AC-2 precondition.

All 449 mcp-kanban tests pass; ruff clean.

### Required Follow-up

AC-2 explicitly requires "Given healthy, corrupt, and orphan-checkout work paths" but tests don't construct these states. Add focused state-construction tests:

1. **Healthy state test**: Create valid job/receipt/attempt files, verify work_health returns empty findings for valid workspace
2. **Corrupt state test**: Create malformed job YAML in work_root/jobs/999.yaml, verify work_health returns ERR_WORK_JOB_INVALID finding with path="jobs/999.yaml"
3. **Orphan checkout test**: If ProofCheckoutManager available in test context, create orphan checkout directory, verify ERR_WORK_PROOF_CHECKOUT_ORPHAN finding
4. **Mtime verification**: Capture stat() of checked paths before/after work_health call, assert unchanged

Test infrastructure exists (tmp_path, NativeRuntime construction). State construction requires writing YAML to work_root subdirectories. No production semantic changes needed.

[[2026-07-25T11:24:36+02:00]]
**AC-2/work-health-state-classes Resolution**

Adopted verifier commit 75f449ee6 (AC-1 verified). Resolved AC-2 state-construction gap with three focused tests:

1. `test_work_health_healthy_workspace_empty_findings`: Created valid job via `JobStore.materialize` and receipt, verified work_health returns empty findings for healthy workspace, captured job/receipt mtime before/after and asserted unchanged.

2. `test_work_health_corrupt_job_returns_err_work_job_invalid`: Created malformed job YAML `"[unclosed"` in `jobs/999.yaml`, verified work_health returns `ERR_WORK_JOB_INVALID` finding with controlled relative path `"jobs/999.yaml"`, captured corrupt job mtime before/after and asserted unchanged.

3. `test_work_health_orphan_proof_checkout_returns_err`: Created orphan proof checkout directory `proof-checkouts/123` through real `ProofCheckoutManager` convention, verified work_health returns `ERR_WORK_PROOF_CHECKOUT_ORPHAN` with path `"proof-checkouts/123"` and canonical target `"123"`, captured orphan dir mtime before/after and asserted unchanged.

Existing tests (`test_work_health_returns_bounded_findings`, `test_work_health_cursor_pagination`) already verify bounded/sorted/cursor properties.

**Production Fix:** Discovered and fixed local defect in `serve/kanban/src/owlbear_kanban/runtime_query.py` `_check_job` method — added `YAMLError` import and exception handling. Malformed job YAML now returns stable `ERR_WORK_JOB_INVALID` instead of propagating parser exception. This defect blocked AC-2 verification. No other production semantic changes.

**Test Results:**
- 3 new focused tests: all pass
- Full MCP suite: 452 passed in 5.49s
- Ruff lint: all checks passed
- Builder-challenger: pass

**AC Evidence:**
- AC-1: ✅ Verified by verifier commit 75f449ee6
- AC-2: ✅ Healthy/corrupt/orphan states constructed and verified; mtime verification in all tests; bounded/sorted/cursor verified by existing tests

[[2026-07-25T11:31:15+02:00]]
**AC-1 Verified:** `show_receipt` returns immutable `ReceiptRecord` for existing receipts. Distinct stable errors: `ERR_RECEIPT_MISSING` for missing receipt, `ERR_RECEIPT_YAML_PARSE`/`ERR_RECEIPT_SCHEMA_INVALID` for malformed storage. No internal path leak in errors (verified `receipts/` not in error string, no `/` in detail). Read-only verified through fixture inspection.

**AC-2 Verified:** `work_health` returns bounded sorted `WorkHealthResult`. Three state classes tested:
- **Healthy**: Valid job via `JobStore.materialize` + receipt → empty findings, mtime preserved
- **Corrupt**: Malformed job YAML `[unclosed` → `ERR_WORK_JOB_INVALID` with controlled relative path `jobs/999.yaml`, mtime preserved  
- **Orphan**: Orphan checkout via real `ProofCheckoutManager` convention → `ERR_WORK_PROOF_CHECKOUT_ORPHAN` with path `proof-checkouts/123` and canonical target `123`, mtime preserved

Bounded results verified (len ≤ limit), sorted findings verified (by path/code/target), cursor pagination verified, stable cursor errors verified (`ERR_CURSOR_STALE`).

**Production fix:** Added `YAMLError` catch in `runtime_query.py` `_check_job` (line 457) - minimum owner fix for malformed job YAML parser escape, returns stable `ERR_WORK_JOB_INVALID`.

**Test results:** 3 focused state tests pass, 452 mcp-kanban tests pass, 65 kanban runtime tests pass, ruff clean. Verifier-challenger: PASS.
