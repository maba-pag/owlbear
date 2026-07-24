---
id: 2028
title: 'P5-02: Publish admission and initial native shape work atomically'
status: build
priority: high
created: 2026-07-24T23:21:52.955135+02:00
updated: 2026-07-24T23:22:44.339185+02:00
tags:
  - phase-5
  - scope:mcp-kanban
  - native-control-plane
  - admission
  - transaction
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - packet:DN-009-PK-002
  - interface:IF-010
parent: 1981
depends_on:
  - 2027
ac:
  - 'AC-1: Given current digest-bound challenge, baseline, approval, and limits evidence,
    public `admit_change` returns a `ReceiptRecord`, `JobGeneration`, and admitted
    `AdmissionAssessment` bound to that digest, and the persisted receipt and generation
    identities match the response.'
  - 'AC-2: Given evidence whose digest, challenge, baseline, approval, or limits fail
    admission, public `admit_change` returns the non-admitted assessment and writes
    neither a receipt nor a job generation.'
  - 'AC-3: Given an exact replay, public `admit_change` returns the persisted receipt
    and generation without duplication; changed immutable identity returns the stable
    admission-conflict `ToolError` and preserves the prior files.'
  - 'AC-4: Given an injected failure before multi-part commit or a recoverable transaction
    manifest, retry through public `admit_change` publishes both receipt and generation
    or neither, with no one-sided admitted artifact.'
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
`replace-delivery-pipeline` at `b56fedd21a54a670b5e192ef88a86d6cb4434597b264135ae6a9fd330458bdca`; `DN-009-PK-002`. Resolve normative behavior from `DN-009`, `IF-002`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Expose `admit_change` as a strict adapter over the existing admission transaction so one current revision publishes its immutable admission receipt and initial native shape-job generation as one recoverable operation.

## Envelope
In: MCP admission parameter/result models, stable admission error mapping, `AdmissionTransaction`, and focused transaction proof.

Out: design editing, graph mutation beyond admission-owned metadata, downstream dispatch/completion, requests, legacy removal, and core admission semantics.

Proof guidance: invoke public `admit_change` over the real admission and runtime transaction owners with a temporary change store and failure injection below the MCP boundary.