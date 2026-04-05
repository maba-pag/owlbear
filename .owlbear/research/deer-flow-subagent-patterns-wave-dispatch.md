# deer-flow Subagent Patterns: Wave Dispatch Evaluation

> **Owning task:** #500 — Evaluate deer-flow subagent patterns for wave dispatch improvements
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

Research #428 identified two deer-flow patterns potentially useful for OwlBear's orchestrator dispatch: (1) SubagentLimitMiddleware's silent truncation of excess parallel calls, and (2) SubagentResult's status enum (PENDING/RUNNING/COMPLETED/FAILED/TIMED_OUT). This research evaluates each pattern against OwlBear's existing wave dispatch architecture and recommends adoption or rejection with rationale.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | deer-flow deep dive (#428), sections 3D–3F | .90 — SubagentLimitMiddleware truncation behavior; SubagentResult lifecycle |
| S2 | OwlBear `waves.py` (codebase) | .95 — Four-bucket wave assembly algorithm; deterministic wave_size enforcement |
| S3 | OwlBear `loop.py` (codebase) | .95 — dispatch_entry bool return; _apply_wave_result; rate-limit sequential fallback |
| S4 | OwlBear `acp_client.py` (codebase) | .90 — ErrorCategory enum (TRANSIENT/AUTH/PERMANENT/TOOL_SEMANTIC) |
| S5 | OwlBear `agent-common.instructions.md` | .95 — Channel A/B protocol; per-agent verdict tokens |
| S6 | Python asyncio.Semaphore docs (docs.python.org) | .75 — Concurrency primitives; not needed when wave sizes are pre-computed |
| S7 | AutoGen AgentChat `TaskResult` pattern (microsoft.github.io) | .70 — Typed result objects for agent dispatch; different execution model |
| S8 | OwlBear `orchestrator.agent.md` (codebase) | .90 — Orchestrator never interprets signals; success = returned, failure = crashed |

## 3. Analysis

### 3A. SubagentLimitMiddleware Truncation → Wave Dispatch Error Handling

| Aspect | deer-flow | OwlBear |
|--------|-----------|---------|
| Dispatch model | Model-driven (LLM calls `task()` tool) | Planner-driven (deterministic wave assembly) |
| Concurrency control | Middleware truncates excess calls at limit (3) | `assemble_waves()` pre-computes waves of `wave_size` (4) |
| Excess call scenario | LLM generates N > limit parallel calls | Cannot occur — algorithm guarantees wave ≤ `wave_size` |
| Error on excess | Silently dropped (no error to caller) | N/A — waves never exceed configured size |
| Backend concurrency | N/A (local thread pools) | Rate-limit string detection → sequential fallback [S3] |

**Key finding (.90 confidence):** deer-flow truncation solves a model-driven concurrency problem — the LLM might request more parallel subagent calls than the system allows. OwlBear's dispatch is planner-driven and deterministic: `assemble_waves()` [S2] guarantees waves never exceed `wave_size`. The scenario SubagentLimitMiddleware addresses cannot occur in OwlBear's architecture.

OwlBear already handles backend concurrency limits via rate-limit detection in `_is_rate_limit()` [S3], which triggers sequential fallback mode. `asyncio.gather(return_exceptions=True)` [S3] ensures individual failures don't cascade within a wave.

**Verdict: REJECT.** YAGNI — deterministic wave assembly prevents the problem. Adding truncation middleware would introduce complexity without addressing a real failure mode. [S1, S2, S3, S6]

### 3B. SubagentResult Status Enum → Channel A Signal Standardization

Two sub-evaluations: (a) dispatch result model, (b) Channel A verdict tokens.

#### 3B-i. Dispatch Result Model (dispatch_entry return type)

| Aspect | deer-flow SubagentResult | OwlBear dispatch_entry |
|--------|--------------------------|------------------------|
| Return type | Enum: PENDING/RUNNING/COMPLETED/FAILED/TIMED_OUT | `bool` (True/False) |
| Timeout distinction | Explicit TIMED_OUT status | Returns `False` (same as AcpClientError) |
| Error classification | Single status field | `ErrorCategory` enum at ACP layer [S4] |
| Consumer behavior | Polling-based result delivery | Fire-and-forget within `asyncio.gather` |
| Decision paths | Status drives retry/cancel logic | Both False cases → recorded as failure; rate-limit detected separately by string match |

**Key finding (.80 confidence):** The bool return type loses the TIMED_OUT vs ERROR distinction. However, OwlBear's orchestrator uses this distinction nowhere — both record as failures in `CycleResult.failures` [S3]. The only differentiated path is rate-limit detection, which operates on exception text, not return type. The ACP layer already provides `ErrorCategory` [S4] for error classification.

An enriched `DispatchOutcome` enum (SUCCESS/FAILED/TIMED_OUT/RATE_LIMITED) would marginally improve diagnostic logging but would not change any decision path in the current codebase.

**Verdict: REJECT.** YAGNI — no decision path uses the finer-grained distinction. `ErrorCategory` already exists at the ACP layer for classification. [S3, S4]

#### 3B-ii. Channel A Verdict Token Standardization

| Aspect | deer-flow SubagentResult | OwlBear Channel A |
|--------|--------------------------|-------------------|
| Format | Python enum | Text convention: `{VERDICT} #{id} -> {status} \| {evidence}` |
| Tokens | 5 states (PENDING–TIMED_OUT) | 10 per-agent tokens (DONE, PASS, FAIL, ARCHIVED, etc.) [S5] |
| Consumer | Executor polls enum value | Orchestrator **ignores** signals; downstream agents read as text [S8] |
| Parser needed | Built-in enum comparison | Would require text parsing or structured output |

**Key finding (.85 confidence):** Converting Channel A's 10 text-based verdict tokens [S5] to a Python enum would require modifying: (a) `agent-common.instructions.md` protocol definition, (b) every agent's output format, (c) a new parsing layer — even though the orchestrator deliberately ignores signals [S8]. This would be a T3 change (modifies agent instructions and pipeline behavior) with no clear consumer. Downstream agents read Channel A as diagnostic prose in task bodies, not structured data.

AutoGen's `TaskResult` [S7] uses typed objects, but AutoGen agents return Python objects within the same process. OwlBear agents return text via ACP sessions — a fundamentally different execution model where untyped text conventions are appropriate.

**Verdict: REJECT.** T3-level complexity for a diagnostic convention the orchestrator deliberately ignores. Text-based verdict tokens provide sufficient clarity for their actual consumers (downstream pipeline agents reading task bodies). [S5, S7, S8]

## 4. Recommendation Summary

| Pattern | Verdict | Conf | Rationale |
|---------|---------|------|-----------|
| SubagentLimitMiddleware truncation | **Reject** | .90 | YAGNI — planner-driven dispatch prevents the concurrency-exceeded scenario |
| SubagentResult enum (dispatch results) | **Reject** | .80 | YAGNI — no decision path uses finer distinction; ErrorCategory exists at ACP layer |
| SubagentResult enum (Channel A signals) | **Reject** | .85 | T3 complexity for a convention the orchestrator ignores; text tokens suffice |

**Risk if adopted:** Both patterns would add abstraction layers that serve no current decision path, violating KISS. The truncation middleware would mask errors that the existing rate-limit fallback already handles properly. The status enum would introduce a typed contract over a convention that works precisely because it's loose.

## 5. Tier Classification and Follow-up

**T1 (Autonomous — Reject):** All three patterns evaluated and rejected. No capability addition, no architecture change, no pipeline modification. The research deliverable is the rejection rationale itself.

**No follow-up implementation tasks.** Both patterns solve problems OwlBear's architecture has already addressed differently (deterministic wave assembly for concurrency; text-based Channel A for diagnostic signaling). Creating implementation tasks for rejected patterns would be waste.

If future requirements introduce model-driven dispatch or structured signal parsing, these patterns should be re-evaluated at that time.
