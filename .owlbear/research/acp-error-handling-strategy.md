# ACP Error Handling Strategy

> **Owning task:** #47 — Document ACP error handling strategy
> **Date:** 2026-03-26 **Status:** Complete

## 1. Context and Question

The v2 orchestrator spawns `copilot --acp --stdio` as a subprocess and communicates
via JSON-RPC 2.0 over stdin/stdout (NDJSON). Task #1 documented the protocol; this
task documents the **error handling strategy** the orchestrator must implement:
process crash detection, JSON parse errors, timeout strategy, and cancellation flow.

ACP itself has no built-in timeout or reconnection mechanism (Sources 1, 4, 6).
The client is responsible for all resilience.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | JSON-RPC 2.0 specification | <https://www.jsonrpc.org/specification> | .95 |
| 2 | ACP Python SDK `exceptions.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/src/acp/exceptions.py> | .95 |
| 3 | ACP Python SDK `examples/gemini.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/gemini.py> | .90 |
| 4 | ACP Python SDK `examples/client.py` | <https://github.com/agentclientprotocol/python-sdk/blob/main/examples/client.py> | .85 |
| 5 | mcp-copilot-acp (TypeScript bridge) | <https://github.com/bsmi021/mcp-copilot-acp> | .80 |
| 6 | ACP specification (architecture) | <https://agentclientprotocol.com/get-started/architecture> | .85 |
| 7 | OwlBear ACP protocol research | `docs/research/acp-protocol.md` §3.6 | .95 |
| 8 | OwlBear v1 error infrastructure | `v1/src/owlbear/core/errors.py`, `daemon.py` | .90 |

## 3. Analysis

### 3.1 JSON-RPC 2.0 Error Codes (Standard + ACP-Specific)

| Code | Name | Trigger | Classification | Recovery |
|------|------|---------|----------------|----------|
| -32700 | Parse error | Malformed JSON on the wire | PERMANENT | Log + respawn agent process |
| -32600 | Invalid Request | JSON valid but not a valid RPC object | PERMANENT | Log; likely SDK bug |
| -32601 | Method not found | Client called unsupported method | PERMANENT | Do not retry; fix call site |
| -32602 | Invalid params | Wrong parameters for method | PERMANENT | Do not retry; fix call site |
| -32603 | Internal error | Agent internal failure | TRANSIENT | Retry once; respawn if repeated |
| -32000 | Auth required | Copilot CLI not authenticated | AUTH | Run `copilot auth`; re-initialize |
| -32002 | Resource not found | Session/file not found | TOOL_SEMANTIC | Re-create session if stale |

The SDK's `RequestError` class (Source 2) provides factory methods for all seven
codes. The orchestrator catches `RequestError` and classifies by `err.code`.

### 3.2 Process Crash Detection

ACP runs over subprocess stdio. Crash detection uses two mechanisms (Sources 3, 4, 5):

| Signal | Detection | Source |
|--------|-----------|--------|
| `proc.returncode is not None` | Process has exited | Python `asyncio.subprocess` |
| `proc.stdout` EOF / `BrokenPipeError` on `proc.stdin` | Pipe broken mid-communication | asyncio stream read returns empty |
| Exit code != 0 | Abnormal termination | `proc.returncode` after `proc.wait()` |

**Strategy (from gemini.py, Source 3):**

1. After each `conn.prompt()` / `conn.initialize()`, check `proc.returncode`
2. On pipe break or unexpected EOF, attempt graceful shutdown (`conn.close()`)
3. `proc.terminate()` with 5s `wait_for` timeout, then `proc.kill()` (Source 3)
4. Re-spawn and re-initialize for the next prompt

**Restart limits (from mcp-copilot-acp, Source 5):** max 3 automatic restarts
(`COPILOT_MAX_RESTARTS`), then escalate to user. Prevents infinite restart loops
on persistent crashes (e.g., bad install, missing auth).

### 3.3 Timeout Strategy

ACP has no protocol-level timeout (Sources 1, 6). The client must implement:

| Timeout | Value | Rationale | Source |
|---------|-------|-----------|--------|
| Prompt response | 300s (5 min) | LLM responses can be long; mcp-copilot-acp default | Source 5 |
| Initialize | 30s | Handshake should be fast; process startup overhead | gemini.py pattern |
| Session create | 15s | Lightweight RPC, no LLM involved | gemini.py pattern |
| Shutdown grace | 5s | `terminate()` then `kill()` after timeout | Source 3 |

**Implementation:** Wrap each `conn.{method}()` call in `asyncio.wait_for(coro, timeout=T)`.
On `asyncio.TimeoutError`: classify as TRANSIENT for prompt (LLM may be slow),
PERMANENT for initialize/session (indicates a stuck process).

### 3.4 Cancellation Flow

Cancellation uses the `session/cancel` notification (Source 7):

```
Client ─── session/cancel(session_id) ──────► Agent
Client ◄── PromptResponse(stopReason="cancelled") ── Agent
```

**Key semantics:**

- `session/cancel` is a JSON-RPC **notification** (no response expected)
- The agent responds to the original `session/prompt` with `stopReason: "cancelled"`
- If the agent ignores `session/cancel`, the prompt timeout (§3.3) is the backstop
- Stop reasons: `end_turn`, `max_tokens`, `max_turn_requests`, `refusal`, `cancelled`

**Integration with OwlBear cancellation:** Wire `CancelSignal.is_set()` checks
before each prompt. If cancelled mid-prompt, send `conn.cancel(session_id)` and
await the `PromptResponse` (with prompt timeout as backstop).

### 3.5 Error Classification Mapping

Map ACP errors to OwlBear's existing `ErrorCategory` (Source 8):

| ACP Scenario | ErrorCategory | Recovery Action |
|-------------|---------------|-----------------|
| `RequestError` code -32700 (parse) | PERMANENT | Log, respawn process |
| `RequestError` code -32601 (method) | PERMANENT | Log, do not retry |
| `RequestError` code -32603 (internal) | TRANSIENT | Retry once, then respawn |
| `RequestError` code -32000 (auth) | AUTH | Re-auth, re-initialize |
| `RequestError` code -32002 (resource) | TOOL_SEMANTIC | Re-create session |
| `asyncio.TimeoutError` on prompt | TRANSIENT | Cancel + retry once |
| `asyncio.TimeoutError` on init | PERMANENT | Respawn process |
| `BrokenPipeError` / EOF | TRANSIENT | Respawn + retry |
| Process exit (returncode != 0) | TRANSIENT | Respawn (up to max restarts) |
| Process exit after max restarts | PERMANENT | Escalate to user |

### 3.6 Recommended Error Handling Architecture

```
                ┌─────────── Orchestrator ───────────┐
                │                                     │
  CancelSignal ─┤  ┌── ProcessSupervisor ──────────┐  │
                │  │  spawn / respawn / kill        │  │
                │  │  restart counter (max 3)       │  │
                │  └───────────┬───────────────────┘  │
                │              │                       │
                │  ┌── AcpClient (conn wrapper) ────┐  │
                │  │  timeout per method             │  │
                │  │  classify RequestError.code     │  │
                │  │  detect pipe break / EOF        │  │
                │  └───────────┬───────────────────┘  │
                │              │                       │
                │  ┌── ErrorClassifier ─────────────┐  │
                │  │  map ACP → ErrorCategory        │  │
                │  │  feed ErrorJournal               │  │
                │  └────────────────────────────────┘  │
                └─────────────────────────────────────┘
```

Three components: `ProcessSupervisor` (owns subprocess lifecycle + restart budget),
`AcpClient` (wraps SDK connection with timeouts + error detection), and the existing
`classify_error` extended with ACP-specific error types.

## 4. Recommendation (.85 confidence)

Implement ACP error handling as a thin layer on top of the existing v1 error
infrastructure. Three new components (~200 LOC total):

1. **`ProcessSupervisor`** (~80 LOC) — spawn/respawn/kill with restart budget (max 3),
   5s graceful shutdown, process health checks. Pattern from mcp-copilot-acp (Source 5)
   and gemini.py (Source 3).

2. **`AcpClient` wrapper** (~80 LOC) — wraps `ClientSideConnection` methods with
   `asyncio.wait_for` timeouts per §3.3 table. Catches `RequestError`, `BrokenPipeError`,
   and `asyncio.TimeoutError`. Sends `session/cancel` on timeout or external cancel.

3. **Extend `classify_error`** (~40 LOC) — add `RequestError` isinstance branch that
   maps error codes per §3.5 table. No new dependencies.

**Risk:** ACP SDK is v0.9.0 (pre-1.0) — error types may change. **Mitigation:** pin
SDK version; the `RequestError.code` integer interface is stable (JSON-RPC standard).

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement ProcessSupervisor for ACP subprocess lifecycle" --priority needed --status ideation --tags "phase-1,scope:orchestrator,type:build" --body "## Objective\nManage Copilot CLI subprocess lifecycle: spawn, health check, graceful shutdown, respawn with restart budget.\n\n## AC\n- [ ] Spawns copilot --acp --stdio subprocess with stdin/stdout PIPE\n- [ ] Detects process exit via returncode and pipe EOF\n- [ ] Graceful shutdown: terminate with 5s wait, then kill\n- [ ] Restart budget: max 3 auto-restarts, then raises permanent error\n- [ ] Restart counter resets on successful prompt completion\n- [ ] async context manager for clean lifecycle\n\nSee docs/research/acp-error-handling-strategy.md SS3.2, SS3.6."

kanban\kanban-md.exe create "Implement AcpClient wrapper with timeouts and error classification" --priority needed --status ideation --tags "phase-1,scope:orchestrator,type:build" --body "## Objective\nWrap ACP SDK ClientSideConnection with per-method timeouts and error classification.\n\n## AC\n- [ ] Wraps initialize (30s), new_session (15s), prompt (300s) with asyncio.wait_for\n- [ ] Catches RequestError and classifies by code per acp-error-handling-strategy.md SS3.5\n- [ ] Sends session/cancel on timeout or external CancelSignal\n- [ ] Detects BrokenPipeError and EOF as TRANSIENT (trigger respawn)\n- [ ] Logs errors to ErrorJournal when available\n\nDepends on: ProcessSupervisor task. See docs/research/acp-error-handling-strategy.md SS3.3, SS3.4."

kanban\kanban-md.exe create "Extend classify_error for ACP RequestError codes" --priority needed --status ideation --tags "phase-1,scope:orchestrator,type:build" --body "## Objective\nAdd ACP-specific error classification to the error module.\n\n## AC\n- [ ] classify_error handles RequestError with code-based mapping per SS3.5 table\n- [ ] -32700/-32601/-32602: PERMANENT\n- [ ] -32603: TRANSIENT\n- [ ] -32000: AUTH\n- [ ] -32002: TOOL_SEMANTIC\n- [ ] BrokenPipeError classified as TRANSIENT\n- [ ] Unit tests for all ACP error code mappings\n\nSee docs/research/acp-error-handling-strategy.md SS3.1, SS3.5."
```
