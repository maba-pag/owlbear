# HeartbeatRunner Test Coverage — Gap Analysis

> **Owning task:** #638 — Tests for HeartbeatRunner
> **Date:** 2026-03-09 **Status:** Complete

## 1. Context and Question

Task #638 requests a TDD test suite for HeartbeatRunner with 9 AC items. During research, `tests/test_heartbeat.py` was discovered already existing (~395 lines). Question: What is the actual gap? Is #638 nearly done or does it need rework?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| tests/test_heartbeat.py (codebase) | `tests/test_heartbeat.py` | .95 |
| src/owlbear/heartbeat.py (codebase) | `src/owlbear/heartbeat.py` | .95 |
| src/owlbear/daemon.py lines 630-643 (codebase) | `src/owlbear/daemon.py` | .90 |
| Python unittest.mock docs | <https://docs.python.org/3/library/unittest.mock.html> | .75 |
| HeartbeatRunner research doc (OwlBear) | `docs/heartbeat-runner-research.md` | .85 |
| PydanticAI test patterns | <https://github.com/pydantic/pydantic-ai/blob/main/tests/test_agent.py> | .60 |

## 3. Analysis — AC Coverage Matrix

| # | AC Item | Test exists? | Location | Notes |
|---|---------|-------------|----------|-------|
| 1 | `test_heartbeat_tick_calls_agent_turn` | **Yes** | `TestHeartbeatTick` L62-84 | Writes HEARTBEAT.md, asserts `agent.turn` called with content |
| 2 | `test_heartbeat_ok_suppresses_channel_send` | **Yes** | `TestHeartbeatOkSuppression` L92-117 | Asserts `channel.send.assert_not_called()` |
| 3 | `test_heartbeat_non_ok_sends_to_channel` | **Yes** | `TestHeartbeatNonOk` L124-151 | Asserts `channel.send` called with findings |
| 4 | `test_heartbeat_active_hours_skip` | **Yes** | `TestActiveHoursSkip` L158-185 | Patches `_utc_hour`, hour=3 outside (8,22) |
| 5 | `test_heartbeat_active_hours_wraparound` | **Yes** | `TestActiveHoursWraparound` L192-257 | 2 async + 2 unit tests for `_is_active_hour` |
| 6 | `test_heartbeat_missing_file_skips` | **Yes** | `TestMissingFile` L264-283 | Asserts no crash, `agent.turn.assert_not_called()` |
| 7 | `test_heartbeat_shutdown_mid_sleep` | **Yes** | `TestShutdownMidSleep` L290-314 | interval=3600, `asyncio.wait_for` with 2s timeout |
| 8 | `test_heartbeat_agent_exception_continues` | **Yes** | `TestAgentException` L321-352 | `side_effect=[RuntimeError, "OK"]`, asserts ≥2 calls + log |
| 9 | `test_heartbeat_disabled_config_skips_launch` | **No** | — | Daemon integration test — not in test_heartbeat.py |

**Result: 8/9 AC items already implemented.** The existing test file covers all HeartbeatRunner unit tests.

## 4. Gap: Disabled-Config Guard

The missing test (`test_heartbeat_disabled_config_skips_launch`) verifies daemon-level behavior: when `heartbeat_enabled=False`, `run_daemon()` should NOT create a HeartbeatRunner task.

**Where it belongs:** `tests/test_daemon.py` — this tests `run_daemon()` conditional logic (lines 632-643 in daemon.py), not HeartbeatRunner itself.

**Implementation approach (.85 confidence):**

- Patch `OwlBearSettings` with `heartbeat_enabled=False` (already the default)
- Patch `owlbear.daemon.HeartbeatRunner` to spy on construction
- Run `run_daemon()` briefly with shutdown after first channel_loop iteration
- Assert `HeartbeatRunner` was never instantiated / `asyncio.create_task` not called for heartbeat

**Risk:** `run_daemon()` has many dependencies (agent, channel, config_dir, sentinel, signals). The existing `test_daemon.py` already mocks these via `MockChannel` and `_run()` helpers — follow the same pattern.

## 5. Recommendation (.90 confidence)

**Task #638 is 89% complete.** The remaining work is a single daemon-integration test (~20-30 LOC). Recommended actions:

1. **Rescope #638** — Update AC to reflect that 8/9 items are done; the remaining item is a daemon-integration test in `test_daemon.py`
2. **Implement the missing test** — Add `test_heartbeat_disabled_config_skips_launch` to `test_daemon.py` following existing `MockChannel`/`_run()` patterns
3. **Run full suite** — Verify existing 8 tests pass + new test passes

## 6. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add test_heartbeat_disabled_config_skips_launch to test_daemon.py" --priority needed --tags "scope:core,test,agent" --body "Add single test to tests/test_daemon.py verifying run_daemon() does NOT create HeartbeatRunner task when heartbeat_enabled=False. Follow existing MockChannel/_run() patterns. See docs/heartbeat-tests-research.md for details.^n^nAC:^n- [ ] test_heartbeat_disabled_config_skips_launch exists in test_daemon.py^n- [ ] Patches HeartbeatRunner import to spy on construction^n- [ ] Asserts HeartbeatRunner never instantiated when heartbeat_enabled=False^n- [ ] pytest passes, ruff clean"
```

Alternatively, if preferred, edit #638 itself to mark 8/9 AC items done and move it to `todo` with only the daemon test remaining.
