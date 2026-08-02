---
id: 2080
title: 'P15-10: Build the typed native Cockpit data boundary'
status: archived
priority: high
created: 2026-07-26T01:59:53.046397+02:00
updated: 2026-07-26T12:06:56.267215+02:00
tags:
  - phase-15
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-011
  - packet:DN-011-PK-001
  - scope:cockpit-frontend
  - api
  - hooks
  - type:build
  - rigor:thorough
  - interface:IF-012
parent: 1988
depends_on:
  - 2079
ac:
  - 'AC-1: Given native success and `404 | 409 | 422 | 503` responses, exported clients
    return typed payloads or an error carrying status, code, message/detail, current
    delivery digest, target, token, and current snapshot when supplied by IF-011.'
  - 'AC-2: Given `{items, next_cursor}` pages, load-more appends unseen identities;
    `ERR_CURSOR_STALE` retains displayed data, resets the cursor, and exposes first-page
    Retry while job requests pass explicit candidate revision `HEAD`.'
  - 'AC-3: Given `native-changed` resource classes and monotonic token, subscribers
    refresh affected data; SSE disconnect resumes polling, and a failed refresh retains
    prior payload plus an actionable Retry state.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; `DN-011` packet 1 for `IF-012`.

## Outcome
The SPA consumes IF-011 through typed clients and retained-data hooks for native resources, errors, pagination, and invalidation.

## Envelope
In: native API types/client, nested FastAPI errors, cursor paging, explicit `candidate_revision=HEAD`, `native-changed` resources/token, polling fallback.

Out: page rendering, board, request UI, browser journey.

Proof guidance: use Vitest at exported client/hook boundaries with real response shapes grounded in OpenAPI; replace transport below the client only.

[[2026-07-26T11:14:22+02:00]]
Builder implementation at digest bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357 and base SHA 7be7839380014695ba8410da94e843350fb15523. Added route-specific typed IF-011 client; NativeApiError preserving nested/flat status/code/message/detail/digest/target/token/current/validation; explicit HEAD job paging; strict admin calls; retained page/value hooks with dedupe, stale cursor first-page Retry, failed-refresh retention, loader generation guards and queued in-flight invalidations; native SSE provider with monotonic tokens/reconnect and polling fallback; production provider mounting while legacy Memory/Ideas remain untouched. Challenger false-shape/race findings were repaired. Validation: 31 focused tests; full frontend 1632 passed/2 skipped; production build passed; final rechallenge PASS.

[[2026-07-26T11:21:54+02:00]]
Verifier rejected 7e12ff32e869248528c78542eac75dd89dde8f25: server nanosecond tokens exceed JS safe integers so native events are ignored while polling is paused; loader ownership changes wait indefinitely for an unresolved prior request; exported job/request unions omit supersession and nullable target_node_id. Return to build for protocol/type/race repair.

[[2026-07-26T11:41:37+02:00]]
Builder repair after verifier rejection of 7e12ff32: corrected flat job/nested request/detail shapes and route-specific endpoints; preserved nested current.token, message/detail and 422 entries; queued in-flight invalidations; generation-guarded ownership/data/error/loading with permanently pending and adverse completion order proofs; mounted provider; mapped only real SSE resources with activity polling; changed native SSE token protocol to exact decimal strings and BigInt monotonic comparison; aligned supersession and nullable request targets. Validation: backend 177, frontend 1635 pass/2 skip, production build; final build + 23 focused tests; final challenger PASS.

[[2026-07-26T12:03:40+02:00]]
Verifier found preexisting provider tokens could duplicate initial page/value requests; returned for token-baseline repair.

[[2026-07-26T12:03:46+02:00]]
Final repair baselines preexisting native tokens in both paged and retained-value hooks, preventing duplicate mount refreshes and retained-payload loss. Exact regressions cover page/value late mount, pending owner replacement, stale completion loading state, exact decimal tokens and backend union alignment. Validation: production build; 25 focused tests; prior full frontend 1635/backend177; final mandatory-AC signoff PASS.

[[2026-07-26T12:06:51+02:00]]
Verifier acceptance at committed HEAD c880659d632e309e3779f65ef590f0c3eb04127e. Production build and 25 focused tests pass; scoped frontend tree clean. Full supplied evidence frontend 1635/backend177 and final mandatory-AC signoff PASS.

[[2026-07-26T12:06:56+02:00]]
Collector confirms digest bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357 and accepted data-boundary SHA c880659d632e309e3779f65ef590f0c3eb04127e. Typed IF-011, exact token protocol, retained paging/races, SSE/poll fallback and provider wiring evidence recorded; Memory/Ideas untouched.
