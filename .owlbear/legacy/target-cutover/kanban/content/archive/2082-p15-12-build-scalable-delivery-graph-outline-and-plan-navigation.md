---
id: 2082
title: 'P15-12: Build scalable delivery graph outline and plan navigation'
status: archived
priority: high
created: 2026-07-26T02:00:06.968192+02:00
updated: 2026-07-26T13:59:32.535566+02:00
tags:
  - phase-15
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-011
  - packet:DN-011-PK-003
  - scope:cockpit-frontend
  - graph
  - virtualization
  - scale
  - type:build
  - rigor:thorough
  - risk:RISK-012
parent: 1988
depends_on:
  - 2081
ac:
  - 'AC-1: Given `ChangeGraphResponse`, the outline exposes node outcome, dependencies,
    owned/supported obligations, modules, produced/consumed interfaces, risks, proof,
    and available packet plans with URL-addressable node selection.'
  - 'AC-2: Given requirement, interface, migration, and proof filters, outline and
    optional graph modes expose the same matching nodes; mobile defaults to the outline,
    and graph visualization is never the sole navigation path.'
  - 'AC-3: Given a schema-valid 300-node fixture, filtering or deep-linking to `DN-275`
    reveals it with fewer than 100 node rows mounted, and desktop/mobile checks show
    nonblank bounded content without horizontal page overflow.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; `DN-011` packet 3 for `REQ-010`, `IF-012`, and `RISK-012`.

## Outcome
Users inspect and filter large delivery graphs and node plans through a scalable outline baseline with optional graph enhancement.

## Envelope
In: graph/list projection, node detail and plan panel, overlays/filters, virtualization, deep links, desktop/mobile geometry.

Out: job board, request resolution, evidence history, assembled backend proof.

Proof guidance: use a proven virtualization library; use a proven graph library only if visualization ships. Component/browser proof uses schema-valid 14-node and 300-node fixtures.

[[2026-07-26T13:43:36+02:00]]
Builder implementation at digest bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357 and base SHA 491fa3183c495dc40153c413c2d6971cfeea6283. Added @tanstack/react-virtual outline, URL node deep links, requirement/interface/migration/proof filters, full node authority and packet plans, listbox Arrow navigation, retained graph Retry. One exact shared generator feeds canonical DeliveryGraph schema tests, 14/300 component fixtures and 300-node Playwright fixtures. Filtered-out selections rewrite URL; zero matches empty; DN-275 mounts <100 rows. Validation: schema/component10, Specification2, browser2 desktop/mobile, full frontend1498 pass/2skip, build, final challenger PASS.

[[2026-07-26T13:53:10+02:00]]
Verifier rejected d102e4e5141b9a0b2b20c3b2fe97adb68dbbd25f: shared fixture packet plans depend on prior-node packets, violating runtime local-plan dependency rules. Return for plan-fixture correction and complete response validation.

[[2026-07-26T13:55:45+02:00]]
Final repair makes every shared one-packet plan dependency-free and validates complete ChangeGraphResponse plan references: plan node exists, dependencies stay local, authority targets resolve. Build, schema/component10, Playwright2 pass; final signoff PASS.

[[2026-07-26T13:58:57+02:00]]
## Verify Notes
PASS at tested commit `c39205ec7199bc3baab872fddd68f7a756c1aae4` (delivery digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`). Read-only verification; no files changed and no commit created.

- Named authority and fixture boundary: the shared 14-node and 300-node generator is accepted by the canonical Python `DeliveryGraph` schema. Complete response checks prove every plan node exists, packet dependencies remain local to its plan, and authority targets resolve. This closes the prior verifier failure for cross-node packet dependencies.
- AC-1: `GraphFixtureSchema.test.ts` and `DeliveryGraphOutline.test.tsx` prove URL-addressable selection plus node outcome, dependencies, obligations, modules, interfaces, risks, proof, and packet plan authority.
- AC-2: component proof covers requirement, interface, migration, and proof filters, zero-match behavior, filtered selection URL repair, and keyboard outline navigation; Chromium mobile proof confirms the outline remains the navigation path.
- AC-3: the schema-valid 300-node fixture deep-links to `DN-275` with fewer than 100 mounted rows. Chromium desktop and mobile proof confirms nonblank bounded outline/list/detail geometry and no horizontal page overflow.
- Focused Vitest: `npm test` targeting `GraphFixtureSchema.test.ts` and `DeliveryGraphOutline.test.tsx` passed 2 files and 10 tests.
- Browser proof: Playwright `delivery-graph-outline.spec.ts` in the Chromium project passed desktop and mobile, 2 tests total; configured startup rebuilt and previewed the frontend.
- Change Module Map deviation: none observed in the requested `serve/cockpit/web` verification boundary. Replacements below the normal-path boundary: API responses only; real Chromium exercised the assembled frontend navigation and geometry.
- Prior same-failure-key rejection: one prior build return for local packet-plan dependency validity; repaired shared fixture and complete response validation close that key.
- Verifier challenger: `pass`; no blocking findings.

Final route: PASS to collect.

[[2026-07-26T13:59:32+02:00]]
## Collect Notes
ARCHIVED as a leaf task. No child tasks exist, dependency gate is clear, and no pending or resolved structured requests remain.

Latest verification evidence is the `## Verify Notes` PASS at tested commit `c39205ec7199bc3baab872fddd68f7a756c1aae4`: focused GraphFixtureSchema plus DeliveryGraphOutline Vitest passed 2 files and 10 tests; Playwright `delivery-graph-outline.spec.ts` in Chromium passed desktop and mobile, 2 tests total, after configured frontend build and preview startup. The verifier challenger returned `pass`, no files were changed during verification, and no unresolved Required Follow-up remains.

Delivery digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357` accepted at SHA `c39205ec7199bc3baab872fddd68f7a756c1aae4`.

Residual decisions: none. Archive rationale: the latest verifier PASS covers AC-1 through AC-3 and closes the prior packet-plan dependency failure; leaf closure is ready.
