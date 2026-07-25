---
id: 2069
title: 'P11-04: Cut Cockpit backend to native SSE and legacy inventory'
status: build
priority: high
created: 2026-07-25T22:31:09.091791+02:00
updated: 2026-07-25T22:31:09.091791+02:00
tags:
  - phase-11
  - scope:cockpit-backend
  - api
  - sse
  - legacy
  - cutover
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-010
  - packet:DN-010-PK-004
  - interface:IF-011
  - migration:MIG-003
parent: 1987
depends_on:
  - 2067
  - 2068
ac:
  - 'AC-1: Given canonical authority or work-path create, modify, delete, or mixed
    batches, `/api/events` emits one `native-changed` event with sorted affected resource
    classes and a monotonic token; temporary noise is suppressed and disconnect or
    missing roots terminate cleanly.'
  - 'AC-2: Given empty or populated legacy task, request, and activity stores, `GET
    /api/legacy` returns bounded read-only inventory with provenance and no mutation
    links; write methods are absent.'
  - 'AC-3: The assembled app returns 404 or 405 for board, task, task activity/session,
    generic request, and task mutation paths, while native resources plus memory,
    ideas, and liveness remain registered.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-010-PK-004`.

## Outcome
The assembled Cockpit backend emits native resource invalidations, exposes read-only legacy inventory, and unregisters its generic task surface.

## Envelope
In: SSE watch/classification, legacy reads, FastAPI router composition, old backend route absence.

Out: frontend migration, immutable legacy snapshot generation, repository-wide cutover.

Proof guidance: inspect assembled FastAPI route inventory and exercise SSE and legacy HTTP boundaries through TestClient.