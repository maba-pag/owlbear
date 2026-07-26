---
id: 2083
title: 'P15-13: Replace task Kanban with immutable-purpose Delivery jobs'
status: verify
priority: high
created: 2026-07-26T02:00:14.063453+02:00
updated: 2026-07-26T14:55:09.654807+02:00
tags:
  - phase-15
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-011
  - packet:DN-011-PK-004
  - scope:cockpit-frontend
  - delivery
  - jobs
  - responsive
  - type:build
  - rigor:thorough
  - requirement:REQ-026
parent: 1988
depends_on:
  - 2079
  - 2081
ac:
  - 'AC-1: Given native jobs, Delivery renders `Plan | Build | Accept | Audit` columns
    or responsive list groups; cards expose job/change/node identity, integer priority,
    readiness, claim age, request/block, digest currentness, latest finding/attempt,
    receipt state, and text/icon status.'
  - 'AC-2: Available job commands are prioritize, cancel, release claim, inspect,
    and resolve linked request when their eligibility permits; drag, arbitrary status
    movement, generic field editing, and job-kind mutation are absent.'
  - 'AC-3: Given administrative/release success, affected job data refreshes; given
    HTTP 409, the card/detail remains visible with submitted intent retained and conflict
    code, current job/token/digest, plus Retry or resolution action.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; `DN-011` packet 4 for `REQ-010`, `REQ-026`, `KEEP-006`, and `IF-012`.

## Outcome
Delivery presents Plan, Build, Accept, and Audit work with immutable purpose, complete operational signals, and intent-specific controls.

## Envelope
In: native job board/list/detail, filters/grouping, priority/cancel/release actions, conflict recovery, keyboard/responsive behavior, retirement of task mutation UI.

Out: request resolver internals, evidence/history views, final real-stack proof.

Proof guidance: component and browser tests may use grounded HTTP fixtures; assert absent drag/arbitrary edit paths and retained state on conflicts.

[[2026-07-26T14:55:09+02:00]]
Builder implementation at digest bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357 and base SHA 5c29404e169456e787d495663c0403ef2d766096. Delivery groups Plan/Build/Accept/Audit native jobs with complete identity/readiness/claim/request/block/digest/attempt/finding/receipt/status signals and no drag/generic edit/status/kind mutation. Intent controls prioritize/cancel/release/inspect/resolve request; actual retained job/request detail and linked action/decision resolver. Success refreshes; 409 retains intent/current authority and adopts safe tokens/digests; release non-owner requires Refresh authority. Backend release conflicts all include current job/token. Validation frontend1509/2skip, backend179, build, component12, Playwright3 desktop/mobile/conflict, Ruff, final challenger PASS.
