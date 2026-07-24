---
id: 2029
title: 'P5-03: Expose native job and attempt history'
status: build
priority: high
created: 2026-07-24T23:22:11.768263+02:00
updated: 2026-07-24T23:22:44.346924+02:00
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
blocked: true
block_reason: 'PARTIAL_GRAPH_COMMIT: #2032 creation rejected by ERR_AC_ITEM_TOO_LONG;
  recovery owner shaper must create approved T6 with each AC <=500 chars, complete
  #1981 projection/dependency routing, audit #2027-#2032, then clear blocks.'
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `b56fedd21a54a670b5e192ef88a86d6cb4434597b264135ae6a9fd330458bdca`; `DN-009-PK-003`. Resolve normative behavior from `DN-009`, `IF-003`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Expose bounded native job, attempt, and activity reads through `list_jobs`, `show_job`, `list_attempts`, and `list_activity` while keeping authority projection distinct from orthogonal operational projection.

## Envelope
In: MCP query models, cursor/error mapping, `NativeRuntime` paged queries, and MCP-local `ShowJobResponse` composed from public `JobStore.read` and `project_job` results.

Out: receipt lookup and work health, lifecycle writes, request mutation, admission, legacy removal, private runtime-query accessors, page scans to emulate single lookup, and core engine changes.

Proof guidance: exercise public MCP reads over real native job and attempt stores with a temporary work root; prove cursor and missing-identity outcomes without bypassing the MCP boundary.