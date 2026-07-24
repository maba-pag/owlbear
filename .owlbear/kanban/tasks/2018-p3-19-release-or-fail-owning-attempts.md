---
id: 2018
title: 'P3-19: Release or fail owning attempts'
status: build
priority: high
created: 2026-07-23T14:41:48.715516+02:00
updated: 2026-07-24T03:23:54.484606+02:00
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
  - packet:DN-003-PK-004-I
parent: 2003
depends_on:
  - 2017
ac:
  - 'AC-1: Given the owning active attempt, release atomically appends one `released`
    event, clears only the matching claim pointers, leaves the job open, and leaves
    graph and receipts unchanged.'
  - 'AC-2: Given the owning active attempt, failed finalization atomically appends
    one `failed` event with supplied detail and evidence references, clears only the
    matching claim pointers, and preserves prior attempt history.'
  - 'AC-3: Given a non-owner, no active claim, or replay of an already committed outcome,
    the operation returns the stable rejection or existing outcome and creates no
    duplicate event or job mutation.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The native runtime lets only the owning attempt release or fail its active claim while preserving immutable history and job purpose.

## Scope
In scope: owner identity; released and failed events; supplied failure detail and evidence references; atomic matching-claim clear; open-job preservation; idempotent replay; non-owner and no-active-claim diagnostics; graph and receipt immutability.

Out of scope: start eligibility, expiry recovery, successful completion, receipt creation, corrective routing, dispatch, MCP, and Cockpit.

## Current Foundation And Ownership
Deepen the native runtime facade from task #2017. Reuse its claim identity and mixed transaction boundary. This task owns release and failed-finalization semantics only.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, design sections 2.2, 2.3, 7.2, 8.6, 13, and 14, and accepted `DEC-007` and `DEC-009`.

## Proof Guidance
Exercise public release and fail operations over owner, non-owner, no-active-claim, and replay states. Do not repeat start guards or transaction failure injection.

[[2026-07-24T03:20:42+02:00]]
## Builder Notes
- Change envelope: deepen `NativeRuntime` only with owner-bound release and failed-finalization operations. Preserve job openness, immutable attempt history, graph, and receipt ownership; no dispatch, MCP, Cockpit, or start-eligibility changes.
- Files changed: `serve/kanban/src/owlbear_kanban/native_runtime.py`; `serve/kanban/src/owlbear_kanban/__init__.py`; `serve/kanban/tests/test_native_runtime.py`.
- Change Module Map deviations: none. Source confirmed task #2017's facade, `AttemptStore`, `JobStore`, and `RuntimeTransaction` are the mapped owners.
- Implementation: added public `release_job` and `fail_job` request/result/diagnostic contracts. Both validate claim and starter identity, append immutable sequence-2 outcome events, clear only matching pointers in one runtime transaction, preserve pending disposition, and return matching committed outcomes on replay.
- Proof selected: one durable public-facade regression test. It earns its maintenance cost because owner isolation, atomic release/failure, immutable history, and replay are shared lifecycle invariants that are hard to verify manually and easy to regress.
- Commands run: `uv run pytest serve/kanban/tests/test_native_runtime.py` passed 10 tests. `uv run ruff check serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_native_runtime.py` and `uv run ruff format --check` for those same files passed.
- AC evidence: AC-1 is exercised by release event, pointer clear, pending disposition, and replay assertions. AC-2 is exercised by failed event detail/evidence assertions, pointer clear, and preserved sequence-1 started event assertions. AC-3 is exercised by matching replay, active non-owner, and post-finalization no-active diagnostics with no mutation branch.
- Current failure-key resolutions: none returned from verify.
- Builder challenger: pass; no concrete blockers.
- Follow-up risks: none identified.

[[2026-07-24T03:23:54+02:00]]
## Verify Notes
- Evidence reviewed: Builder Notes; committed task change `44206943a`; public `NativeRuntime` release/fail contracts; `AttemptStore` immutable event model; `RuntimeTransaction` participant boundary.
- Named authorities checked: `.owlbear/changes/replace-delivery-pipeline/design.md` sections 7.2, 8.6, 13, and 14; `graph.yaml` `REQ-008`, `REQ-009`, `REQ-016`, and `IF-003`; accepted `DEC-007` and `DEC-009`.
- Change Module Map: changed modules remain within `DN-003` runtime ownership. No map deviation.
- Normal-path boundary exercised: `uv run pytest serve/kanban/tests/test_native_runtime.py` passed 10 tests; this calls public `NativeRuntime.start_job`, `release_job`, and `fail_job` against real job/attempt stores. Replacements are limited to the lower-level repository-history stub needed for start eligibility.
- Checks run: `uv run ruff check serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_native_runtime.py` passed. `uv run ruff format --check` on the same files passed. `git diff --check 44206943a^ 44206943a` for the task files passed.
- Finding: verifier-challenger found that `_finalize` replay accepted a sequence-2 event without confirming `completed.job_id == request.job_id`. A later request for another job could receive that event and bypass ownership validation.
- Patch applied: `serve/kanban/src/owlbear_kanban/native_runtime.py` now requires the replay event's `job_id` to match the request before returning it. The focused suite and static checks passed after the repair.
- AC-to-evidence: AC-1 release behavior, AC-2 failed-event detail/evidence and preserved started event, and AC-3 ordinary owner replay/non-owner/no-active cases pass in the public-facade suite. The discovered cross-job replay branch is not covered by the durable test.
- Prior same-failure-key rejection check: none; this is the first verify rejection for `cross-job-finalization-replay`.
- Verifier-challenger: fail. It identified the cross-job replay ownership gap; source repair is applied, but requested regression proof remains absent.
- Final route: reject to build because verifier patch-pass cannot add a durable test.

### Required Follow-up
- Add a public `NativeRuntime` regression test with two materialized jobs: finalize an attempt for one job, then call the same finalization request identity with the other job ID. Assert it does not return the other job's completed event, returns the stable ownership/no-active diagnostic expected by the contract, and does not mutate either job or append a duplicate event.
- Rerun `uv run pytest serve/kanban/tests/test_native_runtime.py` and the existing Ruff checks.
