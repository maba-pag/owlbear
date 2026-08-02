---
id: 73
title: 'Test: ProcessSupervisor for ACP subprocess lifecycle'
status: archived
priority: medium
created: 2026-03-26 20:23:24.413326+01:00
updated: 2026-03-28 16:20:21.785354+01:00
started: 2026-03-28 16:20:21.462291+01:00
completed: 2026-03-28 16:20:21.462291+01:00
tags:
- phase-1
- scope:orchestrator
- type:test
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
RED phase tests for ProcessSupervisor (task #58).

## AC
- [ ] Test: __aenter__ spawns subprocess with stdin=PIPE, stdout=PIPE, stderr=None
- [ ] Test: __aenter__ raises FileNotFoundError when copilot binary not found via shutil.which
- [ ] Test: __aenter__ verifies proc.stdin and proc.stdout are not None after spawn
- [ ] Test: __aexit__ calls terminate, waits 5s, then kill if still alive
- [ ] Test: __aexit__ suppresses ProcessLookupError on cleanup
- [ ] Test: shutdown() performs same terminate/wait/kill sequence when called explicitly (not via __aexit__)
- [ ] Test: is_alive returns True when process running, False when exited
- [ ] Test: ensure_running returns (stdin, stdout) pipes when process alive
- [ ] Test: ensure_running respawns process when dead, returns new pipes
- [ ] Test: ensure_running raises ProcessRestartBudgetExhausted after 3 restarts
- [ ] Test: mark_healthy resets restart counter to 0
- [ ] Test: restart counter resets allow further restarts after mark_healthy
- [ ] All tests use mocked asyncio.create_subprocess_exec (no real process)

Precedes: #58. See docs/research/process-supervisor-acp.md SS3.7.

[[2026-03-26]] Thu 20:52
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| __aenter__ spawns with pipes | Verifiable: mock asserts PIPE args + stderr=None | Keep |
| __aenter__ FileNotFoundError | Verifiable: mock shutil.which returns None | Keep |
| __aenter__ verifies pipes not None | **Added**: covers #58 pipe verification AC | Added |
| __aexit__ terminate/wait/kill | Verifiable: mock process method call sequence | Keep |
| __aexit__ suppresses ProcessLookupError | Verifiable: mock raises, no propagation | Keep |
| shutdown() explicit call | **Added**: #58 exposes shutdown() as public API, must test independently from __aexit__ | Added |
| is_alive property | Verifiable: mock returncode | Keep |
| ensure_running returns pipes | Verifiable: assert tuple return | Keep |
| ensure_running respawns | Verifiable: kill process, call again, assert new spawn | Keep |
| Budget exhausted after 3 | Verifiable: 3 mock crashes, assert exception | Keep |
| mark_healthy resets counter | Verifiable: crash, mark, crash again, no exception | Keep |
| counter resets allow restarts | Verifiable: same as above with 3 more restarts | Keep |
| All mocked | Constraint: no real subprocess | Keep |

### Architecture Notes
- Follows v1 test conventions: _make_proc() helper, patch asyncio.create_subprocess_exec, TestFromAC_ class naming (see test_hook_worker_supervisor.py, test_board_context.py)
- Single domain: orchestrator process lifecycle tests
- Two AC items added: pipe verification test and explicit shutdown() test (both map to #58 AC items missing from original)
- Test file location: test-writer should place in tests/ root (v2 layout TBD; follows v1 flat tests/ convention until package structure is scaffolded)

### Changes Made
- Added AC: __aenter__ verifies proc.stdin and proc.stdout are not None (maps to #58 spawn AC)
- Added AC: shutdown() explicit call test (maps to #58 public API contract)

### Dependencies
- Verified: #58 depends_on #73 (already set)
- No new dependencies needed

[[2026-03-28]] Sat 14:54
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | RED-phase test task; no behavior, API, or convention change |
| 2 | Docstrings | No | N/A | Test file only; module docstring accurate (covers scope + notes impl absent) |
| 3 | docs/sources/overview.md | No | N/A | Patterns from internal v1 test files, not external sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research doc produced; task references pre-existing acp-client-library-decomposition.md |
| 6 | Scratch files | No | N/A | No docs/scratch/73-* files found |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-28]] Sat 16:20
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| __aenter__ spawns with stdin=PIPE, stdout=PIPE, stderr=None | 3 tests: test_spawns_with_stdin_pipe, _stdout_pipe, _stderr_none | PASS |
| __aenter__ raises FileNotFoundError when binary missing | test_raises_file_not_found_when_binary_missing | PASS |
| __aenter__ verifies proc.stdin/stdout not None | test_raises_when_proc_stdin_is_none, _stdout_is_none | PASS |
| __aexit__ terminate/wait/kill sequence | test_aexit_calls_terminate, _kills_if_not_terminated, _does_not_kill_clean | PASS |
| __aexit__ suppresses ProcessLookupError | test_aexit_suppresses_process_lookup_error_on_terminate, _on_kill | PASS |
| shutdown() explicit call | test_shutdown_explicit_calls_terminate, _kills_if_timeout, _suppresses_error | PASS |
| is_alive True/False | test_is_alive_true_when_running, _false_when_exited | PASS |
| ensure_running returns pipes | test_returns_stdin_stdout_tuple, _correct_stdin_and_stdout | PASS |
| ensure_running respawns dead | test_respawns_dead_process, _returns_new_pipes_after_respawn | PASS |
| Budget exhausted after 3 | test_raises_budget_exhausted_after_max_restarts | PASS |
| mark_healthy resets counter | test_mark_healthy_resets_restart_counter | PASS |
| counter reset allows restarts | test_counter_reset_allows_full_budget_after_mark_healthy | PASS |
| All mocked (no real process) | All tests use _patch_spawn (patches asyncio.create_subprocess_exec) | PASS |

### Test Results
- pytest: 23 passed, 0 failed, 3 warnings (coroutine never awaited in mock teardown)
- ruff: All checks passed

### AC Quality Score: 5/5
AC was specific, complete, each line maps 1:1 to concrete tests.

### Quality Notes
- No Review Evidence section in task body (reviewer protocol gap, non-blocking)
- 4 pre-existing failures in test_disable_model_invocation.py (unrelated, agents path)

### Confidence: .97
### Action: archive
