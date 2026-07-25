---
id: 2027
title: 'P5-01: Establish native MCP authority context and change inspection'
status: build
priority: high
created: 2026-07-24T23:21:34.679658+02:00
updated: 2026-07-25T09:16:54.914372+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - authority
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-001
  - interface:IF-010
parent: 1981
depends_on: []
ac:
  - 'AC-1: Given sibling admitted, draft, and malformed change packages, public `list_changes`
    returns deterministic identity-ordered typed summaries carrying state and digest
    or structured load diagnostics, and no response contains an absolute path.'
  - 'AC-2: Given an existing `change_id`, public `show_change` returns the loaded
    `ChangeRevision` projection with canonical digest and graph; missing or malformed
    authority returns a stable JSON `ToolError` code with no partial projection.'
  - 'AC-3: Given a loaded revision and `AdmissionEvidence`, public `validate_change`
    returns its `AdmissionAssessment`, including deterministic evidence and graph
    findings, without writing receipt, job, request, or attempt paths.'
  - 'AC-4: Given an existing or malformed `change_id`, public `change_health` returns
    the canonical `ChangeHealthResult` and leaves authority and work-path mtimes unchanged.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-001`. Resolve normative behavior from `DN-009`, `IF-001`, `IF-010`, `PROOF-011`, and design §14; this record is not specification authority.

## Outcome
Establish one strict native MCP context for sibling change authority and expose `list_changes`, `show_change`, `validate_change`, and `change_health` without mutating authority or work state.

## Envelope
In: `owlbear_mcp_kanban` lifespan/context, strict MCP parameter and response models, stable JSON domain-error mapping, and focused public-boundary proof over `load_change`, `evaluate_admission`, and `change_health`.

Out: admission publication, job/evidence queries, requests, lifecycle writes, generic-tool removal, Cockpit, setup, agents, and core engine changes.

Proof guidance: exercise the public MCP tools over real native authority loaders/evaluators with temporary changes and work roots; no durable test is required unless the existing contract suite cannot protect a concrete regression.

[[2026-07-25T09:16:54+02:00]]
## Shape Notes
Connected partial-commit repair is summarized in #1981. Refreshed this packet to admitted digest `3f6c65628991` and modular DN-009/IF-010 authority; outcome, AC, parent, dependencies, priority, and build route remain the approved T1 contract. Concrete graph passed shaper challenge.
