---
id: 2003
title: 'P3-04: Record claims and immutable attempts'
status: build
priority: high
created: 2026-07-22T21:58:44.211108+02:00
updated: 2026-07-23T12:46:47.171856+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - claims
  - attempts
  - lifecycle
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004
parent: 1979
depends_on:
  - 2002
ac:
  - 'AC-1: Given schema-version-1 attempt-event mappings, public parsers return frozen
    records preserving the fields defined in Scope. Unknown fields, malformed references,
    non-positive sequences, unsupported event kinds, and missing required references
    return stable diagnostics; supported event kinds are `started`, `released`, `failed`,
    `crashed`, and `succeeded`.'
  - 'AC-2: Given public attempt create, read, and list calls against an explicit work
    root, byte-equivalent replay returns the existing record; a differing occupied
    identity raises `AttemptConflictError` with `code == "ERR_ATTEMPT_CONFLICT"`.
    Traversal or symlink substitution returns a stable path diagnostic, listing sorts
    by attempt ID then sequence, and failed writes leave no temporary or partial record.'
  - 'AC-3: Given an open current job with prerequisite receipts whose computed validity
    is current and no pending request, `start_job` atomically records one claim and
    one `started` event. A second active claimant, stale authority, unmet prerequisite,
    terminal disposition, or pending request returns a stable reason with no additional
    event.'
  - 'AC-4: Given the owning attempt, release or failed finalization appends the corresponding
    `released` or `failed` event and clears only that claim. Given an expired claim
    at a supplied clock, recovery appends one `crashed` event and releases only that
    job. Replay is idempotent, graph and receipts remain unchanged, and a later start
    creates a new attempt while prior events remain inspectable in order.'
proof_bundle: behavioral+challenge
blocked: true
block_reason: 'PIPELINE_COST_PAUSE: task predates Scenario Closure gating and combines
  contract parsing, persistence, claim concurrency, and crash recovery. Recovery owner:
  shaper. Resume only after a connected scenario-matrix audit either proves one bounded
  high-risk matrix or splits the task, then clear this block.'
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-004`

## Outcome
Per-job claims and immutable attempt history form one orthogonal runtime boundary: start, release, fail, and crash lifecycle operations append attempt events, and an open job can be retried without changing its purpose. Later successful completion uses the same attempt contract.

## Scope
In scope: public frozen `AttemptEvent` models, parsers, serializers, and stable diagnostics. An attempt event preserves attempt, job, change, digest, and target references; actor and process identity; a positive monotonic sequence; event kind and timestamp; and optional detail and evidence references. Supported event kinds are `started`, `released`, `failed`, `crashed`, and `succeeded`. This task emits the first four; task 2004 later records successful completion through the same contract.

Also in scope: public attempt create, read, and list operations against an explicit work root; byte-equivalent replay; conflict, path-containment, no-overwrite, failed-write cleanup, and deterministic attempt-ID then sequence ordering; public start, release, failed-finalization, and expired-claim recovery operations; process and agent identity; claim timestamps; and current-authority, prerequisite, pending-request, and terminal-disposition guards.

Out of scope: successful purpose-specific completion and receipt creation, owned by task 2004; findings, finding storage, and receipt listing, owned by task 2008; wave selection, global writer compatibility or lease, invalidation, corrective jobs, agent dispatch, MCP, and Cockpit.

## Current Foundation And Ownership
Use the native transaction coordinator and stores delivered through task 2002 behind the transport-free runtime facade. Keep attempt contracts, storage, and lifecycle semantics in one cohesive owner that uses native job references and contained storage primitives. Do not reuse legacy `start_work` or `end_work` status-moving semantics.

Public attempt creation returns the existing record on byte-equivalent replay. A differing record at an occupied attempt-event identity raises exported `AttemptConflictError` with `code == "ERR_ATTEMPT_CONFLICT"`.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, `PROOF-003`, design sections 2.2, 2.3, 7.2, 13, and 14, and accepted decisions `DEC-007` and `DEC-009` under `.owlbear/changes/replace-delivery-pipeline/`. Global dispatch and writer policy remain DN-004.

Proof guidance: exercise public attempt parser and store APIs plus lifecycle operations over an explicit temporary work root with replaceable clock and process identity. Cover parser round trips, conflict, containment, no-overwrite, deterministic order, concurrent claim, release, failure, crash, expiry, retry, and idempotent recovery.

[[2026-07-23T03:13:22+02:00]]
## Shape Notes
- Source and repair mode: user-approved connected material boundary repair for tasks 2001, 2003, and 2008, prompted by task 2008's builder rejection. This task received a local operative-contract replacement inside that approved boundary.
- Rejection resolution: the builder's claim that admitted authority was absent was false. `.owlbear/changes/replace-delivery-pipeline/` contains the admitted intent, design, decisions, graph, and admission receipt. Design sections 2.2, 2.3, and 7.2 place attempts with operational claim/lifecycle history rather than durable finding/receipt evidence.
- User decision: all attempt contracts and attempt storage move from task 2008 to this lifecycle owner. Supported event kinds are `started`, `released`, `failed`, `crashed`, and `succeeded`; this task emits the first four and task 2004 retains successful completion semantics.
- Planning artifacts: none revised. The task projection now matches existing admitted authority.
- Interrupted-layer adoption: adopted the current unstaged claim layer from the interrupted invocation; no conflicting hunk or staged task record existed.

### Readiness And Authorities
- Authorities: `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, `PROOF-003`, design sections 2.2, 2.3, 7.2, 13, and 14, and accepted `DEC-007` and `DEC-009`.
- Readiness: task 2003 remains build-ready after task 2002; task 2004 remains its downstream successful-completion consumer.

### Change Module Map
| Owner | Responsibility | Interface impact |
|---|---|---|
| Task 2003 lifecycle/attempt owner | `AttemptEvent`, contained attempt storage, claim/start/release/fail/crash semantics | New public attempt parser/store and lifecycle facade |
| `jobs.py` | Native job references and records | Consumed, not reassigned |
| `storage_io.py` | Contained durable-write precedent | Reused internally |
| Task 2004 | Purpose-specific successful completion | Uses `succeeded`; unchanged dependency |

### Product Invariant Map
| Invariant | Boundary |
|---|---|
| Attempts remain append-only operational history | Public attempt store and lifecycle operations |
| Failed, crashed, or released attempts do not mutate graph or receipts | Lifecycle transaction proof |
| Retry preserves prior attempts and job purpose | Start after terminal attempt outcome |
| Findings and receipt listing remain outside this task | Task 2008 contract |

### Product Promise Coverage Map
| Promise | Coverage |
|---|---|
| Immutable attempt history and honest runtime dispositions | This task under `REQ-008` and `REQ-009` |
| Crash-safe contained publication | Task 2002 foundation under `REQ-016` |
| Successful receipt-producing completion | Task 2004, unchanged |

### Task And Dependency Changes
- Replaced stale Outcome, Scope, ownership, Authority, proof guidance, and AC with the complete attempt model/store plus lifecycle contract.
- Kept status `build`, parent 1979, dependency 2002, proof bundle, task count, and all unrelated edges unchanged.

### Challenge And Board Audit
- `shaper-challenger` decision: pass; authority, readiness, invariant ownership, boundary proof, fidelity, literals, and adjacent 2004 ownership all met.
- Release audit: task 2003 is `build`, parent 1979, depends on active task 2002, and is dependency-blocked as intended; task 2004 still depends on 2003.

[[2026-07-23T10:51:30+02:00]]
## Builder Notes
- Change envelope: task 2003 requires the native transaction coordinator and stores delivered by task 2002; expected attempt/lifecycle owner cannot be implemented before that foundation exists.
- Files changed: none.
- Change Module Map deviations: none; the mapped task 2003 owner depends on task 2002's delivered foundation.
- Proof selected: task dependency/readiness check before any code edit.
- Commands run: none; no product change was permitted.
- Builder-challenger result: initial pre-implementation challenge correctly returned `fail` because no implementation or evidence existed; it is not a completion claim.
- Follow-up risks: task 2003 was dispatched while dependency 2002 remains unresolved (`dep_status: blocked`). Re-dispatch only after task 2002 reaches a non-blocking completion state.

[[2026-07-23T11:28:27+02:00]]
## Shape Notes
- Repair classification: mechanical reroute inside the user-authorized connected repair. The builder changed no files and returned this task only because it was dispatched while dependency #2002 was unresolved.
- Contract audit: the existing operative body already owns the native append-only attempt/activity stream and atomically couples job claim changes with `started`, `released`, `failed`, and `crashed` events. Task #2004 remains the owner of the `succeeded` event during successful completion.
- Dependency closure: #2003 consumes archived #2001 stores through the transaction kernel now owned by build task #2002. It requires no request, completion, invalidation, or health producer.
- Route: restored to `build` with parent #1979 and dependency #2002 unchanged. It remains dependency-blocked and must not be dispatched until #2002 reaches non-blocking completion.

[[2026-07-23T12:20:29+02:00]]
## Builder Notes
- Change envelope: no product change; task 2003 requires the transaction coordinator owned by dependency 2002.
- Files changed: no product files.
- Change Module Map deviations: none; implementation was not started because the shaped route states this task must not be dispatched until dependency 2002 completes.
- Proof selected: board dependency projection and shaped dependency-closure note.
- Commands run: none; implementation is intentionally deferred.
- Builder-challenger result: not invoked because no DONE verdict is being proposed.
- Follow-up risk: task 2002 is currently in `shape`, so 2003 must be redispatched only after 2002 reaches a non-blocking completed status.
