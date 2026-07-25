---
id: 2042
title: 'P5-02R2: Publish admission plan jobs across authority and work stores'
status: archived
priority: high
created: 2026-07-25T12:56:17.755663+02:00
updated: 2026-07-25T13:33:59.122658+02:00
tags:
  - phase-5
  - scope:kanban
  - admission
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
  - 2041
ac:
  - 'AC-1: Given admitted evidence and a work root, AdmissionTransaction returns receipt,
    generation, and assessment while one transaction persists matching authority receipt/generation,
    sequence, and one numeric plan JobRecord per graph node.'
  - 'AC-2: Given non-admitted evidence, neither root changes; given an exact replay,
    the same receipt, generation, and jobs return without advancing the sequence.'
  - 'AC-3: Changed evidence, an explicit job-ID collision, or an unrecoverable stale
    reservation returns AdmissionConflictError with unchanged authority/work snapshots;
    auto-allocation retries one stale reservation using a fresh monotonic block.'
  - 'AC-4: Failure before publication, after the first publication, or before manifest
    cleanup followed by retry/recovery yields the complete receipt/generation/job
    set or no set, cleans the work-root manifest, and permits only authority and work
    roots.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; repair prerequisite for `DN-009-PK-006`. Resolve behavior from design section 6, IF-002, REQ-016, and the native job reservation boundary.

## Outcome
Extend `AdmissionTransaction` to accept the native work root, reserve initial job IDs when omitted, and atomically publish the authority receipt and generation, the sequence participant, and one numeric plan job per delivery node.

## Envelope
In: cross-root transaction assembly, exact replay, allocation-conflict retry, explicit-ID collision handling, and recovery across authority/work roots.

Out: MCP transport/error mapping, dispatch semantics, later build/accept/audit job allocation, and authority editing.

Proof guidance: exercise the core admission transaction across copied authority and a temporary work root; then run the downstream public PROOF-011 admission-to-job segment.

[[2026-07-25T13:31:56+02:00]]
Builder complete. AdmissionTransaction now accepts the work root, returns before mutation for non-admitted evidence, recovers only authority/work roots, checks exact receipt/generation/full-job replay before allocation, reserves omitted IDs via #2041, publishes receipt/generation/sequence/numeric jobs in one work-root transaction, retries one stale automatic reservation, and rejects explicit active/archive collisions. Proof: 10 focused admission scenarios passed; admission+allocator+transaction suites 54 passed; mapped kanban regression excluding the independently broken legacy-authority fixture file 1111 passed; focused lint and editor diagnostics clean. Public PROOF-011 now fails only at the planned #2040 server constructor wiring that has not yet passed app_ctx.kanban_dir. builder-challenger decision: pass; advance to verify and leave MCP assembly to #2040.

[[2026-07-25T13:33:23+02:00]]
Independent verification PASS at builder SHA 7b1d0bbb9d6e96ea1b52203f3a151a7b8ee1517f. Commit inspection confirmed exactly the task source, durable test, and task record. AC-1 through AC-4 verified: exact cross-root publication and full JobRecord equality; no-op and replay-before-allocation; changed-evidence/active/archive/stale conflicts with snapshot preservation and one retry; all three interruption stages with only authority/work roots and clean manifest recovery. Admission+allocator+transaction suites 54 passed (2 existing fork warnings); focused lint and diagnostics clean. verifier-challenger decision: pass. The server constructor handoff remains explicitly owned by #2040.

[[2026-07-25T13:33:59+02:00]]
Collection complete. Builder SHA 7b1d0bbb9d6e96ea1b52203f3a151a7b8ee1517f is an ancestor of current HEAD c1117cbbeb4928a42a99d0faf1e153b20c7e9a81; task-owned source/test paths are unchanged since the verified builder commit. Durable admission proof rerun: 10 passed. AC-1 through AC-4 remain satisfied; #2040 may now assemble the work-root-aware public boundary.
