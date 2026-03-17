# LLM Cost Tracking per Operation

**Task:** #732 — Research: LLM cost tracking per operation
**Date:** 2026-03-17
**Source:** #597 edgequake-research S3.3

## 1. Catalog of All LLM Call Sites

### Tracked (via UsageTracker)

| # | Call Site | File | Mechanism |
|---|-----------|------|-----------|
| 1 | `OwlBearAgent.turn()` | `core/agent.py` L166 | `_record_usage()` after `inner.run()` — main conversational path |
| 2 | `delegate_to_agent` (delegation) | `core/delegation.py` L137 | `usage=ctx.usage` accumulates delegated tokens into parent OwlBearAgent's usage object |
| 3 | Channel loop (`channel_loop`) | `daemon.py` L462 | Calls `OwlBearAgent.turn()`, so tracked via #1 |

### Untracked (standalone Agent instances, no UsageTracker)

| # | Call Site | File | Lines | Purpose |
|---|-----------|------|-------|---------|
| 4 | `SummarizingCondenser` | `core/condenser.py` | L183-187 | History summarization (history processor) |
| 5 | `RetrospectiveHook` | `core/retrospective_hook.py` | L96, L192 | Post-task retrospective analysis (structured output) |
| 6 | `SessionMemoryHook` summarizer | `bootstrap/__init__.py` | L72 | Inline `Agent(model).run(text)` closure for session-end summaries |
| 7 | `ProjectDefinitionExtractor` | `planning/extractor.py` | L59, L75 | Project scoping from user text (structured output) |
| 8 | `SourceEvaluator` | `memory/knowledge/evaluator.py` | L93, L133 | Relevance scoring for content ingestion (structured output) |
| 9 | `EntityExtractor` | `memory/knowledge/extractor.py` | L65, L89 | Entity/edge extraction from text chunks (structured output) |
| 10 | `IntraDocGraphBuilder` | `memory/knowledge/graph_builder.py` | L71, L119+L146 | Cross-chunk relationship inference within a document (batched) |
| 11 | `InterDocGraphBuilder` | `memory/knowledge/inter_doc_graph_builder.py` | L81, L133 | Cross-document relationship inference (batched) |
| 12 | Daemon `poll_tick` builder dispatch | `daemon.py` | L730-732, L796-798 | `agent_registry.get("builder").run(prompt)` — raw PydanticAI Agent, not OwlBearAgent |

### Not Yet Active

| # | Call Site | File | Notes |
|---|-----------|------|-------|
| 13 | `ConsolidationService._run_llm()` | `memory/knowledge/consolidation.py` L101-107 | Placeholder stub — returns hardcoded string, no LLM call |

**Summary:** 3 tracked call sites, 9 untracked, 1 placeholder. The main conversational path and delegated agents are tracked. All secondary/background LLM calls are completely dark.

## 2. Evaluation of Existing Infrastructure

### Components

| Component | File | Purpose | Assessment |
|-----------|------|---------|------------|
| `UsageTracker` | `memory/usage.py` | JSONL persistence, time-windowed queries, aggregation | **Solid.** Clean JsonlStore pattern, `query(timedelta)` and `summary()` cover all reporting needs. |
| `UsageRecord` | `memory/usage.py` | Per-request usage data model | **Good.** Covers input/output/cache tokens, requests, tool_calls, estimated cost, premium requests. |
| `calc_estimated_cost` | `memory/usage_cost.py` | Dollar cost estimation via genai_prices | **Good.** Handles provider aliases (copilot→openai), graceful fallback on unknown models. |
| `get_premium_requests` | `providers/copilot_multipliers.py` | Copilot premium request multiplier lookup | **Good.** Strips provider prefixes, defaults to 1.0 for unknown models. |
| `OwlBearDeps.tracker` | `core/deps.py` | Carries tracker through PydanticAI deps | **Limited scope.** Only available to OwlBearAgent's inner Agent and delegated agents. Secondary sites never touch deps. |
| `_record_usage()` | `core/agent.py` L185-230 | Extracts usage from result, enriches with cost/premium, appends to tracker | **Good.** The recording logic itself is well-structured and complete. |

### Gaps in Existing Infrastructure

1. **No `operation_type` field on `UsageRecord`.** All records look identical — a condenser summarization and a user conversation turn produce the same record shape. There's no way to break down costs by operation type after the fact.

2. **No mechanism to share UsageTracker with standalone Agent instances.** Secondary components (condenser, hooks, extractors, builders) create standalone `Agent()` instances and call `.run()` directly. None of them receive or use a `UsageTracker`. The recording logic in `_record_usage()` is tightly coupled to `OwlBearAgent`.

3. **Daemon builder dispatch is untracked.** The daemon's `poll_tick` spawns raw PydanticAI Agents via `agent_registry.get("builder")` — these are not `OwlBearAgent` instances and have no tracker. This is the *autonomous workload* — potentially the highest token consumer — and it's completely dark.

4. **Knowledge pipeline is a multiplier.** A single document ingestion triggers EntityExtractor (per chunk) → IntraDocGraphBuilder → InterDocGraphBuilder. For a large document chunked into N pieces, this is O(N) + O(1) + O(batches) LLM calls — all untracked. Passive knowledge ingestion could dominate costs.

## 3. Proposed Pattern for Extending Usage Tracking

### Recommended: Option A — Pass UsageTracker through constructors

The simplest approach is to add an optional `tracker: UsageTracker | None = None` parameter to each secondary component's constructor. After each `Agent.run()` call, extract usage and append a record.

**Implementation sketch:**

```python
# Shared helper (new file: src/owlbear/memory/usage_helpers.py)
def record_agent_usage(
    tracker: UsageTracker | None,
    result: RunResult,       # pydantic_ai result
    model: str,
    provider: str,
    session_id: str,
    operation: str,          # e.g. "condenser", "retrospective", "entity_extraction"
) -> None:
    if tracker is None:
        return
    usage = result.usage()
    record = UsageRecord(
        timestamp=datetime.now(UTC),
        session_id=session_id,
        model=model,
        provider=provider,
        operation=operation,     # NEW field on UsageRecord
        input_tokens=usage.input_tokens or 0,
        output_tokens=usage.output_tokens or 0,
        requests=usage.requests or 0,
        ...
    )
    tracker.append(record)
```

**Per-component changes:** Each secondary site adds `tracker` to `__init__`, calls `record_agent_usage()` after `.run()`. The bootstrap wires the shared `UsageTracker` instance into each component.

### Alternatives Considered

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A (recommended)** | Pass UsageTracker through constructors + shared helper | Simple, explicit, testable, no framework magic | Requires constructor changes on ~8 components + bootstrap wiring |
| **B** | PydanticAI `usage=Usage()` accumulator | Reuses PydanticAI's built-in mechanism | Still need tracker.append() somewhere; doesn't solve recording |
| **C** | Middleware/decorator wrapping Agent.run() | Zero changes to secondary components | Implicit, harder to debug, breaks structured output typing |

**Rationale for Option A:** It follows the existing codebase pattern — `OwlBearAgent` already does exactly this via constructor injection of `tracker`. Extending the same pattern to secondary components is consistent and predictable. The shared helper eliminates boilerplate while keeping each call site explicit.

### Changes Required

1. **Add `operation` field to `UsageRecord`** — string field with default `"turn"` for backward compatibility with existing records.
2. **Create `record_agent_usage()` helper** in a new module or in `usage.py`.
3. **Wire tracker into 8 secondary components** — constructor parameter + post-run recording:
   - `SummarizingCondenser`
   - `RetrospectiveHook`
   - `SessionMemoryHook` (via summarizer closure in bootstrap)
   - `ProjectDefinitionExtractor`
   - `SourceEvaluator`
   - `EntityExtractor`
   - `IntraDocGraphBuilder`
   - `InterDocGraphBuilder`
4. **Wire tracker into daemon poll_tick** — either pass tracker to `agent_registry.get("builder").run()` via a usage accumulator, or restructure to use OwlBearAgent for autonomous dispatch.
5. **Update bootstrap** to pass the `UsageTracker` instance to all secondary components.

## 4. Follow-up Tasks

The infrastructure already exists and is well-designed. The gap is purely wiring — passing the existing `UsageTracker` to secondary call sites. This warrants one implementation task.

### Task 1: Wire UsageTracker to secondary LLM call sites

- **Title:** Wire UsageTracker to secondary LLM call sites
- **Priority:** nice-to-have (visibility improvement, not a functional gap)
- **Tags:** scope:core, phase-3
- **AC:**
  1. Add `operation: str = "turn"` field to `UsageRecord` for backward compatibility.
  2. Create `record_agent_usage()` helper function.
  3. Pass `UsageTracker` to `SummarizingCondenser`, `RetrospectiveHook`, `SessionMemoryHook` summarizer, `ProjectDefinitionExtractor`, `SourceEvaluator`, `EntityExtractor`, `IntraDocGraphBuilder`, `InterDocGraphBuilder`.
  4. Each secondary call site records usage after `Agent.run()` with appropriate `operation` value.
  5. Update `bootstrap()` to wire `UsageTracker` into all secondary components.
  6. Existing tests pass; new tests verify recording from at least 2 secondary sites.
- **Depends on:** none
- **See:** `docs/research/llm-cost-tracking.md` §3

### Task 2: Track daemon autonomous builder dispatch

- **Title:** Track LLM usage in daemon poll_tick builder dispatch
- **Priority:** nice-to-have
- **Tags:** scope:core, phase-3
- **AC:**
  1. Daemon `poll_tick` builder.run() calls record usage via `UsageTracker`.
  2. Either: (a) pass a `usage` accumulator and record after task completion, or (b) restructure dispatch to use a lightweight wrapper that records.
  3. Existing daemon tests pass.
- **Depends on:** Task 1 (needs `operation` field + helper)
- **See:** `docs/research/llm-cost-tracking.md` §3

**Zero follow-up tasks for infrastructure** — UsageTracker, calc_estimated_cost, get_premium_requests, and _record_usage are all solid and need no changes beyond the `operation` field addition.
