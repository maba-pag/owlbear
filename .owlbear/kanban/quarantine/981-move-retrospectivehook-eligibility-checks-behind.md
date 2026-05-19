---
id: 981
title: Move RetrospectiveHook eligibility checks behind supervisor handoff
status: archived
priority: needed
created: 2026-03-24T03:44:34.4634853+01:00
updated: 2026-03-24T17:36:32.1542954+01:00
started: 2026-03-24T17:35:29.6482824+01:00
completed: 2026-03-24T17:35:29.6482824+01:00
tags:
    - agent
    - daemon
    - hooks
    - scope:core
    - type:build
depends_on:
    - 953
    - 989
class: standard
---

AC:

1. `RetrospectiveHook.__call__` must not call `_count_rejections` or `_get_priority` on the awaited hook path â€” neither supervisor nor `create_task` fallback path may invoke them before returning.
2. Eligibility checks (`_count_rejections`, `_get_priority`) and the retrospective run (`_run_retrospective`) must all execute inside the supervisor-scheduled background task (or `asyncio.create_task` fallback). Ineligible tasks (zero rejections + priority < needed) are still filtered and skipped inside the background task.
3. Existing behavior preserved: success-only gating, empty `task_id` guard, `_LazyCoroutine` wrapper for supervisor path, cancellation signal composition, supervisor `shutdown()` integration.
4. Files: `src/owlbear/core/retrospective_hook.py`, `tests/test_retrospective_hook.py`.

See docs/research/non-blocking-retrospective-hook-handoff.md for analysis.
Merged from #964 (deleted â€” duplicate).

[[2026-03-24]] Tue 04:28

## Architecture Review

**Verdict:** APPROVED (merged from #964)

### AC Assessment

| AC Line | Assessment | Action |

|---------|------------|--------|

| AC1: **call** must not call _count_rejections/_get_priority on awaited path | Testable pass/fail via mock/patch assertions | Kept |

| AC2: Eligibility + retro run inside bg task; ineligible filtered there | Testable: await scheduled coroutine, assert calls + early-return | Kept |

| AC3: Preserve existing gates, LazyCoroutine, cancel, supervisor shutdown | Regression-testable against existing TestFromAC_RetrospectiveHookSupervisorSeam (43 tests) | Kept |

| AC4: File scope | src/owlbear/core/retrospective_hook.py + tests/test_retrospective_hook.py | Kept |

### Architecture Notes

- Single domain: core/hooks. No layering violation.

- Pattern: extends existing _LazyCoroutine + supervisor.schedule() seam from #953.

- Current blocking calls: _count_rejections (sync file I/O activity.jsonl L200) and _get_priority (subprocess.run kanban-md L231) both called inline in **call** before supervisor.schedule().

- Fix: wrap eligibility + _run_retrospective in a single coroutine scheduled via supervisor (or create_task fallback). **call** becomes instant.

- Risk: 100ms event-loop block inside bg task from sync I/O. Acceptable for single-conversation daemon per research.

- Security surface: no new system boundaries introduced.

### Changes Made

- Deleted #964 (duplicate — same concern as #981 with vaguer AC)

- Refined #981 AC to 4 testable lines

- Created #989 (Test: RetrospectiveHook non-blocking eligibility handoff) at todo

- Added #989 as dependency on #981

### Dependencies

- Verified: #953 (HookWorkerSupervisor) — archived

- Added: #989 (TDD test task) — todo

[[2026-03-24]] Tue 14:53

## Test-Writer Notes

- Test file: tests/test_retrospective_hook.py
- Classes: TestFromAC_981_StrictEligibilityDeferral (new, 3 tests)
- Note: TestFromAC_981_NonBlockingEligibilityHandoff (12 tests) and TestFromAC_RetrospectiveHookSupervisorSeam (5 tests) already exist from prior tasks and cover AC1 (monkeypatch path) / AC2 / AC3.
- New class fills the gap: AC1 strict interpretation with default helpers and existing activity.jsonl.
- Tests per category: boundary 3 (default-helpers fast-path boundary)
- Total new: 3 tests, all FAIL (AssertionError) on HEAD
- ruff: clean
- Commit: 4b885c0

[[2026-03-24]] Tue 15:40

## Builder Notes

- Files changed: none (temporary strict-deferral edit was reverted after conflict validation).
- Tests: baseline full-file run with current behavior shows 55 passed and 3 failed in TestFromAC_981_StrictEligibilityDeferral.
- Tests: strict-deferral validation run showed 3 passed in TestFromAC_981_StrictEligibilityDeferral and 1 failed in TestFromAC_RetrospectiveHookSupervisorSeam::test_trivial_task_skips_supervisor_schedule.
- Lint: not rerun (no net source change).
- Evidence: strict deferral requires scheduling in ineligible existing-log cases, but legacy seam test still requires no scheduling for trivial supervisor path.
- Fixes applied: attempted removal of inline eligibility fast-path in RetrospectiveHook.**call**; reverted because existing TestFromAC contracts are mutually incompatible.
- BLOCK reason: AC for #981 and legacy seam test disagree on whether trivial tasks should be scheduled when supervisor is present.
- AC suggestion: align contracts by updating TestFromAC_RetrospectiveHookSupervisorSeam::test_trivial_task_skips_supervisor_schedule to expect schedule plus background filtering, or revise #981 AC to explicitly preserve the legacy inline trivial-skip fast-path.

[[2026-03-24]] Tue 16:02

## Test-Writer Notes (retry)

- Retry reason: builder BLOCK. TestFromAC_981_StrictEligibilityDeferral and TestFromAC_RetrospectiveHookSupervisorSeam::test_trivial_task_skips_supervisor_schedule had mutually incompatible contracts.
- Action: updated test_trivial_task_skips_supervisor_schedule to expect the new AC1/AC2 contract: trivial task reaches supervisor.schedule, background coro filters it.
- Test file: tests/test_retrospective_hook.py
- Classes: TestFromAC_981_StrictEligibilityDeferral (3 tests unchanged), TestFromAC_RetrospectiveHookSupervisorSeam (1 test updated)
- Total failing: 4 tests, all FAIL with AssertionError on HEAD
- Preserved: 54 tests PASS
- ruff: clean
- Commit: b0dce19
- AC1 covered by: test_trivial_task_skips_supervisor_schedule, test_ineligible_task_..._reaches_supervisor, test_ineligible_task_..._reaches_create_task
- AC2 covered by: test_background_task_filters_ineligible_when_activity_log_present, test_trivial_task_skips_supervisor_schedule (awaits bg coro, asserts_run_retrospective not called)
- AC3 covered by: existing PASSING tests (failure gate, rejection gate, cancel seam)

[[2026-03-24]] Tue 16:27

## Builder Notes

- Files changed: src/owlbear/core/retrospective_hook.py
- Tests: RED check confirmed 4 failing TestFromAC cases before the fix; GREEN check showed those 4 now pass; full tests/test_retrospective_hook.py run: 58 passed, 2 warnings.
- Coverage: src/owlbear/core/retrospective_hook.py at 94 percent in the scoped bare coverage run.
- Lint: ruff clean for src/owlbear/core/retrospective_hook.py and tests/test_retrospective_hook.py.
- Evidence: uv run pytest tests/test_retrospective_hook.py::TestFromAC_981_StrictEligibilityDeferral tests/test_retrospective_hook.py::TestFromAC_RetrospectiveHookSupervisorSeam::test_trivial_task_skips_supervisor_schedule -q --tb=short first run had 4 failed, rerun had 4 passed; uv run pytest tests/test_retrospective_hook.py -q --tb=short had 58 passed; uv run pytest tests/test_retrospective_hook.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short reported 94 percent for retrospective_hook.py; uv run ruff check src/owlbear/core/retrospective_hook.py tests/test_retrospective_hook.py reported all checks passed.
- Fixes applied: removed the inline default-helper eligibility fast path from RetrospectiveHook.**call** so successful events always schedule background work, and eligibility filtering remains inside _run_retrospective_if_eligible.
- Commit: 0d8a5be

[[2026-03-24]] Tue 16:27

## Builder Notes

- Files changed: src/owlbear/core/retrospective_hook.py
- Tests: targeted RED run had 4 failures; targeted GREEN rerun had 4 passes; full tests/test_retrospective_hook.py run had 58 passes.
- Coverage: src/owlbear/core/retrospective_hook.py reported 94 percent in the scoped run.
- Lint: ruff check passed for src/owlbear/core/retrospective_hook.py and tests/test_retrospective_hook.py.
- Fixes applied: removed the inline default helper eligibility gate from RetrospectiveHook.**call**, so successful events always schedule background work and eligibility filtering remains in _run_retrospective_if_eligible.
- Commit: 0d8a5be

[[2026-03-24]] Tue 16:28

## Builder Notes

- Commit: 0d8a5be

[[2026-03-24]] Tue 16:29

- Files changed: src/owlbear/core/retrospective_hook.py
- Tests: targeted RED run had 4 failures; targeted GREEN rerun had 4 passes; full tests/test_retrospective_hook.py run had 58 passes.
- Coverage: src/owlbear/core/retrospective_hook.py reported 94 percent in the scoped run.
- Lint: ruff check passed for src/owlbear/core/retrospective_hook.py and tests/test_retrospective_hook.py.
- Evidence: targeted TestFromAC run first failed and then passed after the fix; full retrospective_hook test file is green.
- Fixes applied: removed the inline default helper eligibility gate from RetrospectiveHook.**call**, so successful events always schedule background work and eligibility filtering remains in _run_retrospective_if_eligible.

[[2026-03-24]] Tue 16:49

## Review Evidence

### Findings

- No blocking findings.

### Test Results

- Targeted task tests passed: 4 passed, 2 warnings.
- Full retrospective hook file passed: 58 passed, 2 warnings.
- Preserved-behavior regression set passed: 9 passed, 2 warnings across cancellation, linked-cancel, empty-task-id, and bootstrap supervisor-wiring tests.
- Warnings were the existing optional dependency skips from tests/conftest.py:58 about missing qdrant_client.

### Lint Results

- Ruff passed for src/owlbear/core/retrospective_hook.py and tests/test_retrospective_hook.py.

### Coverage

- Scoped coverage reported src/owlbear/core/retrospective_hook.py at 94 percent.

### Pass 1 Critical Review

- Test-writer AC coverage is strong.
- AC1 is covered by tests/test_retrospective_hook.py:1244, 1263, 1362, 1385, 1495, 1523, 1597, and 1631. These fail if **call** touches _count_rejections or _get_priority inline, or if success outcomes fail to reach supervisor.schedule or asyncio.create_task.
- AC2 is covered by tests/test_retrospective_hook.py:1284, 1309, 1336, 1412, 1439, 1467, 1126, and 1664. These await the scheduled background work and fail if eligibility stays inline or if ineligible tasks reach _run_retrospective.
- AC3 is preserved by src/owlbear/core/retrospective_hook.py:61, 158, 187, 191, 195, 199, and 272, together with passing regression tests at tests/test_retrospective_hook.py:579, 742, 756, 942, 1014, 1093, 1111, 1126 and tests/test_bootstrap.py:3143, 3168. Success-only gating, empty task_id guard, LazyCoroutine scheduling, create_task fallback, linked cancel composition, and bootstrap supervisor shutdown wiring remain intact.
- AC4 matches the edited scope. The test file is unchanged since retry test-writer commit b0dce19, and post-retry history shows one source commit, 0d8a5be, touching src/owlbear/core/retrospective_hook.py.
- Security review found no issues in src/owlbear/core/retrospective_hook.py:187-202 and 272-280.
- Data-safety review found no new race, path, or persistence risks in the changed code path.
- Test integrity is preserved. tests/test_retrospective_hook.py is unchanged from b0dce19 to HEAD.
- Test quality ratings: assertion specificity STRONG, negative and error paths STRONG, mutation resistance STRONG, independence STRONG, descriptive names STRONG.
- Implementation-aware gap analysis found no significant untested branch in the reviewed change. The suite now covers supervisor and create_task paths, default-helper and monkeypatched-helper paths, existing-log and missing-log cases, and background filtering of ineligible tasks.

### AC Compliance

- AC1 PASS: **call** returns before inline eligibility work and still schedules background processing. Evidence: src/owlbear/core/retrospective_hook.py:195-200 and the passing tests at tests/test_retrospective_hook.py:1244, 1263, 1362, 1385, 1495, 1523, 1597, and 1631.
- AC2 PASS: eligibility checks and retrospective execution run in _run_retrospective_if_eligible. Evidence: src/owlbear/core/retrospective_hook.py:272-278 and the passing tests at tests/test_retrospective_hook.py:1284, 1309, 1336, 1412, 1439, 1467, 1126, and 1664.
- AC3 PASS: success-only gating and empty-task-id guard remain at src/owlbear/core/retrospective_hook.py:187 and 191; LazyCoroutine remains in use at lines 61, 195, and 199; linked cancel composition remains at line 158; bootstrap cleanup still appends supervisor shutdown in tests/test_bootstrap.py:3143 and avoids it when ingest is unavailable at line 3168.
- AC4 PASS: the implementation change is confined to src/owlbear/core/retrospective_hook.py, and the task test file remains preserved.

### Verdict

- PASS
- Confidence: .94

[[2026-03-24]] Tue 16:56

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Added note: RetrospectiveHook.**call** defers eligibility checks into background coroutine (wired in #981); commit b2b0598 |
| 2 | Docstrings complete | Yes | Pass | Module docstring, RetrospectiveHook class docstring, **call** docstring, _run_retrospective_if_eligible docstring all accurate and reflect new deferred-eligibility behavior |
| 3 | docs/sources/overview.md | No | N/A | No new external patterns introduced; #981 is a refactor. Section 'Non-Blocking Retrospective Hook Handoff (Task #964)' already covers all prior art. |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/non-blocking-retrospective-hook-handoff.md exists and is linked from task body |
| 6 | Scratch files | N/A | Pass | No docs/scratch/981-* files found |

### Files Updated

- .github/copilot-instructions.md (Runtime row — eligibility deferral note added)

### Scratch Files Cleaned

- None

[[2026-03-24]] Tue 17:36

## Audit

AC1 PASS: **call** schedules background work only. AC2 PASS: helpers run in background. AC3 PASS: regression tests pass. AC4 PASS: correct files.
Full suite: 4238 passed, 36 failed (pre-existing). Task scoped: 58 passed. Ruff clean.
Architect quality: 4/5. Confidence: .96. Action: archive.
