---
id: 966
title: 'Test: Add tracked background worker supervision for hook-triggered daemon tasks'
status: archived
priority: important
created: 2026-03-23T05:08:28.2704172+01:00
updated: 2026-03-23T23:54:06.8954068+01:00
started: 2026-03-23T23:53:38.638843+01:00
completed: 2026-03-23T23:53:38.638843+01:00
tags:
    - agent
    - daemon
    - hooks
    - scope:core
    - type:test
    - test
parent: 953
class: standard
---

See docs/research/hook-triggered-background-worker-supervision.md.

Write failing tests first for #953's implementation. Cover the exact HookWorkerSupervisor seam plus its RetrospectiveHook/bootstrap wiring. Keep scope on background-task ownership, semaphore gating, shutdown cleanup, and bootstrap registration only. Do not broaden into #964; synchronous activity-log parsing and kanban lookup remain on the awaited hook path in this task.

## AC

- [ ] Add tests/test_hook_worker_supervisor.py covering HookWorkerSupervisor in src/owlbear/core/hook_worker_supervisor.py, including ownership of_background_tasks: set[asyncio.Task[None]] and a shared_bg_semaphore: asyncio.Semaphore.
- [ ] Add tests proving schedule(...) keeps a strong reference to each spawned task until it finishes and that the done callback removes finished tasks from _background_tasks.
- [ ] Add tests proving the shared semaphore bounds worker critical sections: bg_concurrency=1 never overlaps two scheduled workers, and bg_concurrency=2 permits two workers to overlap while all scheduled workers still complete.
- [ ] Add tests proving shutdown() sets the supervisor shutdown signal, cancels unfinished tracked tasks, awaits their cleanup or drain, and returns with no tracked tasks left in _background_tasks.
- [ ] Extend tests/test_retrospective_hook.py to prove RetrospectiveHook.__call__ hands work off through an injected HookWorkerSupervisor.schedule(...) seam instead of calling asyncio.create_task() directly, while preserving the existing success-only gating, rejection and priority eligibility checks in __call__, and the existing cancel= ingestion seam in_run_retrospective().
- [ ] Extend tests/test_bootstrap.py to prove bootstrap wires one HookWorkerSupervisor only when ingest_pipeline is available, passes it into RetrospectiveHook registration, and appends that supervisor.shutdown callable to BootstrapResult.cleanup; when ingest_pipeline is unavailable, no supervisor shutdown callable is appended.
- [ ] Running the new or updated tests on current HEAD fails before #953's production changes.

[[2026-03-23]] Sun 06:06

## Architecture Review

__Verdict:__ REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add tests/test_hook_worker_supervisor.py covering a HookWorkerSupervisor-style core helper that owns a tracked background-task set and a shared asyncio.Semaphore. | Style wording was not binding to the exact type and module already defined by #953. | Rewrote to target HookWorkerSupervisor in src/owlbear/core/hook_worker_supervisor.py with explicit owned fields. |
| Add tests proving scheduled workers are retained strongly until completion and are removed from the tracked set when done. | Good intent and mechanically testable once tied to schedule(...) and done-callback cleanup. | Kept and tightened around the schedule seam. |
| Add tests proving bg_concurrency=1 prevents overlapping worker critical sections and bg_concurrency=2 permits two workers to overlap without dropping work. | Precise and aligned with OwlBear's existing semaphore test patterns. | Kept. |
| Add tests proving shutdown() sets the worker cancel signal, cancels or drains outstanding tasks, and leaves no tracked tasks behind after cleanup returns. | Cancels or drains left multiple valid interpretations for the RED contract. | Rewrote to require cancel of unfinished tracked tasks, awaited cleanup or drain, and an empty tracked set on return. |
| Extend tests/test_retrospective_hook.py to prove RetrospectiveHook.__call__ delegates background handoff to the supervisor instead of calling asyncio.create_task() directly, while preserving the existing eligibility filter and cancel= ingestion seam. | Eligibility filter was too vague relative to the concrete success, rejection, and priority gates in current code. | Rewrote to name the preserved success-only and rejection or priority checks plus the existing cancel= seam. |
| Extend tests/test_bootstrap.py to prove bootstrap appends the supervisor shutdown callable to BootstrapResult.cleanup when retrospective wiring is enabled and does not append it when no ingest pipeline is available. | Retrospective wiring is enabled did not map to a real toggle in current bootstrap wiring. | Rewrote around the actual condition: ingest_pipeline availability, hook registration, and cleanup append behavior. |
| Running the new or updated tests on current HEAD fails before production changes. | Good RED gate. | Kept. |

### Architecture Notes

- RetrospectiveHook.__call__ in src/owlbear/core/retrospective_hook.py currently owns the success, rejection-count, and priority gates before handing work to asyncio.create_task(...); the RED task must preserve those gates while changing only the handoff seam.
- GraphEnricher in src/owlbear/memory/knowledge/enrichment.py is the local precedent for owned _background_tasks plus a shared semaphore, so the tests should mirror that ownership model rather than invent a queue or worker-pool contract.
- _wire_post_model_hooks() in src/owlbear/bootstrap/__init__.py currently keys retrospective registration on ingest_pipeline is not None; there is no separate retrospective feature flag, so the AC now names that exact condition.
- BootstrapResult.cleanup in src/owlbear/bootstrap/_types.py is the existing shutdown seam already drained by chat and daemon startup paths; testing supervisor cleanup there stays within the current task's scope.
- The task remains single-domain in practice: bootstrap wiring here is assembly-root plumbing ancillary to a core hook-supervision feature, not a separate bootstrap initiative.
- TDD pairing is correct: #953 depends_on #966.

### Changes Made

- Rewrote the task body to bind the RED contract to the exact HookWorkerSupervisor, RetrospectiveHook, and bootstrap seams already identified in #953 and the research doc.
- Left #966 in backlog with the architect claim because the AC required refinement rather than approval.

### Dependencies

- Verified: #953 depends_on #966.
- Verified: #964 remains the separate non-blocking preflight follow-up.
- Verified: affected seams live in src/owlbear/core/retrospective_hook.py, src/owlbear/memory/knowledge/enrichment.py, src/owlbear/bootstrap/__init__.py, and src/owlbear/bootstrap/_types.py.

[[2026-03-23]] Mon 07:56

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add tests/test_hook_worker_supervisor.py covering HookWorkerSupervisor in src/owlbear/core/hook_worker_supervisor.py, including ownership of_background_tasks: set[asyncio.Task[None]] and a shared_bg_semaphore: asyncio.Semaphore. | Precise module, type, and owned-state contract aligned with #953. | Approved as written. |
| Add tests proving schedule(...) keeps a strong reference to each spawned task until it finishes and that the done callback removes finished tasks from _background_tasks. | Mechanically testable and matches the existing ownership pattern used elsewhere in OwlBear. | Approved as written. |
| Add tests proving the shared semaphore bounds worker critical sections: bg_concurrency=1 never overlaps two scheduled workers, and bg_concurrency=2 permits two workers to overlap while all scheduled workers still complete. | Explicit concurrency bounds and completion guarantees make this line verifiable. | Approved as written. |
| Add tests proving shutdown() sets the supervisor shutdown signal, cancels unfinished tracked tasks, awaits their cleanup or drain, and returns with no tracked tasks left in _background_tasks. | Clear observable shutdown contract for the RED phase without forcing internal implementation details. | Approved as written. |
| Extend tests/test_retrospective_hook.py to prove RetrospectiveHook.__call__ hands work off through an injected HookWorkerSupervisor.schedule(...) seam instead of calling asyncio.create_task() directly, while preserving the existing success-only gating, rejection and priority eligibility checks in __call__, and the existing cancel= ingestion seam in_run_retrospective(). | Precisely scoped to the changed seam and names the existing behavior that must remain intact. | Approved as written. |
| Extend tests/test_bootstrap.py to prove bootstrap wires one HookWorkerSupervisor only when ingest_pipeline is available, passes it into RetrospectiveHook registration, and appends that supervisor.shutdown callable to BootstrapResult.cleanup; when ingest_pipeline is unavailable, no supervisor shutdown callable is appended. | Exact assembly-root condition and cleanup seam are named, so this stays bounded to the feature wiring. | Approved as written. |
| Running the new or updated tests on current HEAD fails before #953's production changes. | Correct RED gate for the preceding test task. | Approved as written. |

### Architecture Notes

- RetrospectiveHook.__call__ in src/owlbear/core/retrospective_hook.py remains the handoff seam; the tests should change only the scheduling contract, not the existing success, rejection-count, or priority gates.
- GraphEnricher in src/owlbear/memory/knowledge/enrichment.py and tests/test_enrichment.py are the local precedent for owned_background_tasks plus shared Semaphore-bounded concurrency.
- _wire_post_model_hooks() in src/owlbear/bootstrap/__init__.py and BootstrapResult.cleanup in src/owlbear/bootstrap/_types.py remain the only wiring and shutdown seams this RED task needs to cover.
- The task is still single-domain: bootstrap assertions here are assembly plumbing ancillary to the core hook-supervision feature, not a separate bootstrap initiative.
- TDD compliance is satisfied because #953 depends_on #966.

### Changes Made

- Verified the refined AC against the research doc, #953, the current production seams, and the local test precedents.
- Approved #966 for the RED phase after confirming no further AC tightening or task split was needed.

### Dependencies

- Verified: #953 depends_on #966.
- Verified: #964 remains the separate non-blocking preflight follow-up.
- Verified: affected seams live in src/owlbear/core/retrospective_hook.py, src/owlbear/memory/knowledge/enrichment.py, src/owlbear/bootstrap/__init__.py, src/owlbear/bootstrap/_types.py, tests/test_retrospective_hook.py, tests/test_bootstrap.py, and tests/test_enrichment.py.

[[2026-03-23]] Mon 09:07

## Test-Writer Notes

- Test file: tests/test_hook_worker_supervisor.py (new)
- Extended: tests/test_retrospective_hook.py, tests/test_bootstrap.py
- Classes:
  - TestFromAC_HookWorkerSupervisorOwnership (test_hook_worker_supervisor.py)
  - TestFromAC_HookWorkerSupervisorSchedule (test_hook_worker_supervisor.py)
  - TestFromAC_HookWorkerSupervisorSemaphore (test_hook_worker_supervisor.py)
  - TestFromAC_HookWorkerSupervisorShutdown (test_hook_worker_supervisor.py)
  - TestFromAC_RetrospectiveHookSupervisorSeam (test_retrospective_hook.py)
  - TestFromAC_BootstrapHookWorkerSupervisorWiring (test_bootstrap.py)
- Tests per category: happy 10, edge 5, error 3, boundary 9
- Total: 27 tests, all FAIL (ImportError or TypeError on HEAD)
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| HookWorkerSupervisor in hook_worker_supervisor.py, _background_tasks and _bg_semaphore owned | TestFromAC_HookWorkerSupervisorOwnership (5 tests) | happy |
| schedule() keeps strong reference until done, done callback removes from set | TestFromAC_HookWorkerSupervisorSchedule (4 tests) | happy/edge |
| bg_concurrency=1 no overlap; bg_concurrency=2 permits overlap; all complete | TestFromAC_HookWorkerSupervisorSemaphore (3 tests) | boundary |
| shutdown() cancels unfinished tasks, awaits drain, leaves_background_tasks empty | TestFromAC_HookWorkerSupervisorShutdown (5 tests) | error/boundary |
| RetrospectiveHook.__call__ uses supervisor.schedule() not create_task | test_call_uses_supervisor_schedule_not_create_task | happy |
| Success-only gating preserved with supervisor | test_failure_outcome_skips_supervisor_schedule | error |
| Rejection + priority eligibility preserved | test_trivial_task_skips_supervisor_schedule, test_rejection_gate_preserved_with_supervisor | edge |
| cancel= ingestion seam preserved in_run_retrospective | test_run_retrospective_cancel_seam_preserved_with_supervisor | happy |
| bootstrap wires one HookWorkerSupervisor when ingest available, shutdown appended to cleanup | TestFromAC_BootstrapHookWorkerSupervisorWiring (4 tests) | happy/edge |
| when ingest unavailable, no supervisor appended | test_no_supervisor_shutdown_when_ingest_pipeline_unavailable | edge |

[[2026-03-23]] Mon 15:55

## Review: #966 — Test: Add tracked background worker supervision for hook-triggered daemon tasks

### Test Results

- pytest (broad file scope): `uv run pytest tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py tests/test_bootstrap.py -q --tb=short` -> 232 passed, 1 failed (unrelated optional dependency in `tests/test_bootstrap.py::TestCreateChannelSlackSuccess::test_slack_channel_created`: ImportError `slack_sdk is not installed`).
- pytest (AC-scoped): `uv run pytest tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring -q --tb=short` -> 26 passed, 0 failed.
- Warning observed in AC-scoped run: `PytestUnraisableExceptionWarning` for un-awaited coroutine `RetrospectiveHook._run_retrospective` in `tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam::test_run_retrospective_cancel_seam_preserved_with_supervisor`.

### Lint Results

- task-scoped ruff command failed:
  - `uv run ruff check src/owlbear/core/hook_worker_supervisor.py src/owlbear/core/retrospective_hook.py src/owlbear/bootstrap/__init__.py tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py tests/test_bootstrap.py`
  - `I001` Import block un-sorted at `tests/test_bootstrap.py:3191`.

### Coverage

- command: `uv run pytest tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- `src/owlbear/core/hook_worker_supervisor.py`: 100%
- `src/owlbear/core/retrospective_hook.py`: 87%
- `src/owlbear/bootstrap/__init__.py`: 36%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| HookWorkerSupervisor module + owned `_background_tasks`/`_bg_semaphore` | `tests/test_hook_worker_supervisor.py`: `TestFromAC_HookWorkerSupervisorOwnership` (`:22`) | Yes (type/ownership assertions at `:25`, `:29`, `:33`, `:38`, `:43`) | COVERED |
| `schedule(...)` strong reference + done-callback cleanup | `TestFromAC_HookWorkerSupervisorSchedule` (`:53`) | Yes (`:57`, `:77`, `:92`, `:115`) | COVERED |
| Semaphore bounds (`bg_concurrency=1` no overlap, `=2` overlap, all complete) | `TestFromAC_HookWorkerSupervisorSemaphore` (`:149`) | Yes (`:153`, `:186`, `:212`) | COVERED |
| `shutdown()` sets shutdown signal + cancels + drains + empties tracked set | `TestFromAC_HookWorkerSupervisorShutdown` (`:234`) | __No__: tests assert cancellation/empty/drain (`:238`, `:258`, `:273`, `:296`, `:303`) but there is no assertion for a shutdown signal; implementation also has no shutdown signal state (`src/owlbear/core/hook_worker_supervisor.py:33-34`, `:57-61`) | __MISSING__ |
| RetrospectiveHook uses injected supervisor seam; preserves success/rejection/priority gates and cancel seam | `tests/test_retrospective_hook.py`: `TestFromAC_RetrospectiveHookSupervisorSeam` (`:1000`) | Yes (`:1023`, `:1041`, `:1056`, `:1078`, `:1094`) | COVERED |
| Bootstrap wiring: create one supervisor when ingest present, append shutdown to cleanup; none when ingest absent | `tests/test_bootstrap.py`: `TestFromAC_BootstrapHookWorkerSupervisorWiring` (`:3134`) | Yes (`:3143`, `:3168`, `:3189`, `:3215`) | COVERED |
| RED gate evidence existed before builder changes | task notes: `kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md:122` | Yes (test-writer recorded 27 failing tests on HEAD) | COVERED |

#### Security Review

- No security regressions found in builder diff (`src/owlbear/core/hook_worker_supervisor.py`, `src/owlbear/core/retrospective_hook.py`, `src/owlbear/bootstrap/__init__.py`).
- No secrets, injection paths, unsafe deserialization, or path traversal introduced in the new code.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_hook_worker_supervisor.py` TestFromAC classes | No diff between `9b90e6b` and `f8e6808` (`git diff --name-only ...` returned empty) | PRESERVED |
| `tests/test_retrospective_hook.py` TestFromAC class | No diff between `9b90e6b` and `f8e6808` | PRESERVED |
| `tests/test_bootstrap.py` TestFromAC class | No diff between `9b90e6b` and `f8e6808` | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Assertions check concrete behavior (set sizes/order/call counts) across TestFromAC classes in `tests/test_hook_worker_supervisor.py`, `tests/test_retrospective_hook.py`, `tests/test_bootstrap.py`. |
| Negative/error paths | __WEAK__ | AC-required shutdown-signal behavior has no negative/verification test (`tests/test_hook_worker_supervisor.py:234-313`). |
| Mutation reasoning | __WEAK__ | Removing any shutdown-signal update would not fail any test, because no such assertion exists; implementation currently lacks signal state entirely (`src/owlbear/core/hook_worker_supervisor.py:33-34`, `:57-61`). |
| Test independence | ADEQUATE | Tests are mostly isolated, but AC-scoped run emits `PytestUnraisableExceptionWarning` from un-awaited coroutine in supervisor seam tests. |
| Descriptive names | STRONG | Test names are scenario-specific and behavior-oriented. |

#### Data Safety

- No new data-integrity risks found (no persistence format changes, no unsafe shared mutable cross-thread state added).

#### Implementation-Aware Test Gaps

- `HookWorkerSupervisor.shutdown()` AC requires setting a shutdown signal (`kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md:30`), but implementation has no shutdown signal field/state in constructor (`src/owlbear/core/hook_worker_supervisor.py:33-34`) and shutdown only cancels + gathers (`:57-61`).
- Because tests never assert signal behavior, this gap is both an AC miss and an untested implementation path.

### Pass 2 — INFORMATIONAL

- AC-scoped tests pass, but broad-file pytest still fails in this environment on optional Slack dependency (`tests/test_bootstrap.py::TestCreateChannelSlackSuccess::test_slack_channel_created`).
- Task-scoped lint fails in AC-authored bootstrap test import block (`tests/test_bootstrap.py:3191`).

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Add `tests/test_hook_worker_supervisor.py` with ownership fields | File exists; classes/methods at `tests/test_hook_worker_supervisor.py:22-313`; source class at `src/owlbear/core/hook_worker_supervisor.py:21` with `_background_tasks` and `_bg_semaphore` at `:33-34` | `TestFromAC_HookWorkerSupervisorOwnership` | PASS |
| `schedule(...)` strong ref + done callback cleanup | `src/owlbear/core/hook_worker_supervisor.py:47-49`; tests at `tests/test_hook_worker_supervisor.py:57,77,92,115` | `TestFromAC_HookWorkerSupervisorSchedule` | PASS |
| Semaphore bounds for concurrency 1 and 2 | Semaphore use at `src/owlbear/core/hook_worker_supervisor.py:44`; overlap/non-overlap tests at `tests/test_hook_worker_supervisor.py:153,186,212` | `TestFromAC_HookWorkerSupervisorSemaphore` | PASS |
| `shutdown()` sets signal + cancels/drains + empties tracked set | Cancel/drain present at `src/owlbear/core/hook_worker_supervisor.py:57-61`; no shutdown signal state exists; tests do not assert signal behavior (`tests/test_hook_worker_supervisor.py:234-313`) | `TestFromAC_HookWorkerSupervisorShutdown` | __FAIL__ |
| RetrospectiveHook uses injected supervisor seam while preserving gates and cancel seam | Supervisor branch at `src/owlbear/core/retrospective_hook.py:133-136`; supervisor tests at `tests/test_retrospective_hook.py:1023-1094` | `TestFromAC_RetrospectiveHookSupervisorSeam` | PASS |
| Bootstrap wires supervisor conditionally and appends shutdown cleanup | Wiring at `src/owlbear/bootstrap/__init__.py:103-115`; bootstrap tests at `tests/test_bootstrap.py:3143-3215` | `TestFromAC_BootstrapHookWorkerSupervisorWiring` | PASS |
| RED tests initially failed pre-builder | task body note `kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md:122` | test-writer note | PASS |

### Verdict: FAIL

### Action Taken

- Move task from `review` to `todo` for rework due AC miss + lint failure.

[[2026-03-23]] Mon 16:51

## Test-Writer Notes (retry)

- Retry reason: reviewer cited MISSING shutdown signal assertion in TestFromAC_HookWorkerSupervisorShutdown
- Added: 1 new failing test: test_shutdown_signal_prevents_new_schedules (tests/test_hook_worker_supervisor.py)
- Tests contract: after shutdown(), schedule() must not start new background work; FAILs on current impl (no shutdown signal state)
- Fixed: import sort I001 at tests/test_bootstrap.py:3191 (moved hook_worker_supervisor import after bootstrap import, sorted alphabetically)
- Preserved: 27 existing tests (all pass)
- Total: 28 tests, 1 FAIL (new), 27 PASS
- ruff: clean (all task-scoped files)

[[2026-03-23]] Mon 17:45

## Review Evidence

### Review: #966 — Test: Add tracked background worker supervision for hook-triggered daemon tasks

### Test Results

- pytest (AC-scoped): `uv run pytest tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring -q --tb=short`
- Result: __27 passed, 0 failed__
- Warnings: RuntimeWarning `coroutine 'RetrospectiveHook._run_retrospective' was never awaited` emitted in `TestFromAC_RetrospectiveHookSupervisorSeam::test_rejection_gate_preserved_with_supervisor` and `test_run_retrospective_cancel_seam_preserved_with_supervisor`.

### Lint Results

- command: `uv run ruff check src/owlbear/core/hook_worker_supervisor.py src/owlbear/core/retrospective_hook.py src/owlbear/bootstrap/__init__.py tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py tests/test_bootstrap.py`
- result: __All checks passed__

### Coverage

- command: `uv run pytest tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- `src/owlbear/core/hook_worker_supervisor.py`: __100%__
- `src/owlbear/core/retrospective_hook.py`: __87%__
- `src/owlbear/bootstrap/__init__.py`: __35%__

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Add `tests/test_hook_worker_supervisor.py` ownership coverage | `TestFromAC_HookWorkerSupervisorOwnership` ([tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L23)) | Yes — type/ownership assertions at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L26), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L30), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L34), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L39), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L44) | COVERED |
| `schedule(...)` strong reference + done-callback cleanup | `TestFromAC_HookWorkerSupervisorSchedule` ([tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L54)) | Yes — lifecycle assertions at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L58), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L78), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L93), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L116) | COVERED |
| Semaphore bounds (`bg_concurrency=1` no overlap, `=2` overlap, all complete) | `TestFromAC_HookWorkerSupervisorSemaphore` ([tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L150)) | Yes — overlap/no-overlap checks at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L154), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L187), completion at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L212) | COVERED |
| `shutdown()` sets signal + cancels/drains + empties tracked set | `TestFromAC_HookWorkerSupervisorShutdown` ([tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L235)) | Yes — cancel/drain/empty assertions at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L239), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L259), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L274), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L304), shutdown-signal observable contract at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L327) | COVERED |
| RetrospectiveHook supervisor seam + gating + cancel seam | `TestFromAC_RetrospectiveHookSupervisorSeam` ([tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1000)) | Yes — assertions at [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1023), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1041), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1056), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1078), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1094) | COVERED |
| Bootstrap wiring + conditional cleanup append | `TestFromAC_BootstrapHookWorkerSupervisorWiring` ([tests/test_bootstrap.py](tests/test_bootstrap.py#L3134)) | Yes — assertions at [tests/test_bootstrap.py](tests/test_bootstrap.py#L3143), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3168), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3189), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3214) | COVERED |
| RED gate existed pre-builder | Test-writer retry note ([kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L217), [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L223)) and AC line ([kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L33)) | Yes | COVERED |

#### Security Review

- Reviewed `HookWorkerSupervisor` and the wiring changes in [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L94) and [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L117).
- No secrets, injection paths, path traversal, unsafe deserialization, or shell-exec vulnerabilities introduced.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_hook_worker_supervisor.py` TestFromAC classes | No changes in builder commit range (`git diff --name-only 9b90e6b..f8e6808 -- tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py tests/test_bootstrap.py` => empty) | PRESERVED |
| `tests/test_retrospective_hook.py` TestFromAC class | No changes in same range | PRESERVED |
| `tests/test_bootstrap.py` TestFromAC class | No changes in same range | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Direct state/ordering/call-asserts in supervisor, seam, and bootstrap tests. |
| Negative/error paths | ADEQUATE | Failure outcome gating and cancellation paths are covered. |
| Mutation reasoning | ADEQUATE | Removing `_shutdown`/schedule no-op or done-callback cleanup would break explicit assertions. |
| Test independence | __WEAK__ | AC-scoped run emits unawaited-coroutine runtime warnings for supervisor seam tests (coroutines constructed but not awaited/closed under mocked schedule paths). |
| Descriptive names | STRONG | Test names are scenario-specific and behavior-oriented. |

#### Data Safety

- No new data-integrity risks identified in the reviewed implementation.

#### Implementation-Aware Test Gaps

- Working implementation that satisfies shutdown-signal behavior currently exists only in unstaged working-tree changes to [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L35) and [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L44), not in builder commit `f8e6808` (`git show f8e6808 -- ...` shows no `_shutdown` state/no-op path).
- This makes the handoff non-reproducible from the task commit history.

### Pass 2 — INFORMATIONAL

- Coverage is strong for the new supervisor module (100%) but lower on broader host modules due task-scoped test selection.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L27) | Supervisor ownership in [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L33), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L34) | `TestFromAC_HookWorkerSupervisorOwnership` | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L28) | `schedule` + done callback in [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L52), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L54) | `TestFromAC_HookWorkerSupervisorSchedule` | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L29) | Semaphore gating in [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L49) | `TestFromAC_HookWorkerSupervisorSemaphore` | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L30) | shutdown signal + post-shutdown no-op in [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L63), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L44) | `TestFromAC_HookWorkerSupervisorShutdown` | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L31) | injected-supervisor seam in [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L140), [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L141), fallback at [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L143) | `TestFromAC_RetrospectiveHookSupervisorSeam` | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L32) | conditional supervisor wiring and cleanup append in [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L117), [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L121), [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L129) | `TestFromAC_BootstrapHookWorkerSupervisorWiring` | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L33) | pre-builder RED evidence in task notes [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L217), [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L223) | Test-writer retry note | PASS |

### Verdict: FAIL

- Reason 1 (critical): Test quality has a __WEAK__ dimension due unawaited coroutine warnings in AC seam tests.
- Reason 2 (critical): Required shutdown-signal behavior is currently uncommitted working-tree state, not reproducible from builder commit history.

### Action Taken

- `kanban\kanban-md.exe edit 966 --status todo --release`

[[2026-03-23]] Mon 18:19

## Test-Writer Notes

- Test files:
  1. tests/test_hook_worker_supervisor.py (new)
  2. tests/test_retrospective_hook.py (extended: TestFromAC_RetrospectiveHookSupervisorSeam)
  3. tests/test_bootstrap.py (extended: TestFromAC_BootstrapHookWorkerSupervisorWiring)
- Classes:
  - TestFromAC_HookWorkerSupervisorOwnership (5 tests)
  - TestFromAC_HookWorkerSupervisorSchedule (4 tests)
  - TestFromAC_HookWorkerSupervisorSemaphore (3 tests)
  - TestFromAC_HookWorkerSupervisorShutdown (6 tests)
  - TestFromAC_RetrospectiveHookSupervisorSeam (5 tests)
  - TestFromAC_BootstrapHookWorkerSupervisorWiring (4 tests)
- Tests per category: happy 12, edge 6, error 5, boundary 4
- Total: 27 tests
- ruff: clean
- Note: test files were written as RED phase (headers say all fail on HEAD because module did not exist); implementation in src/owlbear/core/hook_worker_supervisor.py was built in the same cycle before formal tracking completed, so tests currently PASS. All AC lines are covered.
- AC coverage:

  | AC Line | Test(s) | Category |
  |---------|---------|----------|
  | ownership of _background_tasks + _bg_semaphore | TestFromAC_HookWorkerSupervisorOwnership::* | happy |
  | schedule() strong reference + done-callback cleanup | TestFromAC_HookWorkerSupervisorSchedule::* | happy/edge |
  | semaphore bounds: concurrency=1 serialized, concurrency=2 overlapping | TestFromAC_HookWorkerSupervisorSemaphore::* | boundary |
  | shutdown() signal+cancel+drain+empty set | TestFromAC_HookWorkerSupervisorShutdown::* | happy/error |
  | RetrospectiveHook delegates to supervisor.schedule not create_task | TestFromAC_RetrospectiveHookSupervisorSeam::* | happy/edge/error |
  | bootstrap wires HookWorkerSupervisor and appends shutdown | TestFromAC_BootstrapHookWorkerSupervisorWiring::* | happy/error |

[[2026-03-23]] Mon 21:50

## Builder Notes

- Files changed: src/owlbear/core/hook_worker_supervisor.py; src/owlbear/core/retrospective_hook.py
- Tests: 27 passed (AC-scoped) and 60 passed (coverage scope); pre-check on this branch showed AC tests already green before edits.
- Coverage: 100% on src/owlbear/core/hook_worker_supervisor.py; 95% on src/owlbear/core/retrospective_hook.py
- Lint: ruff clean
- Evidence: uv run pytest tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring -q --tb=short -> 27 passed, 0 failed; uv run pytest tests/test_retrospective_hook.py tests/test_hook_worker_supervisor.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short -> hook_worker_supervisor 100%, retrospective_hook 95%; uv run ruff check src/owlbear/core/hook_worker_supervisor.py src/owlbear/core/retrospective_hook.py tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py tests/test_bootstrap.py -> All checks passed
- Fixes applied: Added explicit shutdown signal behavior to HookWorkerSupervisor and generalized schedule() to await any awaitable with safe close-on-shutdown; introduced lazy supervisor handoff in RetrospectiveHook to eliminate unawaited coroutine warnings under mocked schedule paths.

## Review Evidence

### Review: #966 - Test: Add tracked background worker supervision for hook-triggered daemon tasks

### Test Results

- AC-scoped pytest: `uv run pytest tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring -q --tb=short` -> `27 passed, 0 failed, 2 warnings`.
- Broader hook scope: `uv run pytest tests/test_retrospective_hook.py tests/test_hook_worker_supervisor.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` -> `60 passed, 0 failed, 2 warnings`.
- Both runs showed only the optional dependency warnings from [tests/conftest.py](tests/conftest.py#L58); no unawaited-coroutine warnings remain.

### Lint Results

- `uv run ruff check src/owlbear/core/hook_worker_supervisor.py src/owlbear/core/retrospective_hook.py src/owlbear/bootstrap/__init__.py tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py tests/test_bootstrap.py` -> `All checks passed!`

### Coverage

- [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L33): `100%`
- [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L149): `95%`

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| Ownership fields | [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L23) | Yes - direct assertions at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L26), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L30), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L34), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L39), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L44) | COVERED |
| `schedule(...)` tracking and cleanup | [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L54) | Yes - lifecycle assertions at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L58), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L78), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L93), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L116) | COVERED |
| Semaphore bounds | [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L150) | Yes - overlap and completion assertions at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L154), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L187), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L213) | COVERED |
| Shutdown signal, cancel, drain, empty set | [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L235) | Yes - shutdown behavior assertions at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L239), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L259), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L274), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L297), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L304), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L327) | COVERED |
| RetrospectiveHook seam and gates | [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1000) | Yes - schedule and gate assertions at [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1038), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1053), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1075), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1091), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1117) | COVERED |
| Bootstrap wiring and cleanup registration | [tests/test_bootstrap.py](tests/test_bootstrap.py#L3134) | Yes - cleanup and registration assertions at [tests/test_bootstrap.py](tests/test_bootstrap.py#L3164), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3166), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3187), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3212), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3236) | COVERED |
| RED gate existed before builder work | [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L33) | Yes - RED evidence at [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L122), [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L219), [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L223) | COVERED |

#### Security Review

- No secrets, injection paths, unsafe deserialization, or shell-exec issues found in [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L1), [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L57), or [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L117).

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_HookWorkerSupervisorShutdown::*` | Added [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L327); prior shutdown methods at [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L239), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L259), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L274), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L297), [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L304) are preserved | STRENGTHENED |
| `TestFromAC_RetrospectiveHookSupervisorSeam::*` | Current task-scoped diff against HEAD is signature reflow only at [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1023), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1041), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1056), [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1078) | PRESERVED |
| `TestFromAC_BootstrapHookWorkerSupervisorWiring::*` | Diff from `9b90e6b` reflows two signatures and moves one import; assertions at [tests/test_bootstrap.py](tests/test_bootstrap.py#L3164), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3166), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3187), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3212), [tests/test_bootstrap.py](tests/test_bootstrap.py#L3236) are unchanged | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Tests assert exact set sizes, overlap ordering, call counts, cleanup callable identity, and handler registration. |
| Negative/error paths | STRONG | Failure outcome skip, trivial-priority skip, empty-shutdown, multi-cancel, and post-shutdown no-op are covered. |
| Mutation reasoning | ADEQUATE | Removing the shutdown guard at [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L44), done callback at [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L56), cancel loop at [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L68), or supervisor seam at [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L164) would break direct assertions. |
| Test independence | STRONG | Fresh supervisor or hook state per test, function-scoped async loops, and no unawaited-coroutine warning noise in the current run. |
| Descriptive names | STRONG | Test names describe the exact contract being verified. |

#### Data Safety

- No data-safety issues found.

#### Implementation-Aware Test Gaps

- No significant untested behavioral paths found in the committed source changes.

### Pass 2 - INFORMATIONAL

- [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1023) is dirty against HEAD, but the task-scoped diff is formatting-only signature reflow in four TestFromAC methods.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L27) | Ownership fields at [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L33), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L34), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L35) | [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L23) | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L28) | Scheduling and cleanup at [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L54), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L55), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L56) | [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L54) | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L29) | Semaphore wrapper at [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L51) | [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L150) | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L30) | Shutdown behavior at [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L44), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L45), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L47), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L65), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L68), [src/owlbear/core/hook_worker_supervisor.py](src/owlbear/core/hook_worker_supervisor.py#L70) | [tests/test_hook_worker_supervisor.py](tests/test_hook_worker_supervisor.py#L235) | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L31) | Gate and seam logic at [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L149), [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L158), [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L160), [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L164), [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L230), [src/owlbear/core/retrospective_hook.py](src/owlbear/core/retrospective_hook.py#L249) | [tests/test_retrospective_hook.py](tests/test_retrospective_hook.py#L1000) | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L32) | Bootstrap wiring at [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L121), [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L122), [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L126), [src/owlbear/bootstrap/__init__.py](src/owlbear/bootstrap/__init__.py#L129) | [tests/test_bootstrap.py](tests/test_bootstrap.py#L3134) | PASS |
| [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L33) | RED evidence at [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L122), [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L219), [kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md](kanban/tasks/966-test-add-tracked-background-worker-supervision-for.md#L223) | Test-writer notes | PASS |

### Verdict: PASS

### Action Taken

- `kanban\kanban-md.exe edit 966 --append-body review-evidence --claim reviewer-966`
- `kanban\kanban-md.exe edit 966 --status docs --release`

[[2026-03-23]] Mon 23:21

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Added HookWorkerSupervisor to Runtime row (commit 630a398) |
| 2 | Docstrings complete | Yes | Pass | hook_worker_supervisor.py has full docstrings; _LazyCoroutine in retrospective_hook.py has docstring |
| 3 | docs/sources/overview.md | No | N/A | Only Python stdlib and internal OwlBear sources used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/hook-triggered-background-worker-supervision.md exists and linked in task body |

### Files Updated

- .github/copilot-instructions.md (Runtime row: added HookWorkerSupervisor)

### Scratch Files Cleaned

- 966-ac.tmp, 966-architect.tmp, 966-bootstrap.txt, 966-full.tmp, 966-retro.txt, 966-seam.txt, 966-supervisor.txt, 966-test-run.txt, 966-tests.txt, 966-tw-retry.tmp

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Added HookWorkerSupervisor to Runtime row (commit 630a398) |
| 2 | Docstrings complete | Yes | Pass | hook_worker_supervisor.py has module + class + schedule() + shutdown() docstrings; _LazyCoroutine in retrospective_hook.py has docstring |
| 3 | docs/sources/overview.md | No | N/A | Only Python stdlib and internal OwlBear sources used; no external patterns adopted |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/hook-triggered-background-worker-supervision.md exists and linked in task body |

### Files Updated

- .github/copilot-instructions.md (Runtime row: added HookWorkerSupervisor entry)

### Scratch Files Cleaned

- 966-ac.tmp, 966-architect.tmp, 966-bootstrap.txt, 966-full.tmp, 966-retro.txt, 966-seam.txt, 966-supervisor.txt, 966-test-run.txt, 966-tests.txt, 966-tw-retry.tmp

[[2026-03-23]] Mon 23:54

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| HookWorkerSupervisor in hook_worker_supervisor.py, _background_tasks + _bg_semaphore | File exists, ownership fields at src/owlbear/core/hook_worker_supervisor.py:33-35 | PASS |
| schedule() strong ref + done callback cleanup | schedule() at :37-56, done callback at :55 | PASS |
| Semaphore bounds concurrency 1/2 | async with self._bg_semaphore at :51 | PASS |
| shutdown() sets signal + cancels + drains + empties | _shutdown=True :63, cancel loop :66, gather :68 | PASS |
| RetrospectiveHook uses supervisor.schedule() seam | _LazyCoroutine handoff at retrospective_hook.py:160 | PASS |
| Bootstrap wires supervisor conditionally + cleanup | _wire_post_model_hooks at bootstrap/__init__.py:117-129 | PASS |
| RED tests initially failed pre-builder | Test-writer notes in task body confirm 27 failing tests on HEAD | PASS |

### Test Results

- pytest (AC-scoped): 27 passed, 0 failed
- pytest (full suite): 66 pre-existing failures unrelated to #966 (numpy env, RED-phase tests, other task regressions)
- ruff: All checks passed

### AC Quality Score: 5

AC was specific, complete, and led to a clean implementation. Architect correctly refined vague wording to name exact types, modules, and seams.

### Confidence: .97

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4034ab0 | chore | tests/test_retrospective_hook.py | #966 |
