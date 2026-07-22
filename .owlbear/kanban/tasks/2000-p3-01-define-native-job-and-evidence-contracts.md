---
id: 2000
title: 'P3-01: Define native job and evidence contracts'
status: build
priority: high
created: 2026-07-22T21:58:09.010514+02:00
updated: 2026-07-23T00:32:28.777204+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - contracts
  - jobs
  - evidence
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-001
parent: 1979
depends_on: []
ac:
  - 'AC-1: Given schema-version-1 mappings for `shape`, `build`, `accept`, and `audit`,
    the public parser returns immutable job records containing operational identity,
    target/digest/predecessor references, claim/block/evidence links, and disposition;
    unknown kinds, fields, or malformed target identity return stable diagnostics.'
  - 'AC-2: Given one parsed job plus its current `ChangeRevision` and optional node
    plan, the public projection resolves title, outcome, acceptance, modules, interfaces,
    and proof from authority; serializing the job record contains none of those normative
    fields.'
  - "AC-3: Given schema-version-1 `shape`, `build`, `accept`, `audit`, and `supersession`
    receipt mappings, the public parser enforces each kind's target, delivery/node-plan
    digest, predecessor, evidence, and code-revision contract and returns deterministic
    serialization or stable diagnostics."
proof_bundle: behavioral+challenge
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
- `packet_id`: `DN-003-PK-001`

## Outcome
Versioned immutable contracts represent shape, build, accept, and audit jobs plus attempts, findings, claims, dispositions, kind-specific receipts, and authority-derived projections without copying normative graph truth into work records.

## Scope
In scope: public models, parsers, deterministic serializers, stable diagnostics, receipt payload contracts, and projection from `ChangeRevision` plus an optional node plan.

Out of scope: filesystem storage, lifecycle transitions, requests, invalidation, dispatch, agents, MCP, Cockpit, and bootstrap-carrier model changes.

## Current Foundation And Ownership
Deepen the native `jobs.py`, `receipt.py`, and package export boundary delivered by DN-001/DN-002. Do not extend legacy `models.py`, `engine.py`, `storage.py`, `request_models.py`, or `dispatch.py`; those remain the bootstrap carrier until later admitted nodes cut callers over and remove them.

## Authority
Resolve behavior from `DN-003`, `IF-003`, `REQ-009`, `NEG-001`, `NEG-002`, `NEG-010`, and receipt/job sections 3.5, 4, and 7 of the admitted design. Runtime records retain operational identity and references only; title, outcome, acceptance, modules, interfaces, risks, and proof come from authority projection.

Proof guidance: exercise public parsers, serializers, and authority projection with table-driven schema-version-1 mappings. Keep storage and lifecycle replacements outside this packet.

[[2026-07-22T23:43:16+02:00]]
## Builder Notes
- Change envelope: native job/evidence public contracts only; extended existing `jobs.py`, `receipt.py`, and package exports. No storage, lifecycle, dispatch, legacy carrier, MCP, Cockpit, or bootstrap changes.
- Files changed: `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/receipt.py`, `serve/kanban/src/owlbear_kanban/__init__.py`.
- Change Module Map deviations: none. Existing native module ownership supported the shaped boundary.
- Implementation: added immutable operational job references for node-plan, requests, attempts, findings, receipts, and supersession; added public `parse_receipt_mapping`, immutable parse result/diagnostic models, and stable diagnostics for invalid kind/field and missing target, predecessor, evidence, or code revision links. Existing `ReceiptStore` behavior remains unchanged.
- Proof selected: focused native job/receipt tests plus public parser smoke check.
- Durable-test justification: no durable tests added; existing focused coverage passed and the parser smoke check exercises the new public boundary without adding task-scoped test maintenance.
- Commands run: `uv run --project . pytest serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` -> `31 passed`; public parser import and missing-target diagnostic smoke -> `receipt parser smoke: ok`.
- Builder-challenger result: PASS. Challenger confirmed localized scope, typed public contracts, and preserved receipt-store behavior.
- Follow-up risks: receipt kind payloads remain intentionally represented as immutable JSON payloads at this packet boundary; deeper validity, digest, predecessor, code-revision, and lifecycle enforcement belongs to later shaped runtime packets.

[[2026-07-23T00:32:28+02:00]]
## Verify Notes
- Evidence reviewed: builder commit `4faba44e7` changed only `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/receipt.py`, and their public exports; its claimed module map has no ownership deviation. Existing focused suite passed: `uv run --project . pytest serve/kanban/tests/test_jobs.py serve/kanban/tests/test_change_receipts.py -q` produced `31 passed in 1.16s`.
- Named authorities checked: admitted design sections 3.5, 4, and 7.1; `REQ-009`, `IF-003`, `NEG-001`, `NEG-002`, and `NEG-010`. Job records retain only operational references and `project_job` sources title, outcome, acceptance, modules, interfaces, and proof from `ChangeRevision`, matching the authority-projection boundary.
- Change Module Map: no deviation. Changed modules remain `jobs.py`, `receipt.py`, and the package export boundary. No legacy carrier, storage, lifecycle, dispatch, MCP, or Cockpit path was changed.
- Normal-path boundary exercised: a public-API table probe parsed schema-version-1 shape/build/accept/audit jobs and shape/build/accept/audit/supersession receipts, then deterministically serialized the successful receipts. The existing tests did not exercise the new public parser or projection APIs, so they cannot prove the task AC by themselves.
- Finding: AC-3 is not satisfied. `parse_receipt_mapping` accepts a non-admission shape receipt lacking `node_plan_digest`, although the AC and design require enforcement of the delivery/node-plan digest contract. Reproduction command printed `BUG: shape receipt without node_plan_digest was accepted` after asserting `result.receipt is not None` for a shape receipt with target, predecessor, evidence, code revision, and no node-plan digest.
- Patches applied: none. This is an incomplete public receipt contract, not a verifier-local defect.
- Verifier-challenger: not called because the proposed route is rejection; challenger review is required only before PASS.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Implement kind-specific receipt payload validation for the required delivery/node-plan digest contract, including a stable missing-digest diagnostic, and add focused public parser coverage for all AC-3 receipt kinds. Preserve the existing receipt-store boundary. | `serve/kanban/src/owlbear_kanban/receipt.py`, focused existing receipt tests | The public parser accepts a shape receipt with no `node_plan_digest`; design section 3.5 and AC-3 require receipt-kind contracts. |

- Final route: REJECT to build.
