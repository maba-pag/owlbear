---
id: 141
title: 'Test: Voice process manager'
status: review
priority: nice-to-have
created: 2026-03-29T15:39:36.7418317+02:00
updated: 2026-03-31T07:27:40.7520898+02:00
tags:
    - phase-3
    - ' scope:voice'
    - ' type:test'
    - ' test'
depends_on:
    - 61
class: standard
---

## Objective
Write failing tests for VoiceProcessManager (#62) before implementation.

## Acceptance Criteria

### Test file
- [ ] tests/test_voice_process_manager.py

### Test categories (all tests must FAIL on current HEAD)

**Spawn (TestFromAC_Spawn):**
- [ ] Spawns with stdin=PIPE, stdout=PIPE, stderr=None
- [ ] Verifies proc.stdin and proc.stdout are not None
- [ ] Starts background read loop task after spawn

**Read loop (TestFromAC_ReadLoop):**
- [ ] Parses valid NDJSON line into VoiceOutMessage via out_adapter
- [ ] Pushes parsed messages to internal queue
- [ ] Malformed JSON line: logs warning, skips (does not crash)
- [ ] EOF on stdout: detects process crash

**Write / send (TestFromAC_Send):**
- [ ] Serializes VoiceInMessage via model_dump_json() + newline
- [ ] Writes to stdin and drains
- [ ] BrokenPipeError on write: treats as crash, triggers restart

**Init handshake (TestFromAC_InitHandshake):**
- [ ] Waits for StatusMsg(state=ready) within init_timeout
- [ ] Timeout raises VoiceInitTimeout
- [ ] Non-ready status messages before ready are queued normally

**Shutdown 6-phase (TestFromAC_Shutdown):**
- [ ] Phase 1: sends ShutdownMsg to stdin
- [ ] Phase 2: closes stdin
- [ ] Phase 3: waits with shutdown_timeout (5s default)
- [ ] Phase 4: terminates process
- [ ] Phase 5: waits with kill_timeout (2s default)
- [ ] Phase 6: kills process
- [ ] Suppresses ProcessLookupError during phases 4-6
- [ ] Handles BrokenPipeError in phase 1 gracefully (skip to phase 2)

**Restart budget (TestFromAC_RestartBudget):**
- [ ] Raises VoiceRestartBudgetExhausted after max_restarts
- [ ] Restart counter resets after successful init handshake

**Context manager (TestFromAC_ContextManager):**
- [ ] __aenter__ spawns process and completes init handshake
- [ ] __aexit__ calls shutdown

**is_alive (TestFromAC_IsAlive):**
- [ ] True when process running
- [ ] False when process exited

**receive (TestFromAC_Receive):**
- [ ] Returns next VoiceOutMessage from internal queue

### Patterns to follow
- tests/test_process_supervisor.py for mock subprocess patterns
- Use unittest.mock.AsyncMock for async subprocess operations
- Import from owlbear.voice.process (VoiceProcessManager, VoiceInitTimeout, VoiceRestartBudgetExhausted)

## Context
TDD companion for #62. See docs/research/voice-process-manager.md.

[[2026-03-29]] Sun 16:01
## Test-Writer Notes
- Test file: tests/test_voice_process_manager.py
- Classes: TestFromAC_Exceptions, TestFromAC_Spawn, TestFromAC_ReadLoop, TestFromAC_Send, TestFromAC_InitHandshake, TestFromAC_Shutdown, TestFromAC_RestartBudget, TestFromAC_ContextManager, TestFromAC_IsAlive, TestFromAC_Receive
- Tests per category: happy 19, edge 8, error 5, boundary 5
- Total: 37 tests, all FAIL (ImportError: owlbear.voice.process does not exist)
- ruff: clean
- Commit: 1c4a961
- AC coverage: all 27 AC lines mapped (spawn x3, read loop x4, send x3, init x3, shutdown x11, restart x2, ctx x2, is_alive x3, receive x1, exceptions x3)

[[2026-03-29]] Sun 16:02
## Test-Writer Notes
- Test file: tests/test_voice_process_manager.py
- Classes: TestFromAC_Exceptions, TestFromAC_Spawn, TestFromAC_ReadLoop, TestFromAC_Send, TestFromAC_InitHandshake, TestFromAC_Shutdown, TestFromAC_RestartBudget, TestFromAC_ContextManager, TestFromAC_IsAlive, TestFromAC_Receive
- Tests per category: happy 14, edge 10, error 8, boundary 5
- Total: 37 tests, all FAIL (ImportError: owlbear.voice.process does not exist)
- ruff: clean
- AC coverage:
  Spawn stdin/stdout/stderr pipes: test_spawns_with_stdin/stdout/stderr_pipe
  Proc stdin/stdout None verification: test_raises_when_proc_stdin/stdout_is_none
  Background read loop task: (part of ReadLoop class)
  Valid NDJSON parsing: test_valid_ndjson_pushed_to_receive_queue
  Push to queue: test_valid_ndjson_pushed_to_receive_queue
  Malformed JSON warning+skip: test_malformed_json_does_not_crash_manager, test_malformed_json_logs_warning
  EOF crash detection: test_eof_is_treated_as_process_crash
  Serialize + newline: test_send_serializes_with_trailing_newline
  Write + drain: test_send_drains_stdin_after_write
  BrokenPipe on write: test_send_broken_pipe_triggers_restart
  Init handshake completes: test_aenter_completes_when_ready_received
  VoiceInitTimeout: test_aenter_raises_voice_init_timeout
  Non-ready queued: test_non_ready_messages_queued_during_handshake
  All 6 shutdown phases: test_phase1..6 (11 tests)
  RestartBudget exhaustion: test_raises_budget_exhausted_after_max_restarts
  Counter reset: test_restart_counter_resets_after_successful_init
  Context manager protocol: test_aenter_returns_self, test_aexit_calls_shutdown
  is_alive true/false/pre-entry: 3 tests
  receive: test_receive_returns_voice_out_message
- Note: file was committed by prior agent run; task advanced now

[[2026-03-30]] Mon 18:00
## Builder Notes

**Result:** 35/37 tests pass. Ruff clean. 2 tests blocked due to test-level issues.

**Implementation:** Full VoiceProcessManager with exceptions (VoiceProcessError, VoiceInitTimeout, VoiceRestartBudgetExhausted), async context manager, send/receive NDJSON, 6-phase shutdown, init handshake, restart budget with counter reset, is_alive property. Extracted _shutdown_phases_2_to_6 to satisfy ruff C901. Added read loop task cancellation on restart to prevent duplicate tasks.

**Passing (35):** Exceptions(3), Spawn(5), ReadLoop(4), Send(3), InitHandshake(3), Shutdown(10/11), RestartBudget(1/2), ContextManager(2), IsAlive(3), Receive(1).

**Blocked tests (2):**

1. test_shutdown_cancels_read_loop_task: Uses patch.object(asyncio.Task, 'cancel', ...) which fails on CPython 3.12 with TypeError: cannot set 'cancel' attribute of immutable type '_asyncio.Task'. Task is a C extension type since CPython 3.12 and its methods cannot be monkey-patched. Test needs rewrite using a different verification approach.

2. test_raises_budget_exhausted_after_max_restarts: Contradicts test_restart_counter_resets_after_successful_init. Counter reset on successful handshake (required by reset test) prevents budget exhaustion (required by budget test). With reset: counter oscillates 0-to-1 each crash/restart cycle and never reaches max_restarts. Without reset: budget exhausts but reset test fails. Mathematical proof: no single counter scheme satisfies both tests simultaneously. Test-writer needs to reconcile the AC for these two behaviors.

[[2026-03-31]] Tue 07:27
## Builder Notes (2026-03-31, second pass)
- Files changed: None - implementation already committed by prior builder run
- Tests: 37 passed (previously 35/37; 2 blocked tests fixed by test-writer rewrite)
- Coverage: 96% on owlbear/voice/process.py (148 stmts, 6 uncovered: guards/dead branches)
- Lint: ruff clean on both process.py and test file
- Evidence: 37 passed in 0.76s, all TestFromAC classes green
- Fixes applied: None - tests pass against existing committed implementation
