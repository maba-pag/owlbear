---
id: 2023
title: 'P4-02: Plan native graph dispatch waves'
status: archived
priority: high
created: 2026-07-24T16:50:33.396895+02:00
updated: 2026-07-24T17:47:17.848484+02:00
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
archival_reason: completed
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

[[2026-07-24T17:38:27+02:00]]
## Verify Notes

- Evidence reviewed: builder commit `e071d5443`; task ACs; `DN-004`, `IF-004`, and `PROOF-014` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; the shaped module map; committed planner/export/test diff.
- Named authorities checked: `IF-004` requires dependency-aware waves; `PROOF-014` keeps the eventual normal-path boundary at the public engine-selected wave/orchestrator flow. This packet correctly owns only the native planner beneath that later proof boundary.
- Change Module Map: no ownership deviation. The change remains in `dispatch.py`, with native eligibility retained in `native_runtime.py` and public plan contracts exported from `__init__.py`.
- Normal-path boundary exercised: `uv run --project . pytest serve/kanban/tests/test_dispatch_runtime.py` -> `4 passed`. The test drives the public `DispatchRuntime.pick_waves` and `start` paths over persisted `JobStore` state; it does not substitute the planner or eligibility owner.
- Checks run: focused pytest above passed. Builder-recorded Ruff and diff checks were reviewed. No resolved requests. Recalled memories were assessed.
- Finding (failure key `dependency-edge-wave-compatibility`): `DispatchRuntime._plan_waves` batches all adjacent `accept`/`audit` entries solely by size. `DispatchWaveEntry` omits `predecessor_job_ids`, so the planner cannot prevent a shared reader wave when a dependency edge joins two otherwise eligible reader jobs. This violates AC-2 and `IF-004` dependency-aware waves. The focused proof does not create a reader-to-reader dependency edge, so it cannot detect this.
- Patch assessment: repair requires carrying dependency information through the public planner model and adding durable dependent-reader wave proof. That exceeds the verifier's one-owner/local-patch budget; no patch applied.
- AC-to-evidence: AC-1 and AC-3 have passing focused evidence. AC-2 is unsatisfied by the dependency-edge finding above.
- Prior same-failure-key rejection check: none in current Verify Notes.

### Required Follow-up
- Update `DispatchRuntime.pick_waves` / `_plan_waves` so a read-only wave never combines jobs linked by a predecessor dependency edge (in either direction, including non-adjacent IDs), while retaining deterministic job-ID order and size-bounded compatible reader waves.
- Add focused persisted-`JobStore` proof containing at least two eligible `accept`/`audit` jobs connected by a predecessor edge and assert they are planned in separate waves. Rerun `uv run --project . pytest serve/kanban/tests/test_dispatch_runtime.py` and the path-scoped Ruff check.

- Final route: reject to build; implementation gap.

[[2026-07-24T17:43:08+02:00]]
## Builder Notes

- Change envelope: resolve returned failure key `dependency-edge-wave-compatibility` in native dispatch planning only. Expected files: `dispatch.py` and its focused runtime test; no ownership or module-map deviation.
- Files changed: `serve/kanban/src/owlbear_kanban/dispatch.py`; `serve/kanban/tests/test_dispatch_runtime.py`; task record.
- Change Module Map: no deviations. `dispatch.py` remains the planner owner and reads predecessor IDs from live `JobStore` state; `native_runtime.py` remains the eligibility authority.
- Implementation: `DispatchWaveEntry` now preserves persisted `predecessor_job_ids`. `_plan_waves` flushes a reader batch before an `accept` or `audit` entry when either direction contains a direct predecessor edge, so dependent readers never share a wave while unrelated readers remain size-bounded and ID-stable.
- Proof selected: added one durable public-planner regression because dependency-aware scheduling is shared runtime behavior and a non-adjacent reader edge is difficult to detect manually. It passes the Rent Test as a previously observed verifier finding.
- Commands run:
  - `uv run --project . pytest serve/kanban/tests/test_dispatch_runtime.py` -> `5 passed`.
  - `uv run --project . ruff check serve/kanban/src/owlbear_kanban/dispatch.py serve/kanban/tests/test_dispatch_runtime.py` -> `All checks passed!`.
  - `uv run --project . ruff format --check serve/kanban/src/owlbear_kanban/dispatch.py serve/kanban/tests/test_dispatch_runtime.py` -> `2 files already formatted`.
  - `git diff --check -- serve/kanban/src/owlbear_kanban/dispatch.py serve/kanban/tests/test_dispatch_runtime.py` -> clean.
- AC-to-evidence:
  - AC-1: focused public `pick_waves` tests exercise persisted `JobStore` records and native eligibility; profiles and omissions remain covered by `test_pick_waves_is_deterministic_and_uses_current_job_state`.
  - AC-2: `test_pick_waves_separates_dependent_readers` creates persisted `accept` job 1, independent `audit` job 2, and `audit` job 3 with `predecessor_job_ids=(1,)`; after persisting a current receipt for job 1, public `pick_waves(size=3)` returns `[[1, 2], [3]]`, proving the non-adjacent dependency edge splits reader waves while independent readers batch.
  - AC-3: `test_pick_waves_is_deterministic_and_uses_current_job_state` still proves repeated plan equality and persisted-state freshness after a start claim.
- Current failure-key resolutions: `dependency-edge-wave-compatibility` resolved by propagating predecessor IDs into entries and checking direct edges in both directions before reader batching.
- Builder-challenger: pass. Independently ran the focused pytest, Ruff, and format checks; confirmed the minimal scope and bidirectional/non-adjacent reader-edge handling.
- Follow-up risks: only direct predecessor edges are required and represented by native job state; orchestration and proof-checkout remain intentionally outside this packet.

[[2026-07-24T17:46:03+02:00]]
## Verify Notes

- Evidence reviewed: builder commits `e071d5443` and `25b515a5d`; task ACs; `DN-004`, `IF-004`, and `PROOF-014` in `.owlbear/changes/replace-delivery-pipeline/graph.yaml`; builder and prior verifier notes; committed planner/test diff.
- Named authorities checked: `IF-004` requires dependency-aware waves, global writer serialization, and exact profiles. `DN-004` owns graph-aware dispatch with current-state replanning. `PROOF-014` reserves the full orchestrator flow for its later normal-path proof; this packet validly proves the public native planner below that boundary.
- Change Module Map: no deviation. Wave compatibility remains in `dispatch.py`; persisted start eligibility stays in `native_runtime.py`; public contracts remain exported from `__init__.py`.
- Normal-path boundary exercised: the public `DispatchRuntime.pick_waves` and `start` APIs over real persisted `JobStore` and receipt state. The planner and eligibility owner were not replaced.
- Checks run:
  - `uv run --project . pytest serve/kanban/tests/test_dispatch_runtime.py` produced `5 passed`.
  - `uv run --project . ruff check serve/kanban/src/owlbear_kanban/dispatch.py serve/kanban/tests/test_dispatch_runtime.py` produced `All checks passed!`.
  - `uv run --project . ruff format --check serve/kanban/src/owlbear_kanban/dispatch.py serve/kanban/tests/test_dispatch_runtime.py` reported `2 files already formatted`.
  - `git diff --check` for the planner/test slice was clean.
- Findings: none. The prior failure key `dependency-edge-wave-compatibility` is resolved: entries preserve persisted predecessor IDs and `_plan_waves` splits reader batches when a direct edge exists in either direction. The public regression proves output `[[1, 2], [3]]` for a dependent reader after an unrelated reader.
- Patches applied: none by verifier.
- AC-to-evidence:
  - AC-1: `test_pick_waves_is_deterministic_and_uses_current_job_state` uses persisted records and native eligibility to prove stable IDs, exact profiles, and blocked omission.
  - AC-2: `test_pick_waves_separates_dependent_readers` proves dependency-aware reader separation and unrelated reader batching through public `pick_waves`.
  - AC-3: the deterministic/current-state test proves identical repeated plans and a fresh plan that excludes a job after public `start` persists its claim.
- Prior same-failure-key rejection check: one prior verifier rejection for `dependency-edge-wave-compatibility`; this repair closes it, so no repeated repair cycle remains.
- Verifier-challenger result: pass. It confirmed AC-specific public-boundary evidence, repaired bidirectional dependency handling, scope conformance, and passing focused checks.
- Final route: PASS to collect.

[[2026-07-24T17:47:17+02:00]]
## Collect Notes
- Classification: leaf. The task has no child tasks; `parent: 1980` identifies it as a child work item, not an aggregate.
- Latest verification evidence: newest `## Verify Notes` records PASS to collect after `uv run --project . pytest serve/kanban/tests/test_dispatch_runtime.py` produced `5 passed`; path-scoped Ruff passed; format check reported both files formatted; and the planner/test diff check was clean.
- Intent source and invariant coverage: task AC-1 through AC-3 are covered by the verifier's public `DispatchRuntime.pick_waves` and `start` evidence over persisted `JobStore` state. The prior `dependency-edge-wave-compatibility` rejection is explicitly resolved by the newest verification occurrence.
- Child coverage: not applicable; `list_tasks(parent=2023)` returned no tasks.
- Dependency gate: `2022` is satisfied (`dep_status: ok`).
- Residual decisions: no pending or resolved structured requests for this task; no later unresolved follow-up.
- Archive rationale: mechanically archived from current PASS evidence; no aggregate review or re-verification required.
