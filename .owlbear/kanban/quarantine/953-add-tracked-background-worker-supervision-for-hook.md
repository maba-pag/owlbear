---
id: 953
title: Add tracked background worker supervision for hook-triggered daemon tasks
status: archived
priority: important
created: 2026-03-23T03:10:43.4748784+01:00
updated: 2026-03-24T03:47:53.3853964+01:00
started: 2026-03-24T03:47:42.9704221+01:00
completed: 2026-03-24T03:47:42.9704221+01:00
tags:
    - agent
    - daemon
    - hooks
    - scope:core
    - type:build
depends_on:
    - 966
class: standard
---

See docs/research/hook-triggered-background-worker-supervision.md. This task implements the reusable hook-worker supervision seam selected there. Keep HookRegistry.emit() observational. Do not move RetrospectiveHook's synchronous activity-log parsing or kanban-md show preflight off the awaited hook path in this task; that follow-up remains #964.

## AC

- [ ] Add HookWorkerSupervisor in src/owlbear/core/hook_worker_supervisor.py that owns _background_tasks: set[asyncio.Task[None]] and _bg_semaphore: asyncio.Semaphore, following the ownership pattern already used by GraphEnricher in src/owlbear/memory/knowledge/enrichment.py.
- [ ] HookWorkerSupervisor.__init__(bg_concurrency: int = 1) must default to one concurrent worker.
- [ ] HookWorkerSupervisor.schedule(...) must create a per-worker cancel signal, run the worker under async with self._bg_semaphore, retain a strong task reference in _background_tasks, and discard the task from _background_tasks on completion.
- [ ] HookWorkerSupervisor.shutdown() -> Awaitable[None] must set the supervisor shutdown signal, cancel and await unfinished tracked tasks, and return with no unfinished tasks remaining in _background_tasks.
- [ ] RetrospectiveHook must accept an injected HookWorkerSupervisor and use it for background handoff instead of calling asyncio.create_task() directly; the existing success-only, triviality, and priority gating in __call__ and the existing cancel= composition inside_run_retrospective() must remain intact.
- [ ] Bootstrap wiring in src/owlbear/bootstrap/__init__.py must create one supervisor when ingest_pipeline is available, pass it into RetrospectiveHook, and append supervisor.shutdown to the cleanup list returned in BootstrapResult.
- [ ] Do not change HookRegistry.emit() semantics, daemon loop structure, or move RetrospectiveHook's current activity-log or kanban-md show preflight behind a different seam; that performance follow-up is tracked by #964.
- [ ] All tests from #966 pass.
- [ ] uv run ruff check is clean on all touched files.

## Research

- Doc: docs/research/hook-triggered-background-worker-supervision.md
- Recommendation (.92 confidence): implement one small reusable hook-worker supervisor with owned task tracking, Semaphore-bounded scheduling, and async shutdown drain; wire its cleanup through OwlBear's existing bootstrap cleanup list and keep RetrospectiveHook as eligibility filter plus handoff only.
- Key findings:
  - HookRegistry.emit() awaits handlers inline, so the hook callback itself must stay short and observational.
  - Python's asyncio guidance plus OwlBear's GraphEnricher both support the same pattern: keep strong task references, discard them on completion, and gate concurrent work with a Semaphore.
  - BootstrapResult.cleanup is already invoked by both chat and daemon commands, so hook-worker drain should attach there instead of inventing a second lifecycle system.
  - TaskGroup is the wrong default for this seam because its context-managed lifetime and fail-fast sibling cancellation do not fit long-lived observational hooks.
  - RetrospectiveHook already has a per-operation cancel= seam for ingest work; supervision should extend that contract rather than replace it.
  - RetrospectiveHook still performs synchronous activity-log parsing and a kanban-md subprocess before background handoff.
- Follow-up tasks created:
  - #964 Keep TASK_COMPLETE retrospective scheduling non-blocking before background handoff
- Attribution updated: docs/sources/overview.md

[[2026-03-23]] Mon 05:10

## Architecture Review

__Verdict:__ SPLIT

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add a small supervisor for hook-triggered daemon background work. | Vague on module placement, ownership model, and public seam. | Rewrote as HookWorkerSupervisor in core with explicit schedule and shutdown contract. |
| Keep strong references to spawned tasks and remove them on completion. | Good intent, but not mechanically testable as written. | Rewrote around a tracked _background_tasks set with discard-on-done behavior. |
| Bound concurrent worker execution with asyncio.Semaphore. | Missing default bound and integration point. | Rewrote to a shared _bg_semaphore with bg_concurrency defaulting to 1. |
| Expose shutdown cancel/drain behavior for daemon cleanup. | Missing lifecycle seam and cleanup owner. | Rewrote to async shutdown() registered through BootstrapResult.cleanup. |
| Refactor RetrospectiveHook to use the supervisor instead of bare asyncio.create_task(). | Correct direction, but it needed to preserve current gating and cancel composition. | Rewrote to injected-supervisor handoff while keeping __call__ filtering and _run_retrospective() cancel= behavior intact. |
| Add focused tests for task tracking, bounded concurrency, and shutdown cleanup. | Implementation task cannot own its RED work. | Split into #966 and made #953 depend on it. |

### Architecture Notes

- HookRegistry.emit() in src/owlbear/core/hooks.py awaits handlers inline, so the hook callback must stay observational and hand work off only after its current eligibility checks.
- GraphEnricher in src/owlbear/memory/knowledge/enrichment.py is the precedent for _background_tasks ownership plus Semaphore-bounded background work.
- BootstrapResult.cleanup in src/owlbear/bootstrap/_types.py is drained by both src/bearclaw/commands/chat.py and src/bearclaw/commands/daemon.py, so supervisor shutdown belongs there instead of in new daemon lifecycle code.
- Assembly-root wiring is ancillary here, consistent with prior hook tasks #622 and #645; I did not split the bootstrap injection into a separate architecture task.
- Scope boundary: moving RetrospectiveHook's current activity-log parsing or kanban-md subprocess preflight off the awaited path remains #964, not #953.

### Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| HookWorkerSupervisor.schedule() | Background worker raises after handoff | Worker-defined exception | Yes - worker keeps its own exception isolation; supervisor only owns lifecycle. | Retrospective run may be skipped, daemon keeps running. |
| HookWorkerSupervisor.shutdown() | Daemon stops with in-flight worker | asyncio.CancelledError | Yes - shutdown sets cancel intent, cancels tracked tasks, and awaits drain. | No orphan worker remains after cleanup. |

### Changes Made

- Created #966 Test: Add tracked background worker supervision for hook-triggered daemon tasks.
- Rewrote #953 as the GREEN-phase implementation contract.
- Added dependency #966 to #953.

### Dependencies

- Added: #966.
- Verified: BootstrapResult.cleanup is the shared shutdown seam used by chat and daemon startup paths.
- Verified: #964 remains the separate non-blocking preflight follow-up.

[[2026-03-23]] Mon 23:49

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add HookWorkerSupervisor in core/hook_worker_supervisor.py with owned task set and semaphore | Precise: exact module, exact fields, exact types | Kept |
| __init__(bg_concurrency: int = 1) defaults to 1 | Precise: exact parameter and default | Kept |
| schedule() creates per-worker cancel signal, runs under semaphore, retains strong ref, discards on done | Minor: per-worker cancel signal is slightly loose (actual contract is asyncio task cancellation via shutdown, not an explicit event), but rest of the line is unambiguous | Kept â€” tests from #966 define the exact contract |
| shutdown() sets signal, cancels tracked tasks, awaits drain, returns empty | Precise: exact lifecycle guarantee | Kept |
| RetrospectiveHook accepts injected supervisor, preserves existing gating and cancel= seam | Precise: names exact preservation targets | Kept |
| Bootstrap wires supervisor when ingest_pipeline available, appends shutdown to cleanup | Precise: names exact condition and registration point | Kept |
| Negative constraint: no HookRegistry.emit() or daemon loop changes | Clear boundary, defers to #964 | Kept |
| All tests from #966 pass | Verifiable gate | Kept |
| ruff check clean on touched files | Standard lint gate | Kept |

### Architecture Notes

- Module layering verified: HookWorkerSupervisor in core/ imports only asyncio (no upward deps). Bootstrap is the assembly root â€” wiring there is consistent with #622 and #645 precedent.
- Pattern match verified: GraphEnricher in memory/knowledge/enrichment.py uses identical ownership model (set[Task] + Semaphore + done-callback discard). Supervisor mirrors this exactly with a smaller surface (schedule + shutdown only).
- Single domain: core (primary), bootstrap wiring is ancillary per architecture-standards edge-case rule.
- Dependency #966 (tests) is at done â€” TDD RED phase complete.
- #964 (non-blocking preflight) correctly remains a separate follow-up.

### Dependencies

- Verified: #966 (test task) at done
- Verified: BootstrapResult.cleanup is the shared shutdown seam (chat.py + daemon.py)
- Verified: #964 remains separate scope

[[2026-03-24]] Tue 00:34

## Test-Writer Notes

[[2026-03-24]] Tue 00:34

## Test-Writer Notes

- Out-of-order pipeline: implementation was built concurrently with test task #966 (now archived). All 27 tests from #966 pass on current HEAD.

- Test files: tests/test_hook_worker_supervisor.py (18), test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam (5), test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring (4)

- Total: 27 tests, all PASS (implementation pre-exists). ruff: clean. Passing through to builder.

[[2026-03-24]] Tue 01:20

## Builder Notes

- Files changed: none (implementation already present in src/owlbear/core/hook_worker_supervisor.py, src/owlbear/core/retrospective_hook.py, and src/owlbear/bootstrap/__init__.py).
- Tests: 27 passed in task scope (`uv run pytest tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam tests/test_bootstrap.py::TestFromAC_BootstrapHookWorkerSupervisorWiring -q --tb=short`).
- Coverage: scoped bare `--cov` run reported src/owlbear/core/hook_worker_supervisor.py 100%, src/owlbear/core/retrospective_hook.py 84%, src/owlbear/bootstrap/__init__.py 34% (`27 passed, 2 warnings`).
- Lint: ruff clean (`uv run ruff check src/owlbear/core/hook_worker_supervisor.py src/owlbear/core/retrospective_hook.py src/owlbear/bootstrap/__init__.py tests/test_hook_worker_supervisor.py tests/test_retrospective_hook.py tests/test_bootstrap.py`).
- Evidence: TestFromAC scope from #966 is already GREEN on current HEAD; no implementation delta was required for #953.
- Fixes applied: none.

[[2026-03-24]] Tue 02:13

## Review Evidence

### Test Results

- pytest: 27 passed, 2 optional-dependency warnings on the scoped suite (tests/test_hook_worker_supervisor.py + TestFromAC_RetrospectiveHookSupervisorSeam + TestFromAC_BootstrapHookWorkerSupervisorWiring).

- ruff: All checks passed for src/owlbear/core/hook_worker_supervisor.py, src/owlbear/core/retrospective_hook.py, src/owlbear/bootstrap/__init__.py, and the related test files.

- coverage: src/owlbear/core/hook_worker_supervisor.py 100%, src/owlbear/core/retrospective_hook.py 84%, src/owlbear/bootstrap/__init__.py 34%; the uncovered lines are outside the reviewed hook-supervision seam and are not the rejection basis.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |

|---------|-------------|---------------------------|---------|

| HookWorkerSupervisor type + owned _background_tasks/_bg_semaphore + default concurrency | TestFromAC_HookWorkerSupervisorOwnership at tests/test_hook_worker_supervisor.py:23-44 | Yes: type, ownership, and default assertions at :26, :30, :34, :39, :44 | COVERED |

| schedule() tracking/semaphore contract plus shutdown cancellation semantics | TestFromAC_HookWorkerSupervisorSchedule, TestFromAC_HookWorkerSupervisorSemaphore, and TestFromAC_HookWorkerSupervisorShutdown at tests/test_hook_worker_supervisor.py:54-327 | Yes: removing strong refs, done-callback cleanup, semaphore gating, task cancellation, or post-shutdown no-op behavior breaks tests at :58, :78, :154, :187, :213, :239, :259, :274, :297, :304, :327 | COVERED |

| RetrospectiveHook supervisor handoff preserves success/rejection/priority gates and cancel seam | TestFromAC_RetrospectiveHookSupervisorSeam at tests/test_retrospective_hook.py:1070-1168 | Yes: tests at :1093, :1111, :1126, :1148, :1164 fail if the handoff or gating drifts | COVERED |

| Bootstrap creates one HookWorkerSupervisor when ingest is available and appends shutdown cleanup | TestFromAC_BootstrapHookWorkerSupervisorWiring at tests/test_bootstrap.py:3134-3215 | Yes: tests at :3143, :3168, :3189, :3214 fail if wiring or cleanup registration drifts | COVERED |

#### Security Review

- No secrets, injection paths, unsafe deserialization, path traversal, or log leakage issues found in the reviewed seam.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |

|---------------|-------------|------------|

| tests/test_hook_worker_supervisor.py TestFromAC classes from 9b90e6b | One strengthening addition after the original RED commit: test_shutdown_signal_prevents_new_schedules at :327 | STRENGTHENED |

| tests/test_retrospective_hook.py TestFromAC_RetrospectiveHookSupervisorSeam | Only signature reflow; unrelated #870 tests were added outside the class | PRESERVED |

| tests/test_bootstrap.py TestFromAC_BootstrapHookWorkerSupervisorWiring | Only signature reflow/import movement; unrelated #870 tests were added later outside the class | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |

|-----------|--------|----------|

| Assertion specificity | STRONG | Tests assert exact task-set sizes, overlap/non-overlap ordering, cleanup timing, call counts, and handler registration. |

| Negative/error paths | ADEQUATE | Failure outcome, trivial-task gate, rejection gate, cancellation, empty shutdown, and ingest-unavailable wiring are covered. |

| Mutation reasoning | STRONG | Removing semaphore gating, strong refs, done-callback cleanup, shutdown guard, or supervisor handoff would fail named tests above. |

| Test independence | STRONG | The classes use isolated asyncio.Event/AsyncMock state with no shared mutable globals. |

| Descriptive names | STRONG | Method names map directly to the required behavior. |

#### Data Safety

- No data-integrity or concurrency-safety defects found beyond the intended tracked-task/semaphore model.

#### Implementation-Aware Test Gaps

- No significant untested behavioral paths found in the reviewed seam. The task-tracking lifecycle, shutdown behavior, RetrospectiveHook gating/handoff, and bootstrap cleanup registration are all exercised.

### Pass 2 - INFORMATIONAL

- RetrospectiveHook module text still mentions bare asyncio.create_task in its top docstring; runtime behavior now prefers HookWorkerSupervisor when wired. This is documentation drift only.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |

|---------|----------|-------------|--------|

| Add HookWorkerSupervisor with _background_tasks and _bg_semaphore | src/owlbear/core/hook_worker_supervisor.py:32-35 | TestFromAC_HookWorkerSupervisorOwnership | PASS |

| __init__(bg_concurrency: int = 1) defaults to one worker | src/owlbear/core/hook_worker_supervisor.py:32-35 | tests/test_hook_worker_supervisor.py:39 | PASS |

| schedule() runs under semaphore, tracks tasks strongly, discards on completion, and uses per-worker task cancellation via shutdown per the architect note at kanban/tasks/953-add-tracked-background-worker-supervision-for-hook.md:93 | src/owlbear/core/hook_worker_supervisor.py:37-55 and :65-69 | TestFromAC_HookWorkerSupervisorSchedule / Semaphore / Shutdown | PASS |

| shutdown() sets shutdown signal, cancels unfinished tasks, awaits drain, and returns empty | src/owlbear/core/hook_worker_supervisor.py:58-69 | TestFromAC_HookWorkerSupervisorShutdown at tests/test_hook_worker_supervisor.py:239-327 | PASS |

| RetrospectiveHook uses injected supervisor and preserves existing gates/cancel composition | src/owlbear/core/retrospective_hook.py:149-166 and :228 | TestFromAC_RetrospectiveHookSupervisorSeam | PASS |

| Bootstrap creates one supervisor when ingest_pipeline is available, passes it into RetrospectiveHook, and appends cleanup | src/owlbear/bootstrap/__init__.py:124-132 | TestFromAC_BootstrapHookWorkerSupervisorWiring | PASS |

| Do not change HookRegistry.emit semantics, daemon loop structure, or move preflight behind a different seam | Task-specific builder commit f8e6808 touches only bootstrap/__init__.py, core/hook_worker_supervisor.py, and core/retrospective_hook.py;_count_rejections/_get_priority still run before supervisor handoff at retrospective_hook.py:149-164 | Source review | PASS |

| All tests from #966 pass | Scoped pytest command above -> 27 passed | Scoped pytest suite | PASS |

| uv run ruff check is clean on all touched files | Scoped ruff command above -> All checks passed | Scoped ruff run | PASS |

### Verdict: PASS

### Action Taken

- kanban\\kanban-md.exe edit 953 --status docs --release

[[2026-03-24]] Tue 03:12

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |

|---|-------|----------|--------|----------|

| 1 | .github/copilot-instructions.md | Yes | Pass | HookWorkerSupervisor already documented in Runtime row (wired in #966/#953, replaces bare create_task) - no change needed |

| 2 | Docstrings complete | Yes | Updated | Fixed module docstring and __call__ docstring in src/owlbear/core/retrospective_hook.py to reflect supervisor handoff; hook_worker_supervisor.py docstrings were already accurate |

| 3 | docs/sources/overview.md | No | N/A | Pattern mirrors internal GraphEnricher; sources used are Python official docs (asyncio/Semaphore/Event) and aiohttp graceful-shutdown pattern - no third-party code copied |

| 4 | README.md | No | N/A | No CLI commands added or changed |

| 5 | Research doc linked | Yes | Pass | docs/research/hook-triggered-background-worker-supervision.md exists and is linked in task body |

| 6 | No docs impact items | N/A | N/A | Items 1-5 covered above |

### Files Updated

- src/owlbear/core/retrospective_hook.py (module docstring + __call__ docstring)

[[2026-03-24]] Tue 03:47

## Audit

### AC Verification

| AC Line | Evidence | Status |

|---------|----------|--------|

| HookWorkerSupervisor with _background_tasks/_bg_semaphore | src/owlbear/core/hook_worker_supervisor.py:33-34 | PASS |

| __init__(bg_concurrency: int = 1) | src/owlbear/core/hook_worker_supervisor.py:32 | PASS |

| schedule() semaphore/tracking/discard-on-done | src/owlbear/core/hook_worker_supervisor.py:38-60 | PASS |

| shutdown() sets signal, cancels, awaits drain | src/owlbear/core/hook_worker_supervisor.py:62-75 | PASS |

| RetrospectiveHook accepts injected supervisor | src/owlbear/core/retrospective_hook.py:121 (supervisor param), :166 (handoff docstring) | PASS |

| Bootstrap wires supervisor when ingest available, appends shutdown to cleanup | src/owlbear/bootstrap/__init__.py:123-139 | PASS |

| No HookRegistry.emit/daemon loop changes | git log confirms no changes to hooks.py or daemon.py for #953 | PASS |

| All #966 tests pass | Scoped pytest: 27 passed | PASS |

| Ruff clean | uv run ruff check on all 3 touched src files -> All checks passed | PASS |

### Test Results

- pytest full suite: 4103 passed, 98 failed (all unrelated: #921/#925 RED, cli_board_fixtures ModuleNotFoundError, #809 daemon fallback, exception_hierarchy, hook_payloads exports, httpx timeouts, integration_e2e imports, intent_routing AgentRegistry, knowledge exports/expansion, lazy_singleton_settings, model_param_required)

- pytest scoped: 27 passed, 2 warnings

- ruff: All checks passed on src/owlbear/core/hook_worker_supervisor.py, src/owlbear/core/retrospective_hook.py, src/owlbear/bootstrap/__init__.py

### Architect Quality

- AC specificity: Excellent. Exact module paths, field types, defaults, lifecycle guarantees, and negative scope boundaries.

- Edge case coverage: Complete. TaskGroup rejection documented, done-callback discard, shutdown guard, #964 scope split.

- Design direction: GraphEnricher precedent and BootstrapResult.cleanup identified correctly. Builder needed zero improvisation.

- AC quality score: 5/5

### Upstream Commits

- ff378f1 feat: stabilize hook worker supervision seam (#966, builder) - implementation
