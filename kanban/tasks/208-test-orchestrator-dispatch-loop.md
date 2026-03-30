---
id: 208
title: 'Test: orchestrator dispatch loop'
status: todo
priority: needed
created: 2026-03-30T08:24:37.3734451+02:00
updated: 2026-03-30T08:24:41.9816185+02:00
started: 2026-03-30T08:24:41.9816185+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:test
    - test
depends_on:
    - 144
class: standard
---

TDD RED phase tests for #146 (orchestrator dispatch loop). Tests target waves.py and loop.py in packages/orchestrator/src/owlbear/orchestrator/.

## Test file: tests/test_orchestrator_loop.py

### Wave assembly tests (assemble_waves)

- [ ] Empty input returns empty list
- [ ] Single auditor entry returns one wave with one entry
- [ ] Auditor + light flex entries: auditor wave filled with light flex, priority order preserved
- [ ] Builder + heavy flex entries: builder wave filled with heavy flex
- [ ] Builder + light flex + heavy flex: light flex fills first, then heavy flex
- [ ] Multiple builders: one builder per wave (no two builders share a wave)
- [ ] Auditor + builder: never share a wave
- [ ] Overflow: remaining flex agents chunked into wave_size waves
- [ ] Periodic curator: cycle % 5 == 0 adds curator to last wave with free slot
- [ ] Periodic curator: all waves full, curator skipped
- [ ] Non-curator cycle: no curator added
- [ ] Drop rule: solo non-auditor wave dropped
- [ ] Drop rule exception: keep first non-auditor wave if dropping would eliminate all non-auditor waves
- [ ] Worked example from orchestration skill: 14-task input produces expected 4-wave output

### format_prompt tests

- [ ] Standard agent: returns "{prefix}: #{task_id}"
- [ ] With retry_hint: appends "\nRetry context: {hint}"
- [ ] Curator: returns prefix only (no task ID)
- [ ] All 9 agent types have correct prefix

### CycleResult and LoopState dataclass tests

- [ ] CycleResult is frozen (immutable)
- [ ] LoopState defaults: sequential_remaining=0, cycle=0, empty sets

### dispatch_entry tests (mocked AcpClient)

- [ ] Success: new_session + prompt called, returns True
- [ ] AcpClientError: returns False (no retry)
- [ ] TimeoutError: returns False (no retry)

### dispatch_wave tests (mocked AcpClient)

- [ ] Parallel mode: all entries dispatched via gather when sequential_remaining=0
- [ ] Sequential mode: entries dispatched one-by-one when sequential_remaining > 0, counter decremented
- [ ] Rate-limit detection: error message "rate-limited" sets sequential_remaining=3 and rate_limited=True
- [ ] Rate-limit detection: "rate_limited" and "rate limits" variants also detected
- [ ] Non-rate-limit error: retry once, second crash recorded as failure
- [ ] Mixed results: some succeed, some fail, CycleResult reflects both

### run_loop tests (mocked AcpClient + mocked planner)

- [ ] Empty plan: loop exits immediately (no dispatches)
- [ ] Single cycle: plan with entries dispatched, re-plan returns empty, loop exits
- [ ] Crash failures passed to planner in next cycle
- [ ] Stale_retried IDs tracked cross-cycle
- [ ] Cycle counter increments each iteration

### DispatchEntry retry_hint field test

- [ ] DispatchEntry with retry_hint="" — default backward compat
- [ ] DispatchEntry with retry_hint="some hint" — field populated
