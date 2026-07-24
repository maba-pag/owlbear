---
id: 2023
title: 'P4-02: Plan native graph dispatch waves'
status: build
priority: high
created: 2026-07-24T16:50:33.396895+02:00
updated: 2026-07-24T16:50:33.396895+02:00
tags:
  - phase-4
  - scope:core
  - runtime
  - dispatch
  - waves
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-004
  - packet:DN-004-PK-002
parent: 1980
depends_on:
  - 2022
ac:
  - 'AC-1: Given mixed native jobs and a candidate revision, `DispatchRuntime.pick_waves`
    returns job-ID-stable waves containing only pending, unclaimed, unblocked, request-free
    jobs with current authority and predecessor receipts; each entry names `shaper
    | builder | acceptor | auditor` from job kind.'
  - 'AC-2: A returned wave contains at most one `shape | build` job and does not combine
    that writer with `accept | audit`; read-only jobs may share a wave within the
    requested size when no dependency edge joins them.'
  - 'AC-3: Repeating `pick_waves` without persisted mutation returns the same plan.
    After claim, finish, invalidation, or recovery, a fresh call reflects current
    storage; a prior plan does not authorize `DispatchRuntime.start`.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; `DN-004-PK-002`. Resolve normative behavior from `DN-004`, `IF-004`, and `PROOF-014`; this record is not specification authority.

## Outcome
Deepen `owlbear_kanban.dispatch.DispatchRuntime` with deterministic native job planning, exact agent-profile assignment, compatibility-safe waves, typed omission reasons, and fresh-state replanning.

## Envelope
In: `dispatch.py`, public exports, focused native dispatch tests. Out: claiming/finalization implementation owned by #2022, proof checkout, orchestration, MCP, Cockpit, and legacy removal.

Proof guidance: public planner over real job, receipt, request, and attempt state; prove eligibility, compatibility, deterministic repeat, and persisted-state freshness.