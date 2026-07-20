---
id: 1959
title: 'P1-10: Remove generic Kanban cleanup contract'
status: collect
priority: medium
created: 2026-07-17T16:24:21.021571+02:00
updated: 2026-07-20T02:27:20.251180+02:00
tags:
  - phase-1
  - scope:kanban
  - maintenance
  - api
parent: 1945
depends_on:
  - 1942
ac:
  - Given the Kanban package public interface after Cockpit migration, its 
    callable, exported, and documented maintenance inventory contains explicit 
    claim sweep and activity compaction and contains no cleanup operation or 
    CleanupResult.
  - Given a board containing expired claims, stale sessions, archive drift, or 
    duplicate task records, explicit claim sweep changes only eligible claim and
    session state while task repair owns archive and duplicate changes.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Delete the generic Kanban cleanup contract after Cockpit no longer consumes it, leaving explicit claim sweep, activity compaction, and task repair as the only maintenance owners.

## Scope
In scope: Kanban public API, cleanup result model and exports, package documentation, and directly stale Kanban cleanup tests. Out of scope: Cockpit routes and forwarding, frontend cleanup UI, task repair algorithms, and changes to claim lease or activity-compaction semantics.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, Design decision 8 and task 4.4. Dependency #1942 removes the Cockpit cleanup consumer before this task deletes the Kanban contract.

## Proof Guidance
Run focused Kanban behavior checks plus an exhaustive production-consumer and public-inventory scan. Preserve explicit sweep coverage for expired claims and stale-session reconciliation when removing cleanup-specific tests; add no compatibility alias.

[[2026-07-17T20:26:41+02:00]]
## Builder Notes

Change envelope: remove the generic Kanban cleanup contract only: `KanbanEngine.cleanup`, `CleanupResult`, its import, and the package README inventory entry. Preserve explicit claim sweep, stale-session reconciliation, activity compaction, and task repair semantics.

Files changed: `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/models.py`, `serve/kanban/README.md`.

Change Module Map deviations: none. The mapped Kanban engine/model/documentation owners were used. Cockpit frontend CleanupResult references remain intentionally out of scope.

Proof selected: `uv run --project . pytest serve/kanban/tests -q` (735 passed); `uv run --project . ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/src/owlbear_kanban/models.py` (all checks passed); `git diff --check` passed; Kanban inventory search for `CleanupResult|cleanup(` returned no matches.

Durable-test justification: no tests added. Existing focused Kanban coverage passed and preserves explicit maintenance behavior; adding cleanup-specific tests would preserve the removed contract.

Builder-challenger result: pass. No blockers, scope drift, or proof gaps identified.

Follow-up risk: Cockpit frontend cleanup references remain and require their own task/scope; they were explicitly excluded here.

[[2026-07-17T20:29:06+02:00]]
## Verify Notes

Evidence reviewed:
- Task intent, Scope, AC, Planning Authority (OpenSpec `redesign-workspace-health`, decision 8/task 4.4), Builder Notes, and task commit `3fcdf31db`.
- Commit removes `KanbanEngine.cleanup`, `CleanupResult`, its engine import, and the README method inventory entry in the mapped Kanban engine/model/documentation owners.

Named authorities and Change Module Map:
- The mapped owners were used with no implementation-map deviation: `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/models.py`, and `serve/kanban/README.md`.
- The explicit maintenance owners remain: `KanbanEngine.sweep()` releases expired claims and reconciles stale sessions; `repair_storage()` owns corruption/archive repair; `compact_activity()` owns activity retention.
- The public package has no `CleanupResult` export. A direct public-interface smoke check confirmed `KanbanEngine.cleanup` and `owlbear_kanban.models.CleanupResult` are absent.

Normal-path boundary exercised and checks run:
- `uv run --project . pytest serve/kanban/tests/test_engine_atomicity.py -q` — 26 passed (expired-claim sweep behavior).
- `uv run --project . pytest serve/kanban/tests/test_corruption.py -q` — 82 passed (archive drift and duplicate-record repair behavior).
- `uv run --project . pytest serve/kanban/tests/test_activity_store.py -q` — 43 passed (activity compaction behavior).
- `uv run --project . python -c 'from owlbear_kanban import KanbanEngine; from owlbear_kanban import models; assert not hasattr(KanbanEngine, "cleanup"); assert not hasattr(models, "CleanupResult"); print("public cleanup contract absent")'` — passed.
- Language diagnostics for the touched engine and models — no errors.
- `git diff --check` — passed.

Finding:
- `tests/test_engine_cleanup.py` remains a directly stale cleanup-contract test: it contains 21 calls to `engine.cleanup()` and documents the removed `CleanupResult` contract. The task Scope explicitly includes directly stale Kanban cleanup tests, so the public API deletion currently leaves the test suite stale. This is a builder-owned local omission. Existing frontend CleanupResult references are outside this task's stated scope and are not the reject basis.

Patches applied: none.
Verifier-challenger: not called; a PASS claim is not being proposed.
Final route: REJECT to build.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Remove or replace the stale generic-cleanup tests so no maintained test invokes or describes `KanbanEngine.cleanup`/`CleanupResult`; preserve existing explicit sweep, activity compaction, and storage-repair coverage. | `tests/test_engine_cleanup.py` | Verification inventory found 21 `engine.cleanup()` calls; task Scope includes directly stale Kanban cleanup tests. |

[[2026-07-20T02:13:42+02:00]]
## Builder Notes

Change envelope: remove only the directly stale generic-cleanup contract test module; preserve explicit claim sweep, activity compaction, storage repair, and task repair coverage.

Files changed: none durable. Two deletion attempts via apply_patch did not persist; the file was restored or remained present on subsequent checks.

Change Module Map deviations: none.

Proof selected: exhaustive absence scan and focused Kanban tests. The absence scan briefly returned no output immediately after an edit, but a subsequent direct file search found `tests/test_engine_cleanup.py` still present. `uv run --project . pytest serve/kanban/tests -q` exited 130 with no output on two attempts. A separate test invocation against root paths collected no tests and exited 5, so it is not valid proof.

Durable-test justification: no tests added; the required action is removal of stale tests.

Builder-challenger result: fail. It independently confirmed the stale test file and cleanup references remain and identified the proof gap.

Follow-up risk: do not advance to verify until the file deletion persists and the focused Kanban suite can be executed or its environment failure is resolved.

[[2026-07-20T02:21:11+02:00]]
## Builder Notes

Change envelope: remove only the directly stale generic-cleanup test module; preserve explicit claim sweep, activity compaction, storage repair, task repair, and all unrelated user worktree changes.

Files changed: none in this checkout. `tests/test_engine_cleanup.py` is absent; git history records its removal in commit `782104aa1`.

Change Module Map deviations: none. No Kanban source or test module required further edits because the rejected stale test is already absent in the current checkout.

Proof selected: `uv run --project . pytest serve/kanban/tests/test_engine_atomicity.py serve/kanban/tests/test_corruption.py serve/kanban/tests/test_activity_store.py -q` — 151 passed. `git diff --check` — passed. Direct source inventory confirms no `cleanup()` or `CleanupResult` references under `serve/kanban` or `serve/kanban/tests`; public-interface absence was independently confirmed in prior task evidence.

Full-suite limitation: `uv run --project . pytest serve/kanban/tests -q` exited 130 with no output in this environment, so it was not used as passing evidence.

Durable-test justification: no tests added or retained; the stale generic-cleanup test has already been removed, while focused explicit maintenance tests remain green.

Builder-challenger result: pass. It independently confirmed the stale test is absent, no removed-contract references remain in maintained Kanban trees, focused tests pass, and diff hygiene is clean.

Follow-up risk: verifier should re-check the public inventory from the current checkout; unrelated pre-existing worktree changes remain intentionally untouched.

[[2026-07-20T02:27:20+02:00]]
## Verify Notes

Evidence reviewed:
- Task Outcome, Scope, AC, Builder Notes, and the OpenSpec `redesign-workspace-health` authority: design decision 8 and task 4.4.
- Task implementation commit `3fcdf31db` removes `KanbanEngine.cleanup`, `CleanupResult`, its engine import, and the package README inventory entry. Follow-up commit `782104aa1` deletes the directly stale `tests/test_engine_cleanup.py` module.

Named authorities and Change Module Map:
- Design decision 8 requires no cleanup compatibility alias, preserves explicit claim/session maintenance and activity compaction, and assigns archive reconciliation and duplicate correction to task repair.
- Task 4.4 requires no public cleanup operation or `CleanupResult`, while explicit sweep and activity compaction remain callable.
- The mapped Kanban engine, models, README, and directly stale test owners were used. No module-map deviation was found.

Normal-path boundary and checks run:
- `uv run --project . pytest serve/kanban/tests/test_engine_atomicity.py serve/kanban/tests/test_corruption.py serve/kanban/tests/test_activity_store.py -q` passed: 151 tests covering expired-claim sweep, stale-session reconciliation, archive/duplicate repair, and activity compaction.
- Public-interface smoke passed: `KanbanEngine.cleanup` and `owlbear_kanban.models.CleanupResult` are absent; `sweep`, `compact_activity`, and `repair_storage` are callable.
- Repository-root inventory for `CleanupResult` and `.cleanup(` under `serve/kanban` and `serve/mcp-kanban` returned no matches; the stale root cleanup test is absent.
- Whole maintained-source/test scan found only Cockpit frontend `CleanupResult` files, explicitly outside this task scope and not consumers of the removed Python engine contract.
- Language diagnostics for touched engine and models: no errors. `git diff --check` passed.

Findings and patches:
- No verification defect found; no verifier patch applied.
- Recalled memory entries were assessed. The artifact-to-scope and background-debt guidance was applied when distinguishing excluded Cockpit frontend remnants from this Kanban task.

Verifier-challenger result: pass. It confirmed acceptance-criteria coverage, sufficient proof, no scope drift, and no unresolved issue.

Final route: PASS to collect.
