# Agent Analytics: Structured Activity Logging and Performance Metrics

> **Owning task:** #142 — Agent analytics — structured activity logging and performance metrics
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

Task #142 asks for structured logging of agent behavior: tool invocations, delegation chains, success/failure rates, latency per tool, task completion times. JSONL-based with aggregation helpers, feeding a future self-improvement pipeline (#146).

**Critical question:** Does this overlap with #141's ObservabilityHook recommendation? If so, should #142 be closed as a duplicate?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| OwlBear #141 research doc | `docs/agent-observability-research.md` | .95 | ObservabilityHook: structured JSONL events for all lifecycle events with duration tracking |
| OwlBear UsageTracker | `src/owlbear/memory/usage.py` | .90 | Existing JSONL pattern: append-only, `TypeAdapter`, time-windowed queries, `summary()` aggregation |
| OwlBear HookRegistry | `src/owlbear/core/hooks.py` | .90 | 9 lifecycle events, async emit, error-swallowing |
| OwlBear HookedToolset | `src/owlbear/tools/hooked.py` | .85 | PRE/POST_TOOL_USE hooks already fire on every tool call |
| AutoGen event logging | `github.com/microsoft/autogen/.../logging.py` | .75 | `LLMCallEvent`, `ToolCallEvent`, `MessageEvent` — stdlib `logging` + JSON serialization, per-agent attribution via context |
| LangSmith | `docs.langchain.com/langsmith` | .40 | Cloud-hosted tracing/eval platform; YAGNI for single-laptop use |

## 3. Analysis

### 3.1 Overlap matrix: #142 vs #141's ObservabilityHook

| #142 requirement | Covered by #141's ObservabilityHook? | Gap? |
|------------------|--------------------------------------|------|
| Structured logging of agent actions | Yes — JSONL events for all 9 lifecycle hookevents | None |
| Tool invocations | Yes — PRE/POST_TOOL_USE with tool name, args, result | None |
| Delegation chains | Partial — SUBAGENT_COMPLETE fires, but no chain depth/trace ID | Minor: add `trace_id` + `depth` fields |
| Success/failure rates | Yes — ON_ERROR + POST_TOOL_USE capture outcomes | None |
| Latency per tool | Yes — duration tracking via pre/post timestamp pairing | None |
| Task completion times | Yes — SESSION_START to TASK_COMPLETE duration | None |
| JSONL-based storage | Yes — same pattern as UsageTracker | None |
| Aggregation helpers | **No** — #141 recommends raw JSONL only | Gap: need `query()` + `summary()` methods (like UsageTracker) |
| Self-improvement pipeline | No — that's #146's concern, not #141 or #142 | Out of scope |

**Overlap: ~90%.** The only meaningful delta #142 adds is aggregation/query helpers for the event log.

### 3.2 Prior art: how others handle agent analytics

| System | Approach | Complexity | Local? |
|--------|----------|------------|--------|
| AutoGen | Stdlib `logging` + JSON event classes (`LLMCallEvent`, `ToolCallEvent`) | Low (~300 LOC) | Yes |
| LangSmith | Cloud platform, OTel traces, run trees | High | No |
| PydanticAI + Logfire | OTel spans via `instrument_all()`, cloud or self-host viewer | Medium | Optional |
| OwlBear #141 proposal | Hook-based JSONL structured log, no new deps | Low (~80 LOC hook + ~60 LOC store) | Yes |

AutoGen's pattern is closest to what we need: typed event classes serialized to JSON via stdlib logging. #141's ObservabilityHook is essentially the same pattern but using OwlBear's existing hook system instead of Python's logging module — a better fit since hooks already fire at every lifecycle point.

### 3.3 What aggregation helpers should look like

Following `UsageTracker`'s pattern (which #142 explicitly references):

```
EventStore (AppendOnlyJSONL)
├── append(event)         # write
├── load() → list[Event]  # read all
├── query(window) → list  # time-windowed
├── summary(window) → EventSummary
│   ├── total_tool_calls: int
│   ├── error_count: int
│   ├── avg_tool_duration_ms: float
│   ├── tools_by_frequency: dict[str, int]
│   └── agents_by_usage: dict[str, int]
└── tool_stats(window) → dict[str, ToolStats]
    ├── call_count, error_count
    ├── avg_duration_ms, p95_duration_ms
    └── last_used: datetime
```

This is ~60 LOC on top of the ObservabilityHook's ~80 LOC event store. Total: ~140 LOC.

## 4. Recommendation (.90 confidence)

**Close #142 as a duplicate. Fold its aggregation requirement into #141's follow-up tasks.**

Rationale:

- #141's ObservabilityHook already covers 90% of what #142 describes
- The remaining 10% (aggregation helpers) is a natural extension of the ObservabilityHook's event store, not a separate system
- Creating both would produce duplicate infrastructure (two JSONL stores for overlapping events)
- The self-improvement pipeline (#146) should consume the ObservabilityHook's data, not a separate analytics system
- KISS and DRY both argue for one system, not two

**Action:** Add aggregation helpers (query, summary, tool_stats) to the ObservabilityHook implementation task's AC. Tag the task with `analytics` so #142's intent is preserved. Close #142 with a note pointing to #141's follow-up tasks.

## 5. Follow-up Tasks

**No new tasks needed.** Instead, update #141's follow-up tasks (when created) to include:

1. **ObservabilityHook implementation** — expand AC to include:
   - `EventStore` class with `append()`, `load()`, `query(window)`, `summary(window)`, `tool_stats(window)`
   - Tags: `phase-11, hooks, agent, analytics`
   - This single task replaces both #141's "ObservabilityHook" follow-up and #142 entirely

2. **Close #142** with body update noting it's subsumed by #141's implementation tasks

### Recommended kanban commands

```powershell
# Close #142 as duplicate — edit body to explain, then move to done
kanban\kanban-md.exe edit 142 --body "DUPLICATE of #141 follow-up tasks. The ObservabilityHook recommended in docs/agent-observability-research.md covers structured activity logging, tool invocation tracking, latency measurement, and success/failure rates. Aggregation helpers (query, summary, tool_stats) folded into ObservabilityHook implementation AC. See docs/agent-analytics-research.md for analysis." --status done

# When creating #141's follow-up implementation task, include analytics AC:
kanban\kanban-md.exe create "Implement ObservabilityHook with JSONL event store and aggregation" --priority nice-to-have --tags "phase-11,hooks,agent,analytics" --body "Implement the ObservabilityHook recommended in docs/agent-observability-research.md. Includes:\n- EventStore (append-only JSONL, same pattern as UsageTracker)\n- Structured events for all 9 HookEvent types with timestamp, duration, agent/tool name, session ID, success/failure\n- query(window), summary(window), tool_stats(window) aggregation methods\n- trace_id field for delegation chain tracking\n\nAC:\n- [ ] ObservabilityHook registered on all HookEvent types\n- [ ] Events written to configurable JSONL path\n- [ ] Duration tracking for PRE/POST_TOOL_USE pairs\n- [ ] EventStore.summary() returns error count, avg tool duration, tool frequency\n- [ ] >= 90% test coverage\n\nSee docs/agent-observability-research.md §4, docs/agent-analytics-research.md §3.3"
```
