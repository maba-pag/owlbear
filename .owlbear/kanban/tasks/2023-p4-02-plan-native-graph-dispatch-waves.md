---
id: 2023
title: 'P4-02: Plan native graph dispatch waves'
status: verify
priority: high
created: 2026-07-24T16:50:33.396895+02:00
updated: 2026-07-24T17:35:01.209817+02:00
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

[[2026-07-24T17:35:01+02:00]]
## Builder Notes

- Change envelope: add read-only, native graph-wave planning in `DispatchRuntime`; reuse native job eligibility gates; expose only the plan models and add focused planner proof.
- Files changed: `serve/kanban/src/owlbear_kanban/dispatch.py`, `serve/kanban/src/owlbear_kanban/native_runtime.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, `serve/kanban/tests/test_dispatch_runtime.py`, and this task record.
- Change Module Map: no deviations. `dispatch.py` owns wave compatibility; `native_runtime.py` remains the single authority for persisted start eligibility; `__init__.py` exposes public native contracts.
- Implementation: `pick_waves(candidate_revision, size)` reads current jobs in ascending ID order; emits exact shaper/builder/acceptor/auditor profiles; omits claimed, blocked, stale, predecessor-invalid, request-held, and non-pending jobs with typed reasons; isolates each shape/build writer; batches compatible accept/audit jobs to the requested size. Planning is read-only and `start` continues to revalidate current persisted state.
- Proof selected: updated focused durable dispatch-runtime test because the public planner is shared runtime behavior and a deterministic/freshness regression is difficult to spot manually.
- Commands run:
  - `uv run --project . pytest serve/kanban/tests/test_dispatch_runtime.py` -> `4 passed`.
  - `uv run --project . ruff check serve/kanban/src/owlbear_kanban/dispatch.py serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_dispatch_runtime.py` -> `All checks passed!`.
  - `git diff --check` -> clean.
- AC-to-evidence:
  - AC-1: `pick_waves` applies native eligibility over live `JobStore` records, emits typed omissions and exact profiles; focused test verifies profiles and blocked omission.
  - AC-2: `_plan_waves` makes each writer a singleton wave and reader-only waves size-bounded; focused test proves accept/build separation.
  - AC-3: focused test proves identical repeated plans, then starts job 2 and confirms the new plan omits it from fresh persisted state.
- Current failure-key resolutions: none.
- Builder-challenger: pass. It independently ran `uv run pytest -q serve/kanban/tests/test_dispatch_runtime.py -k "pick_waves_is_deterministic_and_uses_current_job_state or writer_conflict_and_release_are_atomic or readers_coexist_and_block_writer"` -> `3 passed`.
- Follow-up risks: orchestration and proof-checkout behavior remain intentionally owned by later DN-004 tasks.
