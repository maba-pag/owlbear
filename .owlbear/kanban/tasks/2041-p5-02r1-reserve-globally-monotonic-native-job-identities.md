---
id: 2041
title: 'P5-02R1: Reserve globally monotonic native job identities'
status: collect
priority: high
created: 2026-07-25T12:56:10.644283+02:00
updated: 2026-07-25T13:22:19.333537+02:00
tags:
  - phase-5
  - scope:kanban
  - admission
  - job-identity
  - transaction
  - repair
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-009
  - interface:IF-010
parent: 1981
depends_on:
  - 2028
ac:
  - 'AC-1: Given an empty work store and count N, the JobStore reservation boundary
    returns IDs 1 through N plus a sequence participant; committing it persists N,
    and the next reservation starts at N+1.'
  - 'AC-2: Given active jobs, archived jobs, or a higher valid persisted sequence,
    reservation starts at the highest observed identity plus one, returns positive
    contiguous IDs, and never reuses an archived identity.'
  - "AC-3: Given two reservations from the same state, committing one makes the other's
    transaction fail with a typed conflict; a fresh reservation starts above the committed
    range and no duplicate identity is issued."
  - 'AC-4: Given a malformed or non-positive sequence document or an unsafe work-store
    path, reservation returns a stable typed error and leaves sequence, active-job,
    and archive bytes unchanged.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; repair prerequisite for `DN-009-PK-006`. Resolve behavior from design section 4's globally monotonic job identity, `JobStore`, and `RuntimeTransaction`.

## Outcome
Add a `JobStore`-owned reservation-participant API for contiguous globally monotonic IDs in the shared flat work store. It returns IDs plus an immutable-create or OCC replacement sequence participant; it does not commit or create jobs.

## Envelope
In: native sequence parsing, active/archive maxima, reservation participant construction, typed fail-closed errors, and focused concurrency proof.

Out: admission publication, MCP behavior, dispatch/completion job creation, and compatibility with legacy task `next_id`.

Proof guidance: exercise `JobStore` plus `RuntimeTransaction` over a temporary work root, including a stale competing participant negative control.

[[2026-07-25T13:20:44+02:00]]
Builder complete. Added JobStore.reserve_job_ids(count), strict native job-sequence parsing, immutable-create/OCC replacement participants, unique reservation bytes for stale same-state conflict detection, typed reservation/sequence/path errors, and package exports. Proof: focused JobStore suite 27 passed; focused lint passed; editor diagnostics clean; mapped kanban regression excluding independently broken legacy-authority fixture file 1104 passed. Unfiltered mapped run had 1102 passes and 8 unrelated failures in test_historical_admission_fixtures.py because legacy graph.yaml authority is no longer permitted. builder-challenger decision: pass, no blocker; recommendation: advance to verify and commit only owned paths.

[[2026-07-25T13:22:19+02:00]]
Independent verification PASS at builder SHA 2f00e7b67542c6d2d25cfc4b2c09aa06fbd39072. Inspected exact committed diff and ownership. AC proof: empty/create and existing/replacement same-state reservations conflict after one commits; fresh reservations advance; active/archive/sequence maxima prevent reuse; malformed YAML, non-positive sequence, and unsafe symlink root return stable typed errors without byte mutation. Verification commands: allocator + RuntimeTransaction suites 44 passed (2 existing fork deprecation warnings); focused lint passed; editor diagnostics clean. verifier-challenger decision: pass, no problem; recommendation: advance to collect.
