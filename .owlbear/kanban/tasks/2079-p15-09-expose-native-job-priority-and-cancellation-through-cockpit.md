---
id: 2079
title: 'P15-09: Expose native job priority and cancellation through Cockpit'
status: build
priority: high
created: 2026-07-26T01:59:40.462624+02:00
updated: 2026-07-26T01:59:40.462624+02:00
tags:
  - phase-15
  - corrective-projection
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-010
  - scope:cockpit-backend
  - api
  - occ
  - type:build
  - rigor:thorough
  - interface:IF-011
  - proof:PROOF-015
parent: 1968
depends_on:
  - 1987
  - 2071
  - 2072
  - 2077
  - 2078
ac:
  - 'AC-1: Native job pages and details expose the current OCC token, and strict priority/cancel
    payloads require job ID, delivery digest, token, desired priority or cancellation
    timestamp without accepting generic mutable fields.'
  - 'AC-2: Public priority and cancel routes delegate to the DN-003 operations; success/replay
    returns refreshed job authority, while stale digest/token, active claim, and incompatible
    terminal state return HTTP 409 containing stable code, detail, current job/token/digest,
    and no partial mutation.'
  - 'AC-3: Assembled PROOF-015 covers malformed payload, injected core transaction
    failure, public OpenAPI intent-specific controls, `native-changed` invalidation,
    and complete store preservation; retired board/task mutation routes remain absent.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; corrective `DN-010` implementation for `REQ-026`, `IF-011`, and `DEC-034`.

## Outcome
Cockpit's native API exposes strict job priority/cancellation controls and current OCC identity without generic task mutation.

## Envelope
In: HTTP request/response models, job page/detail token, intent-specific routes, stable conflict envelopes, SSE invalidation, PROOF-015 refresh.

Out: frontend rendering, candidate-revision defaults, MCP control additions, cutover.

Proof guidance: exercise assembled FastAPI with the real native context/runtime and temporary store; malformed and core-failure cases compare complete state.