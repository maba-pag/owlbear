---
id: 2027
title: 'P5-01: Establish native MCP authority context and change inspection'
status: build
priority: high
created: 2026-07-24T23:21:34.679658+02:00
updated: 2026-07-24T23:22:44.330871+02:00
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
blocked: true
block_reason: 'PARTIAL_GRAPH_COMMIT: #2032 creation rejected by ERR_AC_ITEM_TOO_LONG;
  recovery owner shaper must create approved T6 with each AC <=500 chars, complete
  #1981 projection/dependency routing, audit #2027-#2032, then clear blocks.'
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `b56fedd21a54a670b5e192ef88a86d6cb4434597b264135ae6a9fd330458bdca`; `DN-009-PK-001`. Resolve normative behavior from `DN-009`, `IF-010`, `PROOF-011`, and design §14; this record is not specification authority.

## Outcome
Establish one strict native MCP context for sibling change authority and expose `list_changes`, `show_change`, `validate_change`, and `change_health` without mutating authority or work state.

## Envelope
In: `owlbear_mcp_kanban` lifespan/context, strict MCP parameter and response models, stable JSON domain-error mapping, and focused public-boundary proof over `load_change`, `evaluate_admission`, and `change_health`.

Out: admission publication, job/evidence queries, requests, lifecycle writes, generic-tool removal, Cockpit, setup, agents, and core engine changes.

Proof guidance: exercise the public MCP tools over real native authority loaders/evaluators with temporary changes and work roots; no durable test is required unless the existing contract suite cannot protect a concrete regression.