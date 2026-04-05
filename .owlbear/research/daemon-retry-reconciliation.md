# Daemon Retry Reconciliation — Eliminating Multiplicative Retries

> **Owning task:** #512 — Reconcile daemon retry with tool-level HookedToolset retry
> **Date:** 2026-03-06  **Status:** Complete

## 1. Context and Question

OwlBear has three independent retry layers that can compound multiplicatively on transient errors. Finding R-3 from `docs/resilience-audit.md` identifies that a single transient tool error triggers up to 3 (daemon) x 3 (HookedToolset) = 9 attempts. The question: which layer should own retry for each error type?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| AWS Builders' Library — Timeouts, retries, and backoff with jitter | <https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/> | .95 |
| Microsoft Azure — Retry Pattern | <https://learn.microsoft.com/en-us/azure/architecture/patterns/retry> | .90 |
| tenacity docs | <https://tenacity.readthedocs.io/en/latest/> | .70 |
| OwlBear resilience audit | `docs/resilience-audit.md` (R-1 through R-5) | 1.0 |

## 3. Analysis — Current Retry Layers

### Layer inventory

| Layer | Location | Triggers on | Config | Scope |
|-------|----------|-------------|--------|-------|
| L1: HTTP transport | `providers/copilot.py` `_build_retry_transport()` | `HTTPStatusError` (429/502/503/504), `ConnectError`, `TimeoutException` | 3 attempts, exp 1s×2^n, max 30s, `Retry-After` | Single HTTP request |
| L2: Tool-level | `tools/hooked.py` `_call_with_retry()` | `classify_error() == TRANSIENT` | 3 attempts, exp 0.5s base, max 10s (tenacity) | Single tool invocation |
| L3: Daemon loop | `daemon.py` `_recover_from_error()` | `classify_error() == TRANSIENT` | 3 retries, exp 1s×2^n, max 30s, manual jitter | Entire `agent.turn()` call |

### Multiplicative failure cascade

When a tool makes an HTTP call to Copilot that returns 503:

```
L1 retries HTTP 3x  →  fails  →  raises HTTPStatusError
L2 catches TRANSIENT, retries tool 3x  →  each triggers L1 (3x)  →  9 HTTP attempts
L3 catches TRANSIENT, retries agent.turn() 3x  →  each triggers L2  →  27 HTTP attempts total
```

With auth or non-HTTP transient errors (e.g. `ConnectionError` in a tool):

```
L2 retries tool 3x  →  fails  →  raises to agent.turn()
L3 retries agent.turn() 3x  →  each triggers L2 (3x)  →  9 tool attempts
```

### Trade-off: where to retry

| Criterion | Retry at L2 (tool) | Retry at L3 (daemon) | Both (status quo) |
|-----------|-------------------|---------------------|-------------------|
| Attempt count | 3 | 3 | 9+ (multiplicative) |
| Wasted work | Minimal — retries one tool | High — reruns full LLM turn | Highest |
| Latency on failure | ~10s max | ~30s max | ~90s+ |
| Cost efficiency | Good — no redundant LLM calls | Poor — burns tokens re-running turn | Worst |
| Error specificity | High — retry targets the failed tool | Low — retries everything including tools that succeeded | Lowest |
| Handles non-tool transient errors | No — only tool calls | Yes — covers LLM API errors | Yes |

### External guidance

**AWS Builders' Library** (source 1): *"If each layer retries independently, the load on the [dependency] will increase 243x... our best practice is to retry at a single point in the stack."*

**Azure Retry Pattern** (source 2): *"If a task that contains a retry policy invokes another task that also contains a retry policy, this extra layer of retries can add long delays... configure the lower-level task to fail fast and report the reason for the failure back to the task that invoked it."*

Both sources agree: **one retry owner per error type, at the most appropriate layer**.

## 4. Recommendation (.90 confidence)

### Proposed ownership model

| Error type | Retry owner | Action | Why this layer |
|------------|-------------|--------|---------------|
| HTTP transport (429/502/503/504, connect, timeout) | L1: `copilot.py` transport | Keep as-is (3 attempts, Retry-After) | Closest to problem, knows Retry-After header |
| Transient tool errors | L2: `HookedToolset` | Keep as-is (3 attempts, tenacity) | Atomic retry of the failed tool, no wasted LLM work |
| Transient non-tool errors (LLM API failure) | L1: transport | Already covered by transport retry | Transport catches all Copilot HTTP errors |
| AUTH (401/403) | L3: `daemon.py` | Keep token-refresh-then-retry-once | Only daemon has settings/token-refresh access |
| PERMANENT | L3: `daemon.py` | Log + escalate (no retry) | No change needed |
| TOOL_SEMANTIC | PydanticAI `ModelRetry` | No change | Model self-corrects |

### Key change: remove TRANSIENT retry from daemon

Delete the `if category is ErrorCategory.TRANSIENT` branch in `_recover_from_error()`. Replace with: log the error, journal it, send user-facing message. The L1 + L2 layers already exhausted retries before the error reached the daemon.

**Risk:** If a transient error occurs *outside* a tool call (e.g. in `agent.turn()` itself before/after tool dispatch), there's no retry. **Mitigation:** L1 transport already retries all Copilot HTTP errors. The only scenario where this matters is a transient error in PydanticAI's agent machinery itself — which is not an HTTP/network error and shouldn't be retried anyway.

### Additional fix: daemon.py hand-rolled backoff → standard pattern

The daemon currently hand-rolls exponential backoff with `asyncio.sleep` instead of using tenacity. If any daemon-level retry remains (AUTH), it should use tenacity for consistency. However, the AUTH retry is a single attempt (retry-once after token refresh) — simple enough that tenacity is overkill. Keep it as manual retry-once.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Remove TRANSIENT retry from daemon _recover_from_error" --priority needed --tags "resilience,scope:core,phase-7" --body "Delete the TRANSIENT branch in daemon.py _recover_from_error(). Replace with: log + journal + send error to user. L1 (transport) and L2 (HookedToolset) already retry transient errors. Keeping this branch causes 3x3=9 multiplicative attempts per AWS/Azure best practice on single-layer retry. See docs/research/daemon-retry-reconciliation.md. AC: (1) TRANSIENT errors in _recover_from_error log and escalate, no retry loop. (2) _TRANSIENT_MAX_RETRIES, _TRANSIENT_BACKOFF_BASE, _TRANSIENT_BACKOFF_MAX, _JITTER_FACTOR constants removed. (3) Existing tests updated. (4) No multiplicative retry on transient tool errors."
```

```
kanban\kanban-md.exe create "Add daemon-level tests verifying single-layer retry" --priority important --tags "test,resilience,scope:core,phase-7" --body "Write integration tests proving that a transient tool error is retried exactly 3 times (by HookedToolset), not 9 times. Mock a tool that raises ConnectError, assert call count == 3 after agent.turn() completes. See docs/research/daemon-retry-reconciliation.md. AC: (1) Test proves max 3 attempts for transient tool error. (2) Test proves AUTH errors still refresh token + retry once."
```

```
kanban\kanban-md.exe create "Update python.instructions.md retry convention to match reality" --priority nice-to-have --tags "docs,resilience" --body "R-5 from resilience audit: instructions say 'max 5 attempts' but all code uses 3. Update python.instructions.md to document actual retry policy: 3 attempts at transport and tool layers. Reference docs/research/daemon-retry-reconciliation.md. AC: (1) python.instructions.md retry section matches code. (2) No conflicting retry guidance."
```
