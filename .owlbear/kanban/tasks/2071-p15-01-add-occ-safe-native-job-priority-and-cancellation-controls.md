---
id: 2071
title: 'P15-01: Add OCC-safe native job priority and cancellation controls'
status: verify
priority: high
created: 2026-07-26T01:58:18.179812+02:00
updated: 2026-07-26T02:29:12.632898+02:00
tags:
  - phase-15
  - corrective-projection
  - change:replace-delivery-pipeline
  - digest:bf5edd67478d
  - node:DN-003
  - scope:core
  - jobs
  - occ
  - type:build
  - rigor:thorough
  - requirement:REQ-026
  - interface:IF-003
parent: 1968
depends_on:
  - 1979
ac:
  - 'AC-1: Given a pending unclaimed job plus matching change, delivery digest, and
    OCC token, the public priority operation atomically persists the requested integer
    priority and timestamp, returns the refreshed `StoredJob` token, and a matching
    desired-state replay returns that persisted result.'
  - 'AC-2: Given a pending unclaimed job plus matching identity, the public cancel
    operation atomically persists disposition `cancelled`; a matching replay is stable,
    while stale digest/token, an active claim, or an incompatible terminal disposition
    returns a typed diagnostic containing current job authority and leaves job, attempt,
    and coordination bytes unchanged.'
  - 'AC-3: Given competing processes or an injected transaction failure, one matching
    administrative operation publishes while stale competitors fail through OCC, interrupted
    state remains recoverable, and native list/detail projections expose the current
    token required by adapters.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `bf5edd67478d5304943e695bbb6d53186f2520773c0964f448b658613ee96357`; corrective `DN-003` implementation for `REQ-026`, `DEC-034`, and `IF-003`.

## Outcome
The native runtime exposes intent-specific priority and cancellation operations without restoring generic task or job editing.

## Envelope
In: strict requests/results/diagnostics, delivery-digest and JobStore OCC identity, pending-unclaimed eligibility, replay, concurrency, transaction recovery, job projection token.

Out: HTTP/MCP adapters, Cockpit rendering, candidate-digest re-acceptance of descendant nodes.

Proof guidance: exercise public runtime operations and real stores/transactions across success, replay, stale identity, active claim, terminal state, concurrent writers, and injected transaction failure.

[[2026-07-26T02:29:12+02:00]]
## Builder Notes
DONE: Added strict transport-free OCC job priority and cancellation controls for candidate digest `bf5edd...`.

Changed:
- `native_runtime.py`: frozen request/result/diagnostic contracts; complete change/digest/token identity; pending-unclaimed eligibility; exact desired-state replay; atomic one-participant replacement; current-authority diagnostics for stale/claimed/terminal/not-found; transaction recovery.
- `runtime_query.py`: current OCC token in job projections and refreshed token index.
- package exports and durable runtime proof.

Evidence:
- Focused public runtime matrix: 3 passed, including two-process one-winner OCC race and interrupted-publication recovery.
- Complete native runtime/query: 58 passed.
- Complete Kanban package: 1035 passed; only eight unrelated known legacy `graph.yaml` fixture failures.
- Cockpit backend consumers: 169 passed.
- lint-all and editor diagnostics: passed/clean.
- Builder challenger: pass; independently reran 3 focused, 58 runtime/query, 20 native Cockpit, and lint checks.

Builder memories assessed before closure.
