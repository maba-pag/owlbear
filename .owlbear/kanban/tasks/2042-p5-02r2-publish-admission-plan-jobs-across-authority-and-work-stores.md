---
id: 2042
title: 'P5-02R2: Publish admission plan jobs across authority and work stores'
status: build
priority: high
created: 2026-07-25T12:56:17.755663+02:00
updated: 2026-07-25T12:56:17.755663+02:00
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
archival_reason:
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