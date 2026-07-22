---
id: 1994
title: 'P2-02: Define initial shape-job generations'
status: build
priority: medium
created: 2026-07-22T05:49:48.187184+02:00
updated: 2026-07-22T13:47:11.797985+02:00
tags:
  - phase-1
  - scope:core
  - admission
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-002
  - packet:DN-002-PK-002
  - jobs
  - schema
parent: 1978
depends_on:
  - 1993
ac:
  - 'AC-1: Given a revision, admission receipt identity, and allocated numeric IDs,
    the public planner returns one immutable kind=`shape` job per authored delivery
    node in authored order; records bind change ID, digest, target node, receipt prerequisite,
    priority, and timestamps.'
  - 'AC-2: Serialized generation readback preserves those operational fields and rejects
    duplicate numeric IDs, duplicate or missing node targets, non-shape kinds, digest
    or receipt mismatch, and targets outside the revision with structured diagnostics.'
  - 'AC-3: Job mappings omit authority-owned title, outcome, acceptance, module, interface,
    risk, and proof prose; inspection confirms claims, attempts, transitions, invalidation,
    supersession, requests, MCP, HTTP, and UI remain absent.'
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
- `delivery_node_id`: `DN-002`
- `packet_id`: `DN-002-PK-002`

## Outcome
The public validate/admit operation commits one immutable schema-version-1 admission receipt plus exactly one initial shape job per delivery node as one observable generation, or returns stable findings with no newly visible admission or jobs.

## Scope
In scope: validate/admit composition over the real evaluator; minimal native shape-job identity/state required at admission; staged receipt/job publication; conflict-safe all-or-none commit, replay, concurrency, scoped cleanup, durable readback, public exports, and focused transaction/failure tests.

Out of scope: shape execution; claims, attempts, completion, requests, activity, invalidation, supersession, generalized transaction recovery or health; build/accept/audit job creation; MCP, HTTP, and UI contracts.

## Authority
Resolve normative behavior from `DN-002`, `REQ-002`, `REQ-003`, `IF-002`, `RISK-003`, `RISK-007`, and `PROOF-002` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`, plus the job-record and transaction constraints in sections 7, 9, and 13 of `design.md`. This bootstrap task cannot add, weaken, or supersede those obligations.

Proof guidance: exercise the assembled public validate/admit operation before any native jobs exist. Use temporary repository/job stores and failure injection only below admission; do not mock the evaluator. Run the focused admission, ChangeRevision, and receipt suites plus Ruff on touched files. Durable tests are required by the atomic no-work-before-admission boundary.

[[2026-07-22T13:47:11+02:00]]
## Shape Notes
- Connected repair supersedes this task's original atomic-publication Outcome and Scope. This packet now owns only the immutable initial shape-job generation schema, planner, serialization, and malformed-generation diagnostics.
- It performs no live job or receipt publication. The assembled receipt-plus-jobs transaction, concurrency, replay, failure injection, and zero-mutation proof moved to #1998.
- This split preserves the admitted job fields in design section 7 while keeping claims, attempts, transitions, requests, invalidation, supersession, generalized recovery/health, MCP, HTTP, and UI outside DN-002.
- Dependency remains #1993; route remains build. The independently corrected six-packet graph passed `shaper-challenger`.
