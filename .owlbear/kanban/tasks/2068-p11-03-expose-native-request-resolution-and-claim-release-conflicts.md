---
id: 2068
title: 'P11-03: Expose native request resolution and claim release conflicts'
status: build
priority: high
created: 2026-07-25T22:31:02.444553+02:00
updated: 2026-07-25T22:31:02.444553+02:00
tags:
  - phase-11
  - scope:cockpit-backend
  - api
  - requests
  - conflict
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-010
  - packet:DN-010-PK-003
  - interface:IF-011
parent: 1987
depends_on:
  - 2067
ac:
  - 'AC-1: Given a pending native request and matching revision and resolution identity,
    `POST` resolution returns local resume or material design reentry; replay returns
    the persisted result, while changed identity returns HTTP 409 with current authority.'
  - 'AC-2: Given an active job and matching claim identity, `POST` release appends
    one release event and clears coordination and checkout state; replay is stable,
    while stale, non-owner, terminal, or injected transaction failure preserves complete
    state and returns a stable conflict.'
  - 'AC-3: Malformed control payloads return HTTP 422 before runtime dispatch, and
    native diagnostics preserve code, detail, lower code, target, and current holder
    or digest fields in the HTTP envelope.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-010-PK-003`.

## Outcome
Cockpit exposes only native intent-specific request resolution and matching-identity claim release controls with stable conflict responses.

## Envelope
In: request resolution, claim release, strict payloads, replay, ownership and transaction diagnostics.

Out: start/finish/reject/invalidate controls, generic task transitions, SSE, frontend, cutover.

Proof guidance: cross public TestClient routes; inject failures below the route/runtime boundary and compare complete store state.