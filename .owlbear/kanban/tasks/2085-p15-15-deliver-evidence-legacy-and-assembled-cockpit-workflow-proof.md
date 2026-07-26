---
id: 2085
title: 'P15-15: Deliver evidence, legacy, and assembled Cockpit workflow proof'
status: build
priority: high
created: 2026-07-26T02:00:36.235890+02:00
updated: 2026-07-26T02:00:36.235890+02:00
tags:
  - phase-15
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-011
  - packet:DN-011-PK-006
  - scope:cockpit-frontend
  - evidence
  - legacy
  - e2e
  - type:build
  - rigor:thorough
  - proof:PROOF-012
  - risk:RISK-010
  - risk:RISK-012
parent: 1988
depends_on:
  - 2082
  - 2083
  - 2084
ac:
  - 'AC-1: Final routing exposes Specification, Delivery, Requests, Activity, Evidence,
    Legacy, Memory, and Ideas; superseded Kanban/Decisions routes, task mutation components,
    and their maintained tests are absent, while Memory/Ideas core workflows remain
    unchanged.'
  - 'AC-2: Activity/Evidence defaults to current job/receipt state, permits full attempt/finding/receipt/invalidation
    history, displays receipt `code_revision`, labels stale/superseded chains, and
    shows legacy provenance plus truncation without mutation affordances.'
  - 'AC-3: A built SPA over real FastAPI and seeded native change/job stores completes
    change selection, graph/list, Delivery, request resolution, corrective history,
    evidence, legacy, Memory, and Ideas journeys at 1440×900 and 390×844 with no mocked
    HTTP; screenshots and checks prove nonblank, nonoverlapping, keyboard-reachable,
    bounded layout plus the 300-node scale case.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; `DN-011` packet 6 and `PROOF-012`.

## Outcome
Activity, Evidence, and Legacy complete the native Cockpit experience, and a built SPA over real FastAPI proves the desktop/mobile workflow while preserving Memory and Ideas continuity.

## Envelope
In: current/full history views, receipt commits/invalidation chain, legacy inventory, final routes/retirement, real native fixture stack, Playwright screenshots/geometry/a11y/scale.

Out: setup/snapshot/global cutover (DN-012), complete-system audit (DN-013), Memory/Ideas feature expansion.

Complexity waiver: Activity, Evidence, Legacy, route retirement, and assembled proof close one immutable-provenance experience; splitting proof would leave no build-owned real-stack boundary.

Proof guidance: build the SPA, start real FastAPI over a seeded native store, and run Playwright with no HTTP route interception under PROOF-012.