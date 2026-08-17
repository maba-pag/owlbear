# Context Condenser as PydanticAI HistoryProcessor

> **Owning task:** #619 — Implement context condenser as PydanticAI HistoryProcessor
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear sessions with many tool calls can exceed context windows. Task #619 asks: how should we implement a rolling-window LLM-summarizing condenser using PydanticAI's HistoryProcessor protocol?

Sub-questions: (1) Exact HistoryProcessor contract and constraints? (2) OpenHands adaptation? (3) ModelMessage vs Event structure? (4) Where to wire in?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PydanticAI `_agent_graph.py` source | <https://ai.pydantic.dev/api/agent/> | 1.0 |
| PydanticAI messages API | <https://ai.pydantic.dev/api/messages/> | .90 |
| OpenHands `LLMSummarizingCondenser` | <https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/memory/condenser/impl/llm_summarizing_condenser.py> | .90 |
| OpenHands `condenser.py` base classes | <https://github.com/All-Hands-AI/OpenHands/blob/main/openhands/memory/condenser/condenser.py> | .70 |
| OwlBear `agent.py` | local `src/owlbear/core/agent.py` | 1.0 |
| OwlBear `bootstrap.py` | local `src/owlbear/bootstrap.py` | .90 |
| OwlBear `config.py` | local `src/owlbear/config.py` | .80 |

## 3. Analysis

### 3a. HistoryProcessor Contract

HistoryProcessor is a **callable type alias** (not a Protocol class to inherit). Four variants:

| Variant | Signature |
|---------|-----------|
| sync | `(list[ModelMessage]) -> list[ModelMessage]` |
| async | `(list[ModelMessage]) -> list[ModelMessage]` |
| sync+ctx | `(RunContext[DepsT], list[ModelMessage]) -> list[ModelMessage]` |
| async+ctx | `(RunContext[DepsT], list[ModelMessage]) -> list[ModelMessage]` |

Runtime behavior (`_process_message_history` in `_agent_graph.py`):

- Applied **sequentially** before every model request (`ModelRequestNode._prepare_request`)
- Operates on a **copy** of `message_history`
- Validates: result non-empty, must end with `ModelRequest`, sets timestamp if missing
- After processing, replaces `message_history[:]` with result

Our condenser should use the **async+ctx** variant (LLM call is async; ctx gives `OwlBearDeps`).

### 3b. PydanticAI Message Structure vs OpenHands Events

| Aspect | OpenHands | PydanticAI |
|--------|-----------|------------|
| Unit | `Event` (Action/Observation) | `ModelMessage` (Request/Response) |
| Counting | Flat event list | Alternating Request + Response |
| Content | `.message` string, truncatable | `.parts` list (typed: text, tool-call, etc.) |
| Tool pairing | Implicit | Explicit: `ToolCallPart` <-> `ToolReturnPart` via `tool_call_id` |

**Key adaptation:** OpenHands truncates individual event `.message` strings. We operate on whole `ModelMessage` objects and cannot split tool-call/return pairs across head/tail boundaries.

### 3c. OpenHands Pattern

`LLMSummarizingCondenser(max_size=100, keep_first=1, target_size=max_size//2)`:

1. If `len(events) <= max_size`: return as-is (no-op fast path)
2. `head = events[:keep_first]`
3. `tail = events[-(target_size - len(head) - 1):]`
4. `middle = events[keep_first : len(events) - len(tail)]`
5. `summary = llm.summarize(middle)` (single LLM call)
6. Return `head + [summary_event] + tail`

### 3d. Implementation Approach

| Approach | KISS | LOC | Risk |
|----------|------|-----|------|
| **A. Direct port, model at init** | High | ~100 | Model must be passed at construction |
| B. Use RunContext for model | Medium | +20 | RunContext doesn't expose Model directly |
| C. Separate summarizer Agent | Medium | +30 | Extra agent lifecycle |

**Recommendation (.85):** Approach A. Accept `model` param in `__init__`, use `pydantic_ai.Agent` internally for the summarization call. In `bootstrap.py`, pass the same model used for OwlBearAgent.

### 3e. Summary Message Format

The summary replaces the condensed middle section as a `ModelRequest`:

```python
ModelRequest(
    parts=[UserPromptPart(content="[Condensed Context]\n{summary}")],
    metadata={"condensed_at": iso_timestamp, "forgotten_count": N},
)
```

This preserves Request/Response alternation; the summary occupies a "request" slot.

### 3f. Settings Fields

Following existing `Field(default=X, description="...")` pattern in `OwlBearSettings`:

- `condenser_enabled: bool = Field(default=False, description="...")`
- `condenser_max_events: int = Field(default=120, description="...")`

Only 2 config fields. `keep_first` (4) and `target_size` (`max_events // 2`) stay as constructor defaults -- YAGNI to expose as config.

### 3g. Bootstrap Wiring

In `bootstrap.py` step 8 (agent construction, ~line 967):

```python
history_processors = None
if settings.condenser_enabled:
    from owlbear.core.condenser import SummarizingCondenser

    condenser = SummarizingCondenser(max_events=settings.condenser_max_events, model=model)
    history_processors = [condenser]
agent = OwlBearAgent(..., history_processors=history_processors)
```

### 3h. Testing Strategy

| Test | Verifies |
|------|----------|
| `test_noop_below_threshold` | Returns original messages when count < max_events |
| `test_condenses_above_threshold` | Triggers LLM summary, result = head + summary + tail |
| `test_keep_first_preserved` | First N messages always retained |
| `test_target_size_respected` | Output length = target_size |
| `test_metadata_tags` | Summary has `condensed_at` + `forgotten_count` |
| `test_ends_with_model_request` | Validates PydanticAI invariant |
| `test_disabled_by_default` | condenser_enabled=False -> no processors wired |

Mock the LLM via PydanticAI `TestModel` or mock the internal summarizer agent.

## 4. Recommendation (.85 confidence)

Direct port of OpenHands pattern adapted to PydanticAI `ModelMessage` types. `SummarizingCondenser` class with async `__call__` matching HistoryProcessor[OwlBearDeps]. ~100 LOC condenser + ~10 LOC settings + ~5 LOC bootstrap wiring.

**Risk:** Tool-call/return pairing at head/tail boundary. **Mitigation:** boundary-alignment logic (~15 LOC) ensures we never split a `ModelResponse` with `ToolCallPart` from its next `ModelRequest` with `ToolReturnPart`.

**AC refinements from research:**

- `target_size` default: `max_events // 2` (= 60), not 56 as in original AC
- `__call__` signature: `async def __call__(self, ctx: RunContext[OwlBearDeps], messages: list[ModelMessage]) -> list[ModelMessage]`
- Constructor should accept `model: Model | None` (PydanticAI Model, not string)
- Add boundary alignment to avoid splitting tool-call/return pairs

## 5. Follow-up Tasks

See kanban commands below (presented for review, not executed).
