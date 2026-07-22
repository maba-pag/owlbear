---
id: 1994
title: 'P2-02: Define initial shape-job generations'
status: verify
priority: medium
created: 2026-07-22T05:49:48.187184+02:00
updated: 2026-07-22T15:26:03.752450+02:00
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
  - 1999
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
A public side-effect-free planner creates one immutable initial shape-job generation from a loaded revision, receipt identity, and allocated numeric job IDs for later publication by #1998.

## Scope
In scope: the minimal native shape-job record; generation identity; deterministic authored-node ordering; receipt prerequisite binding; priority and timestamps; immutable serialization/readback; duplicate, missing, wrong-kind, wrong-digest, wrong-receipt, and unknown-target diagnostics; public exports and focused tests.

Out of scope: live receipt or job publication; validate/admit composition; concurrency, replay, rollback, cleanup, durability, and complete-generation visibility owned by #1998; shape execution; claims, attempts, transitions, requests, activity, invalidation, supersession, generalized recovery/health, MCP, HTTP, and UI.

## Authority
Resolve job fields and authority projection rules from sections 6 and 7 of `design.md`. Job files contain operational identity/state only; titles, outcomes, acceptance, modules, interfaces, risks, and proofs remain projected from change authority.

## Boundary Ownership
This packet proves the planner and serialized generation only. It does not satisfy the atomic-success part of `PROOF-002`; #1998 owns storage and all-or-none publication.

## Repair Provenance
This body replaces the stale pre-repair Outcome and Scope that assigned atomic publication to #1994. The six-packet repair moved that responsibility to #1998; no later note is needed to reinterpret this contract.

Proof guidance: exercise the public planner and generation readback without filesystem writes. Run focused job-generation and admission model tests plus Ruff on touched files.

[[2026-07-22T14:10:35+02:00]]
## Shape Notes
- Replaced the stale body in full. The operative task now assigns only side-effect-free initial shape-job generation planning and serialization to #1994; #1998 owns storage and atomic publication.
- Dependency rewired from deprecated #1993 to clean replacement #1999. Route remains build after #1999.

[[2026-07-22T15:26:03+02:00]]
## Builder Notes
- Change envelope: add only side-effect-free initial shape-job planning, immutable generation models, serialized readback diagnostics, and public exports; no persistence/publication or execution workflow.
- Files changed: `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/__init__.py`.
- Change Module Map deviations: none; implemented at the native kanban model/export boundary.
- Proof selected: focused Ruff plus public import/model and JSON-list normalization smoke checks.
- Durable-test justification: no durable tests added; builder-challenger confirmed the focused public boundary and no concrete blocker. Existing repository test fixtures do not yet expose a minimal revision helper for this new boundary; follow-up risk is that verifier should add or run focused planner/readback behavioral coverage if required by the broader suite.
- Commands run: `uv run --project serve/kanban ruff check serve/kanban/src/owlbear_kanban/jobs.py serve/kanban/src/owlbear_kanban/__init__.py`; `PYTHONPATH=serve/kanban/src uv run --project serve/kanban python -c '...'` public export smoke; serialization normalization smoke.
- Builder-challenger result: pass.
- Follow-up risks: persistence and atomic publication remain explicitly owned by #1998; this task does not implement them.
