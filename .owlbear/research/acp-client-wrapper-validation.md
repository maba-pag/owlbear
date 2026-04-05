# AcpClient Wrapper Validation

> **Owning task:** #59 — Implement AcpClient wrapper with timeouts and error classification
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #59 defines an `AcpClient` wrapper around the ACP SDK's `ClientSideConnection`
with per-method timeouts (30s/15s/300s), JSON-RPC error classification, and
cancellation. Due to pipeline ordering, both implementation and tests were pre-built
during the #94 test task lifecycle. This research validates the approach, verifies
source alignment, and flags gaps for the architect.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | ACP Python SDK `exceptions.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/exceptions.py> | .95 |
| 2 | ACP Python SDK `client/connection.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/client/connection.py> | .95 |
| 3 | ACP Python SDK `examples/gemini.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/gemini.py> | .90 |
| 4 | mcp-copilot-acp (TypeScript bridge) | <https://github.com/bsmi021/mcp-copilot-acp> | .80 |
| 5 | OwlBear error handling strategy | `docs/research/acp-error-handling-strategy.md` §3.3–3.5 | .95 |
| 6 | JSON-RPC 2.0 specification | <https://www.jsonrpc.org/specification> | .95 |
| 7 | ACP SDK `utils.py` (`@param_model`) | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/utils.py> | .85 |

## 3. Analysis

### 3.1 Approach Validation

The thin-wrapper pattern is confirmed by two independent implementations:

| Criterion | gemini.py (Source 3) | mcp-copilot-acp (Source 4) | #59 wrapper |
|-----------|---------------------|---------------------------|-------------|
| Timeout mechanism | implicit (no wrapper) | `COPILOT_TIMEOUT_MS=300000` | `asyncio.wait_for` per-method |
| Error handling | catch `RequestError` per-call | process-manager restart | `AcpClientError` with category |
| Cancel flow | `conn.cancel(session_id)` | N/A | `conn.cancel` on timeout/signal |
| Shutdown | terminate/5s wait/kill | max restarts + escalate | deferred to ProcessSupervisor |

Neither reference implements per-method timeout differentiation — that is OwlBear's
improvement over prior art. The 30s/15s/300s split follows the rationale in Source 5
§3.3: handshake/session ops should be fast; LLM prompts need minutes.

### 3.2 Error Code Mapping Verification

All 7 `RequestError` factory methods (Source 1) map correctly to `_ACP_ERROR_CODES`:

| Code | SDK factory | Wrapper ErrorCategory | Correct? |
|------|------------|-----------------------|----------|
| -32700 | `parse_error()` | PERMANENT | Yes (Source 6: parse errors are protocol-level) |
| -32600 | `invalid_request()` | PERMANENT | Yes |
| -32601 | `method_not_found()` | PERMANENT | Yes |
| -32602 | `invalid_params()` | PERMANENT | Yes |
| -32603 | `internal_error()` | TRANSIENT | Yes (Source 5 §3.1: retry once) |
| -32000 | `auth_required()` | AUTH | Yes (Source 5 §3.5) |
| -32002 | `resource_not_found()` | TOOL_SEMANTIC | Yes (Source 5 §3.5) |

Unknown codes default to PERMANENT — conservative and correct.

### 3.3 Critical Gap: Wrapper API Signature Mismatch

The SDK's `@param_model` decorator is a no-op marker (Source 7), so the underlying
Python signatures enforce required parameters at runtime:

| Wrapper method | Params forwarded | SDK required params | Missing |
|---------------|-----------------|---------------------|---------|
| `initialize()` | none | `protocol_version: int` | `protocol_version` |
| `new_session()` | none | `cwd: str` | `cwd`, `mcp_servers` |
| `prompt(session_id)` | `session_id` | `prompt: list[...], session_id` | `prompt` content |

All three core methods would raise `TypeError` at runtime. Tests don't catch this
because they patch `asyncio.wait_for`, bypassing the actual SDK call entirely.

**Impact:** The wrapper compiles and tests pass, but cannot be used in production.
**Fix:** Forward required params via `*args, **kwargs` or explicit parameter lists.

### 3.4 ErrorJournal AC Line

AC states "Logs errors to ErrorJournal when available." ErrorJournal is a v1 component
not yet ported to v2. The "when available" phrasing makes this conditional — the
current no-op is valid. A separate integration task should wire this when ErrorJournal
exists in v2.

### 3.5 CancelSignal Protocol

The `_CancelSignal` Protocol (duck-typed `is_set() -> bool`) is the correct approach:
it decouples from any specific cancellation implementation. The v1 `CancelSignal`
class (Source 5 §3.4) and Python's `threading.Event` both satisfy this protocol
without import coupling.

### 3.6 Pre-Built Status

Implementation (`acp_client.py`, 121 LOC) and tests (`test_acp_client.py`, 13 tests)
were committed during task #94. All tests pass. Coverage: 92% on `acp_client.py`.
The task can fast-track through the pipeline once the API signature gap (§3.3) is
addressed.

## 4. Recommendation (.85 confidence)

Advance to `backlog` with two refinements for the architect:

1. **Fix wrapper API surface** (blocking) — Forward required SDK params in
   `initialize()`, `new_session()`, `prompt()`. Estimated ~20 LOC change.
   Add integration-level tests that call through to the real (mocked) SDK signatures.
2. **Defer ErrorJournal** (non-blocking) — Keep AC line as conditional. Create a
   separate task to wire ErrorJournal integration when v2 error infrastructure exists.

Risk: ACP SDK pre-1.0 (v0.9.0) — parameter names may change. Mitigated by version
pin `>=0.9.0,<1.0.0` (already in pyproject.toml).

## 5. Follow-up Tasks

See task body for `kanban-md create` commands executed at `ideation`.
