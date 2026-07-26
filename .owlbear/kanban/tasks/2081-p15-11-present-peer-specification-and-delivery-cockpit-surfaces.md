---
id: 2081
title: 'P15-11: Present peer Specification and Delivery Cockpit surfaces'
status: build
priority: high
created: 2026-07-26T01:59:59.934764+02:00
updated: 2026-07-26T01:59:59.934764+02:00
tags:
  - phase-15
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-011
  - packet:DN-011-PK-002
  - scope:cockpit-frontend
  - shell
  - specification
  - responsive
  - type:build
  - rigor:thorough
  - risk:RISK-010
parent: 1988
depends_on:
  - 2080
ac:
  - 'AC-1: Given loaded and invalid change summaries, the shell exposes peer `Specification`
    and `Delivery` navigation, stores selected `change_id` in the URL, and labels
    invalid authority with text plus icon rather than color alone.'
  - 'AC-2: Given change detail, Specification displays current digest, Product Intent,
    implementation design, accepted decisions, and authority metadata with retained-data
    Retry states and no task-history dependency.'
  - 'AC-3: At 1440×900 and 390×844, keyboard navigation reaches change selection and
    authority sections, shell controls do not overlap, and the page has no horizontal
    viewport overflow.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; `DN-011` packet 2 for `REQ-010`, `IF-012`, and `RISK-010`.

## Outcome
Cockpit navigation presents Specification and Delivery as peer product phases, with URL-addressable current change authority.

## Envelope
In: routes/shell/provider, change selector, Specification authority reader, invalid/missing/loading/error states, responsive keyboard shell.

Out: graph visualization, operational board, requests, evidence, legacy, feature changes to Memory/Ideas.

Proof guidance: component tests plus browser geometry/focus checks at 1440×900 and 390×844; lower HTTP may be replaced here because PROOF-012 belongs to the final packet.