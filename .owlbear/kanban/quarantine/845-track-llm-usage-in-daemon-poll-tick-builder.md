---
id: 845
title: Track LLM usage in daemon poll_tick builder dispatch
status: archived
priority: nice-to-have
created: 2026-03-17T17:41:27.1244234+01:00
updated: 2026-03-25T19:56:30.5836008+01:00
tags:
    - scope:core
    - phase-3
depends_on:
    - 844
    - 1003
class: standard
---

**Source:** docs/research/llm-cost-tracking.md S3
**Depends on:** #844 (needs operation field + helper)

**AC:**

1. Daemon poll_tick builder.run() calls record usage via UsageTracker.
2. Either: (a) pass a usage accumulator and record after task completion, or (b) restructure dispatch to use a lightweight wrapper that records.
3. Existing daemon tests pass.

[[2026-03-25]] Wed 13:01

## Research

See docs/research/daemon-usage-tracking.md for full findings.

### Recommendation (.85 confidence)

Option A: inline wrapper in _run_builder_with_context. Smallest diff, follows #844's established pattern.

### Refined AC

1. Add tracker and provider params to poll_tick and poll_loop
2. Thread from run_daemon using agent.tracker and settings.provider
3. Add tracker/model/provider to _run_builder_with_context; call record_agent_usage with operation=builder_dispatch after both normal and fallback .run paths
4. Both retry-dispatch and fresh-dispatch call sites pass tracker/model/provider
5. Existing daemon tests pass; new tests verify recording in both dispatch paths

[[2026-03-25]] Wed 13:55

## Architecture Review

See docs/scratch/845-architect.md for full review.

[[2026-03-25]] Wed 14:23

## Test-Writer Notes

- Test file: tests/test_845_daemon_usage_tracking.py
- Classes: TestFromAC_RunBuilderWithContextSignature, TestFromAC_RunBuilderWithContextUsageNormalPath, TestFromAC_RunBuilderWithContextUsageFallbackPath, TestFromAC_PollTickUsageParams, TestFromAC_PollLoopUsageParams, TestFromAC_RunDaemonUsageThreading
- Tests per category: happy 18, edge 5, error 6, boundary 5
- Total: 34 tests, all FAIL
- ruff: clean
- AC coverage:
  AC1 (_run_builder_with_context new params): Signature tests (4 tests)
  AC2 (record in normal path): NormalPath tests (8 tests)
  AC3 (record in fallback path): FallbackPath tests (5 tests)
  AC4 (poll_tick threads tracker/model/provider): PollTick tests (7 tests)
  AC5 (poll_loop threads to poll_tick): PollLoop tests (6 tests)
  AC6 (run_daemon passes agent.tracker/settings.provider to poll_loop): RunDaemon tests (4 tests)
