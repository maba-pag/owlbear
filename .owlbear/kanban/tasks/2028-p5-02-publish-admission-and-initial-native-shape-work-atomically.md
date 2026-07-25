---
id: 2028
title: 'P5-02: Publish admission and initial native plan work atomically'
status: build
priority: high
created: 2026-07-24T23:21:52.955135+02:00
updated: 2026-07-25T09:16:55.055026+02:00
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
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-009-PK-002`. Resolve normative behavior from `DN-009`, `IF-002`, `IF-010`, and `PROOF-011`; this record is not specification authority.

## Outcome
Expose `admit_change` as a strict adapter over the existing admission transaction so one current revision publishes its immutable admission receipt and initial native plan-job generation as one recoverable operation.

## Envelope
In: MCP admission parameter/result models, stable admission error mapping, `AdmissionTransaction`, and focused transaction proof.

Out: design editing, delivery-authority mutation beyond admission-owned metadata, downstream dispatch/completion, requests, legacy removal, and core admission semantics.

Proof guidance: invoke public `admit_change` over the real admission and runtime transaction owners with a temporary change store and failure injection below the MCP boundary.

[[2026-07-25T09:16:55+02:00]]
## Shape Notes
Connected partial-commit repair is summarized in #1981. Refreshed this packet to admitted digest `3f6c65628991` and replaced stale shape-job wording with initial plan-job generation. AC, parent, dependency on #2027, priority, and build route remain the approved T2 contract. Concrete graph passed shaper challenge.
