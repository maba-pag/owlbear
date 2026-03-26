# Daemon Usage Tracking — RED Test Validation

> **Owning task:** #1003 — Test: Track LLM usage in daemon poll_tick builder dispatch
> **Date:** 2026-03-25 **Status:** Complete

## 1. Context and Question

Task #1003 is the TDD RED phase for #845, which adds `record_agent_usage()` calls to the daemon's builder dispatch paths. The AC specifies 7 test cases. This research validates that the AC is testable, identifies the right patterns, and flags any risks.

Parent research: `docs/research/daemon-usage-tracking.md` (from #845) established Option A — inline recording in `_run_builder_with_context`.

## 2. Sources Studied

| Source | Relevance | What |
|--------|-----------|------|
| `tests/test_daemon_coverage_gaps.py` L1570–1690, 2155–2330 | 1.0 | Existing dispatch-context tests for both retry and fresh paths — exact template for AC1–2 |
| `tests/test_daemon_coverage_gaps.py` L2768–2930 | .95 | `_run_builder_with_context` TypeError-fallback tests — template for AC3–4 |
| `tests/test_usage_wiring.py` L125–280 | .95 | `record_agent_usage` unit tests — mock patterns, `_make_usage_result`, error swallowing |
| `tests/test_daemon_coverage_gaps.py` L1140–1200 | .85 | `poll_loop` exception-recovery tests — template for AC7 (patching `poll_tick`) |
| `src/owlbear/daemon.py` L788–810 | 1.0 | Current `_run_builder_with_context` — no tracker/model/provider params yet |
| `src/owlbear/daemon.py` L811–975 | 1.0 | Current `poll_tick` — no tracker/provider params; two dispatch call sites |
| `src/owlbear/daemon.py` L975–1020 | .90 | Current `poll_loop` — no tracker/provider params; threading site for AC7 |
| `src/owlbear/memory/usage.py` L117–180 | 1.0 | `record_agent_usage` — no-op when tracker=None, swallows exceptions |

## 3. Analysis

### AC-by-AC testability assessment

| AC | Target | Pattern source | Test approach | Risk |
|----|--------|---------------|---------------|------|
| 1 | poll_tick retry path | `TestFromAC_PollTickRetryDispatchContext` | Patch `record_agent_usage` in daemon module; trigger retry via due `RetryEntry`; assert called with correct kwargs | None — pattern proven |
| 2 | poll_tick fresh path | `TestFromAC_PollTickFreshDispatchContext` | Same as AC1 but with todo tasks in kanban_list | None |
| 3 | `_run_builder_with_context` normal path | `TestFromAC_809_RunBuilderContextFallback` | Call directly with mock builder accepting **kwargs; patch `record_agent_usage`; assert called | New params don't exist yet — tests must import with current signature and fail |
| 4 | `_run_builder_with_context` fallback path | Same as AC3 | Mock builder rejects **kwargs at call-time (sync TypeError); verify recording still happens | Same as AC3 |
| 5 | Error resilience | `TestFromAC_RecordAgentUsage.test_enrichment_failure_does_not_raise` | Patch `record_agent_usage` to raise; verify builder result returned | Straightforward |
| 6 | None tracker no-op | `TestFromAC_RecordAgentUsage.test_noop_when_tracker_is_none` | Pass tracker=None; verify `record_agent_usage` not called | Straightforward |
| 7 | poll_loop threading | `TestFromAC_PollLoopExceptionRecovery` | Patch `poll_tick`; call `poll_loop` with tracker/provider; verify poll_tick receives them | Requires new params on poll_loop — test fails at call site |

### Test failure modes (RED phase)

All 7 tests fail today for clearly diagnosable reasons:

- **AC1–2:** `poll_tick` signature lacks `tracker`/`provider` params → `TypeError` on call, or `record_agent_usage` never imported in daemon module → patch target doesn't exist or assertion fails.
- **AC3–4:** `_run_builder_with_context` has no `tracker`/`model`/`provider` params → `TypeError` on direct call, or recording never invoked.
- **AC5–6:** Same root cause — recording code doesn't exist in the function.
- **AC7:** `poll_loop` lacks `tracker`/`provider` → `TypeError` or kwargs silently dropped.

These are clean RED failures: each test fails for exactly the reason its AC describes.

### Dependency note

Task #845 (implementation) should depend on #1003 (tests) to enforce TDD ordering. Currently #845 has no dependency on #1003.

## 4. Recommendation (.90 confidence)

**The AC is sound and directly testable.** All 7 items map to established test patterns in the daemon test suite. No blockers identified.

Test file placement: extend `tests/test_daemon_coverage_gaps.py` (which already contains the dispatch-context and `_run_builder_with_context` tests) with a new class `TestFromAC_1003_UsageTrackingDispatch`.

Add `depends_on: [1003]` to #845's frontmatter so the builder waits for RED tests.

## 5. Follow-up Tasks

No new tasks needed — #1003 and #845 already cover the full RED→GREEN cycle. The only action is adding the dependency link from #845 to #1003.
