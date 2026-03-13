# Token Usage Tracking, Premium Requests, and Cost Estimation

> **Owning task:** #82 — Track token usage, premium requests, and costs
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear needs to track LLM token usage per request, aggregate by time windows (1h, 24h, 7d), and produce cost estimates. When using GitHub Copilot, it should also track premium request consumption. The solution should be zero-config — infer costs from model name + provider automatically.

Key questions: (a) what data to capture, (b) where to store it, (c) how to compute costs, (d) how to surface it.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| PydanticAI `pydantic_ai.usage` | <https://ai.pydantic.dev/api/usage/> | .95 | `RunUsage` dataclass: `requests`, `tool_calls`, `input_tokens`, `output_tokens`, `cache_write_tokens`, `cache_read_tokens`, `details`, `total_tokens`. `RequestUsage.extract()` uses genai-prices for cost calc. |
| genai-prices (Pydantic) | <https://github.com/pydantic/genai-prices> | .90 | Python library for LLM price calculation. `calc_price(Usage(...), model_ref, provider_id)` returns input/output/total price. Auto-updates from GitHub. 30+ providers, 900+ models. |
| LiteLLM `model_prices_and_context_window.json` | <https://github.com/BerriAI/litellm> | .60 | Comprehensive model pricing DB (JSON). Useful reference but heavy dependency (37k stars, 80% Python). Not needed if genai-prices covers our models. |
| PydanticAI `RunResult.usage()` / `StreamedRunResult.usage()` | <https://ai.pydantic.dev/api/result/> | .95 | Both result types expose `.usage() -> RunUsage`. Available after `Agent.run()` or after stream completion. |
| GitHub Copilot premium request pricing | <https://docs.github.com/en/copilot/managing-copilot/monitoring-usage-and-spending/> | .80 | Premium requests use model multipliers (e.g. GPT-4o = 1x, o1 = varies, Claude Sonnet = 1x). Publicly documented but page structure changes frequently. |

## 3. Analysis

### 3.1 Data Capture — What PydanticAI Gives Us

After `Agent.run()`, `result.usage()` returns `RunUsage` with:

| Field | Type | Description |
|-------|------|-------------|
| `requests` | int | Number of LLM API requests in this run |
| `tool_calls` | int | Successful tool calls executed |
| `input_tokens` | int | Total input/prompt tokens |
| `output_tokens` | int | Total output/completion tokens |
| `cache_write_tokens` | int | Tokens written to cache |
| `cache_read_tokens` | int | Tokens read from cache |
| `total_tokens` | property | `input_tokens + output_tokens` |
| `details` | dict | Extra provider-specific details |

**Integration point:** `OwlBearAgent.turn()` in `src/owlbear/core/agent.py` already has access to `result` from `self.inner.run()`. Currently it only uses `result.output` and `result.all_messages()`. Adding `result.usage()` capture is a 2-line change.

### 3.2 Cost Calculation — Options Comparison

| Criterion | genai-prices (.85) | LiteLLM JSON (.50) | Manual config (.30) |
|-----------|--------------------|--------------------|---------------------|
| Dependency weight | 1 package (~26KB data) | JSON file only, no dep | Zero deps |
| Model coverage | 900+ models, 30+ providers | 2000+ models | Only what we hardcode |
| Auto-update | `UpdatePrices()` background fetch | Manual download | Manual |
| PydanticAI integration | Native — `RequestUsage.extract()` uses it | None | None |
| KISS score | High — already in PydanticAI ecosystem | Medium | Low (maintenance burden) |
| Copilot coverage | No (Copilot uses OpenAI-compatible API, maps to underlying model) | Partial | Yes (we control it) |

**Verdict (.85 confidence):** Use **genai-prices** via PydanticAI's native integration. It's already an indirect dependency through PydanticAI's `RequestUsage.extract()`, covers our models, and auto-updates. For Copilot premium request tracking, maintain a small in-code multiplier lookup (see §3.4).

### 3.3 Storage — Options Comparison

| Criterion | JSONL (.80) | SQLite (.65) | In-memory (.40) |
|-----------|-------------|--------------|-----------------|
| Consistency with project | High — matches SessionStore | Medium — new dep pattern | Low — data loss risk |
| Time-window queries | Filter in Python (simple) | SQL `WHERE timestamp > ?` | Native but volatile |
| New dependencies | Zero | Zero (stdlib sqlite3) | Zero |
| Append performance | Excellent | Good | Excellent |
| Aggregation complexity | ~20 LOC Python filter | SQL GROUP BY | Simple sum |
| KISS score | High | Medium | Low (recovery needed) |

**Verdict (.80 confidence):** Use **JSONL** — a separate `usage.jsonl` file alongside session files. Consistent with the existing `SessionStore` pattern. Time-window queries are simple Python timestamp comparisons. If the file grows too large, add rotation later (YAGNI — don't build it now).

### 3.4 Copilot Premium Request Tracking

GitHub Copilot premium requests use model-based multipliers. The multiplier table is publicly documented but changes periodically. Key data points:

- Base models (GPT-4o, Claude 3.5 Sonnet) ≈ 1 premium request per interaction
- Reasoning models (o1, o3-mini) ≈ higher multipliers
- The Copilot API response does not include a `premium_requests_consumed` header

**Approach (.75 confidence):** Maintain a small `COPILOT_MULTIPLIERS: dict[str, float]` mapping in code. Map the model name from the API response to a multiplier. Default to 1x for unknown models. Update the dict periodically by checking GitHub docs. This is intentionally simple — a 10-line dict, not a config file or database.

### 3.5 Architecture: Where to Hook

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Modify `OwlBearAgent.turn()` directly | Simplest, 100% reliable capture | Couples tracking to agent | **.85 — recommended** |
| `SESSION_END` hook | Decoupled, pluggable | Only fires at session end, not per-turn | .50 |
| New `POST_TURN` hook event | Clean separation, per-turn | Adds new hook event + handler | .65 |

**Verdict (.85 confidence):** Capture usage **inside `OwlBearAgent.turn()`** after `self.inner.run()`. This is 2-3 lines of code, guarantees every turn is tracked, and follows the surgical-change principle. The captured data flows to a `UsageTracker` service passed as a constructor dependency.

### 3.6 CLI Interface

Surface via `bearclaw usage` with time-window flags:

```
bearclaw usage                   # default: last 24h
bearclaw usage --last-hour
bearclaw usage --last-24h
bearclaw usage --last-7d
bearclaw usage --all
```

Output: table with model, requests, input tokens, output tokens, estimated cost. For Copilot: additional premium requests column.

## 4. Recommendation (.82 confidence)

**Minimal, zero-config token + cost tracking using PydanticAI's native usage API + genai-prices:**

1. Capture `result.usage()` in `OwlBearAgent.turn()` after each LLM call
2. Store records as JSONL (one line per turn: timestamp, model, session_id, usage fields, cost estimate)
3. Use `genai-prices` `calc_price()` for dollar-cost estimation (via PydanticAI integration)
4. For Copilot premium requests: hardcode a small model→multiplier dict
5. Surface via `bearclaw usage` CLI command with time-window flags

**Risks and mitigations:**

- **genai-prices missing a model:** Falls back to zero cost, logs warning. Non-blocking.
- **JSONL size growth:** Add file rotation when file exceeds 10MB. YAGNI for now.
- **Copilot multiplier drift:** Low-maintenance dict update. Check quarterly.

## 5. Follow-up Tasks

1. **Create `UsageRecord` Pydantic model and `UsageTracker` service** — data model + JSONL append/query logic
2. **Integrate usage capture into `OwlBearAgent.turn()`** — capture `result.usage()`, pass to tracker
3. **Add `genai-prices` dependency and cost calculation** — `calc_price()` wrapper with fallback
4. **Add Copilot premium request multiplier lookup** — small dict in provider module
5. **Create `bearclaw usage` CLI command** — time-window flags, tabular output
6. **Tests for usage tracking** — unit tests with mock usage data
