---
id: 2074
title: 'P15-04: Re-accept resumable design and admission at the candidate digest'
status: build
priority: high
created: 2026-07-26T01:59:00.156507+02:00
updated: 2026-07-26T01:59:00.156507+02:00
tags:
  - phase-15
  - candidate-reacceptance
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-005
  - scope:core
  - type:test
  - rigor:thorough
  - proof:PROOF-004
parent: 1968
depends_on:
  - 1982
  - 2073
ac:
  - 'AC-1: Given a rough or clear idea, the assembled design workflow persists intent
    and one-at-a-time decisions, delegates repository-grounded evidence/challenge,
    and resumes without losing confirmed state.'
  - 'AC-2: Given the candidate authority, the workflow presents its complete delivery
    graph and admits only the user-approved semantic digest through public validation/admission
    tools.'
  - 'AC-3: The task records candidate digest, tested SHA, commands, and results for
    DN-005; a failing interaction contract produces a scoped corrective implementation
    before re-acceptance.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; candidate re-acceptance of unchanged `DN-005` under `PROOF-004`.

## Outcome
The resumable user-facing design/admission workflow is re-proven against the newly admitted authority and current MCP surface.

## Envelope
In: `/ideate` and `/design`, decision persistence, research/challenge, graph presentation, approval/admission, PROOF-004.

Out: frontier planning, build, Cockpit, cutover.

Proof guidance: exercise the assembled workflow with durable session state and public tools; do not substitute a completed workflow fixture for the invocation boundary.