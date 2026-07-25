---
id: 2067
title: 'P11-02: Expose paged native work evidence and health resources'
status: build
priority: high
created: 2026-07-25T22:30:56.487007+02:00
updated: 2026-07-25T22:30:56.487007+02:00
tags:
  - phase-11
  - scope:cockpit-backend
  - api
  - jobs
  - evidence
  - health
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-010
  - packet:DN-010-PK-002
  - interface:IF-011
  - proof:PROOF-015
parent: 1987
depends_on:
  - 2066
ac:
  - 'AC-1: Given current native state plus cursor and limit inputs, nested jobs, attempts,
    findings, receipts, requests, activity, and health routes return core ordering
    and `next_cursor`; stale cursors return HTTP 409 `ERR_CURSOR_STALE`, and bad limits
    return 422.'
  - 'AC-2: Given a job, finding, or receipt identity, show routes return the authority-composed
    record; an absent identity returns its stable resource-specific 404 code without
    a filesystem path.'
  - 'AC-3: Given supersession receipts and corrective jobs, invalidation reads expose
    the affected closure, while work and change health expose bounded integrity and
    currentness findings without mutating authority or work stores.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-010-PK-002`.

## Outcome
Cockpit exposes bounded typed reads for native jobs, attempts, findings, receipts, requests, history, invalidation closure, and health.

## Envelope
In: native read routes, show routes, cursor/limit validation, supersession projection, work and change health.

Out: lifecycle controls, SSE, legacy inventory, frontend, cutover.

Proof guidance: drive public TestClient routes over a real NativeRuntime with a temporary lower store.