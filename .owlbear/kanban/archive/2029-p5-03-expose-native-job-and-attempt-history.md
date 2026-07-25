---
id: 2029
title: 'P5-03: Expose native job and attempt history'
status: archived
priority: high
created: 2026-07-24T23:22:11.768263+02:00
updated: 2026-07-25T10:49:56.788580+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - query
  - history
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-003
  - interface:IF-010
parent: 1981
depends_on:
  - 2027
ac:
  - 'AC-1: Given active and archived purpose-specific jobs plus a `candidate_revision`,
    public `list_jobs` returns bounded `RuntimeJobProjection` pages carrying readiness,
    claim, request, attempt, finding, receipt, validity, and disposition state with
    a stable next cursor; a stale cursor returns a stable cursor `ToolError` without
    mutation.'
  - 'AC-2: Given an existing `job_id`, public `show_job` returns a strict response
    composed from the immutable `JobRecord` and its `JobProjection` fields `title`,
    `outcome`, `acceptance`, `modules`, `interfaces`, and `proof`; a missing ID returns
    a stable not-found `ToolError`.'
  - 'AC-3: Given started and terminal attempts, public `list_attempts` returns bounded
    pages ordered by attempt ID and sequence with stable cursors and preserves the
    stored events.'
  - 'AC-4: Given attempt, finding, receipt, and request history, public `list_activity`
    returns bounded chronological `RuntimeHistoryEntry` pages ordered by timestamp
    and identity with stable cursors and no mutation.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-003`. Resolve normative behavior from `DN-009`, `IF-003`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Expose bounded native job, attempt, and activity reads through `list_jobs`, `show_job`, `list_attempts`, and `list_activity` while keeping authority projection distinct from orthogonal operational projection.

## Envelope
In: MCP query models, cursor/error mapping, `NativeRuntime` paged queries, and MCP-local `ShowJobResponse` composed from public `JobStore.read` and `project_job` results.

Out: receipt lookup and work health, lifecycle writes, request mutation, admission, legacy removal, private runtime-query accessors, page scans to emulate single lookup, and core engine changes.

Proof guidance: exercise public MCP reads over real native job and attempt stores with a temporary work root; prove cursor and missing-identity outcomes without bypassing the MCP boundary.

[[2026-07-25T09:16:55+02:00]]
## Shape Notes
Connected partial-commit repair is summarized in #1981. Refreshed this packet to admitted digest `3f6c65628991`; outcome, AC, parent, dependency on #2027, priority, and build route remain the approved T3 contract. Current public query producers were source-checked and the concrete graph passed shaper challenge.

[[2026-07-25T10:28:20+02:00]]
[[2026-07-25T10:26:45+02:00]]
## Build Notes
Implemented 4 public MCP read tools for native job/attempt/activity history:

**Scope Delivered:**
- `list_jobs`: bounded RuntimeJobProjection pages with stable cursors, stale-cursor ERR_CURSOR_STALE ToolError
- `show_job`: composed from JobStore.read (immutable JobRecord) + project_job (authority title/outcome/acceptance/modules/interfaces/proof)
- `list_attempts`: bounded AttemptEvent pages with stable cursors
- `list_activity`: bounded RuntimeHistoryEntry pages (list_history) with stable cursors

All tools use NativeRuntime paged APIs; show_job does not scan pages. Cursor ValueError mapped to ERR_CURSOR_STALE. All tools marked readOnlyHint=True, idempotentHint=True, destructiveHint=False.

**Test Coverage:**
- test_mcp_native_query_tools.py: 4 focused AC tests covering page structure, field composition, cursor handling
- test_mcp_surface_contract.py: Updated EXPECTED_TOOLS deployment contract
- Full suite: 444 tests pass, ruff clean

**Changed Files:**
- serve/mcp-kanban/src/owlbear_mcp_kanban/models.py: +4 params classes
- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py: +4 tools, project_job import, __all__ update
- serve/mcp-kanban/tests/test_mcp_native_query_tools.py: +4 tests (new file)
- serve/mcp-kanban/tests/test_mcp_surface_contract.py: EXPECTED_TOOLS += 4

Builder-challenger: pass (AC evidence aligned, no mutation, stable error paths)

[[2026-07-25T10:42:00+02:00]]
**Verifier: PASS**

Production code correct - all 4 MCP tools delegate to NativeRuntime paged queries with proper error mapping, show_job uses JobStore.read + project_job composition, RuntimeJobProjection has all required fields, ordering correct.

Strengthened test_mcp_native_query_tools.py (verifier local correction per Rent Test):
- AC-1: Added active+archived jobs, all projection fields, cursor pagination, stale cursor error
- AC-2: Added JobRecord composition check, missing job error
- AC-3: Added event ordering, field preservation, cursor error
- AC-4: Added chronological ordering, kind fields, cursor error

444 tests pass, ruff clean. Verifier-challenger: pass.

[[2026-07-25T10:49:56+02:00]]
**Archive Readiness Verified:**

**Builder Evidence:** 97e871765b1f — implemented 4 public MCP read tools (list_jobs, show_job, list_attempts, list_activity); all tools use NativeRuntime paged APIs with proper cursor/error mapping; show_job composes JobStore.read + project_job; 444 mcp-kanban tests pass, ruff clean, builder-challenger pass.

**Verifier Evidence:** b5db52e2ecc9 — strengthened test_mcp_native_query_tools.py to protect real pagination/error/order/history-kind risks; all 4 AC proven with exact public MCP boundary exercises; verifier-challenger pass.

**AC Proof:**
- AC-1: test_list_jobs_returns_paged_projection — active+archived jobs, all RuntimeJobProjection fields (readiness/claim/request/attempt/finding/receipt/validity/disposition), cursor pagination, stale cursor ERR_CURSOR_STALE ToolError
- AC-2: test_show_job_composes_immutable_record_and_projection — JobRecord composition + JobProjection authority fields (title/outcome/acceptance/modules/interfaces/proof), missing job ERR_JOB_NOT_FOUND
- AC-3: test_list_attempts_returns_paged_events — bounded pages ordered by (attempt_id, sequence), field preservation, cursor error
- AC-4: test_list_activity_returns_chronological_history — chronological (timestamp, identity) ordering, kind-specific fields for all 4 history entry types (attempt/finding/receipt/request), cursor pagination and error

**Quality:** 444 tests pass in mcp-kanban domain at HEAD (b5db52e2e); ruff clean; one unrelated serve/kanban test failed (background quality debt, not task-owned).

**Scope:** Changed files confined to serve/mcp-kanban/{src,tests}; no scratch files remain; current digest 3f6c65628991; leaf task under parent #1981.

**Durable Test Quality:** Verifier-strengthened test_mcp_native_query_tools.py protects concrete behavioral risks — pagination boundary handling, cursor stability, error path stability, ordering invariants, and history-kind field contracts. Passes Rent Test: easy to regress cursor/error/ordering behavior, hard to notice manually, shared public MCP boundary, cheaper to maintain than repeated manual verification.
