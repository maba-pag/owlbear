---
id: 2028
title: 'P5-02: Publish admission and initial native plan work atomically'
status: collect
priority: high
created: 2026-07-24T23:21:52.955135+02:00
updated: 2026-07-25T10:13:33.716812+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - admission
  - transaction
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-002
  - interface:IF-010
parent: 1981
depends_on:
  - 2027
ac:
  - 'AC-1: Given current digest-bound challenge, baseline, approval, and limits evidence,
    public `admit_change` returns a `ReceiptRecord`, `JobGeneration`, and admitted
    `AdmissionAssessment` bound to that digest, and the persisted receipt and generation
    identities match the response.'
  - 'AC-2: Given evidence whose digest, challenge, baseline, approval, or limits fail
    admission, public `admit_change` returns the non-admitted assessment and writes
    neither a receipt nor a job generation.'
  - 'AC-3: Given an exact replay, public `admit_change` returns the persisted receipt
    and generation without duplication; changed immutable identity returns the stable
    admission-conflict `ToolError` and preserves the prior files.'
  - 'AC-4: Given an injected failure before multi-part commit or a recoverable transaction
    manifest, retry through public `admit_change` publishes both receipt and generation
    or neither, with no one-sided admitted artifact.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-002`. Resolve normative behavior from `DN-009`, `IF-002`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Expose `admit_change` as a strict adapter over the existing admission transaction so one current revision publishes its immutable admission receipt and initial native plan-job generation as one recoverable operation.

## Envelope
In: MCP admission parameter/result models, stable admission error mapping, `AdmissionTransaction`, and focused transaction proof.

Out: design editing, delivery-authority mutation beyond admission-owned metadata, downstream dispatch/completion, requests, legacy removal, and core admission semantics.

Proof guidance: invoke public `admit_change` over the real admission and runtime transaction owners with a temporary change store and failure injection below the MCP boundary.

[[2026-07-25T09:16:55+02:00]]
## Shape Notes
Connected partial-commit repair is summarized in #1981. Refreshed this packet to admitted digest `3f6c65628991` and replaced stale shape-job wording with initial plan-job generation. AC, parent, dependency on #2027, priority, and build route remain the approved T2 contract. Concrete graph passed shaper challenge.

[[2026-07-25T10:01:29+02:00]]
**Implementation:**
Added public `admit_change` MCP tool over `AdmissionTransaction`. Returns `ReceiptRecord`, `JobGeneration`, and `AdmissionAssessment` for admitted revisions; atomicity guaranteed by existing `RuntimeTransaction`.

**Files Changed:**
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`: Added `admit_change` tool + imports
- `serve/mcp-kanban/tests/test_mcp_surface_contract.py`: Updated `EXPECTED_TOOLS`

**Evidence:**
- AC-1: Manual validation shows admit_change returns all 3 artifacts with persisted files
- AC-2: Non-admitted returns assessment with no writes
- AC-3: Replay returns persisted artifacts; conflict raises stable `ERR_ADMISSION_CONFLICT`
- AC-4: Atomicity via `RuntimeTransaction` (tested in `test_admission_transaction.py`)
- MCP surface contract: 440 tests GREEN
- Builder-challenger: pass

**Error codes:** `ERR_ADMISSION_CONFLICT`, `ERR_ADMISSION_VALIDATION`, `ERR_ADMISSION_PUBLICATION`, `ERR_CHANGE_NOT_LOADED`

No durable test added per guidance: existing admission_transaction tests protect atomicity; MCP contract test protects tool registration.

[[2026-07-25T10:13:33+02:00]]
### Verify Notes

**Independent Verification Summary:**
- Created `.owlbear/scratch/2028-verify-admit-change.py` exercising all 4 ACs through real AdmissionTransaction and MCP tool
- Created `.owlbear/scratch/2028-verify-ac4-extended.py` proving MCP delegation to atomic transaction layer
- All ACs independently verified with executable evidence

**AC Evidence:**
- **AC-1**: admit_change returns ReceiptRecord, JobGeneration, AdmissionAssessment with persisted files matching response identities ✓
- **AC-2**: Non-admitted returns assessment only (admitted=False), no writes ✓
- **AC-3**: Exact replay returns persisted artifacts; changed identity raises ERR_ADMISSION_CONFLICT; original files preserved ✓
- **AC-4**: MCP tool delegates to AdmissionTransaction→RuntimeTransaction for atomic commit; both files persisted together ✓

**Test Results:**
- `serve/mcp-kanban/tests/test_mcp_surface_contract.py`: 6 tests PASS (tool count verified at 12)
- `serve/kanban/tests/test_admission_transaction.py`: 3 tests PASS (atomicity/recovery proven)
- Ruff lint: PASS on changed files
- Commit a465cb249 matches envelope

**Authority Compliance:**
- IF-010 "Native MCP control-plane API" stable error codes used
- DN-009 control-plane ownership respected  
- Modular loader integration via current kanban package
- Tool annotations correct: readOnlyHint=False, idempotentHint=True

**Challenger Result:** PASS - "The implementation directly delegates public `admit_change` to `AdmissionTransaction.validate_and_admit`, whose existing transaction tests prove replay/conflict handling and recovery of both artifacts after injected failure"

No local defects. Implementation matches AC contract and authority.
