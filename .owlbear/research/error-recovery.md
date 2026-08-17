# Error Recovery and Escalation — Retry, Fallback, and Human Escalation

> **Owning task:** #306 — Error recovery and escalation — retry, fallback, and human escalation
> **Date:** 2026-03-01
> **Status:** Complete

## 1. Context and Question

When OwlBear agent tasks fail (tool errors, LLM API errors, auth expiry, test failures),
the system has no structured recovery. The daemon loop catches all exceptions with a bare
`except`, the agent's `turn()` method emits ON_ERROR then re-raises, and delegation
returns error strings. Need: retry policies, error classification, fallback strategies,
and escalation to user.

**Current error handling inventory:**

| Location | Pattern | Problem |
|---|---|---|
| `daemon.py` L253–267 | Catch-all; special-case auth → token refresh → retry once | No backoff, no classification, single retry |
| `core/agent.py` L115–122 | Emit ON_ERROR hook, re-raise | Hook is fire-and-forget; caller gets raw exception |
| `core/delegation.py` L112–120 | Catch-all → return `"Error: ..."` string | Agent receives unstructured text, no retry |
| `tools/hooked.py` L65–85 | Guards block, but no retry on tool failure | Tool exceptions propagate unhandled |
| Various toolsets | Return `f"error: {stderr}"` strings | No classification; agent can't distinguish transient vs permanent |

**Key constraint:** tenacity is already a dependency but unused in source code.

## 2. Sources Studied

| Source | URL | Relevance | What |
|---|---|---|---|
| PydanticAI Retries | <https://ai.pydantic.dev/retries/> | .95 | `AsyncTenacityTransport`, `RetryConfig`, `wait_retry_after` for HTTP-level retry |
| PydanticAI ModelRetry | <https://ai.pydantic.dev/agents/#reflection-and-self-correction> | .90 | `ModelRetry` exception — tool tells LLM "try again" with hint; per-tool `retries` param |
| PydanticAI FallbackModel | <https://ai.pydantic.dev/models/overview/#fallback-model> | .80 | `FallbackModel` — try multiple models in sequence; `FallbackExceptionGroup` |
| PydanticAI UsageLimits | <https://ai.pydantic.dev/agents/#usage-limits> | .70 | `request_limit`, `tool_calls_limit` — bound runaway retries |
| Anthropic tool_result | <https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/overview> | .65 | `is_error: true` in tool_result; `pause_turn` stop reason for resumption |
| tenacity docs | <https://tenacity.readthedocs.io/> | .85 | `retry`, `stop_after_attempt`, `wait_exponential`, `retry_if_exception_type` |

## 3. Analysis

### 3.1 Error Classification Scheme

Errors fall into four categories with distinct recovery strategies:

| Category | Examples | Recovery | Max retries |
|---|---|---|---|
| **Transient** | Network timeout, 429 rate limit, 502/503/504, DNS failure | Retry with exponential backoff + jitter | 3–5 |
| **Auth** | 401 Unauthorized, 403 Forbidden, expired Copilot token | Refresh token, then retry once | 1 |
| **Permanent** | FileNotFoundError, PermissionError, BlockedCommandError, ValidationError, schema mismatch | Do not retry; escalate immediately | 0 |
| **Tool-semantic** | Wrong tool args, stale data, command returned non-zero exit | Use PydanticAI `ModelRetry` — tell LLM to try different approach | 2 |

Classification function signature: `classify_error(exc: Exception) → ErrorCategory`.
This is a pure function (~30 LOC) using `isinstance` checks, importable by all layers.

### 3.2 Recovery Layers (innermost → outermost)

| Layer | Scope | Mechanism | Already exists? |
|---|---|---|---|
| L1: HTTP transport | Network/API errors | tenacity `AsyncTenacityTransport` wrapping httpx client | No (tenacity dep exists, unused) |
| L2: Tool-level retry | Individual tool call failures | `HookedToolset.call_tool` catches transient errors, retries via tenacity | No |
| L3: Model self-correction | Bad tool args, validation errors | PydanticAI `ModelRetry` (built-in, per-tool `retries` param) | Partially (PydanticAI has it, OwlBear doesn't use it) |
| L4: Agent-level fallback | Entire agent turn fails | Retry `agent.turn()` with backoff; optional model fallback | No (daemon retries auth only) |
| L5: Human escalation | All retries exhausted | `AskUserToolset.ask_user()` with error context and options | Exists but unwired |

### 3.3 Comparison: Build custom vs. Lean on PydanticAI

| Criterion | Custom retry in HookedToolset (.65) | PydanticAI ModelRetry + transport (.85) | Hybrid (.80) |
|---|---|---|---|
| HTTP retry | Must implement | `AsyncTenacityTransport` built-in | Use PydanticAI transport |
| Tool retry | Full control in `call_tool` | Per-tool `retries` param + `ModelRetry` | PydanticAI for LLM-aware, custom for infra |
| Error classification | Must implement | Not provided | Must implement (both need it) |
| Escalation to user | Must wire AskUser | Not provided | Must wire AskUser |
| Complexity | High (~300 LOC) | Low (~50 LOC config) | Medium (~150 LOC) |
| KISS score | Low | High | Medium |
| Stack alignment | Partial (tenacity is there) | Full (PydanticAI + tenacity) | Full |

### 3.4 Error Journal

A lightweight append-only JSONL log capturing every error and its resolution:

```json
{"ts": "...", "error_type": "transient", "tool": "run_command", "exc": "TimeoutError",
 "action": "retry", "attempt": 2, "resolved": true, "session_id": "..."}
```

- Location: `{workspace}/.owlbear/error_journal.jsonl`
- Query tool: `query_error_journal(tool_name?, error_type?, last_n?)` for agents to learn from past failures
- Rotation: cap at 10K entries, rotate on overflow

### 3.5 Structured Error Feedback to Agent

Instead of `f"Error: {exc}"`, return a typed dict the LLM can reason about:

```python
{
    "status": "error",
    "error_type": "transient",  # from classification
    "tool_name": "run_command",
    "message": "Process timed out after 30s",
    "attempts": 3,
    "max_attempts": 3,
    "suggestion": "Try a shorter command or increase timeout",
    "can_retry": False,
    "escalate": True,
}
```

This replaces bare error strings in delegation.py and toolsets.

## 4. Recommendation (.85 confidence)

**Hybrid approach:** Lean on PydanticAI's built-in mechanisms where they exist, add
thin custom layers for what's missing.

1. **L1 — HTTP transport retry:** Use PydanticAI's `AsyncTenacityTransport` with
   `RetryConfig` in `create_copilot_client()`. ~20 LOC. Handles 429, 502, 503, 504
   with exponential backoff + `wait_retry_after`.

2. **L2 — Tool-level retry in HookedToolset:** Wrap `super().call_tool()` in a
   tenacity `@retry` decorator keyed on transient errors. Classify exceptions before
   retrying. ~60 LOC in `tools/hooked.py`.

3. **L3 — Model self-correction:** Use PydanticAI's per-tool `retries` parameter
   on tools that can benefit from LLM re-attempts (e.g., file operations, search).
   Raise `ModelRetry("hint")` from tools when the error is semantic. ~10 LOC per tool.

4. **L4 — Agent turn retry in daemon:** Replace the bare except in `run_daemon()`
   with classified error handling: transient → retry with backoff (max 3),
   auth → refresh + retry (max 1), permanent → escalate. ~40 LOC.

5. **L5 — Human escalation:** After retries exhausted, invoke `ask_user` with
   structured error context and options: [retry / skip / abort]. Wire through
   ON_ERROR hook. ~50 LOC.

6. **Error classification:** `classify_error()` function in `core/errors.py`. ~30 LOC.

7. **Error journal:** JSONL append logger + query tool in `memory/error_journal.py`. ~80 LOC.

8. **Structured error feedback:** `ToolError` dataclass returned to agent instead of
   bare strings. ~20 LOC in `core/errors.py`.

**Total estimate:** ~310 LOC across 4–5 files. No new dependencies (tenacity already present).

**Risks:**

- Over-retrying can amplify costs (mitigate: strict `max_attempts`, `UsageLimits`)
- Retry in HookedToolset may conflict with PydanticAI's own retry (mitigate: only
  retry transient infra errors at L2; let PydanticAI handle semantic retries at L3)
- Error journal grows unbounded (mitigate: 10K entry cap with rotation)

## 5. Follow-up Tasks

1. **Error classification module** — `core/errors.py` with `ErrorCategory` enum and `classify_error()` function
2. **HTTP transport retry** — Wire `AsyncTenacityTransport` into `create_copilot_client()`
3. **Tool-level retry in HookedToolset** — Retry transient errors with exponential backoff
4. **Daemon loop structured recovery** — Replace bare except with classified error handling
5. **Human escalation wiring** — ON_ERROR hook → AskUser with structured context
6. **Error journal** — JSONL logger + query tool for agent learning
7. **Structured error feedback** — `ToolError` dataclass replacing bare error strings
8. **Unit tests for all recovery paths** — retry, fallback, escalation, classification
