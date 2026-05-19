---
id: 1003
title: 'Test: Track LLM usage in daemon poll_tick builder dispatch'
status: archived
priority: nice-to-have
created: 2026-03-25 13:52:00.368272+01:00
updated: 2026-03-25 14:31:32.551114+01:00
tags:
- scope:core
- phase-3
- test
blocked: true
block_reason: 'Redundant: all 7 ACs already covered by 34 tests in tests/test_845_daemon_usage_tracking.py
  (test-writer output for #845 in-progress)'
class: standard
archival_reason: completed
archival_refs: []
---

**AC (RED phase — all tests must fail before implementation):**

1. Test that poll_tick passes tracker/model/provider to_run_builder_with_context in the retry-dispatch path (mock builder, assert record_agent_usage called with operation='builder_dispatch' and session_id='background:builder_dispatch' after awaiting result).
2. Test that poll_tick passes tracker/model/provider to_run_builder_with_context in the fresh-dispatch path (same assertions as AC1 but for new-task dispatch).
3. Test that _run_builder_with_context calls record_agent_usage after the normal (kwargs-accepted) code path, with the correct tracker/model/provider/operation/session_id arguments.
4. Test that _run_builder_with_context calls record_agent_usage after the TypeError-fallback code path (legacy builder that rejects kwargs), with the same argument contract.
5. Test that record_agent_usage failures (exceptions) do not propagate from _run_builder_with_context — builder result is still returned successfully.
6. Test that when tracker is None, no recording is attempted (no-op path).
7. Test that poll_loop threads tracker and provider from settings to poll_tick.

**Pattern:** Follow existing daemon test patterns in tests/ (search for poll_tick,_run_builder_with_context test fixtures).

[[2026-03-25]] Wed 14:11

## Research

See docs/research/daemon-usage-tracking-tests.md for full validation.

All 7 ACs validated against existing daemon test patterns (test_daemon_coverage_gaps.py, test_usage_wiring.py). Each test maps to proven mock patterns. Clean RED failures expected:_run_builder_with_context and poll_tick lack tracker/model/provider params until #845 implements them.

Recommended test file: tests/test_daemon_coverage_gaps.py, new class TestFromAC_1003_UsageTrackingDispatch.

Added depends_on #1003 to #845 frontmatter for TDD ordering.

[[2026-03-25]] Wed 14:31

## Architecture Review

**Verdict:** Block (redundant)

### AC Assessment

All 7 ACs fully covered by 34 tests in tests/test_845_daemon_usage_tracking.py (test-writer output for #845).

### Architecture Notes

Task #845 is already in-progress with Test-Writer Notes. All 7 ACs of #1003 map 1:1 to existing tests. This task was created after researcher validated testability, but #845 independently progressed through the test-writer phase. Redundant.

### Changes Made

- Blocked to ideation as fully redundant with #845 test suite
