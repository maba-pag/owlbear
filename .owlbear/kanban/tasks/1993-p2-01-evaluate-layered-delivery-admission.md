---
id: 1993
title: 'P2-01: Evaluate layered delivery admission'
status: build
priority: medium
created: 2026-07-22T05:49:37.434986+02:00
updated: 2026-07-22T05:49:37.434986+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - validation
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-001
parent: 1978
depends_on: []
ac:
  - 'AC-1: Given the admitted historical fixture plus complete challenge dispositions,
    passing baselines, explicit approval, and known limits bound to its digest, the
    public evaluator returns no error findings, preserves warnings and limits, and
    repeated evaluation produces identical ordered findings and serialized output;
    verify through focused public-API tests.'
  - 'AC-2: Given A1-A10 table cases for uncovered or multiply-owned obligations, incomplete
    interfaces, migrations, risks, or proofs, and conflicting authority, each case
    returns its assigned stable error code with severity, target, evidence, detail,
    and remediation; verify through the public evaluator.'
  - 'AC-3: Given duplicate or dangling identities, cycles or disconnected nodes, invalid
    dependency assembly, boundary-substituting proof, stale digests, or node-bound
    violations, property cases reject deterministically and leave authority, receipt,
    and job paths absent or byte-for-byte unchanged.'
  - 'AC-4: Given missing, incomplete, failed, stale, or digest-mismatched challenge,
    baseline, approval, or limit evidence, stable findings block admission; challenge
    evidence must cover every requirement, interface, migration, risk, proof, workflow,
    and node, and a free-form pass cannot satisfy the gate.'
  - 'AC-5: Given durable fixtures for the four known historical defective-plan families
    and corrected equivalents, each defect rejects before persistence and each correction
    reaches an error-free assessment; verify with `uv run pytest serve/kanban/tests/test_admission.py
    -q` and Ruff on touched files.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-002`
- `packet_id`: `DN-002-PK-001`

## Outcome
A public deterministic admission-evaluation boundary consumes one loaded `ChangeRevision` plus structured, digest-bound challenge, baseline, approval, and known-limit evidence and returns one immutable ordered assessment with stable findings without mutating authority, receipts, or jobs.

## Scope
In scope: layered admission evidence models; A1-A10-equivalent delivery completeness and consistency checks; complete entity-by-entity challenge disposition validation; baseline, approval, digest, and limit gates; versioned stable findings; deterministic ordering and serialization; durable historical defective/corrected fixtures; public package exports and focused tests.

Out of scope: receipt or job writes; subprocess or agent spawning; a general command runner; MCP, HTTP, or UI contracts; job claims/transitions; invalidation, supersession, or recovery.

## Authority
Resolve normative behavior from `DN-002`, `REQ-002`, `REQ-003`, `IF-002`, `RISK-003`, `RISK-007`, and `PROOF-002` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`, plus admission sections 5 and 9 of `design.md`. This bootstrap task cannot add, weaken, or supersede those obligations.

Proof guidance: exercise the public evaluation boundary with the real `ChangeRevision`; temporary repositories and command-runner results may replace only mechanisms below admission. Run focused package pytest and Ruff on touched files. Durable tests are required for the admitted invariant matrix and historical planning defects.