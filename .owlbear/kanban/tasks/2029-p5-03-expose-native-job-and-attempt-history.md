---
id: 2029
title: 'P5-03: Expose native job and attempt history'
status: build
priority: high
created: 2026-07-24T23:22:11.768263+02:00
updated: 2026-07-25T09:16:55.064294+02:00
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
archival_reason:
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
