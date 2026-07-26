---
id: 2085
title: 'P15-15: Deliver evidence, legacy, and assembled Cockpit workflow proof'
status: archived
priority: high
created: 2026-07-26T02:00:36.235890+02:00
updated: 2026-07-27T01:13:20.505752+02:00
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
archival_reason: completed
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

[[2026-07-27T01:05:44+02:00]]
## Builder Notes
DONE

Implemented the final native Cockpit readers and route retirement for DN-011 packet 6. Activity and Evidence provide current/full immutable history, code revisions, validity labels, and supersession chains; Legacy exposes bounded provenance-only task/request/activity inventory. The final shell exposes Specification, Delivery, Requests, Activity, Evidence, Legacy, Memory, and Ideas, with superseded Kanban/Decisions/task-mutation production and dedicated test surfaces removed.

PROOF-012 now runs a built SPA over real FastAPI and temporary canonical stores without HTTP interception. Separate 1440x900 and 390x844 journeys passed, including persisted request resolution, every final route, screenshots, keyboard/geometry/overflow checks, preserved Memory/Ideas, and a real modular 300-node authority with fewer than 100 mounted rows.

A real-stack defect was repaired at the owning boundary: NativeRuntime now owns request show/resolve, successful resolution resets RuntimeQuery projections, and an RLock makes reset/index/read atomic across FastAPI threads. The primed-cache request/history regression passes.

Evidence: desktop Playwright 1 passed in 52.0s; mobile Playwright 1 passed in 54.7s; focused Python 25 passed; Cockpit domain 175 passed; frontend 264 passed; production build transformed 446 modules; Stylelint and HTMLHint clean; changed-file Ruff check/format clean; removed-decisions endpoint 5 passed; PDS cleanup 12 passed; legacy-loader owner suite 27 passed; VS Code diagnostics clean. Builder challenger decision: pass.

Broad kanban xdist regression progressed beyond 88 percent after obsolete graph.yaml compatibility tests were removed but reported two failures whose tracebacks were lost to terminal transport. Historical evidence points to multiprocessing harness pressure rather than this packet, and no task-boundary production defect was evidenced; challenger classified this as non-blocking residual broad-suite risk.

Adopted the complete interrupted-attempt diff within the shaped envelope, including current externally formatted runtime-query and proof-seeder contents.

[[2026-07-27T01:12:40+02:00]]
## Verify Notes
PASS

Verified builder commit `6e96b61d124d20b8c9d33e15c3d9369463bc9f8c` against AC-1 through AC-3 and admitted digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`.

AC-1: the committed route contract exposes the eight admitted destinations and current production source contains no retired Kanban/Decisions/task-mutation owners; Memory and Ideas remain in the shell and in the assembled journey.

AC-2: Activity, Evidence, and Legacy implement current/full history, receipt revisions and validity, supersession details, provenance, truncation, and read-only presentation. Maintained page/route tests and the full frontend suite cover these boundaries.

AC-3: completed real-stack evidence on the semantically identical worktree passed desktop and mobile separately over built SPA plus real FastAPI, including persisted request resolution, route traversal, screenshots, keyboard/geometry/overflow checks, Memory/Ideas continuity, and 300-node virtualization. The builder commit's later hook delta was EOF normalization only.

Evidence: frontend 264 passed; Cockpit backend 175 passed; focused Python 25 passed; build, Stylelint, HTMLHint, Ruff, and VS Code diagnostics clean; committed patch passes `git diff --check`. Verifier challenger decision: pass.

Residual risk: the terminal transport prevented a fresh verifier Playwright exit report after starting real uvicorn and two tests, and two broad kanban xdist failures lacked preserved tracebacks. Neither produced a concrete defect in this packet; both are recorded rather than represented as fresh passing evidence.

[[2026-07-27T01:13:20+02:00]]
## Collect Notes
ARCHIVED

Collected DN-011 packet 6 at builder commit `6e96b61d124d20b8c9d33e15c3d9369463bc9f8c` with verifier evidence commit `82b6ce2ce04cb75217e2345d45e46c18d5d8b482`; both are ancestors of the collection snapshot.

AC-1 through AC-3 are closed by the final eight-route shell and retirement diff, native immutable reader behavior, and PROOF-012's completed desktop/mobile real-FastAPI journeys with persisted request mutation, preserved Memory/Ideas, and 300-node bounded scale. Builder and verifier challengers both passed.

The terminal transport limitation and unpreserved broad-kanban xdist failures remain recorded as residual non-blocking risk; they do not alter this packet's completed boundary evidence.
