---
id: 2040
title: 'P5-06: Complete and prove the native MCP control plane'
status: build
priority: high
created: 2026-07-25T09:11:58.219921+02:00
updated: 2026-07-25T09:11:58.219921+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - integration
  - removal
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-006
  - interface:IF-010
  - proof:PROOF-011
parent: 1981
depends_on:
  - 2028
  - 2029
  - 2030
  - 2031
ac:
  - 'AC-1: With tool exclusions unset, the live FastMCP registry is `list_changes
    | show_change | validate_change | admit_change | list_jobs | show_job | pick_jobs
    | start_job | finish_plan | finish_build | finish_accept | finish_audit | release_job
    | recover_expired_claims | create_request | list_requests | show_request | change_health
    | work_health | list_activity | list_attempts | show_receipt`; schemas and `ToolAnnotations`
    match read, mutation, and idempotency semantics.'
  - 'AC-2: Registry and source inspection prove `list_tasks | show_task | create_task
    | edit_task | move_task | start_work | end_work | pick_tasks | finish_shape` plus
    compatibility aliases are absent, while the eight IF-015 operations preserve their
    proved request, result, and proof-checkout cleanup contracts.'
  - 'AC-3: A maintained PROOF-011 scenario invokes public MCP tools over the real
    graph-aware engine from change inspection and validation through admission, native
    request creation, job query, pick, start, purpose-specific completion, receipt,
    attempt and activity reads, and health; only temporary authority, work, and repository
    stores replace lower persistence.'
  - 'AC-4: Given malformed parameters, unknown identities, stale authority, request
    conflicts, admission conflicts, or transaction failure, public tools return stable
    JSON domain codes and artifact snapshots show no partial mutation by the affected
    operation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-006`. Resolve normative behavior from `DN-009`, `IF-010`, retained `IF-015`, `MIG-003`, `PROOF-011`, and `PROOF-014`; this record is not specification authority.

## Outcome
Complete one strict native OwlBear Kanban MCP control plane, preserve the eight IF-015 job operations within IF-010, remove generic task and old lifecycle registrations, and prove the assembled public workflow.

## Envelope
In: final FastMCP registration, strict schemas and annotations, stable JSON domain-error mapping, removal or replacement of obsolete MCP adapters/tests, retained IF-015 contracts, and maintained PROOF-011 integration evidence.

Out: activating native orchestration as the default, setup and seed changes, agent/prompt migration, Cockpit HTTP/UI, OpenSpec removal, legacy history snapshot, consumer cutover, and request resolution. DN-012 owns those atomic cutover outcomes.

Proof guidance: exercise public MCP tools over the real graph-aware engine from change inspection through admission, native request creation, job lifecycle, evidence reads, and health; replacements are limited to temporary authority, work, and repository stores below the MCP boundary.