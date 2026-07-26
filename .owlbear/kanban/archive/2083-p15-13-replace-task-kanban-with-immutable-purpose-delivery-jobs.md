---
id: 2083
title: 'P15-13: Replace task Kanban with immutable-purpose Delivery jobs'
status: archived
priority: high
created: 2026-07-26T02:00:14.063453+02:00
updated: 2026-07-26T15:11:03.097180+02:00
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
archival_reason: completed
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

[[2026-07-26T15:04:22+02:00]]
Verifier rejected 173633e823b71e7fe2bafb315ff58bfac8651ec5: after ERR_RELEASE_NON_OWNER the conflict panel correctly requires Refresh authority, but the primary Release claim button remains enabled and can repeat an unsafe mixed-identity request. Return to disable release until refresh.

[[2026-07-26T15:06:41+02:00]]
Final repair disables the primary Release claim action whenever ERR_RELEASE_NON_OWNER/current authority requires refresh, preventing mixed-identity retries; only Refresh authority remains. Exact second-click regression, build and9 board tests pass; final signoff PASS.

[[2026-07-26T15:10:37+02:00]]
## Verify Notes
PASS at HEAD `a12c9ac1f5665885a49173c87068c18cf1286ba5` for projection digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`.

- Read-only boundary: `serve/cockpit/web` matched HEAD before and after verification (`git diff --quiet HEAD -- serve/cockpit/web`, exit 0). Changed files: none.
- `npm run build`: PASS; TypeScript build and Vite build completed, 441 modules transformed.
- `npm test -- src/__tests__/DeliveryJobBoard.test.tsx src/__tests__/DeliveryPage.test.tsx`: PASS; 2 files, 12 tests.
- `npm run test:e2e:all -- e2e/delivery-job-board.spec.ts --project=chromium`: PASS; 3 tests covering desktop groups/navigation, mobile groups/navigation, and retained intent/current authority on conflict.
- AC-1: focused component and Chromium desktop/mobile cases prove Plan, Build, Accept, and Audit grouping plus operational card signals.
- AC-2: focused component cases prove eligible intent-specific commands and absence of drag, arbitrary movement, generic field editing, and kind mutation.
- AC-3: successful priority, cancel, and release branches are exercised; all successful awaited operations share the unconditional `onRefresh()` continuation, while conflict enters catch and retains intent/current authority. The repaired non-owner release case disables a second unsafe release until Refresh authority.
- Verifier challenger: PASS; accepted the shared success-refresh control-flow proof and supplied executable evidence.

[[2026-07-26T15:11:03+02:00]]
## Collect Notes
ARCHIVED completed. Projection digest `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357` accepted at SHA `a12c9ac1f5665885a49173c87068c18cf1286ba5`.

Collector accepted the verifier's read-only HEAD evidence: `npm run build` passed; focused `DeliveryJobBoard` plus `DeliveryPage` passed 2 files and 12 tests; Playwright `delivery-job-board.spec.ts` on Chromium passed 3 tests. All ACs are closed, the ERR_RELEASE_NON_OWNER follow-up is resolved, verifier challenger passed, and no frontend edits or commits were made.
