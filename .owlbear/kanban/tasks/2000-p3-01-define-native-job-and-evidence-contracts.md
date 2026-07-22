---
id: 2000
title: 'P3-01: Define native job and evidence contracts'
status: verify
priority: high
created: 2026-07-22T21:58:09.010514+02:00
updated: 2026-07-22T23:44:29.787380+02:00
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
blocked: true
block_reason: 'COMMIT_FAILED: commit-owned refused mixed pre-existing edits in task-owned
  source paths; recover with an explicit scoped commit after separating the pre-existing
  changes from builder changes.'
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
