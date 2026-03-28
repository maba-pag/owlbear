---
id: 73
title: 'Test: ProcessSupervisor for ACP subprocess lifecycle'
status: in-progress
priority: needed
created: 2026-03-26T20:23:24.4133263+01:00
updated: 2026-03-27T03:32:01.948802+01:00
tags:
    - phase-1
    - scope:orchestrator
    - type:test
    - test
class: standard
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
