---
id: 2084
title: 'P15-14: Build native change and job request resolution'
status: build
priority: high
created: 2026-07-26T02:00:27.248344+02:00
updated: 2026-07-26T15:12:14.272099+02:00
tags:
  - phase-15
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-011
  - packet:DN-011-PK-005
  - scope:cockpit-frontend
  - requests
  - accessibility
  - type:build
  - rigor:thorough
  - requirement:REQ-015
parent: 1988
depends_on:
  - 2083
ac:
  - 'AC-1: Given pending and resolved native requests, Requests displays decision
    pros, cons, risks, recommendation, confidence, or action evidence/resume condition,
    with current change/node/job context and working deep links.'
  - 'AC-2: Given local or material resolution, submission includes the selected change
    digest and renders resumed linked jobs or `design-reentry` from the server result
    before refreshing affected resources.'
  - 'AC-3: Given revision/reference/persisted-resolution conflict, the resolver retains
    the submitted option or response, displays server current request snapshot/digest,
    and offers Retry or return with predictable focus at desktop and mobile widths.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at: 2026-07-26T15:12:14.272099+02:00
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; `DN-011` packet 5 for `REQ-010`, `REQ-015`, `KEEP-006`, and `IF-012`.

## Outcome
Requests presents complete decision/action context and preserves user input across local/material success and authority conflicts.

## Envelope
In: pending/resolved request lists/details, decision tradeoffs, action evidence, linked navigation, resolver modal/page, focus/mobile/conflict state.

Out: backend request semantics, job controls, evidence history, final real-stack proof.

Proof guidance: component/browser tests use IF-011-grounded payloads and exercise keyboard/focus restoration plus responsive layouts.